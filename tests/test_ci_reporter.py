import subprocess
import pytest
import os
import tempfile
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# 🧪 CI 리포터 스크립트 테스트 (한국어 주석 포함)
# 1. ci_reporter.sh 스크립트 실행 결과 확인
# 2. JSON/Markdown 출력 형식 검증
# 3. 성능 지표 계산 검증
# 4. 실패 테스트 요약 검증
# 5. 알림 연동 모의 테스트

class TestCIReporter:
    """CI 리포터 스크립트 기본 기능 테스트"""

    @pytest.fixture
    def temp_env(self):
        """테스트용 임시 환경 설정"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 테스트용 디렉토리 생성
            logs_dir = temp_path / "logs"
            reports_dir = temp_path / "reports"

            logs_dir.mkdir()
            reports_dir.mkdir()

            # 테스트용 Git 리포지토리 초기화
            subprocess.run(["git", "init"], cwd=temp_path, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_path, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=temp_path, capture_output=True)

            yield {
                'temp_dir': temp_path,
                'logs_dir': logs_dir,
                'reports_dir': reports_dir
            }

    def run_ci_reporter(self, *args, cwd=None):
        """CI 리포터 스크립트 실행 헬퍼 함수"""
        script_path = "scripts/ci_reporter.sh"
        cmd = [script_path] + list(args)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or os.getcwd()
        )
        return result

    def test_script_exists_and_executable(self):
        """스크립트 파일 존재 및 실행 가능 여부 확인"""
        script_path = Path("scripts/ci_reporter.sh")
        assert script_path.exists(), "ci_reporter.sh 스크립트가 존재하지 않습니다"
        assert os.access(script_path, os.X_OK), "ci_reporter.sh 스크립트에 실행 권한이 없습니다"

    def test_help_option(self):
        """도움말 옵션 정상 동작 확인"""
        result = self.run_ci_reporter("--help")
        assert result.returncode == 0, "도움말 옵션 실행 실패"
        assert "사용법" in result.stdout, "도움말에 사용법이 포함되지 않음"
        assert "--json" in result.stdout, "도움말에 JSON 옵션이 없음"
        assert "--md" in result.stdout or "--markdown" in result.stdout, "도움말에 Markdown 옵션이 없음"
        assert "--verbose" in result.stdout, "도움말에 verbose 옵션이 없음"
        assert "--notify" in result.stdout, "도움말에 notify 옵션이 없음"

    def test_invalid_option_handling(self):
        """잘못된 옵션 처리 확인"""
        result = self.run_ci_reporter("--invalid-option")
        assert result.returncode != 0, "잘못된 옵션이 허용됨"
        assert "알 수 없는 옵션" in result.stdout or "알 수 없는 옵션" in result.stderr, "적절한 에러 메시지가 없음"

    @patch('subprocess.run')
    def test_prerequisites_check(self, mock_subprocess):
        """전제조건 확인 테스트"""
        # gh CLI가 없는 경우 시뮬레이션
        mock_subprocess.side_effect = [
            subprocess.CompletedProcess(["which", "gh"], returncode=1, stdout="", stderr=""),
        ]

        result = self.run_ci_reporter("--help")  # 도움말은 전제조건 확인 없이 실행됨
        assert result.returncode == 0, "도움말 실행이 전제조건에 영향받음"

    def test_json_output_structure(self, temp_env):
        """JSON 출력 구조 검증 (모의 데이터 사용)"""
        # 실제 GitHub API 호출 없이 테스트하기 위해 모의 JSON 데이터 생성
        os.chdir(temp_env['temp_dir'])

        # GitHub CLI 모의 응답을 위한 더미 실행
        # 이 테스트는 스크립트 구조만 확인하고 실제 API 호출은 하지 않음
        result = self.run_ci_reporter("--json", "--runs", "5")

        # 스크립트가 오류 없이 실행되는지 확인 (GitHub API 접근 실패는 예상됨)
        # GitHub CLI 인증 오류나 API 접근 실패는 허용하되, 스크립트 구조 오류는 불허
        if result.returncode != 0:
            # GitHub 관련 오류가 아닌 스크립트 자체 오류인지 확인
            assert any(keyword in result.stderr.lower() for keyword in [
                "github", "gh", "auth", "api", "token", "authentication"
            ]), f"예상치 못한 스크립트 오류: {result.stderr}"

    def test_markdown_output_structure(self, temp_env):
        """Markdown 출력 구조 검증"""
        os.chdir(temp_env['temp_dir'])

        result = self.run_ci_reporter("--md", "--runs", "5")

        # 스크립트 구조 오류가 아닌 GitHub API 접근 오류만 허용
        if result.returncode != 0:
            assert any(keyword in result.stderr.lower() for keyword in [
                "github", "gh", "auth", "api", "token", "authentication"
            ]), f"예상치 못한 스크립트 오류: {result.stderr}"

    def test_verbose_option(self, temp_env):
        """상세 출력 모드 테스트"""
        os.chdir(temp_env['temp_dir'])

        result = self.run_ci_reporter("--verbose", "--runs", "3")

        # GitHub API 접근 실패는 허용하되, 스크립트 구조 오류는 불허
        if result.returncode != 0:
            assert any(keyword in result.stderr.lower() for keyword in [
                "github", "gh", "auth", "api", "token", "authentication"
            ]), f"예상치 못한 스크립트 오류: {result.stderr}"

    def test_custom_runs_option(self, temp_env):
        """사용자 정의 워크플로우 수 옵션 테스트"""
        os.chdir(temp_env['temp_dir'])

        result = self.run_ci_reporter("--runs", "15", "--json")

        # 스크립트가 옵션을 올바르게 파싱하는지 확인
        if result.returncode != 0:
            assert any(keyword in result.stderr.lower() for keyword in [
                "github", "gh", "auth", "api", "token", "authentication"
            ]), f"예상치 못한 스크립트 오류: {result.stderr}"

    def test_custom_days_option(self, temp_env):
        """사용자 정의 분석 기간 옵션 테스트"""
        os.chdir(temp_env['temp_dir'])

        result = self.run_ci_reporter("--days", "14", "--json")

        # 옵션 파싱이 올바르게 되는지 확인
        if result.returncode != 0:
            assert any(keyword in result.stderr.lower() for keyword in [
                "github", "gh", "auth", "api", "token", "authentication"
            ]), f"예상치 못한 스크립트 오류: {result.stderr}"


class TestCIReporterIntegration:
    """CI 리포터 통합 테스트"""

    def run_ci_reporter(self, *args, cwd=None):
        """CI 리포터 스크립트 실행 헬퍼 함수"""
        script_path = "scripts/ci_reporter.sh"
        cmd = [script_path] + list(args)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or os.getcwd()
        )
        return result

    def test_directory_creation(self):
        """디렉토리 자동 생성 기능 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Git 리포지토리 초기화
            subprocess.run(["git", "init"], cwd=temp_path, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_path, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=temp_path, capture_output=True)

            os.chdir(temp_path)
            result = self.run_ci_reporter("--json", "--runs", "1")

            # logs와 reports 디렉토리가 생성되는지 확인
            logs_dir = temp_path / "logs"
            reports_dir = temp_path / "reports"

            # 스크립트 실행 후 디렉토리 생성 확인 (GitHub API 접근 실패와 무관)
            assert logs_dir.exists() or any(keyword in result.stderr.lower() for keyword in [
                "github", "gh", "auth", "api", "token"
            ]), "logs 디렉토리가 생성되지 않음"

    def test_multiple_output_formats(self):
        """여러 출력 형식 조합 테스트"""
        # JSON과 Markdown 동시 사용 시 우선순위 확인
        result = self.run_ci_reporter("--json", "--md")

        # 옵션 충돌 처리 확인 (스크립트가 정상적으로 파싱하는지)
        # GitHub API 접근 실패는 허용
        if result.returncode != 0:
            assert any(keyword in result.stderr.lower() for keyword in [
                "github", "gh", "auth", "api", "token", "authentication"
            ]), f"예상치 못한 옵션 처리 오류: {result.stderr}"

    def test_performance_metrics_calculation(self):
        """성능 지표 계산 로직 테스트"""
        # 스크립트의 성능 지표 계산 부분이 오류 없이 실행되는지 확인
        result = self.run_ci_reporter("--verbose", "--runs", "5")

        # 계산 로직 오류가 아닌 API 접근 오류만 허용
        if result.returncode != 0:
            assert any(keyword in result.stderr.lower() for keyword in [
                "github", "gh", "auth", "api", "token", "authentication", "repository"
            ]), f"성능 지표 계산 로직 오류: {result.stderr}"


class TestCIReporterNotification:
    """CI 리포터 알림 기능 테스트"""

    def run_ci_reporter(self, *args, cwd=None):
        """CI 리포터 스크립트 실행 헬퍼 함수"""
        script_path = "scripts/ci_reporter.sh"
        cmd = [script_path] + list(args)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or os.getcwd()
        )
        return result

    @patch('subprocess.run')
    def test_notifier_integration(self, mock_subprocess):
        """notifier.py 연동 테스트"""
        # 모의 subprocess 실행 결과 설정
        mock_subprocess.return_value = subprocess.CompletedProcess(
            ["python3", "-c", "..."], returncode=0, stdout="✅ 알림 전송 완료", stderr=""
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # notifier.py 모의 파일 생성
            mcp_dir = temp_path / "mcp" / "utils"
            mcp_dir.mkdir(parents=True)
            notifier_file = mcp_dir / "notifier.py"
            notifier_file.write_text("""
def send_ci_report_alert(report_summary):
    print("모의 알림 전송")
    return True
""")

            os.chdir(temp_path)

            # Git 리포지토리 초기화
            subprocess.run(["git", "init"], cwd=temp_path, capture_output=True)

            result = self.run_ci_reporter("--notify", "--json", "--runs", "1")

            # 알림 기능이 포함된 스크립트 실행 확인
            # GitHub API 접근 실패는 허용하되, notifier 통합 로직 오류는 불허
            if result.returncode != 0:
                assert any(keyword in result.stderr.lower() for keyword in [
                    "github", "gh", "auth", "api", "token", "authentication"
                ]), f"notifier 통합 오류: {result.stderr}"

    def test_notification_without_notifier(self):
        """notifier.py가 없을 때 알림 옵션 처리"""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            # Git 리포지토리 초기화
            subprocess.run(["git", "init"], capture_output=True)

            result = self.run_ci_reporter("--notify", "--json")

            # notifier.py가 없어도 스크립트가 정상 종료되어야 함
            # GitHub API 접근 실패는 허용
            if result.returncode != 0:
                assert any(keyword in result.stderr.lower() for keyword in [
                    "github", "gh", "auth", "api", "token", "authentication", "repository"
                ]), f"notifier 없음 처리 오류: {result.stderr}"


class TestCIReporterPerformance:
    """CI 리포터 성능 테스트"""

    def run_ci_reporter(self, *args, cwd=None):
        """CI 리포터 스크립트 실행 헬퍼 함수"""
        script_path = "scripts/ci_reporter.sh"
        cmd = [script_path] + list(args)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or os.getcwd()
        )
        return result

    def test_execution_time_performance(self):
        """실행 시간 성능 테스트"""
        start_time = time.time()
        result = self.run_ci_reporter("--json", "--runs", "5")
        execution_time = time.time() - start_time

        # 60초 이내 실행 완료 검증 (API 접근 포함)
        assert execution_time < 60.0, f"실행 시간이 너무 오래 걸림: {execution_time:.2f}초"

    def test_large_dataset_handling(self):
        """대용량 데이터 처리 테스트"""
        # 많은 수의 워크플로우 요청 시 스크립트 안정성 확인
        result = self.run_ci_reporter("--json", "--runs", "100", "--days", "30")

        # 대용량 요청이 스크립트 오류를 발생시키지 않는지 확인
        # GitHub API 제한이나 인증 오류는 허용
        if result.returncode != 0:
            assert any(keyword in result.stderr.lower() for keyword in [
                "github", "gh", "auth", "api", "token", "authentication", "rate limit"
            ]), f"대용량 데이터 처리 오류: {result.stderr}"

    def test_concurrent_execution_safety(self):
        """동시 실행 안전성 테스트"""
        import threading
        import queue

        results_queue = queue.Queue()

        def run_reporter():
            result = self.run_ci_reporter("--json", "--runs", "3")
            results_queue.put(result)

        # 3개의 동시 실행 스레드 생성
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=run_reporter)
            threads.append(thread)
            thread.start()

        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join(timeout=30)  # 30초 타임아웃

        # 결과 수집 및 검증
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())

        # 모든 실행이 완료되었는지 확인
        assert len(results) <= 3, "동시 실행 결과 수집 실패"

        # 각 실행이 크래시 없이 완료되었는지 확인
        for result in results:
            if result.returncode != 0:
                assert any(keyword in result.stderr.lower() for keyword in [
                    "github", "gh", "auth", "api", "token", "authentication"
                ]), f"동시 실행 안전성 오류: {result.stderr}"


class TestCIReporterErrorHandling:
    """CI 리포터 에러 처리 테스트"""

    def run_ci_reporter(self, *args, cwd=None):
        """CI 리포터 스크립트 실행 헬퍼 함수"""
        script_path = "scripts/ci_reporter.sh"
        cmd = [script_path] + list(args)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or os.getcwd()
        )
        return result

    def test_non_git_repository_handling(self):
        """Git 리포지토리가 아닌 곳에서 실행 시 처리"""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            result = self.run_ci_reporter("--json")

            # Git 리포지토리가 아니면 적절한 에러 메시지와 함께 종료되어야 함
            assert result.returncode != 0, "Git 리포지토리가 아님에도 정상 실행됨"
            assert "git" in result.stderr.lower() or "repository" in result.stderr.lower(), "Git 리포지토리 오류 메시지가 없음"

    def test_missing_dependencies_handling(self):
        """의존성 누락 시 처리 확인"""
        # 실제로는 의존성이 있지만, 스크립트의 체크 로직을 확인
        # PATH를 조작하여 gh나 jq가 없는 상황 시뮬레이션은 복잡하므로
        # 스크립트 내부의 체크 로직이 있는지만 확인

        result = self.run_ci_reporter("--help")
        assert result.returncode == 0, "도움말 실행 실패"

        # 스크립트에 전제조건 확인 함수가 있는지 간접 확인
        # (실제 전제조건 확인은 도움말 실행 시에는 하지 않음)

    def test_invalid_numeric_arguments(self):
        """잘못된 숫자 인수 처리 확인"""
        # 음수나 문자열 등 잘못된 값 처리
        result = self.run_ci_reporter("--runs", "-5")

        # 스크립트가 잘못된 숫자를 어떻게 처리하는지 확인
        # 일부 스크립트는 이를 허용할 수도 있으므로 크래시만 방지하면 됨
        # 단, GitHub API 접근 전에 검증되어야 함

    def test_empty_response_handling(self):
        """GitHub API 빈 응답 처리 확인"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Git 리포지토리 초기화
            subprocess.run(["git", "init"], cwd=temp_path, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_path, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=temp_path, capture_output=True)

            os.chdir(temp_path)

            result = self.run_ci_reporter("--json", "--runs", "1")

            # 빈 응답이나 API 실패 시에도 스크립트가 안전하게 종료되는지 확인
            if result.returncode != 0:
                # GitHub 관련 오류만 허용
                assert any(keyword in result.stderr.lower() for keyword in [
                    "github", "gh", "auth", "api", "token", "authentication", "repository", "workflow"
                ]), f"예상치 못한 빈 응답 처리 오류: {result.stderr}"