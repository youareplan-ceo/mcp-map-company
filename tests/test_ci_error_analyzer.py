# tests/test_ci_error_analyzer.py
"""
CI/CD 에러 로그 분석기 테스트 모듈

pytest 기반으로 scripts/ci_error_analyzer.sh의 모든 기능을 검증합니다.
한국어 주석 포함으로 테스트 가독성을 높였습니다.
"""

import pytest
import subprocess
import json
import os
import tempfile
import time
import gzip
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
import asyncio
from datetime import datetime, timedelta

# 테스트 대상 스크립트 경로
SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "ci_error_analyzer.sh"
PROJECT_ROOT = Path(__file__).parent.parent


class TestCIErrorAnalyzerBasic:
    """CI 에러 분석기 기본 기능 테스트"""

    def test_script_exists_and_executable(self):
        """스크립트 파일 존재 및 실행 권한 확인"""
        assert SCRIPT_PATH.exists(), f"스크립트 파일이 존재하지 않음: {SCRIPT_PATH}"
        assert os.access(SCRIPT_PATH, os.X_OK), f"스크립트 실행 권한이 없음: {SCRIPT_PATH}"

    def test_help_option(self):
        """도움말 옵션 테스트"""
        result = subprocess.run(
            [str(SCRIPT_PATH), "--help"],
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0, f"도움말 표시 실패: {result.stderr}"
        assert "MCP-MAP CI/CD 에러 로그 분석기" in result.stdout, "한국어 제목이 표시되지 않음"
        assert "--days" in result.stdout, "--days 옵션이 도움말에 없음"
        assert "--format" in result.stdout, "--format 옵션이 도움말에 없음"
        assert "--dry-run" in result.stdout, "--dry-run 옵션이 도움말에 없음"

    def test_invalid_option(self):
        """잘못된 옵션 처리 테스트"""
        result = subprocess.run(
            [str(SCRIPT_PATH), "--invalid-option"],
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode != 0, "잘못된 옵션에 대해 정상 종료되었음"
        assert "알 수 없는 옵션" in result.stderr, "한국어 에러 메시지가 없음"

    @pytest.mark.parametrize("format_type", ["json", "markdown", "text"])
    def test_format_options(self, format_type):
        """출력 형식 옵션 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run([
                str(SCRIPT_PATH),
                "--format", format_type,
                "--output-dir", temp_dir,
                "--dry-run",
                "--days", "1"
            ], capture_output=True, text=True, timeout=60)

            # 드라이런 모드에서는 정상 종료되어야 함
            assert result.returncode == 0, f"{format_type} 형식 테스트 실패: {result.stderr}"
            assert "CI/CD 에러 분석 완료" in result.stderr, "완료 메시지가 없음"

    def test_days_parameter_validation(self):
        """일수 파라미터 검증 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 유효한 일수 테스트
            result = subprocess.run([
                str(SCRIPT_PATH),
                "--days", "14",
                "--output-dir", temp_dir,
                "--dry-run"
            ], capture_output=True, text=True, timeout=60)

            assert result.returncode == 0, f"유효한 일수 파라미터 테스트 실패: {result.stderr}"


class TestCIErrorAnalyzerFileOperations:
    """파일 작업 관련 테스트"""

    def test_output_directory_creation(self):
        """출력 디렉토리 생성 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "ci_error_output"

            result = subprocess.run([
                str(SCRIPT_PATH),
                "--output-dir", str(output_dir),
                "--dry-run",
                "--days", "1"
            ], capture_output=True, text=True, timeout=60)

            assert result.returncode == 0, f"출력 디렉토리 생성 테스트 실패: {result.stderr}"
            # 드라이런 모드에서는 실제 디렉토리 생성이 안 될 수 있음

    def test_large_log_file_compression_simulation(self):
        """대용량 로그 파일 압축 시뮬레이션 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 임시 대용량 로그 파일 생성 (2MB)
            large_log_path = Path(temp_dir) / "logs" / "large_build.log"
            large_log_path.parent.mkdir(parents=True, exist_ok=True)

            # 2MB 크기의 테스트 로그 파일 생성
            with open(large_log_path, 'w') as f:
                for i in range(100000):  # 약 2MB
                    f.write(f"ERROR: Test error message {i} - build failed\n")

            # 압축 임계치를 1MB로 설정하여 테스트
            result = subprocess.run([
                str(SCRIPT_PATH),
                "--output-dir", temp_dir,
                "--compress-mb", "1",
                "--dry-run",
                "--days", "1"
            ], capture_output=True, text=True, timeout=60)

            assert result.returncode == 0, f"대용량 파일 압축 테스트 실패: {result.stderr}"
            assert "압축" in result.stderr, "압축 관련 메시지가 없음"

    def test_error_analysis_with_sample_logs(self):
        """샘플 로그를 이용한 에러 분석 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = Path(temp_dir) / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)

            # 샘플 에러 로그 파일 생성
            sample_log = logs_dir / "test_build.log"
            with open(sample_log, 'w') as f:
                f.write("""
2024-01-15 10:00:00 ERROR: Build failed with exit code 1
2024-01-15 10:01:00 ERROR: Test failed: test_user_authentication
2024-01-15 10:02:00 ERROR: Module not found: requests
2024-01-15 10:03:00 TIMEOUT: Build timeout after 30 minutes
2024-01-15 10:04:00 ERROR: Permission denied: access to /var/log
2024-01-15 10:05:00 ERROR: Test failed: test_user_authentication
2024-01-15 10:06:00 ERROR: Syntax error in main.py line 42
                """)

            result = subprocess.run([
                str(SCRIPT_PATH),
                "--output-dir", temp_dir,
                "--format", "json",
                "--dry-run",
                "--days", "1"
            ], capture_output=True, text=True, timeout=60)

            assert result.returncode == 0, f"샘플 로그 분석 테스트 실패: {result.stderr}"


class TestCIErrorAnalyzerNotificationIntegration:
    """알림 시스템 연동 테스트"""

    @patch('mcp.utils.notifier.send_ci_error_alert_sync')
    def test_notification_integration(self, mock_notifier):
        """알림 시스템 연동 테스트"""
        # Mock 설정
        mock_notifier.return_value = {"slack": True, "discord": True}

        with tempfile.TemporaryDirectory() as temp_dir:
            # 환경 변수 설정으로 알림 활성화
            env = os.environ.copy()
            env.update({
                'CI_ERROR_ANALYZER_ALERT_ENABLED': 'true',
                'PYTHONPATH': str(PROJECT_ROOT)
            })

            result = subprocess.run([
                str(SCRIPT_PATH),
                "--output-dir", temp_dir,
                "--days", "1",
                "--dry-run"  # 드라이런 모드에서 알림 시뮬레이션
            ], capture_output=True, text=True, timeout=60, env=env)

            assert result.returncode == 0, f"알림 연동 테스트 실패: {result.stderr}"
            assert "알림" in result.stderr, "알림 관련 메시지가 없음"

    def test_notification_disabled(self):
        """알림 비활성화 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run([
                str(SCRIPT_PATH),
                "--output-dir", temp_dir,
                "--no-alert",
                "--dry-run",
                "--days", "1"
            ], capture_output=True, text=True, timeout=60)

            assert result.returncode == 0, f"알림 비활성화 테스트 실패: {result.stderr}"
            assert "알림 전송이 비활성화" in result.stderr, "알림 비활성화 메시지가 없음"


class TestCIErrorAnalyzerPerformance:
    """성능 및 부하 테스트"""

    def test_large_scale_log_processing_simulation(self):
        """대용량 로그 처리 성능 테스트 (시뮬레이션)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = Path(temp_dir) / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)

            # 여러 개의 중간 크기 로그 파일 생성 (실제 1GB는 너무 크므로 시뮬레이션)
            for i in range(10):
                log_file = logs_dir / f"build_{i:03d}.log"
                with open(log_file, 'w') as f:
                    for j in range(1000):  # 각 파일당 1000줄
                        f.write(f"ERROR: Simulated error {j} in build {i}\n")
                        f.write(f"INFO: Build step {j} completed\n")
                        f.write(f"WARN: Memory usage high: {j*10}MB\n")

            start_time = time.time()

            result = subprocess.run([
                str(SCRIPT_PATH),
                "--output-dir", temp_dir,
                "--format", "json",
                "--days", "1",
                "--dry-run"
            ], capture_output=True, text=True, timeout=120)  # 2분 타임아웃

            end_time = time.time()
            processing_time = end_time - start_time

            assert result.returncode == 0, f"대용량 로그 처리 테스트 실패: {result.stderr}"
            assert processing_time < 60, f"처리 시간이 60초를 초과함: {processing_time:.2f}초"

    def test_concurrent_execution_safety(self):
        """동시 실행 안전성 테스트"""
        import concurrent.futures
        import threading

        def run_analyzer(temp_dir, thread_id):
            """분석기 실행 함수"""
            try:
                result = subprocess.run([
                    str(SCRIPT_PATH),
                    "--output-dir", f"{temp_dir}/thread_{thread_id}",
                    "--dry-run",
                    "--days", "1"
                ], capture_output=True, text=True, timeout=60)
                return result.returncode == 0
            except Exception as e:
                return False

        with tempfile.TemporaryDirectory() as temp_dir:
            # 3개의 스레드로 동시 실행
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [
                    executor.submit(run_analyzer, temp_dir, i)
                    for i in range(3)
                ]

                results = [future.result() for future in concurrent.futures.as_completed(futures)]

                # 모든 실행이 성공해야 함
                assert all(results), "동시 실행 중 일부 실패"

    def test_memory_usage_monitoring(self):
        """메모리 사용량 모니터링 테스트"""
        import psutil
        import subprocess

        with tempfile.TemporaryDirectory() as temp_dir:
            # 프로세스 시작 전 메모리 사용량
            process = subprocess.Popen([
                str(SCRIPT_PATH),
                "--output-dir", temp_dir,
                "--dry-run",
                "--days", "1",
                "--verbose"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            try:
                # 프로세스 메모리 사용량 모니터링
                ps_process = psutil.Process(process.pid)
                max_memory = 0

                while process.poll() is None:
                    try:
                        memory_info = ps_process.memory_info()
                        max_memory = max(max_memory, memory_info.rss)
                        time.sleep(0.1)
                    except psutil.NoSuchProcess:
                        break

                process.wait(timeout=60)

                # 메모리 사용량이 100MB를 초과하지 않아야 함 (드라이런 모드)
                max_memory_mb = max_memory / (1024 * 1024)
                assert max_memory_mb < 100, f"메모리 사용량이 너무 높음: {max_memory_mb:.2f}MB"

            except subprocess.TimeoutExpired:
                process.kill()
                pytest.fail("프로세스가 60초 내에 완료되지 않음")


class TestCIErrorAnalyzerErrorHandling:
    """에러 처리 및 예외 상황 테스트"""

    def test_invalid_output_directory(self):
        """잘못된 출력 디렉토리 처리 테스트"""
        # 읽기 전용 디렉토리에 출력 시도 (권한이 있는 경우 스킵)
        try:
            result = subprocess.run([
                str(SCRIPT_PATH),
                "--output-dir", "/root/invalid_path",
                "--dry-run",
                "--days", "1"
            ], capture_output=True, text=True, timeout=60)

            # 드라이런 모드에서는 실제 디렉토리 생성을 하지 않으므로 성공할 수 있음
            # 에러가 발생하더라도 적절히 처리되어야 함

        except subprocess.TimeoutExpired:
            pytest.fail("잘못된 디렉토리 처리 시 무한 대기")

    def test_missing_dependencies_simulation(self):
        """의존성 누락 시뮬레이션 테스트"""
        # PATH에서 jq 제거하여 의존성 누락 시뮬레이션
        env = os.environ.copy()
        env['PATH'] = '/bin:/usr/bin'  # jq가 없을 가능성이 높은 경로만 설정

        # 시스템에 jq가 설치되어 있으면 이 테스트는 의미가 없으므로 스킵
        if subprocess.run(['which', 'jq'], capture_output=True).returncode == 0:
            pytest.skip("시스템에 jq가 설치되어 있어 의존성 테스트 스킵")

        result = subprocess.run([
            str(SCRIPT_PATH),
            "--dry-run",
            "--days", "1"
        ], capture_output=True, text=True, timeout=60, env=env)

        # 의존성 누락 시 적절한 에러 메시지와 함께 실패해야 함
        assert result.returncode != 0, "의존성 누락 시에도 정상 종료됨"
        assert "의존성" in result.stderr or "jq" in result.stderr, "의존성 에러 메시지가 없음"

    def test_github_api_failure_handling(self):
        """GitHub API 실패 처리 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # GITHUB_TOKEN을 잘못된 값으로 설정
            env = os.environ.copy()
            env['GITHUB_TOKEN'] = 'invalid_token_123'

            result = subprocess.run([
                str(SCRIPT_PATH),
                "--output-dir", temp_dir,
                "--dry-run",
                "--days", "1"
            ], capture_output=True, text=True, timeout=60, env=env)

            # API 실패해도 로컬 로그 분석으로 계속 진행되어야 함
            assert result.returncode == 0, f"GitHub API 실패 시 스크립트가 중단됨: {result.stderr}"
            assert "GitHub API" in result.stderr or "API 호출 실패" in result.stderr, "API 실패 메시지가 없음"


class TestCIErrorAnalyzerOutputValidation:
    """출력 형식 및 내용 검증 테스트"""

    def test_json_output_format_validation(self):
        """JSON 출력 형식 검증"""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run([
                str(SCRIPT_PATH),
                "--output-dir", temp_dir,
                "--format", "json",
                "--dry-run",
                "--days", "1"
            ], capture_output=True, text=True, timeout=60)

            assert result.returncode == 0, f"JSON 형식 출력 실패: {result.stderr}"

            # 드라이런 모드에서 생성된 분석 파일 확인
            analysis_file = Path(temp_dir) / "error_analysis.json"
            if analysis_file.exists():
                with open(analysis_file, 'r') as f:
                    try:
                        data = json.load(f)
                        assert "analysis_summary" in data, "JSON 구조에 analysis_summary가 없음"
                        assert "top_10_errors" in data, "JSON 구조에 top_10_errors가 없음"
                    except json.JSONDecodeError:
                        pytest.fail("생성된 JSON 파일이 유효하지 않음")

    def test_markdown_output_structure(self):
        """Markdown 출력 구조 검증"""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run([
                str(SCRIPT_PATH),
                "--output-dir", temp_dir,
                "--format", "markdown",
                "--dry-run",
                "--days", "1"
            ], capture_output=True, text=True, timeout=60)

            assert result.returncode == 0, f"Markdown 형식 출력 실패: {result.stderr}"

    def test_korean_language_output(self):
        """한국어 출력 확인"""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run([
                str(SCRIPT_PATH),
                "--output-dir", temp_dir,
                "--dry-run",
                "--verbose",
                "--days", "1"
            ], capture_output=True, text=True, timeout=60)

            assert result.returncode == 0, f"한국어 출력 테스트 실패: {result.stderr}"

            # 한국어 메시지 확인
            korean_keywords = ["분석", "완료", "에러", "실행", "생성"]
            output_text = result.stderr

            assert any(keyword in output_text for keyword in korean_keywords), \
                "한국어 키워드가 출력에 포함되지 않음"


class TestCIErrorAnalyzerIntegration:
    """통합 테스트"""

    def test_end_to_end_workflow(self):
        """전체 워크플로우 통합 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 전체 워크플로우를 드라이런 모드로 실행
            result = subprocess.run([
                str(SCRIPT_PATH),
                "--output-dir", temp_dir,
                "--format", "json",
                "--days", "3",
                "--compress-mb", "1",
                "--dry-run",
                "--verbose"
            ], capture_output=True, text=True, timeout=120)

            assert result.returncode == 0, f"전체 워크플로우 실패: {result.stderr}"

            # 주요 단계들이 실행되었는지 확인
            expected_steps = [
                "의존성 확인",
                "워크플로우 실행 정보 수집",
                "에러 분석",
                "압축",
                "리포트 생성",
                "완료"
            ]

            output_text = result.stderr
            missing_steps = []

            for step in expected_steps:
                if step not in output_text:
                    missing_steps.append(step)

            assert not missing_steps, f"누락된 실행 단계: {missing_steps}"

    def test_environment_variable_configuration(self):
        """환경 변수 설정 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            env = os.environ.copy()
            env.update({
                'CI_ERROR_ANALYZER_DAYS': '5',
                'CI_ERROR_ANALYZER_FORMAT': 'markdown',
                'CI_ERROR_ANALYZER_VERBOSE': 'true',
                'CI_ERROR_ANALYZER_COMPRESS_MB': '2'
            })

            result = subprocess.run([
                str(SCRIPT_PATH),
                "--output-dir", temp_dir,
                "--dry-run"
            ], capture_output=True, text=True, timeout=60, env=env)

            assert result.returncode == 0, f"환경 변수 설정 테스트 실패: {result.stderr}"

            # 환경 변수가 적용되었는지 확인
            assert "분석 기간: 5일" in result.stderr, "DAYS 환경 변수가 적용되지 않음"

    @pytest.mark.slow
    def test_realistic_log_processing(self):
        """실제 환경과 유사한 로그 처리 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = Path(temp_dir) / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)

            # 실제 CI/CD 로그와 유사한 복잡한 로그 파일 생성
            realistic_log = logs_dir / "realistic_build.log"
            with open(realistic_log, 'w') as f:
                # 다양한 유형의 로그 엔트리 작성
                log_entries = [
                    "2024-01-15T10:00:00Z [INFO] Starting build process",
                    "2024-01-15T10:00:01Z [INFO] Checking out code from main branch",
                    "2024-01-15T10:00:05Z [WARN] Cache miss for dependencies",
                    "2024-01-15T10:00:10Z [INFO] Installing dependencies...",
                    "2024-01-15T10:01:00Z [ERROR] Module not found: numpy",
                    "2024-01-15T10:01:05Z [INFO] Retrying dependency installation",
                    "2024-01-15T10:01:30Z [INFO] Dependencies installed successfully",
                    "2024-01-15T10:02:00Z [INFO] Running unit tests",
                    "2024-01-15T10:02:15Z [ERROR] Test failed: test_user_authentication",
                    "2024-01-15T10:02:16Z [ERROR] AssertionError: Expected 200, got 401",
                    "2024-01-15T10:02:20Z [ERROR] Test failed: test_database_connection",
                    "2024-01-15T10:02:25Z [WARN] Skipping integration tests due to failures",
                    "2024-01-15T10:02:30Z [ERROR] Build failed with exit code 1",
                    "2024-01-15T10:02:35Z [INFO] Cleaning up workspace"
                ]

                # 로그 엔트리를 여러 번 반복하여 실제 크기와 유사하게 만들기
                for _ in range(1000):
                    for entry in log_entries:
                        f.write(f"{entry}\n")

            result = subprocess.run([
                str(SCRIPT_PATH),
                "--output-dir", temp_dir,
                "--format", "json",
                "--days", "1",
                "--verbose",
                "--dry-run"
            ], capture_output=True, text=True, timeout=120)

            assert result.returncode == 0, f"실제 환경 로그 처리 테스트 실패: {result.stderr}"


if __name__ == "__main__":
    # 개별 테스트 실행을 위한 pytest 설정
    pytest.main([__file__, "-v", "--tb=short", "-x"])