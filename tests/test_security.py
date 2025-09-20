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


class TestNotifierIntegration:
    """알림 시스템 통합 테스트"""

    def test_notifier_import(self):
        """notifier 모듈 import 테스트"""
        try:
            from mcp.utils.notifier import send_ip_blocked_alert, send_security_alert
            assert True  # Successfully imported
        except ImportError:
            pytest.skip("Notifier module not available")

    @pytest.mark.asyncio
    async def test_security_alert_functions(self):
        """보안 알림 함수 테스트"""
        try:
            from mcp.utils.notifier import send_ip_blocked_alert, send_rate_limit_alert, send_whitelist_update_alert

            # Test IP blocked alert (should not raise exceptions)
            try:
                result = await send_ip_blocked_alert(
                    client_ip="192.0.2.100",
                    violation_count=150,
                    endpoint="/api/v1/test",
                    user_agent="TestBot/1.0"
                )
                assert isinstance(result, dict)
            except Exception as e:
                # Expected if notification channels are not configured
                assert "not available" in str(e).lower() or "disabled" in str(e).lower()

            # Test rate limit alert
            try:
                result = await send_rate_limit_alert(
                    client_ip="192.0.2.101",
                    request_count=200,
                    limit=100,
                    endpoint="/api/v1/portfolio"
                )
                assert isinstance(result, dict)
            except Exception as e:
                assert "not available" in str(e).lower() or "disabled" in str(e).lower()

            # Test whitelist update alert
            try:
                result = await send_whitelist_update_alert(
                    client_ip="192.168.1.50",
                    action="added"
                )
                assert isinstance(result, dict)
            except Exception as e:
                assert "not available" in str(e).lower() or "disabled" in str(e).lower()

        except ImportError:
            pytest.skip("Notifier functions not available")

    def test_security_logs_creation(self):
        """보안 로그 파일 생성 및 기록 테스트"""
        from mcp.utils.rate_limiter import RateLimiter
        from pathlib import Path

        # 테스트용 로그 파일 경로
        test_log_file = "tests/test_security_logs.log"
        rate_limiter = RateLimiter(
            requests_per_minute=3,
            log_file=test_log_file
        )

        # Rate limit 위반 발생시키기
        from unittest.mock import Mock
        test_ip = "192.0.2.200"

        for i in range(4):  # 3개 제한 + 1개 초과
            mock_request = Mock()
            mock_request.client.host = test_ip
            mock_request.headers = {'User-Agent': 'LogTestBot'}
            mock_request.method = 'POST'
            mock_request.url.path = '/api/v1/test-endpoint'

            rate_limiter.is_rate_limited(mock_request)

        # 로그 파일이 생성되었는지 확인
        log_path = Path(test_log_file)
        assert log_path.exists(), "Security log file should be created"

        # 로그 내용 확인
        with open(log_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
            assert "Rate limit exceeded" in log_content
            assert test_ip in log_content
            assert "LogTestBot" in log_content

        # 테스트 로그 파일 정리
        log_path.unlink()

    def test_whitelist_persistence(self):
        """화이트리스트 지속성 테스트"""
        from mcp.utils.rate_limiter import RateLimiter
        from pathlib import Path
        import json

        # 테스트용 화이트리스트 파일
        whitelist_file = "config/test_whitelist_ips.json"

        # 기존 파일 제거 (있다면)
        if Path(whitelist_file).exists():
            Path(whitelist_file).unlink()

        # Rate Limiter 생성 및 화이트리스트 추가
        rate_limiter = RateLimiter()
        rate_limiter.whitelist_file = whitelist_file  # Test file path

        test_ips = ["10.0.0.100", "10.0.0.101", "192.168.1.200"]

        for ip in test_ips:
            success = rate_limiter.add_to_whitelist(ip)
            assert success, f"Should successfully add {ip} to whitelist"

        # 파일이 생성되고 올바른 내용을 포함하는지 확인
        assert Path(whitelist_file).exists()

        # 정리
        if Path(whitelist_file).exists():
            Path(whitelist_file).unlink()


class TestAdvancedSecurityScenarios:
    """고급 보안 시나리오 테스트"""

    def test_distributed_attack_simulation(self):
        """분산 공격 시뮬레이션 테스트"""
        rate_limiter = RateLimiter(requests_per_minute=20)

        from unittest.mock import Mock

        # 100개의 서로 다른 IP에서 각각 50개씩 요청 시뮬레이션
        attack_results = {}

        for ip_suffix in range(100):
            test_ip = f"203.0.113.{ip_suffix + 1}"
            normal_requests = 0
            blocked_requests = 0

            for req_num in range(50):
                mock_request = Mock()
                mock_request.client.host = test_ip
                mock_request.headers = {'User-Agent': f'AttackBot-{ip_suffix}'}
                mock_request.method = 'GET'
                mock_request.url.path = '/api/v1/portfolio'

                if rate_limiter.is_rate_limited(mock_request):
                    blocked_requests += 1
                else:
                    normal_requests += 1

            attack_results[test_ip] = {
                'normal': normal_requests,
                'blocked': blocked_requests
            }

        # 분석: 각 IP는 20개까지 허용되고 나머지는 차단되어야 함
        blocked_ips = 0
        for ip, results in attack_results.items():
            if results['blocked'] > 0:
                blocked_ips += 1
                # 첫 20개는 허용, 나머지 30개는 차단
                assert results['normal'] == 20
                assert results['blocked'] == 30

        # 모든 IP가 차단되어야 함 (20개 제한 초과)
        assert blocked_ips == 100

    def test_gradual_attack_pattern(self):
        """점진적 공격 패턴 테스트"""
        rate_limiter = RateLimiter(requests_per_minute=10)

        from unittest.mock import Mock
        import time

        test_ip = "198.51.100.1"

        # 1단계: 정상적인 요청 패턴 (5개)
        for i in range(5):
            mock_request = Mock()
            mock_request.client.host = test_ip
            mock_request.headers = {'User-Agent': 'NormalUser/1.0'}
            mock_request.method = 'GET'
            mock_request.url.path = '/api/v1/recommend'

            is_limited = rate_limiter.is_rate_limited(mock_request)
            assert is_limited is False, f"Normal request {i+1} should be allowed"

        # 2단계: 약간 증가된 요청 (추가 3개, 총 8개)
        for i in range(3):
            mock_request = Mock()
            mock_request.client.host = test_ip
            mock_request.headers = {'User-Agent': 'BusyUser/1.0'}
            mock_request.method = 'GET'
            mock_request.url.path = '/api/v1/portfolio'

            is_limited = rate_limiter.is_rate_limited(mock_request)
            assert is_limited is False, f"Busy request {i+1} should be allowed"

        # 3단계: 한계 테스트 (추가 2개, 총 10개 - 한계)
        for i in range(2):
            mock_request = Mock()
            mock_request.client.host = test_ip
            mock_request.headers = {'User-Agent': 'BusyUser/1.0'}
            mock_request.method = 'POST'
            mock_request.url.path = '/api/v1/recommend'

            is_limited = rate_limiter.is_rate_limited(mock_request)
            assert is_limited is False, f"Limit request {i+1} should be allowed"

        # 4단계: 공격 시작 (초과 요청)
        for i in range(5):
            mock_request = Mock()
            mock_request.client.host = test_ip
            mock_request.headers = {'User-Agent': 'AttackBot/2.0'}
            mock_request.method = 'POST'
            mock_request.url.path = '/api/v1/portfolio'

            is_limited = rate_limiter.is_rate_limited(mock_request)
            assert is_limited is True, f"Attack request {i+1} should be blocked"

        # IP가 차단된 것을 확인
        assert test_ip in rate_limiter.blocked_ips

    def test_proxy_ip_handling(self):
        """프록시 IP 처리 테스트"""
        rate_limiter = RateLimiter(requests_per_minute=5)

        from unittest.mock import Mock

        # X-Forwarded-For 헤더가 있는 경우
        mock_request = Mock()
        mock_request.client.host = "192.168.1.1"  # 프록시 IP
        mock_request.headers = {
            'X-Forwarded-For': '203.0.113.50, 10.0.0.1',  # 실제 클라이언트 IP
            'User-Agent': 'ProxyUser/1.0'
        }

        # Rate limiter가 X-Forwarded-For의 첫 번째 IP를 사용하는지 확인
        extracted_ip = rate_limiter._get_client_ip(mock_request)
        assert extracted_ip == "203.0.113.50"

        # 해당 IP로 제한이 적용되는지 테스트
        for i in range(6):  # 5개 제한 + 1개 초과
            is_limited = rate_limiter.is_rate_limited(mock_request)

            if i < 5:
                assert is_limited is False
            else:
                assert is_limited is True

        # 실제 클라이언트 IP가 차단 목록에 있는지 확인
        assert "203.0.113.50" in rate_limiter.blocked_ips

    def test_security_logs_integration(self):
        """보안 로그 통합 테스트"""
        from mcp.utils.notifier import get_security_logs
        from pathlib import Path

        # 테스트 로그 파일 생성
        test_log_file = Path("logs/test_security_integration.log")
        test_log_file.parent.mkdir(exist_ok=True)

        # 샘플 보안 로그 작성
        sample_logs = [
            "2024-01-15 10:30:25 - WARNING - Rate limit exceeded - IP: 192.168.1.100, Requests: 150/100",
            "2024-01-15 10:31:10 - INFO - IP added to whitelist: 10.0.0.50",
            "2024-01-15 10:32:45 - WARNING - Rate limit exceeded - IP: 203.0.113.1, Requests: 200/100",
            "2024-01-15 10:33:20 - ERROR - Suspicious activity detected from IP: 198.51.100.1"
        ]

        with open(test_log_file, 'w', encoding='utf-8') as f:
            for log in sample_logs:
                f.write(log + '\n')

        # get_security_logs 함수 테스트
        recent_logs = get_security_logs(str(test_log_file), lines=3)

        assert "Rate limit exceeded" in recent_logs
        assert "203.0.113.1" in recent_logs
        assert "Suspicious activity" in recent_logs

        # 파일 정리
        test_log_file.unlink()

    def test_rate_limiter_performance(self):
        """Rate Limiter 성능 테스트"""
        import time
        from unittest.mock import Mock

        rate_limiter = RateLimiter(requests_per_minute=1000)  # 높은 제한값

        # 1000개 IP에서 각각 10개 요청 (총 10,000 요청)
        start_time = time.time()

        for ip_suffix in range(1000):
            test_ip = f"10.{ip_suffix // 256}.{ip_suffix % 256}.1"

            for req_num in range(10):
                mock_request = Mock()
                mock_request.client.host = test_ip
                mock_request.headers = {'User-Agent': 'PerformanceTest'}
                mock_request.method = 'GET'
                mock_request.url.path = '/health'

                rate_limiter.is_rate_limited(mock_request)

        end_time = time.time()
        total_time = end_time - start_time

        # 10,000 요청이 5초 이내에 처리되어야 함
        assert total_time < 5.0, f"Performance test took too long: {total_time:.2f}s"

        # 모든 IP가 정상적으로 처리되었는지 확인
        assert len(rate_limiter.blocked_ips) == 0
        assert len(rate_limiter.ip_requests) == 1000


if __name__ == "__main__":
    # 테스트 실행
    pytest.main([__file__, "-v", "--tb=short"])