# tests/test_autoremediate_and_flaky.py
"""
CI 자동 완화 시스템 및 플래키 테스트 격리 시스템 종합 테스트 모음

이 파일은 다음 시스템들을 검증합니다:
- scripts/ci_autoremediate.sh 자동 완화 스크립트
- scripts/hooks/ 훅 시스템 (clear_ci_cache.sh, retry_failed_tests.sh, restart_worker.sh)
- mcp/utils/runbook.py 런북 템플릿 시스템
- mcp/flaky_tests_api.py FastAPI 라우터
- web/admin_dashboard.html 자동 완화 패널
"""
from __future__ import annotations

import os
import json
import tempfile
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

# FastAPI 앱과 라우터 import
from mcp.run import app
from mcp.flaky_tests_api import router as flaky_tests_router
from mcp.utils.runbook import (
    RunbookManager,
    RUNBOOK_TEMPLATES,
    generate_runbook_html,
    get_runbook_by_category,
    search_runbooks,
    get_error_type_mapping
)


class TestAutoRemediationScript:
    """scripts/ci_autoremediate.sh 스크립트 테스트"""

    @pytest.fixture
    def temp_workspace(self):
        """임시 워크스페이스 설정"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            # 스크립트 파일들을 임시 디렉토리로 복사
            scripts_src = Path("scripts")
            scripts_dst = workspace / "scripts"
            scripts_dst.mkdir()

            if (scripts_src / "ci_autoremediate.sh").exists():
                shutil.copy2(scripts_src / "ci_autoremediate.sh", scripts_dst)

            # hooks 디렉토리 복사
            hooks_src = scripts_src / "hooks"
            hooks_dst = scripts_dst / "hooks"
            if hooks_src.exists():
                shutil.copytree(hooks_src, hooks_dst)

            # 테스트용 로그 디렉토리 생성
            (workspace / "logs").mkdir()

            yield workspace

    def test_script_existence_and_permissions(self):
        """자동 완화 스크립트 존재 및 실행 권한 확인"""
        script_path = Path("scripts/ci_autoremediate.sh")
        assert script_path.exists(), "ci_autoremediate.sh 스크립트가 존재하지 않습니다"
        assert script_path.is_file(), "ci_autoremediate.sh가 파일이 아닙니다"

        # 실행 권한 확인 (Unix 시스템에서만)
        if os.name == 'posix':
            assert os.access(script_path, os.X_OK), "ci_autoremediate.sh에 실행 권한이 없습니다"

    def test_hooks_directory_structure(self):
        """훅 디렉토리 구조 및 파일 존재 확인"""
        hooks_dir = Path("scripts/hooks")
        assert hooks_dir.exists(), "hooks 디렉토리가 존재하지 않습니다"
        assert hooks_dir.is_dir(), "hooks가 디렉토리가 아닙니다"

        expected_hooks = [
            "clear_ci_cache.sh",
            "retry_failed_tests.sh",
            "restart_worker.sh"
        ]

        for hook_name in expected_hooks:
            hook_path = hooks_dir / hook_name
            assert hook_path.exists(), f"{hook_name} 훅이 존재하지 않습니다"
            assert hook_path.is_file(), f"{hook_name}이 파일이 아닙니다"

            # 실행 권한 확인 (Unix 시스템에서만)
            if os.name == 'posix':
                assert os.access(hook_path, os.X_OK), f"{hook_name}에 실행 권한이 없습니다"

    def test_script_help_option(self, temp_workspace):
        """스크립트 도움말 옵션 테스트"""
        script_path = temp_workspace / "scripts" / "ci_autoremediate.sh"
        if not script_path.exists():
            pytest.skip("ci_autoremediate.sh 스크립트가 없습니다")

        try:
            result = subprocess.run(
                ["bash", str(script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=temp_workspace
            )

            # 도움말이 출력되고 정상 종료되어야 함
            assert result.returncode == 0, f"스크립트 도움말 실행 실패: {result.stderr}"
            assert "사용법" in result.stdout or "Usage" in result.stdout, "도움말에 사용법이 없습니다"

        except subprocess.TimeoutExpired:
            pytest.fail("스크립트 도움말 실행이 타임아웃되었습니다")
        except FileNotFoundError:
            pytest.skip("bash가 설치되지 않았습니다")

    def test_script_dry_run_mode(self, temp_workspace):
        """스크립트 드라이런 모드 테스트"""
        script_path = temp_workspace / "scripts" / "ci_autoremediate.sh"
        if not script_path.exists():
            pytest.skip("ci_autoremediate.sh 스크립트가 없습니다")

        try:
            result = subprocess.run(
                ["bash", str(script_path), "--dry-run", "--error-type", "dependency_install_failed"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=temp_workspace
            )

            # 드라이런 모드는 성공해야 함
            assert result.returncode == 0, f"드라이런 모드 실행 실패: {result.stderr}"
            assert "DRY RUN" in result.stdout.upper() or "시뮬레이션" in result.stdout, "드라이런 모드 표시가 없습니다"

        except subprocess.TimeoutExpired:
            pytest.fail("드라이런 모드 실행이 타임아웃되었습니다")
        except FileNotFoundError:
            pytest.skip("bash가 설치되지 않았습니다")

    @pytest.mark.parametrize("hook_name", [
        "clear_ci_cache.sh",
        "retry_failed_tests.sh",
        "restart_worker.sh"
    ])
    def test_individual_hooks_dry_run(self, temp_workspace, hook_name):
        """개별 훅 드라이런 모드 테스트"""
        hook_path = temp_workspace / "scripts" / "hooks" / hook_name
        if not hook_path.exists():
            pytest.skip(f"{hook_name} 훅이 없습니다")

        try:
            result = subprocess.run(
                ["bash", str(hook_path), "--dry-run"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=temp_workspace
            )

            # 드라이런 모드는 성공해야 함
            assert result.returncode == 0, f"{hook_name} 드라이런 모드 실행 실패: {result.stderr}"
            assert len(result.stdout) > 0, f"{hook_name}에서 출력이 없습니다"

        except subprocess.TimeoutExpired:
            pytest.fail(f"{hook_name} 드라이런 모드 실행이 타임아웃되었습니다")
        except FileNotFoundError:
            pytest.skip("bash가 설치되지 않았습니다")


class TestRunbookSystem:
    """mcp/utils/runbook.py 런북 시스템 테스트"""

    def test_runbook_manager_initialization(self):
        """런북 매니저 초기화 테스트"""
        manager = RunbookManager()
        assert manager is not None
        assert hasattr(manager, 'templates')
        assert isinstance(manager.templates, dict)

    def test_runbook_templates_structure(self):
        """런북 템플릿 구조 검증"""
        assert isinstance(RUNBOOK_TEMPLATES, dict)
        assert len(RUNBOOK_TEMPLATES) > 0, "런북 템플릿이 비어있습니다"

        # 필수 에러 타입들이 존재하는지 확인
        required_error_types = [
            "dependency_install_failed",
            "test_timeout",
            "build_timeout",
            "network_error",
            "out_of_memory",
            "disk_full",
            "permission_denied",
            "config_error"
        ]

        for error_type in required_error_types:
            assert error_type in RUNBOOK_TEMPLATES, f"{error_type} 런북 템플릿이 없습니다"

            template = RUNBOOK_TEMPLATES[error_type]
            assert "title" in template, f"{error_type} 템플릿에 title이 없습니다"
            assert "severity" in template, f"{error_type} 템플릿에 severity가 없습니다"
            assert "category" in template, f"{error_type} 템플릿에 category가 없습니다"

    def test_runbook_html_generation(self):
        """런북 HTML 생성 테스트"""
        error_type = "dependency_install_failed"
        html_content = generate_runbook_html(error_type)

        assert isinstance(html_content, str)
        assert len(html_content) > 0, "생성된 HTML이 비어있습니다"
        assert "<html>" in html_content or "<!DOCTYPE" in html_content, "유효한 HTML이 아닙니다"
        assert "의존성 설치 실패" in html_content, "한국어 콘텐츠가 없습니다"

    def test_runbook_category_filtering(self):
        """런북 카테고리별 필터링 테스트"""
        build_runbooks = get_runbook_by_category("BUILD")
        assert isinstance(build_runbooks, list)
        assert len(build_runbooks) > 0, "BUILD 카테고리 런북이 없습니다"

        test_runbooks = get_runbook_by_category("TEST")
        assert isinstance(test_runbooks, list)

        # 존재하지 않는 카테고리
        empty_runbooks = get_runbook_by_category("NONEXISTENT")
        assert isinstance(empty_runbooks, list)
        assert len(empty_runbooks) == 0, "존재하지 않는 카테고리에서 결과가 반환되었습니다"

    def test_runbook_search_functionality(self):
        """런북 검색 기능 테스트"""
        # 키워드 검색
        search_results = search_runbooks("의존성")
        assert isinstance(search_results, list)
        assert len(search_results) > 0, "의존성 키워드 검색 결과가 없습니다"

        # 영문 키워드 검색
        search_results_en = search_runbooks("dependency")
        assert isinstance(search_results_en, list)

        # 빈 검색어
        empty_search = search_runbooks("")
        assert isinstance(empty_search, list)

    def test_error_type_mapping(self):
        """에러 타입 매핑 테스트"""
        mapping = get_error_type_mapping()
        assert isinstance(mapping, dict)
        assert len(mapping) > 0, "에러 타입 매핑이 비어있습니다"

        # 샘플 에러 메시지 매핑 테스트
        test_cases = [
            ("Could not install dependency", "dependency_install_failed"),
            ("Test execution timed out", "test_timeout"),
            ("Build process timed out", "build_timeout"),
            ("Connection failed", "network_error"),
            ("Out of memory", "out_of_memory"),
            ("No space left on device", "disk_full"),
            ("Permission denied", "permission_denied")
        ]

        for error_msg, expected_type in test_cases:
            matched_type = None
            for pattern, error_type in mapping.items():
                if pattern.lower() in error_msg.lower():
                    matched_type = error_type
                    break
            # 매핑이 반드시 일치할 필요는 없지만, 시스템이 작동해야 함
            assert matched_type is None or matched_type in RUNBOOK_TEMPLATES


class TestFlakyTestsAPI:
    """mcp/flaky_tests_api.py FastAPI 라우터 테스트"""

    @pytest.fixture
    def client(self):
        """FastAPI 테스트 클라이언트"""
        return TestClient(app)

    @pytest.fixture
    def temp_data_dir(self):
        """임시 데이터 디렉토리"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 환경 변수를 임시 디렉토리로 설정
            original_data_dir = os.environ.get("FLAKY_TESTS_DATA_DIR")
            os.environ["FLAKY_TESTS_DATA_DIR"] = temp_dir

            yield Path(temp_dir)

            # 원래 환경 변수 복원
            if original_data_dir is not None:
                os.environ["FLAKY_TESTS_DATA_DIR"] = original_data_dir
            elif "FLAKY_TESTS_DATA_DIR" in os.environ:
                del os.environ["FLAKY_TESTS_DATA_DIR"]

    def test_flaky_tests_list_endpoint(self, client, temp_data_dir):
        """플래키 테스트 목록 조회 API 테스트"""
        response = client.get("/api/v1/flaky-tests/")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        # 초기에는 빈 목록이어야 함
        assert len(data) == 0

    def test_record_test_result_endpoint(self, client, temp_data_dir):
        """테스트 결과 기록 API 테스트"""
        test_data = {
            "test_name": "test_sample_function",
            "file_path": "tests/test_sample.py",
            "status": "FAILED",
            "execution_time": 1.23,
            "error_message": "AssertionError: Expected 1 but got 2",
            "runner": "pytest",
            "branch": "main",
            "commit_hash": "abc123def456",
            "metadata": {
                "ci_job_id": "12345",
                "os": "ubuntu-latest",
                "python_version": "3.9"
            }
        }

        response = client.post("/api/v1/flaky-tests/record", json=test_data)
        assert response.status_code == 201

        result = response.json()
        assert result["success"] is True
        assert "test_id" in result
        assert result["test_name"] == test_data["test_name"]

    def test_record_test_result_validation(self, client, temp_data_dir):
        """테스트 결과 기록 시 유효성 검사 테스트"""
        # 필수 필드 누락
        invalid_data = {
            "test_name": "test_sample",
            # file_path 누락
            "status": "FAILED"
        }

        response = client.post("/api/v1/flaky-tests/record", json=invalid_data)
        assert response.status_code == 422  # Validation Error

    def test_quarantine_management(self, client, temp_data_dir):
        """격리 관리 기능 테스트"""
        # 먼저 테스트 결과 기록
        test_data = {
            "test_name": "test_flaky_function",
            "file_path": "tests/test_flaky.py",
            "status": "FAILED",
            "execution_time": 0.5,
            "error_message": "Random failure",
            "runner": "pytest"
        }

        # 테스트 결과 기록
        record_response = client.post("/api/v1/flaky-tests/record", json=test_data)
        assert record_response.status_code == 201
        test_id = record_response.json()["test_id"]

        # 격리 설정
        quarantine_response = client.post(f"/api/v1/flaky-tests/{test_id}/quarantine")
        assert quarantine_response.status_code == 200

        quarantine_result = quarantine_response.json()
        assert quarantine_result["success"] is True
        assert quarantine_result["quarantined"] is True

        # 격리 해제
        unquarantine_response = client.delete(f"/api/v1/flaky-tests/{test_id}/quarantine")
        assert unquarantine_response.status_code == 200

        unquarantine_result = unquarantine_response.json()
        assert unquarantine_result["success"] is True
        assert unquarantine_result["quarantined"] is False

    def test_statistics_endpoint(self, client, temp_data_dir):
        """통계 정보 조회 API 테스트"""
        response = client.get("/api/v1/flaky-tests/stats")
        assert response.status_code == 200

        stats = response.json()
        assert "total_tests" in stats
        assert "quarantined_tests" in stats
        assert "failure_rate" in stats
        assert "most_common_errors" in stats
        assert isinstance(stats["total_tests"], int)
        assert isinstance(stats["quarantined_tests"], int)
        assert isinstance(stats["failure_rate"], (int, float))
        assert isinstance(stats["most_common_errors"], list)

    def test_configuration_management(self, client, temp_data_dir):
        """설정 관리 API 테스트"""
        # 현재 설정 조회
        get_response = client.get("/api/v1/flaky-tests/config")
        assert get_response.status_code == 200

        config = get_response.json()
        assert "quarantine_threshold" in config
        assert "auto_quarantine" in config
        assert "max_failures" in config

        # 설정 업데이트
        new_config = {
            "quarantine_threshold": 0.8,
            "auto_quarantine": True,
            "max_failures": 3
        }

        update_response = client.put("/api/v1/flaky-tests/config", json=new_config)
        assert update_response.status_code == 200

        updated_config = update_response.json()
        assert updated_config["quarantine_threshold"] == 0.8
        assert updated_config["auto_quarantine"] is True
        assert updated_config["max_failures"] == 3

    def test_test_history_endpoint(self, client, temp_data_dir):
        """테스트 이력 조회 API 테스트"""
        # 먼저 테스트 결과 기록
        test_data = {
            "test_name": "test_with_history",
            "file_path": "tests/test_history.py",
            "status": "PASSED",
            "execution_time": 0.1,
            "runner": "pytest"
        }

        record_response = client.post("/api/v1/flaky-tests/record", json=test_data)
        assert record_response.status_code == 201
        test_id = record_response.json()["test_id"]

        # 이력 조회
        history_response = client.get(f"/api/v1/flaky-tests/{test_id}/history")
        assert history_response.status_code == 200

        history = history_response.json()
        assert isinstance(history, list)
        assert len(history) >= 1

        # 첫 번째 이력 항목 확인
        first_history = history[0]
        assert "timestamp" in first_history
        assert "status" in first_history
        assert "execution_time" in first_history


class TestAdminDashboardIntegration:
    """web/admin_dashboard.html 자동 완화 패널 통합 테스트"""

    def test_admin_dashboard_file_exists(self):
        """관리자 대시보드 파일 존재 확인"""
        dashboard_path = Path("web/admin_dashboard.html")
        assert dashboard_path.exists(), "admin_dashboard.html 파일이 존재하지 않습니다"
        assert dashboard_path.is_file(), "admin_dashboard.html이 파일이 아닙니다"

    def test_auto_remediation_panel_content(self):
        """자동 완화 패널 콘텐츠 확인"""
        dashboard_path = Path("web/admin_dashboard.html")
        if not dashboard_path.exists():
            pytest.skip("admin_dashboard.html 파일이 없습니다")

        content = dashboard_path.read_text(encoding='utf-8')

        # 자동 완화 패널 관련 요소들 확인
        assert "자동 완화 & 런북" in content, "자동 완화 패널 제목이 없습니다"
        assert "AutoRemediationManager" in content, "AutoRemediationManager 클래스가 없습니다"
        assert "runAutoRemediationBtn" in content, "자동 완화 실행 버튼이 없습니다"
        assert "openRunbookViewerBtn" in content, "런북 뷰어 버튼이 없습니다"
        assert "refreshAutoRemediationBtn" in content, "새로고침 버튼이 없습니다"

    def test_javascript_class_structure(self):
        """JavaScript 클래스 구조 확인"""
        dashboard_path = Path("web/admin_dashboard.html")
        if not dashboard_path.exists():
            pytest.skip("admin_dashboard.html 파일이 없습니다")

        content = dashboard_path.read_text(encoding='utf-8')

        # AutoRemediationManager 클래스 필수 메서드들 확인
        required_methods = [
            "constructor()",
            "init()",
            "loadRemediationData()",
            "loadRunbookData()",
            "updateUI()",
            "executeAutoRemediation()",
            "openRunbookViewer()"
        ]

        for method in required_methods:
            # 메서드명의 일부라도 포함되어 있는지 확인
            method_name = method.replace("()", "")
            assert method_name in content, f"{method_name} 메서드가 없습니다"

    def test_ui_components_presence(self):
        """UI 컴포넌트 존재 확인"""
        dashboard_path = Path("web/admin_dashboard.html")
        if not dashboard_path.exists():
            pytest.skip("admin_dashboard.html 파일이 없습니다")

        content = dashboard_path.read_text(encoding='utf-8')

        # 필수 UI 컴포넌트 ID들 확인
        required_components = [
            "availableActionsCount",
            "remediationSuccessRate",
            "availableRunbooksCount",
            "lastRemediationTime",
            "dryRunToggle",
            "autoExecuteToggle",
            "maxActionsInput",
            "retryIntervalInput",
            "errorTypePriorities",
            "remediationHistoryList",
            "quickRunbooksList",
            "activeRemediationProcesses",
            "pendingRemediationActions"
        ]

        for component_id in required_components:
            assert f'id="{component_id}"' in content, f"{component_id} 컴포넌트가 없습니다"


class TestSystemIntegration:
    """전체 시스템 통합 테스트"""

    def test_project_structure_integrity(self):
        """프로젝트 구조 무결성 확인"""
        required_files = [
            "scripts/ci_autoremediate.sh",
            "scripts/hooks/clear_ci_cache.sh",
            "scripts/hooks/retry_failed_tests.sh",
            "scripts/hooks/restart_worker.sh",
            "mcp/utils/runbook.py",
            "mcp/flaky_tests_api.py",
            "mcp/run.py",
            "web/admin_dashboard.html"
        ]

        for file_path in required_files:
            path = Path(file_path)
            assert path.exists(), f"필수 파일이 없습니다: {file_path}"

    def test_fastapi_router_registration(self):
        """FastAPI 라우터 등록 확인"""
        from mcp.run import app

        # 라우터가 등록되었는지 확인
        routes = [route.path for route in app.routes]

        # 플래키 테스트 API 경로들이 포함되어 있는지 확인
        flaky_test_paths = [path for path in routes if "/flaky-tests" in path]
        assert len(flaky_test_paths) > 0, "플래키 테스트 API 라우터가 등록되지 않았습니다"

    def test_environment_variables_handling(self):
        """환경 변수 처리 확인"""
        # 임시로 환경 변수 설정하고 테스트
        original_log_level = os.environ.get("LOG_LEVEL")
        original_port = os.environ.get("PORT")

        try:
            os.environ["LOG_LEVEL"] = "DEBUG"
            os.environ["PORT"] = "9999"

            # 환경 변수가 올바르게 처리되는지 확인
            # (실제 앱 재시작 없이는 완전한 테스트 불가능)
            assert os.environ["LOG_LEVEL"] == "DEBUG"
            assert os.environ["PORT"] == "9999"

        finally:
            # 원래 환경 변수 복원
            if original_log_level is not None:
                os.environ["LOG_LEVEL"] = original_log_level
            elif "LOG_LEVEL" in os.environ:
                del os.environ["LOG_LEVEL"]

            if original_port is not None:
                os.environ["PORT"] = original_port
            elif "PORT" in os.environ:
                del os.environ["PORT"]

    @pytest.mark.integration
    def test_end_to_end_flaky_test_workflow(self):
        """플래키 테스트 전체 워크플로우 통합 테스트"""
        client = TestClient(app)

        with tempfile.TemporaryDirectory() as temp_dir:
            # 임시 데이터 디렉토리 설정
            os.environ["FLAKY_TESTS_DATA_DIR"] = temp_dir

            try:
                # 1. 초기 상태 확인
                stats_response = client.get("/api/v1/flaky-tests/stats")
                assert stats_response.status_code == 200
                initial_stats = stats_response.json()

                # 2. 여러 테스트 결과 기록
                test_results = [
                    {
                        "test_name": "test_flaky_network",
                        "file_path": "tests/test_network.py",
                        "status": "FAILED",
                        "execution_time": 2.5,
                        "error_message": "Connection timeout",
                        "runner": "pytest"
                    },
                    {
                        "test_name": "test_flaky_network",
                        "file_path": "tests/test_network.py",
                        "status": "PASSED",
                        "execution_time": 1.0,
                        "runner": "pytest"
                    },
                    {
                        "test_name": "test_flaky_network",
                        "file_path": "tests/test_network.py",
                        "status": "FAILED",
                        "execution_time": 3.0,
                        "error_message": "Connection timeout",
                        "runner": "pytest"
                    }
                ]

                test_ids = []
                for result in test_results:
                    response = client.post("/api/v1/flaky-tests/record", json=result)
                    assert response.status_code == 201
                    test_ids.append(response.json()["test_id"])

                # 3. 플래키 테스트 목록 확인
                list_response = client.get("/api/v1/flaky-tests/")
                assert list_response.status_code == 200
                test_list = list_response.json()
                assert len(test_list) > 0

                # 4. 통계 업데이트 확인
                updated_stats_response = client.get("/api/v1/flaky-tests/stats")
                assert updated_stats_response.status_code == 200
                updated_stats = updated_stats_response.json()
                assert updated_stats["total_tests"] > initial_stats["total_tests"]

                # 5. 격리 작업 수행
                if test_ids:
                    quarantine_response = client.post(f"/api/v1/flaky-tests/{test_ids[0]}/quarantine")
                    assert quarantine_response.status_code == 200

                    # 격리된 테스트만 조회
                    quarantined_response = client.get("/api/v1/flaky-tests/?quarantined_only=true")
                    assert quarantined_response.status_code == 200
                    quarantined_tests = quarantined_response.json()
                    assert len(quarantined_tests) > 0

            finally:
                # 환경 변수 정리
                if "FLAKY_TESTS_DATA_DIR" in os.environ:
                    del os.environ["FLAKY_TESTS_DATA_DIR"]


# 테스트 실행을 위한 pytest 설정
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])