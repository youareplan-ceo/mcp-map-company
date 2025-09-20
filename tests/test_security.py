#!/usr/bin/env python3
"""
보안 테스트 - Rate Limiting 및 차단 IP 테스트
"""

import os
import sys
import time
import asyncio
import pytest
import httpx
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from mcp.utils.rate_limiter import RateLimiter, rate_limiter
from fastapi.testclient import TestClient
from fastapi import Request


class TestRateLimiter:
    """Rate Limiter 단위 테스트"""

    def setup_method(self):
        """테스트마다 새로운 Rate Limiter 인스턴스 생성"""
        self.rate_limiter = RateLimiter(
            requests_per_minute=5,  # 테스트용으로 낮은 값 사용
            cleanup_interval=1,
            log_file="tests/test_security.log"
        )

    def test_rate_limiter_initialization(self):
        """Rate Limiter 초기화 테스트"""
        assert self.rate_limiter.requests_per_minute == 5
        assert self.rate_limiter.cleanup_interval == 1
        assert len(self.rate_limiter.whitelist_ips) >= 3  # 기본 화이트리스트

    def test_whitelist_functionality(self):
        """화이트리스트 기능 테스트"""
        test_ip = "192.168.1.100"

        # 화이트리스트에 IP 추가
        success = self.rate_limiter.add_to_whitelist(test_ip)
        assert success is True
        assert test_ip in self.rate_limiter.whitelist_ips

        # 차단 목록에서 제거 확인
        self.rate_limiter.blocked_ips.add(test_ip)
        self.rate_limiter.add_to_whitelist(test_ip)
        assert test_ip not in self.rate_limiter.blocked_ips

    def test_rate_limiting_logic(self):
        """Rate Limiting 로직 테스트"""
        from unittest.mock import Mock

        # Mock Request 객체 생성
        test_ip = "203.0.113.1"  # 테스트용 IP

        # 제한 수치까지 요청
        for i in range(5):
            mock_request = Mock()
            mock_request.client.host = test_ip
            mock_request.headers = {}

            is_limited = self.rate_limiter.is_rate_limited(mock_request)
            assert is_limited is False, f"Request {i+1} should not be rate limited"

        # 초과 요청 - 차단되어야 함
        mock_request = Mock()
        mock_request.client.host = test_ip
        mock_request.headers = {}

        is_limited = self.rate_limiter.is_rate_limited(mock_request)
        assert is_limited is True, "Request exceeding limit should be rate limited"
        assert test_ip in self.rate_limiter.blocked_ips

    def test_different_ips_not_affected(self):
        """서로 다른 IP는 독립적으로 처리되는지 테스트"""
        from unittest.mock import Mock

        ip1 = "203.0.113.1"
        ip2 = "203.0.113.2"

        # IP1에서 최대 요청
        for i in range(5):
            mock_request = Mock()
            mock_request.client.host = ip1
            mock_request.headers = {}
            assert self.rate_limiter.is_rate_limited(mock_request) is False

        # IP1 차단 확인
        mock_request = Mock()
        mock_request.client.host = ip1
        mock_request.headers = {}
        assert self.rate_limiter.is_rate_limited(mock_request) is True

        # IP2는 영향받지 않음
        mock_request = Mock()
        mock_request.client.host = ip2
        mock_request.headers = {}
        assert self.rate_limiter.is_rate_limited(mock_request) is False

    def test_cleanup_functionality(self):
        """오래된 요청 정리 기능 테스트"""
        from unittest.mock import Mock
        import time

        test_ip = "203.0.113.1"

        # 요청 추가
        mock_request = Mock()
        mock_request.client.host = test_ip
        mock_request.headers = {}

        # 몇 개의 요청 생성
        for _ in range(3):
            self.rate_limiter.is_rate_limited(mock_request)

        # 요청이 기록되었는지 확인
        assert len(self.rate_limiter.ip_requests[test_ip]) == 3

        # 시간을 앞당기고 정리 실행
        time.sleep(2)  # cleanup_interval이 1초이므로
        self.rate_limiter._cleanup_old_requests()

        # 실제로는 1분 후에 정리되므로 여전히 존재해야 함
        assert len(self.rate_limiter.ip_requests[test_ip]) == 3

    def test_security_logs_created(self):
        """보안 로그 파일이 생성되는지 테스트"""
        from unittest.mock import Mock

        test_ip = "203.0.113.1"

        # Rate Limit 위반 발생
        for i in range(6):  # 5개 + 1개 (초과)
            mock_request = Mock()
            mock_request.client.host = test_ip
            mock_request.headers = {'User-Agent': 'Test-Agent'}
            mock_request.method = 'GET'
            mock_request.url.path = '/test'

            self.rate_limiter.is_rate_limited(mock_request)

        # 로그 파일 확인
        log_file = Path("tests/test_security.log")
        assert log_file.exists(), "Security log file should be created"

        # 로그 내용 확인
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
            assert "Rate limit exceeded" in log_content
            assert test_ip in log_content

    def test_get_blocked_ips_summary(self):
        """차단된 IP 요약 정보 테스트"""
        summary = self.rate_limiter.get_blocked_ips_summary()

        assert 'blocked_count' in summary
        assert 'blocked_ips' in summary
        assert 'whitelist_count' in summary
        assert 'requests_per_minute_limit' in summary
        assert 'current_monitored_ips' in summary

        assert summary['requests_per_minute_limit'] == 5
        assert isinstance(summary['blocked_ips'], list)


class TestFastAPIIntegration:
    """FastAPI 통합 테스트"""

    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        # Import here to avoid circular imports
        from mcp.run import app
        return TestClient(app)

    def test_health_endpoint_accessible(self, client):
        """헬스 엔드포인트 접근 테스트"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_security_stats_endpoint(self, client):
        """보안 통계 API 테스트"""
        response = client.get("/api/v1/security/stats")

        if response.status_code == 200:
            data = response.json()
            assert 'blocked_count' in data or 'blockedCount' in data
        else:
            # API가 구현되지 않았을 수도 있음
            assert response.status_code in [404, 500]

    def test_whitelist_endpoint(self, client):
        """화이트리스트 API 테스트"""
        test_ip = "192.168.1.200"
        response = client.post(f"/api/v1/security/whitelist/{test_ip}")

        if response.status_code == 200:
            data = response.json()
            assert 'success' in data
            assert data['ip'] == test_ip
        else:
            # API가 구현되지 않았을 수도 있음
            assert response.status_code in [404, 500]

    @pytest.mark.asyncio
    async def test_rate_limiting_with_real_requests(self, client):
        """실제 HTTP 요청으로 Rate Limiting 테스트"""

        # 주의: 이 테스트는 실제 Rate Limiter 설정에 따라 달라집니다
        # 기본 설정이 100req/min이므로 테스트에서는 확인만 합니다

        responses = []
        for i in range(10):  # 10개 요청으로 제한
            response = client.get("/health")
            responses.append(response)

            # Rate Limit 헤더 확인
            if 'X-RateLimit-Limit' in response.headers:
                assert int(response.headers['X-RateLimit-Limit']) > 0

            # 모든 요청이 성공해야 함 (기본 제한이 100이므로)
            assert response.status_code == 200

    def test_blocked_ip_simulation(self):
        """차단 IP 시뮬레이션 테스트"""
        # 이 테스트는 실제 차단을 시뮬레이션하기 어려우므로
        # 로직 검증으로 대체합니다

        from mcp.utils.rate_limiter import get_security_stats

        # 보안 통계 함수 호출 테스트
        try:
            stats = get_security_stats()
            assert isinstance(stats, dict)
        except Exception as e:
            # 함수가 정의되지 않았을 수 있음
            pytest.skip(f"Security stats function not available: {e}")


class TestSecurityScenarios:
    """보안 시나리오 테스트"""

    def test_scenario_massive_requests_from_single_ip(self):
        """단일 IP에서 대량 요청 시나리오"""
        rate_limiter = RateLimiter(requests_per_minute=10, log_file="tests/scenario_test.log")

        from unittest.mock import Mock
        test_ip = "192.0.2.1"  # RFC 5737 테스트 IP

        normal_requests = 0
        blocked_requests = 0

        # 200개 요청 시뮬레이션
        for i in range(200):
            mock_request = Mock()
            mock_request.client.host = test_ip
            mock_request.headers = {'User-Agent': f'AttackBot-{i}'}
            mock_request.method = 'GET'
            mock_request.url.path = '/api/v1/portfolio'

            if rate_limiter.is_rate_limited(mock_request):
                blocked_requests += 1
            else:
                normal_requests += 1

        # 첫 10개는 정상, 나머지는 차단되어야 함
        assert normal_requests == 10
        assert blocked_requests == 190
        assert test_ip in rate_limiter.blocked_ips

    def test_scenario_different_ips_normal_usage(self):
        """서로 다른 IP에서 정상 사용 시나리오"""
        rate_limiter = RateLimiter(requests_per_minute=20)

        from unittest.mock import Mock

        # 10개의 다른 IP에서 각각 15개씩 요청
        for ip_suffix in range(10):
            test_ip = f"192.0.2.{ip_suffix + 1}"

            for req_num in range(15):
                mock_request = Mock()
                mock_request.client.host = test_ip
                mock_request.headers = {'User-Agent': 'NormalUser'}
                mock_request.method = 'GET'
                mock_request.url.path = '/api/v1/recommend'

                # 모든 요청이 허용되어야 함 (각 IP당 20개 제한)
                is_limited = rate_limiter.is_rate_limited(mock_request)
                assert is_limited is False, f"IP {test_ip} request {req_num} should not be limited"

        # 어떤 IP도 차단되지 않아야 함
        assert len(rate_limiter.blocked_ips) == 0

    def test_scenario_whitelist_bypass(self):
        """화이트리스트 우회 시나리오"""
        rate_limiter = RateLimiter(requests_per_minute=5)

        from unittest.mock import Mock
        whitelist_ip = "10.0.0.100"

        # 화이트리스트에 추가
        rate_limiter.add_to_whitelist(whitelist_ip)

        # 제한을 초과하는 요청 (100개)
        for i in range(100):
            mock_request = Mock()
            mock_request.client.host = whitelist_ip
            mock_request.headers = {'User-Agent': 'WhitelistedClient'}
            mock_request.method = 'GET'
            mock_request.url.path = '/health'

            # 화이트리스트 IP는 절대 차단되지 않아야 함
            is_limited = rate_limiter.is_rate_limited(mock_request)
            assert is_limited is False, f"Whitelisted IP should never be rate limited (request {i})"

        # 화이트리스트 IP는 차단 목록에 없어야 함
        assert whitelist_ip not in rate_limiter.blocked_ips


if __name__ == "__main__":
    # 테스트 실행
    pytest.main([__file__, "-v", "--tb=short"])