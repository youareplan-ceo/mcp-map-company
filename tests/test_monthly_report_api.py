#!/usr/bin/env python3
"""
월간 운영 리포트 API 테스트
Monthly Operations Report API Tests

이 파일은 mcp/monthly_report_api.py의 FastAPI 엔드포인트들을 테스트합니다.
Tests the FastAPI endpoints in mcp/monthly_report_api.py.
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
    from mcp.monthly_report_api import router
    from mcp.run import app
except ImportError:
    pytest.skip("monthly_report_api 모듈을 찾을 수 없습니다", allow_module_level=True)


class TestMonthlyReportAPI:
    """월간 리포트 API 테스트 클래스"""

    @pytest.fixture
    def client(self):
        """FastAPI 테스트 클라이언트"""
        return TestClient(app)

    @pytest.fixture
    def temp_reports_dir(self):
        """임시 리포트 디렉토리 생성"""
        with tempfile.TemporaryDirectory() as temp_dir:
            reports_dir = Path(temp_dir) / "reports" / "monthly"
            reports_dir.mkdir(parents=True, exist_ok=True)
            yield reports_dir

    @pytest.fixture
    def sample_report_data(self):
        """테스트용 월간 리포트 데이터"""
        return {
            "report_metadata": {
                "period_start": "2024-08-22",
                "period_end": "2024-09-21",
                "generated_at": datetime.now().isoformat(),
                "report_type": "monthly_operations"
            },
            "security_events": {
                "blocked_ips": 245,
                "unique_blocked_ips": 68,
                "rate_limit_violations": 180,
                "whitelist_additions": 12,
                "monitoring_events": 520,
                "total_security_events": 957
            },
            "backup_operations": {
                "successful_backups": 28,
                "failed_backups": 2,
                "cleanup_operations": 8,
                "success_rate_percent": 93,
                "total_backup_operations": 30
            },
            "system_resources": {
                "average_disk_usage_percent": 72,
                "max_disk_usage_percent": 89,
                "security_log_size_bytes": 15728640,
                "backup_directory_size_kb": 5242880
            },
            "performance_score": {
                "security_score": 32,
                "backup_score": 37,
                "system_score": 18,
                "total_score": 87,
                "grade": "우수"
            }
        }

    def create_test_report_files(self, reports_dir: Path, sample_data: dict, dates: list):
        """테스트용 리포트 파일들 생성"""
        created_files = []

        for date in dates:
            # 날짜별로 약간씩 다른 데이터 생성
            data = sample_data.copy()
            data["report_metadata"]["period_end"] = date

            # JSON 파일 생성
            json_file = reports_dir / f"monthly-report-{date}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            created_files.append(json_file)

            # Markdown 파일 생성
            md_file = reports_dir / f"monthly-report-{date}.md"
            md_content = f"""# 월간 운영 리포트 ({date})

## 📈 성과 요약
- 총점: {data['performance_score']['total_score']}/100점
- 등급: {data['performance_score']['grade']}

## 🛡️ 보안 현황
- 차단 IP: {data['security_events']['blocked_ips']}회
- 고유 IP: {data['security_events']['unique_blocked_ips']}개

## 📦 백업 현황
- 성공률: {data['backup_operations']['success_rate_percent']}%
"""
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(md_content)
            created_files.append(md_file)

        return created_files

    def test_get_monthly_reports_summary_empty(self, client, temp_reports_dir):
        """월간 리포트 요약 조회 테스트 (빈 디렉토리)"""
        with patch('mcp.monthly_report_api.REPORTS_DIR', temp_reports_dir):
            response = client.get("/api/v1/reports/monthly/")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "success"
            assert data["reports_count"] == 0
            assert data["latest_reports"] == []
            assert data["latest_performance"] is None

    def test_get_monthly_reports_summary_with_data(self, client, temp_reports_dir, sample_report_data):
        """월간 리포트 요약 조회 테스트 (데이터 있음)"""
        # 테스트 파일 생성
        test_dates = ["2024-09-21", "2024-08-21", "2024-07-21"]
        self.create_test_report_files(temp_reports_dir, sample_report_data, test_dates)

        with patch('mcp.monthly_report_api.REPORTS_DIR', temp_reports_dir):
            response = client.get("/api/v1/reports/monthly/")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "success"
            assert data["reports_count"] == 3
            assert len(data["latest_reports"]) == 3
            assert data["latest_performance"] is not None
            assert data["latest_performance"]["total_score"] == 87
            assert data["latest_performance"]["grade"] == "우수"

    def test_get_latest_monthly_report_not_found(self, client, temp_reports_dir):
        """최신 월간 리포트 조회 테스트 (파일 없음)"""
        with patch('mcp.monthly_report_api.REPORTS_DIR', temp_reports_dir):
            response = client.get("/api/v1/reports/monthly/latest")

            assert response.status_code == 404
            assert "월간 리포트를 찾을 수 없습니다" in response.json()["detail"]

    def test_get_latest_monthly_report_success(self, client, temp_reports_dir, sample_report_data):
        """최신 월간 리포트 조회 테스트 (성공)"""
        # 테스트 파일 생성
        test_dates = ["2024-09-21", "2024-08-21"]
        self.create_test_report_files(temp_reports_dir, sample_report_data, test_dates)

        with patch('mcp.monthly_report_api.REPORTS_DIR', temp_reports_dir):
            response = client.get("/api/v1/reports/monthly/latest")

            assert response.status_code == 200
            data = response.json()

            assert "report_metadata" in data
            assert "performance_score" in data
            assert "file_info" in data
            assert data["performance_score"]["total_score"] == 87
            assert data["performance_score"]["grade"] == "우수"

    def test_get_performance_trend_no_data(self, client, temp_reports_dir):
        """성과 추이 조회 테스트 (데이터 없음)"""
        with patch('mcp.monthly_report_api.REPORTS_DIR', temp_reports_dir):
            response = client.get("/api/v1/reports/monthly/performance-trend")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "no_data"
            assert data["trend_data"] == []
            assert data["summary"] == {}

    def test_get_performance_trend_with_data(self, client, temp_reports_dir, sample_report_data):
        """성과 추이 조회 테스트 (데이터 있음)"""
        # 6개월 테스트 데이터 생성 (점수 변화)
        test_dates = [
            "2024-09-21", "2024-08-21", "2024-07-21",
            "2024-06-21", "2024-05-21", "2024-04-21"
        ]

        for i, date in enumerate(test_dates):
            data = sample_report_data.copy()
            # 점수를 약간씩 변화시킴
            data["performance_score"]["total_score"] = 85 + i * 2
            data["report_metadata"]["period_end"] = date
            self.create_test_report_files(temp_reports_dir, data, [date])

        with patch('mcp.monthly_report_api.REPORTS_DIR', temp_reports_dir):
            response = client.get("/api/v1/reports/monthly/performance-trend?months=6")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "success"
            assert len(data["trend_data"]) == 6
            assert "summary" in data
            assert data["summary"]["data_points"] == 6
            assert "average_total_score" in data["summary"]

    def test_get_performance_trend_custom_months(self, client, temp_reports_dir, sample_report_data):
        """성과 추이 조회 테스트 (사용자 정의 개월 수)"""
        test_dates = ["2024-09-21", "2024-08-21", "2024-07-21"]
        self.create_test_report_files(temp_reports_dir, sample_report_data, test_dates)

        with patch('mcp.monthly_report_api.REPORTS_DIR', temp_reports_dir):
            response = client.get("/api/v1/reports/monthly/performance-trend?months=3")

            assert response.status_code == 200
            data = response.json()

            assert data["period_months"] == 3
            assert len(data["trend_data"]) == 3

    def test_generate_monthly_report_already_running(self, client):
        """월간 리포트 생성 테스트 (이미 실행 중)"""
        with patch('mcp.monthly_report_api.report_generation_status', {"is_running": True}):
            response = client.post("/api/v1/reports/monthly/generate")

            assert response.status_code == 429
            assert "이미 월간 리포트 생성이 진행 중입니다" in response.json()["detail"]

    def test_generate_monthly_report_script_not_found(self, client):
        """월간 리포트 생성 테스트 (스크립트 없음)"""
        with patch('mcp.monthly_report_api.report_generation_status', {"is_running": False}), \
             patch('mcp.monthly_report_api.MONTHLY_SCRIPT_PATH') as mock_path:

            mock_path.exists.return_value = False

            response = client.post("/api/v1/reports/monthly/generate")

            assert response.status_code == 404
            assert "월간 리포트 스크립트를 찾을 수 없습니다" in response.json()["detail"]

    def test_generate_monthly_report_success(self, client):
        """월간 리포트 생성 테스트 (성공)"""
        with patch('mcp.monthly_report_api.report_generation_status', {"is_running": False, "last_error": None}), \
             patch('mcp.monthly_report_api.MONTHLY_SCRIPT_PATH') as mock_path:

            mock_path.exists.return_value = True

            response = client.post("/api/v1/reports/monthly/generate")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "started"
            assert "월간 리포트 생성이 시작되었습니다" in data["message"]
            assert "estimated_duration" in data

    def test_generate_monthly_report_with_period(self, client):
        """월간 리포트 생성 테스트 (기간 지정)"""
        with patch('mcp.monthly_report_api.report_generation_status', {"is_running": False, "last_error": None}), \
             patch('mcp.monthly_report_api.MONTHLY_SCRIPT_PATH') as mock_path:

            mock_path.exists.return_value = True

            response = client.post("/api/v1/reports/monthly/generate?period=2024-08")

            assert response.status_code == 200
            data = response.json()

            assert data["period"] == "2024-08"

    def test_get_generation_status_idle(self, client):
        """리포트 생성 상태 조회 테스트 (대기 중)"""
        with patch('mcp.monthly_report_api.report_generation_status', {
            "is_running": False,
            "last_run": "2024-09-21T10:00:00",
            "last_error": None
        }):
            response = client.get("/api/v1/reports/monthly/status")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "idle"
            assert data["is_running"] is False
            assert data["last_run"] == "2024-09-21T10:00:00"

    def test_get_generation_status_running(self, client):
        """리포트 생성 상태 조회 테스트 (실행 중)"""
        with patch('mcp.monthly_report_api.report_generation_status', {
            "is_running": True,
            "last_run": None,
            "last_error": None
        }):
            response = client.get("/api/v1/reports/monthly/status")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "running"
            assert data["is_running"] is True

    def test_download_monthly_report_not_found(self, client, temp_reports_dir):
        """월간 리포트 다운로드 테스트 (파일 없음)"""
        with patch('mcp.monthly_report_api.REPORTS_DIR', temp_reports_dir):
            response = client.get("/api/v1/reports/monthly/download/2024-09-21?format=markdown")

            assert response.status_code == 404
            assert "리포트를 찾을 수 없습니다" in response.json()["detail"]

    def test_download_monthly_report_markdown(self, client, temp_reports_dir, sample_report_data):
        """월간 리포트 다운로드 테스트 (Markdown)"""
        # 테스트 파일 생성
        test_date = "2024-09-21"
        self.create_test_report_files(temp_reports_dir, sample_report_data, [test_date])

        with patch('mcp.monthly_report_api.REPORTS_DIR', temp_reports_dir):
            response = client.get(f"/api/v1/reports/monthly/download/{test_date}?format=markdown")

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/plain; charset=utf-8"
            assert "월간 운영 리포트" in response.text
            assert test_date in response.text

    def test_download_monthly_report_json(self, client, temp_reports_dir, sample_report_data):
        """월간 리포트 다운로드 테스트 (JSON)"""
        # 테스트 파일 생성
        test_date = "2024-09-21"
        self.create_test_report_files(temp_reports_dir, sample_report_data, [test_date])

        with patch('mcp.monthly_report_api.REPORTS_DIR', temp_reports_dir):
            response = client.get(f"/api/v1/reports/monthly/download/{test_date}?format=json")

            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"

            data = response.json()
            assert "performance_score" in data
            assert data["performance_score"]["grade"] == "우수"

    def test_download_monthly_report_invalid_format(self, client):
        """월간 리포트 다운로드 테스트 (잘못된 형식)"""
        response = client.get("/api/v1/reports/monthly/download/2024-09-21?format=invalid")

        assert response.status_code == 422  # Validation error

    def test_test_monthly_report_system(self, client):
        """월간 리포트 시스템 테스트 엔드포인트"""
        with patch('mcp.monthly_report_api.MONTHLY_SCRIPT_PATH') as mock_path, \
             patch('mcp.monthly_report_api.REPORTS_DIR') as mock_dir, \
             patch('os.access') as mock_access, \
             patch('glob.glob') as mock_glob:

            # Mock 설정
            mock_path.exists.return_value = True
            mock_dir.exists.return_value = True
            mock_access.return_value = True
            mock_glob.return_value = ["report1.json", "report2.json"]

            response = client.get("/api/v1/reports/monthly/test")

            assert response.status_code == 200
            data = response.json()

            assert data["system_ready"] is True
            assert data["test_results"]["script_exists"] is True
            assert data["test_results"]["existing_reports"] == 2

    def test_test_monthly_report_system_not_ready(self, client):
        """월간 리포트 시스템 테스트 (시스템 준비 안됨)"""
        with patch('mcp.monthly_report_api.MONTHLY_SCRIPT_PATH') as mock_path, \
             patch('mcp.monthly_report_api.REPORTS_DIR') as mock_dir, \
             patch('os.access') as mock_access, \
             patch('glob.glob') as mock_glob:

            # Mock 설정 (스크립트 없음)
            mock_path.exists.return_value = False
            mock_dir.exists.return_value = False
            mock_access.return_value = False
            mock_glob.return_value = []

            response = client.get("/api/v1/reports/monthly/test")

            assert response.status_code == 200
            data = response.json()

            assert data["system_ready"] is False
            assert data["test_results"]["script_exists"] is False
            assert data["test_results"]["existing_reports"] == 0


class TestMonthlyReportAPIIntegration:
    """월간 리포트 API 통합 테스트 클래스"""

    @pytest.fixture
    def client(self):
        """FastAPI 테스트 클라이언트"""
        return TestClient(app)

    @pytest.mark.integration
    def test_api_endpoints_accessibility(self, client):
        """모든 월간 리포트 API 엔드포인트 접근성 테스트"""
        # 기본 요약 엔드포인트
        response = client.get("/api/v1/reports/monthly/")
        assert response.status_code == 200

        # 성과 추이 엔드포인트
        response = client.get("/api/v1/reports/monthly/performance-trend")
        assert response.status_code == 200

        # 상태 조회 엔드포인트
        response = client.get("/api/v1/reports/monthly/status")
        assert response.status_code == 200

        # 시스템 테스트 엔드포인트
        response = client.get("/api/v1/reports/monthly/test")
        assert response.status_code == 200

    @pytest.mark.integration
    def test_api_response_format_consistency(self, client):
        """API 응답 형식 일관성 테스트"""
        # 모든 성공 응답이 JSON 형식인지 확인
        endpoints = [
            "/api/v1/reports/monthly/",
            "/api/v1/reports/monthly/performance-trend",
            "/api/v1/reports/monthly/status",
            "/api/v1/reports/monthly/test"
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"

            # JSON 파싱 가능한지 확인
            data = response.json()
            assert isinstance(data, dict)

    @pytest.mark.integration
    def test_error_handling_consistency(self, client):
        """오류 처리 일관성 테스트"""
        # 존재하지 않는 리포트 다운로드 시도
        response = client.get("/api/v1/reports/monthly/download/nonexistent-date")
        assert response.status_code == 404

        error_data = response.json()
        assert "detail" in error_data
        assert isinstance(error_data["detail"], str)

        # 잘못된 월 수로 성과 추이 조회
        response = client.get("/api/v1/reports/monthly/performance-trend?months=15")
        assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    # 개별 테스트 실행을 위한 메인 함수
    import asyncio

    async def run_basic_tests():
        """기본 API 테스트 실행"""
        print("🧪 월간 리포트 API 기본 테스트 시작...")

        # 간단한 클라이언트 테스트
        try:
            client = TestClient(app)

            # 기본 엔드포인트 테스트
            response = client.get("/api/v1/reports/monthly/")
            print(f"✅ 요약 API 테스트: {response.status_code}")

            response = client.get("/api/v1/reports/monthly/test")
            print(f"✅ 시스템 테스트 API: {response.status_code}")

        except Exception as e:
            print(f"❌ API 테스트 실패: {e}")

        print("🧪 월간 리포트 API 기본 테스트 완료")

    # 비동기 테스트 실행
    asyncio.run(run_basic_tests())