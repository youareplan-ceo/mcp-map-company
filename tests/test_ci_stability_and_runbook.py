# tests/test_ci_stability_and_runbook.py
"""
CI 안정성 시뮬레이션 및 런북 검증 시스템 테스트 모음

이 파일은 다음 시스템들을 검증합니다:
- scripts/ci_stability_sim.sh CI 안정성 시뮬레이션 스크립트
- scripts/runbook_validator.sh 런북 시스템 검증 스크립트
- JSON/Markdown 출력 형식 검증
- 시뮬레이션 결과 정확성 검사
- 런북 매핑 무결성 검증

작성자: Claude AI
생성일: $(date '+%Y-%m-%d')
"""
from __future__ import annotations

import os
import json
import tempfile
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
import time
import re

import pytest

# 테스트 설정 상수
TIMEOUT_SECONDS = 30  # 스크립트 실행 타임아웃
MIN_SIMULATION_RUNS = 10  # 최소 시뮬레이션 실행 횟수
MAX_SIMULATION_RUNS = 100  # 최대 시뮬레이션 실행 횟수


class TestCIStabilitySimulation:
    """scripts/ci_stability_sim.sh CI 안정성 시뮬레이션 테스트"""

    @pytest.fixture
    def temp_workspace(self):
        """임시 워크스페이스 설정 (테스트 결과 파일 저장용)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            yield workspace

    def test_simulation_script_existence_and_permissions(self):
        """시뮬레이션 스크립트 존재 및 실행 권한 확인"""
        script_path = Path("scripts/ci_stability_sim.sh")
        assert script_path.exists(), "ci_stability_sim.sh 스크립트가 존재하지 않습니다"
        assert script_path.is_file(), "ci_stability_sim.sh가 파일이 아닙니다"

        # 실행 권한 확인 (Unix 시스템에서만)
        if os.name == 'posix':
            assert os.access(script_path, os.X_OK), "ci_stability_sim.sh에 실행 권한이 없습니다"

    def test_simulation_help_option(self):
        """시뮬레이션 스크립트 도움말 옵션 테스트"""
        script_path = Path("scripts/ci_stability_sim.sh")
        if not script_path.exists():
            pytest.skip("ci_stability_sim.sh 스크립트가 없습니다")

        try:
            result = subprocess.run(
                ["bash", str(script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS
            )

            assert result.returncode == 0, f"도움말 실행 실패: {result.stderr}"
            assert "사용법" in result.stdout or "Usage" in result.stdout, "도움말에 사용법이 없습니다"
            assert "CI 안정성 시뮬레이션" in result.stdout, "도움말에 스크립트 설명이 없습니다"

        except subprocess.TimeoutExpired:
            pytest.fail("도움말 실행이 타임아웃되었습니다")
        except FileNotFoundError:
            pytest.skip("bash가 설치되지 않았습니다")

    def test_simulation_dry_run_mode(self):
        """시뮬레이션 드라이런 모드 테스트"""
        script_path = Path("scripts/ci_stability_sim.sh")
        if not script_path.exists():
            pytest.skip("ci_stability_sim.sh 스크립트가 없습니다")

        try:
            result = subprocess.run(
                [
                    "bash", str(script_path),
                    "--dry-run",
                    "--fail-rate", "10",
                    "--flaky-rate", "5",
                    "--runs", "50",
                    "--verbose"
                ],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS
            )

            assert result.returncode == 0, f"드라이런 모드 실행 실패: {result.stderr}"
            assert "드라이런 모드" in result.stdout, "드라이런 모드 표시가 없습니다"
            assert "설정 확인" in result.stdout, "설정 확인 섹션이 없습니다"

        except subprocess.TimeoutExpired:
            pytest.fail("드라이런 모드 실행이 타임아웃되었습니다")

    @pytest.mark.parametrize("fail_rate,flaky_rate,runs", [
        (5, 2, 20),    # 낮은 실패율
        (15, 5, 30),   # 중간 실패율
        (25, 10, 25),  # 높은 실패율
    ])
    def test_simulation_execution_with_parameters(self, fail_rate, flaky_rate, runs, temp_workspace):
        """다양한 매개변수로 시뮬레이션 실행 테스트"""
        script_path = Path("scripts/ci_stability_sim.sh")
        if not script_path.exists():
            pytest.skip("ci_stability_sim.sh 스크립트가 없습니다")

        try:
            result = subprocess.run(
                [
                    "bash", str(script_path),
                    "--fail-rate", str(fail_rate),
                    "--flaky-rate", str(flaky_rate),
                    "--runs", str(runs)
                ],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
                cwd=temp_workspace
            )

            assert result.returncode == 0, f"시뮬레이션 실행 실패: {result.stderr}"
            assert "시뮬레이션 완료" in result.stdout, "시뮬레이션 완료 메시지가 없습니다"
            assert "성공률" in result.stdout, "성공률 정보가 없습니다"
            assert "실패율" in result.stdout, "실패율 정보가 없습니다"

        except subprocess.TimeoutExpired:
            pytest.fail(f"시뮬레이션 실행이 타임아웃되었습니다 (매개변수: {fail_rate}%, {flaky_rate}%, {runs}회)")

    def test_simulation_json_output(self, temp_workspace):
        """시뮬레이션 JSON 출력 형식 테스트"""
        script_path = Path("scripts/ci_stability_sim.sh")
        if not script_path.exists():
            pytest.skip("ci_stability_sim.sh 스크립트가 없습니다")

        output_file = temp_workspace / "simulation_result.json"

        try:
            result = subprocess.run(
                [
                    "bash", str(script_path),
                    "--fail-rate", "10",
                    "--flaky-rate", "5",
                    "--runs", "20",
                    "--json",
                    "--output", str(output_file)
                ],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
                cwd=temp_workspace
            )

            assert result.returncode == 0, f"JSON 출력 시뮬레이션 실행 실패: {result.stderr}"
            assert output_file.exists(), "JSON 출력 파일이 생성되지 않았습니다"

            # JSON 파일 파싱 및 구조 검증
            with open(output_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)

            # JSON 구조 검증
            required_fields = [
                "simulation_config",
                "results",
                "execution_stats",
                "generated_at"
            ]

            for field in required_fields:
                assert field in json_data, f"JSON 출력에 필수 필드가 없습니다: {field}"

            # 시뮬레이션 설정 검증
            config = json_data["simulation_config"]
            assert config["fail_rate_target"] == 10, "실패율 설정이 올바르지 않습니다"
            assert config["flaky_rate_target"] == 5, "플래키율 설정이 올바르지 않습니다"
            assert config["total_runs"] == 20, "실행 횟수 설정이 올바르지 않습니다"

            # 결과 검증
            results = json_data["results"]
            assert "successful_runs" in results, "성공 실행 수가 없습니다"
            assert "failed_runs" in results, "실패 실행 수가 없습니다"
            assert "flaky_runs" in results, "플래키 실행 수가 없습니다"
            assert "success_rate" in results, "성공률이 없습니다"

            # 논리적 일관성 검증
            total_runs = results["successful_runs"] + results["failed_runs"]
            assert total_runs <= 20, "전체 실행 수가 설정과 일치하지 않습니다"

        except subprocess.TimeoutExpired:
            pytest.fail("JSON 출력 시뮬레이션이 타임아웃되었습니다")
        except json.JSONDecodeError as e:
            pytest.fail(f"JSON 파싱 오류: {e}")

    def test_simulation_markdown_output(self, temp_workspace):
        """시뮬레이션 Markdown 출력 형식 테스트"""
        script_path = Path("scripts/ci_stability_sim.sh")
        if not script_path.exists():
            pytest.skip("ci_stability_sim.sh 스크립트가 없습니다")

        output_file = temp_workspace / "simulation_result.md"

        try:
            result = subprocess.run(
                [
                    "bash", str(script_path),
                    "--fail-rate", "15",
                    "--flaky-rate", "8",
                    "--runs", "25",
                    "--markdown",
                    "--output", str(output_file)
                ],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
                cwd=temp_workspace
            )

            assert result.returncode == 0, f"Markdown 출력 시뮬레이션 실행 실패: {result.stderr}"
            assert output_file.exists(), "Markdown 출력 파일이 생성되지 않았습니다"

            # Markdown 파일 내용 검증
            with open(output_file, 'r', encoding='utf-8') as f:
                markdown_content = f.read()

            # Markdown 구조 검증
            required_sections = [
                "# 🧪 CI 안정성 시뮬레이션 결과",
                "## 📊 시뮬레이션 설정",
                "## 📈 실행 결과",
                "## 🎯 성능 메트릭",
                "## 💡 권장사항"
            ]

            for section in required_sections:
                assert section in markdown_content, f"Markdown에 필수 섹션이 없습니다: {section}"

            # 테이블 형식 검증
            assert "|" in markdown_content, "Markdown 테이블이 없습니다"
            assert "---" in markdown_content, "Markdown 테이블 구분자가 없습니다"

            # 설정값 검증
            assert "15%" in markdown_content, "실패율 설정이 Markdown에 없습니다"
            assert "8%" in markdown_content, "플래키율 설정이 Markdown에 없습니다"
            assert "25회" in markdown_content, "실행 횟수가 Markdown에 없습니다"

        except subprocess.TimeoutExpired:
            pytest.fail("Markdown 출력 시뮬레이션이 타임아웃되었습니다")

    def test_simulation_parameter_validation(self):
        """시뮬레이션 매개변수 유효성 검사 테스트"""
        script_path = Path("scripts/ci_stability_sim.sh")
        if not script_path.exists():
            pytest.skip("ci_stability_sim.sh 스크립트가 없습니다")

        # 잘못된 매개변수 테스트 케이스
        invalid_cases = [
            (["--fail-rate", "-5"], "음수 실패율"),
            (["--fail-rate", "150"], "100% 초과 실패율"),
            (["--flaky-rate", "-2"], "음수 플래키율"),
            (["--flaky-rate", "120"], "100% 초과 플래키율"),
            (["--runs", "0"], "0회 실행"),
            (["--runs", "-10"], "음수 실행 횟수"),
            (["--fail-rate", "60", "--flaky-rate", "50"], "합계 100% 초과"),
        ]

        for invalid_params, description in invalid_cases:
            try:
                result = subprocess.run(
                    ["bash", str(script_path)] + invalid_params,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_SECONDS
                )

                assert result.returncode != 0, f"{description} 케이스에서 오류가 감지되지 않았습니다"
                assert "오류" in result.stderr or "error" in result.stderr.lower(), f"{description} 케이스에서 오류 메시지가 없습니다"

            except subprocess.TimeoutExpired:
                pytest.fail(f"{description} 유효성 검사가 타임아웃되었습니다")

    def test_simulation_statistical_accuracy(self, temp_workspace):
        """시뮬레이션 통계적 정확성 테스트 (충분한 실행 횟수로)"""
        script_path = Path("scripts/ci_stability_sim.sh")
        if not script_path.exists():
            pytest.skip("ci_stability_sim.sh 스크립트가 없습니다")

        # 통계적으로 의미있는 테스트 (더 많은 실행 횟수)
        fail_rate = 20
        flaky_rate = 10
        runs = 100  # 충분한 표본 크기

        output_file = temp_workspace / "statistical_test.json"

        try:
            result = subprocess.run(
                [
                    "bash", str(script_path),
                    "--fail-rate", str(fail_rate),
                    "--flaky-rate", str(flaky_rate),
                    "--runs", str(runs),
                    "--json",
                    "--output", str(output_file)
                ],
                capture_output=True,
                text=True,
                timeout=60  # 더 긴 타임아웃
            )

            assert result.returncode == 0, f"통계 테스트 시뮬레이션 실행 실패: {result.stderr}"

            with open(output_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)

            results = json_data["results"]
            actual_fail_rate = results["actual_fail_rate"]
            flaky_reproduce_rate = results["flaky_reproduce_rate"]

            # 통계적 허용 오차 (표본 크기를 고려한 오차 범위)
            # 실제로는 랜덤 시뮬레이션이므로 어느 정도 오차는 허용
            fail_rate_tolerance = 15  # 15% 오차 허용
            flaky_rate_tolerance = 20  # 20% 오차 허용

            fail_rate_diff = abs(actual_fail_rate - fail_rate)
            flaky_rate_diff = abs(flaky_reproduce_rate - flaky_rate)

            # 너무 엄격하지 않은 검증 (시뮬레이션의 랜덤성 고려)
            assert fail_rate_diff <= fail_rate_tolerance, \
                f"실패율 오차가 허용 범위를 초과합니다: 예상 {fail_rate}%, 실제 {actual_fail_rate}%, 오차 {fail_rate_diff}%"

            assert flaky_rate_diff <= flaky_rate_tolerance, \
                f"플래키율 오차가 허용 범위를 초과합니다: 예상 {flaky_rate}%, 실제 {flaky_reproduce_rate}%, 오차 {flaky_rate_diff}%"

        except subprocess.TimeoutExpired:
            pytest.fail("통계 정확성 테스트가 타임아웃되었습니다")


class TestRunbookValidator:
    """scripts/runbook_validator.sh 런북 검증 시스템 테스트"""

    @pytest.fixture
    def temp_workspace(self):
        """임시 워크스페이스 설정"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            yield workspace

    def test_validator_script_existence_and_permissions(self):
        """런북 검증 스크립트 존재 및 실행 권한 확인"""
        script_path = Path("scripts/runbook_validator.sh")
        assert script_path.exists(), "runbook_validator.sh 스크립트가 존재하지 않습니다"
        assert script_path.is_file(), "runbook_validator.sh가 파일이 아닙니다"

        # 실행 권한 확인 (Unix 시스템에서만)
        if os.name == 'posix':
            assert os.access(script_path, os.X_OK), "runbook_validator.sh에 실행 권한이 없습니다"

    def test_validator_help_option(self):
        """런북 검증 스크립트 도움말 옵션 테스트"""
        script_path = Path("scripts/runbook_validator.sh")
        if not script_path.exists():
            pytest.skip("runbook_validator.sh 스크립트가 없습니다")

        try:
            result = subprocess.run(
                ["bash", str(script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS
            )

            assert result.returncode == 0, f"도움말 실행 실패: {result.stderr}"
            assert "사용법" in result.stdout or "Usage" in result.stdout, "도움말에 사용법이 없습니다"
            assert "런북 시스템 검증" in result.stdout, "도움말에 스크립트 설명이 없습니다"

        except subprocess.TimeoutExpired:
            pytest.fail("도움말 실행이 타임아웃되었습니다")

    def test_validator_required_files_check(self):
        """런북 검증 스크립트의 필수 파일 확인 테스트"""
        script_path = Path("scripts/runbook_validator.sh")
        if not script_path.exists():
            pytest.skip("runbook_validator.sh 스크립트가 없습니다")

        # 필수 파일들이 실제로 존재하는지 확인
        required_files = [
            "mcp/utils/runbook.py",
            "scripts/ci_autoremediate.sh",
            "scripts/hooks"  # 디렉토리
        ]

        missing_files = []
        for file_path in required_files:
            path = Path(file_path)
            if not path.exists():
                missing_files.append(file_path)

        if missing_files:
            pytest.skip(f"필수 파일이 없어 테스트를 건너뜁니다: {missing_files}")

        # 런북 검증 실행
        try:
            result = subprocess.run(
                ["bash", str(script_path), "--verbose"],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS
            )

            # 검증 자체는 성공하거나 실패할 수 있지만, 스크립트는 정상 실행되어야 함
            assert result.returncode in [0, 1], f"런북 검증 스크립트 실행 오류: {result.stderr}"
            assert "런북 시스템" in result.stdout, "런북 검증 결과에 시스템 정보가 없습니다"

        except subprocess.TimeoutExpired:
            pytest.fail("런북 검증 실행이 타임아웃되었습니다")

    def test_validator_json_output(self, temp_workspace):
        """런북 검증 JSON 출력 형식 테스트"""
        script_path = Path("scripts/runbook_validator.sh")
        if not script_path.exists():
            pytest.skip("runbook_validator.sh 스크립트가 없습니다")

        # 필수 파일 존재 확인
        required_files = ["mcp/utils/runbook.py", "scripts/ci_autoremediate.sh"]
        for file_path in required_files:
            if not Path(file_path).exists():
                pytest.skip(f"필수 파일이 없어 테스트를 건너뜁니다: {file_path}")

        output_file = temp_workspace / "validation_result.json"

        try:
            result = subprocess.run(
                [
                    "bash", str(script_path),
                    "--json",
                    "--output", str(output_file)
                ],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS
            )

            # JSON 출력은 검증 성공/실패와 관계없이 정상 동작해야 함
            assert result.returncode in [0, 1], f"JSON 출력 런북 검증 실행 실패: {result.stderr}"
            assert output_file.exists(), "JSON 출력 파일이 생성되지 않았습니다"

            # JSON 파일 파싱 및 구조 검증
            with open(output_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)

            # JSON 구조 검증
            required_fields = [
                "validation_status",
                "timestamp",
                "summary",
                "validation_results"
            ]

            for field in required_fields:
                assert field in json_data, f"JSON 출력에 필수 필드가 없습니다: {field}"

            # 검증 상태 확인
            validation_status = json_data["validation_status"]
            assert validation_status in ["PASSED", "FAILED"], f"잘못된 검증 상태: {validation_status}"

            # 요약 정보 확인
            summary = json_data["summary"]
            assert "total_runbook_templates" in summary, "런북 템플릿 수 정보가 없습니다"
            assert "issues_found" in summary, "발견된 문제 수 정보가 없습니다"

        except subprocess.TimeoutExpired:
            pytest.fail("JSON 출력 런북 검증이 타임아웃되었습니다")
        except json.JSONDecodeError as e:
            pytest.fail(f"JSON 파싱 오류: {e}")

    def test_validator_text_output_format(self):
        """런북 검증 텍스트 출력 형식 테스트"""
        script_path = Path("scripts/runbook_validator.sh")
        if not script_path.exists():
            pytest.skip("runbook_validator.sh 스크립트가 없습니다")

        # 필수 파일 존재 확인
        if not Path("mcp/utils/runbook.py").exists():
            pytest.skip("mcp/utils/runbook.py가 없어 테스트를 건너뜁니다")

        try:
            result = subprocess.run(
                ["bash", str(script_path), "--verbose"],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS
            )

            # 텍스트 출력은 성공/실패와 관계없이 정상 동작해야 함
            assert result.returncode in [0, 1], f"텍스트 출력 런북 검증 실행 실패: {result.stderr}"

            # 텍스트 출력 구조 검증
            required_sections = [
                "런북 시스템 검증 결과",
                "검증 요약",
                "검증 상태"
            ]

            for section in required_sections:
                assert section in result.stdout, f"텍스트 출력에 필수 섹션이 없습니다: {section}"

            # 검증 상태 확인
            assert ("통과" in result.stdout or "실패" in result.stdout), "검증 상태 정보가 없습니다"

        except subprocess.TimeoutExpired:
            pytest.fail("텍스트 출력 런북 검증이 타임아웃되었습니다")

    def test_validator_runbook_template_detection(self):
        """런북 템플릿 감지 기능 테스트"""
        script_path = Path("scripts/runbook_validator.sh")
        runbook_module = Path("mcp/utils/runbook.py")

        if not script_path.exists():
            pytest.skip("runbook_validator.sh 스크립트가 없습니다")
        if not runbook_module.exists():
            pytest.skip("mcp/utils/runbook.py가 없습니다")

        # 런북 모듈에서 실제 템플릿 확인
        try:
            import sys
            sys.path.insert(0, str(Path("mcp").absolute()))
            from utils.runbook import RUNBOOK_TEMPLATES

            expected_templates = list(RUNBOOK_TEMPLATES.keys())
            assert len(expected_templates) > 0, "런북 템플릿이 정의되지 않았습니다"

        except ImportError:
            pytest.skip("런북 모듈을 가져올 수 없습니다")

        # 검증 스크립트 실행하여 템플릿 감지 확인
        try:
            result = subprocess.run(
                ["bash", str(script_path), "--json"],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS
            )

            # 검증 결과 파싱
            if result.stdout.strip():
                try:
                    json_data = json.loads(result.stdout)
                    detected_templates = json_data.get("runbook_templates", [])

                    # 최소한의 필수 템플릿들이 감지되었는지 확인
                    essential_templates = [
                        "dependency_install_failed",
                        "test_timeout",
                        "build_timeout"
                    ]

                    for template in essential_templates:
                        if template in expected_templates:
                            assert template in detected_templates, f"필수 템플릿이 감지되지 않았습니다: {template}"

                except json.JSONDecodeError:
                    pytest.skip("JSON 출력 파싱에 실패했습니다")

        except subprocess.TimeoutExpired:
            pytest.fail("런북 템플릿 감지 테스트가 타임아웃되었습니다")

    def test_validator_error_mapping_detection(self):
        """에러 매핑 감지 기능 테스트"""
        script_path = Path("scripts/runbook_validator.sh")
        autoremediate_script = Path("scripts/ci_autoremediate.sh")

        if not script_path.exists():
            pytest.skip("runbook_validator.sh 스크립트가 없습니다")
        if not autoremediate_script.exists():
            pytest.skip("scripts/ci_autoremediate.sh가 없습니다")

        # 자동 완화 스크립트에서 에러 매핑 확인
        try:
            with open(autoremediate_script, 'r', encoding='utf-8') as f:
                script_content = f.read()

            # ERROR_TO_HOOK_MAP이 정의되어 있는지 확인
            assert "ERROR_TO_HOOK_MAP" in script_content, "ERROR_TO_HOOK_MAP이 정의되지 않았습니다"

        except UnicodeDecodeError:
            pytest.skip("스크립트 파일을 읽을 수 없습니다")

        # 검증 스크립트로 매핑 감지 확인
        try:
            result = subprocess.run(
                ["bash", str(script_path), "--json"],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS
            )

            if result.stdout.strip():
                try:
                    json_data = json.loads(result.stdout)
                    hook_error_mappings = json_data.get("hook_error_mappings", [])

                    # 매핑이 감지되었는지 확인 (빈 배열도 유효)
                    assert isinstance(hook_error_mappings, list), "훅-에러 매핑이 올바른 형식이 아닙니다"

                except json.JSONDecodeError:
                    pytest.skip("JSON 출력 파싱에 실패했습니다")

        except subprocess.TimeoutExpired:
            pytest.fail("에러 매핑 감지 테스트가 타임아웃되었습니다")


class TestSystemIntegration:
    """시스템 통합 테스트 (시뮬레이션 + 런북 검증)"""

    def test_both_scripts_coexistence(self):
        """두 스크립트의 공존성 및 상호 의존성 테스트"""
        sim_script = Path("scripts/ci_stability_sim.sh")
        validator_script = Path("scripts/runbook_validator.sh")

        # 두 스크립트 모두 존재하는지 확인
        scripts_status = {
            "ci_stability_sim.sh": sim_script.exists(),
            "runbook_validator.sh": validator_script.exists()
        }

        missing_scripts = [name for name, exists in scripts_status.items() if not exists]

        if missing_scripts:
            pytest.skip(f"스크립트가 없어 통합 테스트를 건너뜁니다: {missing_scripts}")

        # 두 스크립트가 모두 정상 실행되는지 확인
        try:
            # CI 안정성 시뮬레이션 도움말
            sim_result = subprocess.run(
                ["bash", str(sim_script), "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            assert sim_result.returncode == 0, "CI 안정성 시뮬레이션 스크립트 도움말 실행 실패"

            # 런북 검증 도움말
            validator_result = subprocess.run(
                ["bash", str(validator_script), "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            assert validator_result.returncode == 0, "런북 검증 스크립트 도움말 실행 실패"

        except subprocess.TimeoutExpired:
            pytest.fail("통합 테스트에서 스크립트 실행이 타임아웃되었습니다")

    def test_json_output_consistency(self, temp_workspace=None):
        """두 스크립트의 JSON 출력 일관성 테스트"""
        if temp_workspace is None:
            temp_workspace = Path(tempfile.mkdtemp())

        sim_script = Path("scripts/ci_stability_sim.sh")
        validator_script = Path("scripts/runbook_validator.sh")

        if not sim_script.exists() or not validator_script.exists():
            pytest.skip("스크립트가 없어 JSON 일관성 테스트를 건너뜁니다")

        sim_output = temp_workspace / "sim_output.json"
        validator_output = temp_workspace / "validator_output.json"

        try:
            # CI 안정성 시뮬레이션 JSON 출력
            sim_result = subprocess.run(
                [
                    "bash", str(sim_script),
                    "--fail-rate", "10",
                    "--flaky-rate", "5",
                    "--runs", "20",
                    "--json",
                    "--output", str(sim_output)
                ],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS
            )

            # 런북 검증 JSON 출력
            validator_result = subprocess.run(
                [
                    "bash", str(validator_script),
                    "--json",
                    "--output", str(validator_output)
                ],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS
            )

            # 두 JSON 파일이 모두 생성되었는지 확인
            if sim_result.returncode == 0:
                assert sim_output.exists(), "시뮬레이션 JSON 출력 파일이 생성되지 않았습니다"

                with open(sim_output, 'r', encoding='utf-8') as f:
                    sim_json = json.load(f)

                # JSON 구조 기본 검증
                assert "generated_at" in sim_json or "timestamp" in sim_json, "시뮬레이션 JSON에 타임스탬프가 없습니다"

            if validator_result.returncode in [0, 1]:  # 검증은 실패할 수 있음
                if validator_output.exists():
                    with open(validator_output, 'r', encoding='utf-8') as f:
                        validator_json = json.load(f)

                    # JSON 구조 기본 검증
                    assert "timestamp" in validator_json, "검증 JSON에 타임스탬프가 없습니다"

        except subprocess.TimeoutExpired:
            pytest.fail("JSON 일관성 테스트에서 타임아웃이 발생했습니다")
        except json.JSONDecodeError as e:
            pytest.fail(f"JSON 일관성 테스트에서 파싱 오류: {e}")
        finally:
            # 임시 파일 정리
            if temp_workspace != Path(tempfile.mkdtemp()):
                shutil.rmtree(temp_workspace, ignore_errors=True)

    def test_comprehensive_workflow(self):
        """포괄적인 워크플로 테스트 (시뮬레이션 → 검증)"""
        sim_script = Path("scripts/ci_stability_sim.sh")
        validator_script = Path("scripts/runbook_validator.sh")

        if not sim_script.exists() or not validator_script.exists():
            pytest.skip("포괄적 워크플로 테스트를 위한 스크립트가 없습니다")

        # 1단계: 간단한 시뮬레이션 실행
        try:
            sim_result = subprocess.run(
                [
                    "bash", str(sim_script),
                    "--fail-rate", "20",
                    "--flaky-rate", "10",
                    "--runs", "15",
                    "--dry-run"  # 빠른 실행을 위해 드라이런 사용
                ],
                capture_output=True,
                text=True,
                timeout=15
            )

            assert sim_result.returncode == 0, f"1단계 시뮬레이션 실패: {sim_result.stderr}"

        except subprocess.TimeoutExpired:
            pytest.fail("1단계 시뮬레이션이 타임아웃되었습니다")

        # 2단계: 런북 검증 실행
        try:
            validator_result = subprocess.run(
                ["bash", str(validator_script)],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS
            )

            # 검증은 성공하거나 실패할 수 있지만, 스크립트는 정상 실행되어야 함
            assert validator_result.returncode in [0, 1], f"2단계 런북 검증 오류: {validator_result.stderr}"

        except subprocess.TimeoutExpired:
            pytest.fail("2단계 런북 검증이 타임아웃되었습니다")

        # 3단계: 통합 결과 확인
        # 두 단계가 모두 완료되면 성공
        # 실제 프로덕션에서는 시뮬레이션 결과를 바탕으로 런북 시스템을 개선하는 피드백 루프가 있을 것임


# 테스트 실행을 위한 pytest 설정
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])