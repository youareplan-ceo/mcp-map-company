#!/usr/bin/env python3
"""
CI/CD 리포트 API 테스트
CI/CD Report API Tests

이 파일은 mcp/ci_report_api.py의 FastAPI 엔드포인트들을 테스트합니다.
Tests the FastAPI endpoints in mcp/ci_report_api.py.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, MagicMock
import sys

# mcp 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from mcp.ci_report_api import router
    from mcp.run import app
except ImportError:
    pytest.skip("ci_report_api 모듈을 찾을 수 없습니다", allow_module_level=True)


class TestCIReportAPI:
    """CI 리포트 API 테스트 클래스"""

    @pytest.fixture
    def client(self):
        """FastAPI 테스트 클라이언트"""
        return TestClient(app)

    @pytest.fixture
    def temp_reports_dir(self):
        """임시 CI 리포트 디렉토리 생성"""
        with tempfile.TemporaryDirectory() as temp_dir:
            reports_dir = Path(temp_dir) / "reports" / "ci_reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            yield reports_dir

    @pytest.fixture
    def sample_success_report(self):
        """테스트용 성공 CI 리포트 데이터"""
        return {
            "id": "build-123",
            "date": "2025-01-15",
            "timestamp": "2025-01-15T10:30:00Z",
            "status": "success",
            "execution_time": 245,
            "test_results": {
                "total": 156,
                "passed": 156,
                "failed": 0,
                "skipped": 2
            },
            "coverage": {
                "percentage": 85.7,
                "lines_covered": 2145,
                "lines_total": 2504
            },
            "build_info": {
                "branch": "main",
                "commit": "a1b2c3d",
                "trigger": "push",
                "environment": "production"
            },
            "stages": [
                {
                    "name": "테스트",
                    "status": "success",
                    "duration": 120,
                    "start_time": "2025-01-15T10:30:00Z",
                    "end_time": "2025-01-15T10:32:00Z"
                },
                {
                    "name": "빌드",
                    "status": "success",
                    "duration": 85,
                    "start_time": "2025-01-15T10:32:00Z",
                    "end_time": "2025-01-15T10:33:25Z"
                }
            ],
            "artifacts": {
                "build_size": "12.3MB",
                "logs_url": "/logs/build-123.log"
            }
        }

    @pytest.fixture
    def sample_failed_report(self):
        """테스트용 실패 CI 리포트 데이터"""
        return {
            "id": "build-122",
            "date": "2025-01-14",
            "timestamp": "2025-01-14T15:45:00Z",
            "status": "failed",
            "execution_time": 189,
            "test_results": {
                "total": 154,
                "passed": 142,
                "failed": 12,
                "skipped": 0
            },
            "coverage": {
                "percentage": 82.1,
                "lines_covered": 2056,
                "lines_total": 2504
            },
            "build_info": {
                "branch": "feature/user-auth",
                "commit": "x9y8z7w",
                "trigger": "pull_request",
                "environment": "staging"
            },
            "stages": [
                {
                    "name": "테스트",
                    "status": "failed",
                    "duration": 189,
                    "start_time": "2025-01-14T15:45:00Z",
                    "end_time": "2025-01-14T15:48:09Z",
                    "error": "12개의 테스트 실패"
                }
            ],
            "failed_tests": [
                {
                    "name": "test_user_login_invalid_credentials",
                    "error": "AssertionError: Expected 401, got 500",
                    "file": "tests/test_auth.py",
                    "line": 45
                },
                {
                    "name": "test_password_validation",
                    "error": "ValidationError: Password too weak",
                    "file": "tests/test_auth.py",
                    "line": 67
                }
            ],
            "artifacts": {
                "logs_url": "/logs/build-122.log"
            }
        }

    def create_test_report_files(self, reports_dir: Path, reports_data: list):
        """테스트용 CI 리포트 파일들 생성"""
        created_files = []

        for report_data in reports_data:
            file_name = f"{report_data['date']}-{report_data['id']}.json"
            file_path = reports_dir / file_name

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            created_files.append(file_path)

        return created_files

    def test_get_ci_reports_empty(self, client, temp_reports_dir):
        """CI 리포트 목록 조회 테스트 (빈 디렉토리)"""
        with patch('mcp.ci_report_api.REPORTS_DIR', temp_reports_dir):
            response = client.get("/api/v1/ci/reports")

            assert response.status_code == 200
            data = response.json()
            assert data == []

    def test_get_ci_reports_with_data(self, client, temp_reports_dir, sample_success_report, sample_failed_report):
        """CI 리포트 목록 조회 테스트 (데이터 있음)"""
        # 테스트 파일 생성
        reports_data = [sample_success_report, sample_failed_report]
        self.create_test_report_files(temp_reports_dir, reports_data)

        with patch('mcp.ci_report_api.REPORTS_DIR', temp_reports_dir):
            response = client.get("/api/v1/ci/reports")

            assert response.status_code == 200
            data = response.json()

            assert len(data) == 2
            assert data[0]["id"] in ["build-123", "build-122"]
            assert "file_name" in data[0]

    def test_get_ci_reports_with_status_filter(self, client, temp_reports_dir, sample_success_report, sample_failed_report):
        """CI 리포트 목록 조회 테스트 (상태 필터)"""
        # 테스트 파일 생성
        reports_data = [sample_success_report, sample_failed_report]
        self.create_test_report_files(temp_reports_dir, reports_data)

        with patch('mcp.ci_report_api.REPORTS_DIR', temp_reports_dir):
            # 성공 리포트만 조회
            response = client.get("/api/v1/ci/reports?status=success")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["status"] == "success"

            # 실패 리포트만 조회
            response = client.get("/api/v1/ci/reports?status=failed")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["status"] == "failed"

    def test_get_ci_reports_with_limit(self, client, temp_reports_dir, sample_success_report):
        """CI 리포트 목록 조회 테스트 (개수 제한)"""
        # 여러 리포트 생성
        reports_data = []
        for i in range(5):
            report = sample_success_report.copy()
            report["id"] = f"build-{120 + i}"
            report["date"] = f"2025-01-{10 + i}"
            reports_data.append(report)

        self.create_test_report_files(temp_reports_dir, reports_data)

        with patch('mcp.ci_report_api.REPORTS_DIR', temp_reports_dir):
            response = client.get("/api/v1/ci/reports?limit=3")

            assert response.status_code == 200
            data = response.json()
            assert len(data) <= 3

    def test_get_latest_ci_report_not_found(self, client, temp_reports_dir):
        """최신 CI 리포트 조회 테스트 (파일 없음)"""
        with patch('mcp.ci_report_api.REPORTS_DIR', temp_reports_dir):
            response = client.get("/api/v1/ci/reports/latest")

            assert response.status_code == 404
            assert "CI 리포트를 찾을 수 없습니다" in response.json()["detail"]

    def test_get_latest_ci_report_success(self, client, temp_reports_dir, sample_success_report):
        """최신 CI 리포트 조회 테스트 (성공)"""
        # 테스트 파일 생성
        self.create_test_report_files(temp_reports_dir, [sample_success_report])

        with patch('mcp.ci_report_api.REPORTS_DIR', temp_reports_dir):
            response = client.get("/api/v1/ci/reports/latest")

            assert response.status_code == 200
            data = response.json()

            assert data["id"] == "build-123"
            assert data["status"] == "success"
            assert "file_name" in data

    def test_get_failed_ci_reports(self, client, temp_reports_dir, sample_failed_report):
        """실패한 CI 리포트 조회 테스트"""
        # 실패 리포트 생성 (최근 날짜로)
        recent_failed = sample_failed_report.copy()
        recent_failed["timestamp"] = datetime.now().isoformat() + "Z"
        recent_failed["date"] = datetime.now().strftime("%Y-%m-%d")

        self.create_test_report_files(temp_reports_dir, [recent_failed])

        with patch('mcp.ci_report_api.REPORTS_DIR', temp_reports_dir):
            response = client.get("/api/v1/ci/reports/failed?days=7")

            assert response.status_code == 200
            data = response.json()

            assert len(data) == 1
            assert data[0]["status"] == "failed"

    def test_get_ci_performance_stats_no_data(self, client, temp_reports_dir):
        """CI 성능 통계 조회 테스트 (데이터 없음)"""
        with patch('mcp.ci_report_api.REPORTS_DIR', temp_reports_dir):
            response = client.get("/api/v1/ci/stats")

            assert response.status_code == 200
            data = response.json()

            assert data["total_builds"] == 0
            assert data["success_rate"] == 0
            assert data["failure_rate"] == 0

    def test_get_ci_performance_stats_with_data(self, client, temp_reports_dir, sample_success_report, sample_failed_report):
        """CI 성능 통계 조회 테스트 (데이터 있음)"""
        # 최근 날짜로 리포트 생성
        recent_success = sample_success_report.copy()
        recent_success["timestamp"] = datetime.now().isoformat() + "Z"
        recent_success["date"] = datetime.now().strftime("%Y-%m-%d")

        recent_failed = sample_failed_report.copy()
        recent_failed["timestamp"] = (datetime.now() - timedelta(days=1)).isoformat() + "Z"
        recent_failed["date"] = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        self.create_test_report_files(temp_reports_dir, [recent_success, recent_failed])

        with patch('mcp.ci_report_api.REPORTS_DIR', temp_reports_dir):
            response = client.get("/api/v1/ci/stats?days=30")

            assert response.status_code == 200
            data = response.json()

            assert data["total_builds"] == 2
            assert data["successful_builds"] == 1
            assert data["failed_builds"] == 1
            assert data["success_rate"] == 50.0
            assert data["failure_rate"] == 50.0
            assert data["period_days"] == 30

    def test_get_failed_tests_summary(self, client, temp_reports_dir, sample_failed_report):
        """실패한 테스트 요약 조회 테스트"""
        # 최근 실패 리포트 생성
        recent_failed = sample_failed_report.copy()
        recent_failed["timestamp"] = datetime.now().isoformat() + "Z"
        recent_failed["date"] = datetime.now().strftime("%Y-%m-%d")

        self.create_test_report_files(temp_reports_dir, [recent_failed])

        with patch('mcp.ci_report_api.REPORTS_DIR', temp_reports_dir):
            response = client.get("/api/v1/ci/failed-tests?days=7")

            assert response.status_code == 200
            data = response.json()

            assert len(data) == 2  # 2개의 실패한 테스트
            assert data[0]["name"] in ["test_user_login_invalid_credentials", "test_password_validation"]
            assert data[0]["count"] == 1
            assert "latest_error" in data[0]

    def test_get_ci_report_by_id_not_found(self, client, temp_reports_dir):
        """특정 CI 리포트 조회 테스트 (ID 없음)"""
        with patch('mcp.ci_report_api.REPORTS_DIR', temp_reports_dir):
            response = client.get("/api/v1/ci/reports/nonexistent-id")

            assert response.status_code == 404
            assert "리포트 ID 'nonexistent-id'를 찾을 수 없습니다" in response.json()["detail"]

    def test_get_ci_report_by_id_success(self, client, temp_reports_dir, sample_success_report):
        """특정 CI 리포트 조회 테스트 (성공)"""
        self.create_test_report_files(temp_reports_dir, [sample_success_report])

        with patch('mcp.ci_report_api.REPORTS_DIR', temp_reports_dir):
            response = client.get("/api/v1/ci/reports/build-123")

            assert response.status_code == 200
            data = response.json()

            assert data["id"] == "build-123"
            assert data["status"] == "success"

    def test_get_ci_report_markdown_not_found(self, client, temp_reports_dir):
        """CI 리포트 마크다운 조회 테스트 (ID 없음)"""
        with patch('mcp.ci_report_api.REPORTS_DIR', temp_reports_dir):
            response = client.get("/api/v1/ci/reports/nonexistent-id/markdown")

            assert response.status_code == 404
            assert "리포트 ID 'nonexistent-id'를 찾을 수 없습니다" in response.json()["detail"]

    def test_get_ci_report_markdown_success(self, client, temp_reports_dir, sample_success_report):
        """CI 리포트 마크다운 조회 테스트 (성공)"""
        self.create_test_report_files(temp_reports_dir, [sample_success_report])

        with patch('mcp.ci_report_api.REPORTS_DIR', temp_reports_dir):
            response = client.get("/api/v1/ci/reports/build-123/markdown")

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/markdown; charset=utf-8"
            assert "CI/CD 빌드 리포트" in response.text
            assert "build-123" in response.text

    def test_get_ci_api_health(self, client, temp_reports_dir, sample_success_report):
        """CI API 상태 확인 테스트"""
        # 테스트 리포트 생성
        self.create_test_report_files(temp_reports_dir, [sample_success_report])

        with patch('mcp.ci_report_api.REPORTS_DIR', temp_reports_dir):
            response = client.get("/api/v1/ci/health")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "healthy"
            assert "timestamp" in data
            assert data["message"] == "CI 리포트 API가 정상 작동 중입니다"
            assert data["details"]["reports_directory_exists"] is True
            assert data["details"]["total_reports"] == 1
            assert data["details"]["latest_report_id"] == "build-123"

    def test_validation_errors(self, client):
        """유효성 검사 오류 테스트"""
        # 잘못된 limit 파라미터
        response = client.get("/api/v1/ci/reports?limit=0")
        assert response.status_code == 422

        response = client.get("/api/v1/ci/reports?limit=200")
        assert response.status_code == 422

        # 잘못된 days 파라미터
        response = client.get("/api/v1/ci/stats?days=0")
        assert response.status_code == 422

        response = client.get("/api/v1/ci/stats?days=400")
        assert response.status_code == 422


class TestCIReportAPIIntegration:
    """CI 리포트 API 통합 테스트 클래스"""

    @pytest.fixture
    def client(self):
        """FastAPI 테스트 클라이언트"""
        return TestClient(app)

    @pytest.mark.integration
    def test_api_endpoints_accessibility(self, client):
        """모든 CI 리포트 API 엔드포인트 접근성 테스트"""
        # 기본 리포트 목록 엔드포인트
        response = client.get("/api/v1/ci/reports")
        assert response.status_code == 200

        # 실패 리포트 엔드포인트
        response = client.get("/api/v1/ci/reports/failed")
        assert response.status_code == 200

        # 성능 통계 엔드포인트
        response = client.get("/api/v1/ci/stats")
        assert response.status_code == 200

        # 실패 테스트 요약 엔드포인트
        response = client.get("/api/v1/ci/failed-tests")
        assert response.status_code == 200

        # 헬스체크 엔드포인트
        response = client.get("/api/v1/ci/health")
        assert response.status_code == 200

    @pytest.mark.integration
    def test_api_response_format_consistency(self, client):
        """API 응답 형식 일관성 테스트"""
        # 모든 성공 응답이 JSON 형식인지 확인
        endpoints = [
            "/api/v1/ci/reports",
            "/api/v1/ci/reports/failed",
            "/api/v1/ci/stats",
            "/api/v1/ci/failed-tests",
            "/api/v1/ci/health"
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"

            # JSON 파싱 가능한지 확인
            data = response.json()
            assert isinstance(data, (dict, list))

    @pytest.mark.integration
    def test_error_handling_consistency(self, client):
        """오류 처리 일관성 테스트"""
        # 존재하지 않는 리포트 조회 시도
        response = client.get("/api/v1/ci/reports/nonexistent-id")
        assert response.status_code == 404

        error_data = response.json()
        assert "detail" in error_data
        assert isinstance(error_data["detail"], str)

        # 존재하지 않는 리포트 마크다운 조회
        response = client.get("/api/v1/ci/reports/nonexistent-id/markdown")
        assert response.status_code == 404

        # 최신 리포트 조회 (리포트 없음)
        response = client.get("/api/v1/ci/reports/latest")
        assert response.status_code == 404

    @pytest.mark.integration
    def test_parameter_validation_consistency(self, client):
        """파라미터 유효성 검사 일관성 테스트"""
        # limit 파라미터 유효성 검사
        response = client.get("/api/v1/ci/reports?limit=-1")
        assert response.status_code == 422

        response = client.get("/api/v1/ci/reports?limit=101")
        assert response.status_code == 422

        # days 파라미터 유효성 검사
        response = client.get("/api/v1/ci/stats?days=0")
        assert response.status_code == 422

        response = client.get("/api/v1/ci/stats?days=366")
        assert response.status_code == 422

        response = client.get("/api/v1/ci/failed-tests?days=0")
        assert response.status_code == 422

        response = client.get("/api/v1/ci/failed-tests?days=91")
        assert response.status_code == 422


if __name__ == "__main__":
    # 개별 테스트 실행을 위한 메인 함수
    import asyncio

    async def run_basic_tests():
        """기본 API 테스트 실행"""
        print("🧪 CI 리포트 API 기본 테스트 시작...")

        # 간단한 클라이언트 테스트
        try:
            client = TestClient(app)

            # 기본 엔드포인트 테스트
            response = client.get("/api/v1/ci/reports")
            print(f"✅ CI 리포트 목록 API 테스트: {response.status_code}")

            response = client.get("/api/v1/ci/stats")
            print(f"✅ CI 성능 통계 API 테스트: {response.status_code}")

            response = client.get("/api/v1/ci/health")
            print(f"✅ CI API 헬스체크 테스트: {response.status_code}")

        except Exception as e:
            print(f"❌ API 테스트 실패: {e}")

        print("🧪 CI 리포트 API 기본 테스트 완료")

    # 비동기 테스트 실행
    asyncio.run(run_basic_tests())