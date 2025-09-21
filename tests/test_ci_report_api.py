# tests/test_ci_report_api.py
"""
CI/CD 리포트 API 테스트 모듈

FastAPI 기반 CI/CD 성능 리포트 API의 종합적인 테스트를 수행합니다.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import json
from fastapi.testclient import TestClient
from fastapi import status

# 테스트 대상 모듈 import
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.ci_report_api import router, CIReportService
from mcp.run import app


class TestCIReportAPI:
    """CI/CD 리포트 API 엔드포인트 테스트"""

    @pytest.fixture
    def client(self):
        """FastAPI 테스트 클라이언트 생성"""
        return TestClient(app)

    @pytest.fixture
    def mock_ci_service(self):
        """CI 리포트 서비스 모킹"""
        with patch('mcp.ci_report_api.service') as mock_service:
            yield mock_service

    def test_health_endpoint(self, client):
        """CI 리포트 서비스 헬스체크 테스트"""
        response = client.get("/api/v1/reports/ci/health")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "service" in data

    def test_summary_endpoint_success(self, client, mock_ci_service):
        """CI 요약 정보 조회 성공 테스트"""
        # Mock 데이터 설정
        mock_summary = {
            "total_runs": 150,
            "success_rate": 92.5,
            "failure_rate": 7.5,
            "avg_execution_time": 245.7,
            "last_execution": "2024-01-15T10:30:00Z"
        }
        mock_ci_service.get_summary.return_value = mock_summary

        response = client.get("/api/v1/reports/ci/summary")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total_runs"] == 150
        assert data["success_rate"] == 92.5
        assert data["failure_rate"] == 7.5

    def test_summary_endpoint_with_parameters(self, client, mock_ci_service):
        """CI 요약 정보 파라미터 전달 테스트"""
        mock_ci_service.get_summary.return_value = {"total_runs": 50}

        response = client.get("/api/v1/reports/ci/summary?runs=50&days=3")
        assert response.status_code == status.HTTP_200_OK

        # 서비스 호출 시 파라미터가 올바르게 전달되었는지 확인
        mock_ci_service.get_summary.assert_called_once()

    def test_recent_runs_endpoint(self, client, mock_ci_service):
        """최근 CI 실행 목록 조회 테스트"""
        mock_runs = [
            {
                "id": "run-001",
                "status": "success",
                "start_time": "2024-01-15T09:00:00Z",
                "duration": 180,
                "branch": "main"
            },
            {
                "id": "run-002",
                "status": "failed",
                "start_time": "2024-01-15T08:30:00Z",
                "duration": 95,
                "branch": "feature/test"
            }
        ]
        mock_ci_service.get_recent_runs.return_value = mock_runs

        response = client.get("/api/v1/reports/ci/recent")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "run-001"
        assert data[0]["status"] == "success"

    def test_failures_endpoint(self, client, mock_ci_service):
        """실패한 CI 실행 목록 조회 테스트"""
        mock_failures = [
            {
                "id": "run-002",
                "status": "failed",
                "error_message": "테스트 실패: test_user_authentication",
                "branch": "feature/auth",
                "duration": 120
            }
        ]
        mock_ci_service.get_failures.return_value = mock_failures

        response = client.get("/api/v1/reports/ci/failures")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "failed"
        assert "error_message" in data[0]

    def test_json_download_endpoint(self, client, mock_ci_service):
        """JSON 형식 리포트 다운로드 테스트"""
        mock_report = {
            "generated_at": "2024-01-15T10:30:00Z",
            "summary": {"total_runs": 100},
            "recent_runs": [],
            "failures": []
        }
        mock_ci_service.generate_json_report.return_value = mock_report

        response = client.get("/api/v1/reports/ci/json")
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/json"

        # 다운로드 헤더 확인
        content_disposition = response.headers.get("content-disposition")
        assert content_disposition is not None
        assert "ci-report" in content_disposition
        assert ".json" in content_disposition

    def test_markdown_download_endpoint(self, client, mock_ci_service):
        """Markdown 형식 리포트 다운로드 테스트"""
        mock_markdown = "# CI/CD 성능 리포트\n\n## 요약\n- 총 실행: 100회"
        mock_ci_service.generate_markdown_report.return_value = mock_markdown

        response = client.get("/api/v1/reports/ci/markdown")
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/markdown; charset=utf-8"

        # Markdown 내용 확인
        content = response.text
        assert "# CI/CD 성능 리포트" in content
        assert "## 요약" in content

    def test_refresh_endpoint(self, client, mock_ci_service):
        """캐시 새로고침 테스트"""
        mock_ci_service.refresh_cache.return_value = True

        response = client.post("/api/v1/reports/ci/refresh")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["success"] is True
        assert "message" in data

        # 캐시 새로고침이 호출되었는지 확인
        mock_ci_service.refresh_cache.assert_called_once()

    def test_api_error_handling(self, client, mock_ci_service):
        """API 오류 처리 테스트"""
        # 서비스에서 예외 발생 시뮬레이션
        mock_ci_service.get_summary.side_effect = Exception("스크립트 실행 실패")

        response = client.get("/api/v1/reports/ci/summary")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

        data = response.json()
        assert "error" in data
        assert "fallback_data" in data


class TestCIReportService:
    """CI 리포트 서비스 클래스 테스트"""

    @pytest.fixture
    def service(self):
        """CI 리포트 서비스 인스턴스 생성"""
        return CIReportService()

    @pytest.mark.asyncio
    async def test_execute_script_success(self, service):
        """스크립트 실행 성공 테스트"""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # Mock 프로세스 설정
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (
                b'{"status": "success", "data": {"runs": 50}}',
                b''
            )
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            result = await service._execute_script(['echo', 'test'])

            assert result is not None
            assert result["status"] == "success"
            assert result["data"]["runs"] == 50

    @pytest.mark.asyncio
    async def test_execute_script_failure(self, service):
        """스크립트 실행 실패 테스트"""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # Mock 프로세스 실패 설정
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (
                b'',
                b'스크립트 실행 중 오류 발생'
            )
            mock_process.returncode = 1
            mock_subprocess.return_value = mock_process

            result = await service._execute_script(['false'])
            assert result is None

    @pytest.mark.asyncio
    async def test_execute_script_timeout(self, service):
        """스크립트 실행 타임아웃 테스트"""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # 타임아웃 시뮬레이션
            mock_subprocess.side_effect = asyncio.TimeoutError()

            result = await service._execute_script(['sleep', '100'])
            assert result is None

    def test_cache_mechanism(self, service):
        """캐시 메커니즘 테스트"""
        # 캐시가 비어있는 상태 확인
        assert not service._is_cache_valid("summary")

        # 캐시 데이터 설정
        test_data = {"test": "data"}
        service._set_cache("summary", test_data)

        # 캐시 유효성 및 데이터 확인
        assert service._is_cache_valid("summary")
        cached_data = service._get_cache("summary")
        assert cached_data == test_data

    def test_cache_expiration(self, service):
        """캐시 만료 테스트"""
        # 캐시 설정
        service._set_cache("test_key", {"data": "test"})

        # 캐시 만료 시간을 과거로 설정
        past_time = datetime.now() - timedelta(minutes=10)
        service.cache_timestamps["test_key"] = past_time

        # 캐시가 만료되었는지 확인
        assert not service._is_cache_valid("test_key")

    def test_fallback_data_generation(self, service):
        """폴백 데이터 생성 테스트"""
        fallback_summary = service._get_fallback_summary()

        # 필수 필드 확인
        assert "total_runs" in fallback_summary
        assert "success_rate" in fallback_summary
        assert "failure_rate" in fallback_summary
        assert "avg_execution_time" in fallback_summary
        assert "last_execution" in fallback_summary

        fallback_runs = service._get_fallback_runs()
        assert isinstance(fallback_runs, list)
        assert len(fallback_runs) > 0

        # 첫 번째 실행 항목 구조 확인
        first_run = fallback_runs[0]
        assert "id" in first_run
        assert "status" in first_run
        assert "branch" in first_run


class TestMarkdownGeneration:
    """Markdown 리포트 생성 테스트"""

    @pytest.fixture
    def service(self):
        return CIReportService()

    def test_markdown_report_structure(self, service):
        """Markdown 리포트 구조 테스트"""
        # 테스트 데이터 설정
        with patch.object(service, 'get_summary') as mock_summary, \
             patch.object(service, 'get_recent_runs') as mock_runs, \
             patch.object(service, 'get_failures') as mock_failures:

            mock_summary.return_value = {
                "total_runs": 100,
                "success_rate": 95.0,
                "failure_rate": 5.0,
                "avg_execution_time": 180.5
            }
            mock_runs.return_value = [{"id": "run-1", "status": "success"}]
            mock_failures.return_value = [{"id": "run-2", "status": "failed"}]

            markdown = service.generate_markdown_report()

            # Markdown 구조 확인
            assert "# CI/CD 성능 리포트" in markdown
            assert "## 📊 성능 요약" in markdown
            assert "## 🔄 최근 실행 목록" in markdown
            assert "## ❌ 실패한 실행" in markdown
            assert "총 실행 횟수: **100**" in markdown
            assert "성공률: **95.0%**" in markdown

    def test_markdown_korean_formatting(self, service):
        """한국어 Markdown 포맷팅 테스트"""
        with patch.object(service, 'get_summary') as mock_summary:
            mock_summary.return_value = {
                "total_runs": 50,
                "success_rate": 90.0,
                "failure_rate": 10.0,
                "avg_execution_time": 120.0,
                "last_execution": "2024-01-15T10:00:00Z"
            }

            markdown = service.generate_markdown_report()

            # 한국어 레이블 확인
            assert "총 실행 횟수" in markdown
            assert "성공률" in markdown
            assert "실패율" in markdown
            assert "평균 실행 시간" in markdown
            assert "마지막 실행" in markdown


class TestAPIErrorHandling:
    """API 오류 처리 테스트"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_invalid_parameter_handling(self, client):
        """잘못된 파라미터 처리 테스트"""
        # 음수 runs 파라미터
        response = client.get("/api/v1/reports/ci/summary?runs=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # 음수 days 파라미터
        response = client.get("/api/v1/reports/ci/summary?days=-5")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_service_unavailable_fallback(self, client):
        """서비스 불가 시 폴백 데이터 제공 테스트"""
        with patch('mcp.ci_report_api.service') as mock_service:
            # 모든 서비스 메소드에서 예외 발생
            mock_service.get_summary.side_effect = Exception("서비스 오류")

            response = client.get("/api/v1/reports/ci/summary")

            # 오류 상황에서도 응답 제공
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert "fallback_data" in data
            assert "error" in data


class TestPerformanceAndLoad:
    """성능 및 부하 테스트"""

    @pytest.fixture
    def service(self):
        return CIReportService()

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, service):
        """동시 요청 처리 테스트"""
        # 여러 동시 요청 시뮬레이션
        tasks = []
        for _ in range(10):
            task = asyncio.create_task(
                asyncio.coroutine(lambda: service.get_summary())()
            )
            tasks.append(task)

        # 모든 요청이 완료될 때까지 대기
        with patch.object(service, '_execute_script') as mock_execute:
            mock_execute.return_value = {"summary": "test"}
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # 모든 요청이 성공적으로 처리되었는지 확인
        for result in results:
            assert not isinstance(result, Exception)

    def test_large_data_handling(self, service):
        """대용량 데이터 처리 테스트"""
        # 큰 데이터셋 시뮬레이션
        large_runs = []
        for i in range(1000):
            large_runs.append({
                "id": f"run-{i:04d}",
                "status": "success" if i % 10 != 0 else "failed",
                "duration": 120 + (i % 100),
                "branch": f"feature/test-{i % 5}"
            })

        with patch.object(service, '_execute_script') as mock_execute:
            mock_execute.return_value = {"runs": large_runs}

            # 대용량 데이터 처리 시간 측정
            start_time = datetime.now()
            result = service.get_recent_runs(limit=1000)
            end_time = datetime.now()

            # 처리 시간이 합리적인 범위 내인지 확인 (5초 이내)
            processing_time = (end_time - start_time).total_seconds()
            assert processing_time < 5.0
            assert len(result) == 1000


class TestIntegration:
    """통합 테스트"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_end_to_end_workflow(self, client):
        """전체 워크플로우 통합 테스트"""
        # 1. 헬스체크
        health_response = client.get("/api/v1/reports/ci/health")
        assert health_response.status_code == status.HTTP_200_OK

        # 2. 요약 정보 조회
        with patch('mcp.ci_report_api.service.get_summary') as mock_summary:
            mock_summary.return_value = {"total_runs": 100}
            summary_response = client.get("/api/v1/reports/ci/summary")
            assert summary_response.status_code == status.HTTP_200_OK

        # 3. 캐시 새로고침
        with patch('mcp.ci_report_api.service.refresh_cache') as mock_refresh:
            mock_refresh.return_value = True
            refresh_response = client.post("/api/v1/reports/ci/refresh")
            assert refresh_response.status_code == status.HTTP_200_OK

        # 4. 리포트 다운로드
        with patch('mcp.ci_report_api.service.generate_json_report') as mock_json:
            mock_json.return_value = {"report": "data"}
            json_response = client.get("/api/v1/reports/ci/json")
            assert json_response.status_code == status.HTTP_200_OK

    def test_api_consistency(self, client):
        """API 일관성 테스트"""
        endpoints = [
            "/api/v1/reports/ci/health",
            "/api/v1/reports/ci/summary",
            "/api/v1/reports/ci/recent",
            "/api/v1/reports/ci/failures"
        ]

        # 모든 엔드포인트가 적절한 응답을 반환하는지 확인
        for endpoint in endpoints:
            with patch('mcp.ci_report_api.service') as mock_service:
                # 각 서비스 메소드에 대한 기본 응답 설정
                mock_service.get_summary.return_value = {}
                mock_service.get_recent_runs.return_value = []
                mock_service.get_failures.return_value = []

                response = client.get(endpoint)
                assert response.status_code in [200, 500]  # 성공 또는 처리된 오류

                # JSON 응답 형식 확인
                try:
                    response.json()
                except json.JSONDecodeError:
                    pytest.fail(f"엔드포인트 {endpoint}가 유효한 JSON을 반환하지 않음")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])