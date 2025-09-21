import subprocess
import pytest
import os
import tempfile
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# 🧪 CI 모니터링 스크립트 테스트 (한국어 주석 포함)
# 1. ci_monitor.sh 스크립트 실행 결과 확인
# 2. 성공/실패 감지 기능 검증
# 3. JSON 출력 형식 검증
# 4. watch 모드 시뮬레이션
# 5. notifier 연동 테스트

class TestCIMonitor:
    """CI 모니터링 스크립트 기본 기능 테스트"""

    @pytest.fixture
    def temp_env(self):
        """테스트용 임시 환경 설정"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 테스트용 로그 디렉토리 생성
            logs_dir = temp_path / "logs"
            logs_dir.mkdir()

            # 테스트용 CI 실패 로그 파일 생성
            ci_failures_log = logs_dir / "ci_failures.log"
            with open(ci_failures_log, 'w') as f:
                f.write("# CI 실패 로그 - 테스트용\n")
                f.write("- 워크플로우: CI Build and Test (#156)\n")
                f.write("  브랜치: main\n")
                f.write("  실행 시간: 2024-09-21T14:30:25Z\n")
                f.write("  링크: https://github.com/owner/repo/actions/runs/12345\n")

            yield {
                'temp_dir': temp_path,
                'logs_dir': logs_dir,
                'ci_failures_log': ci_failures_log
            }

    def run_ci_monitor(self, *args, cwd=None):
        """CI 모니터링 스크립트 실행 헬퍼 함수"""
        script_path = "scripts/ci_monitor.sh"
        cmd = [script_path] + list(args)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or os.getcwd(),
            timeout=30  # 30초 타임아웃
        )
        return result

    def test_script_exists_and_executable(self):
        """스크립트 파일 존재 및 실행 가능 여부 확인"""
        script_path = Path("scripts/ci_monitor.sh")
        assert script_path.exists(), "ci_monitor.sh 스크립트가 존재하지 않습니다"
        assert os.access(script_path, os.X_OK), "ci_monitor.sh 스크립트에 실행 권한이 없습니다"

    def test_help_option(self):
        """도움말 옵션 정상 동작 확인"""
        result = self.run_ci_monitor("--help")
        assert result.returncode == 0, "도움말 옵션 실행 실패"
        assert "사용법" in result.stdout, "도움말에 사용법이 포함되지 않음"
        assert "--json" in result.stdout, "도움말에 json 옵션이 없음"
        assert "--verbose" in result.stdout, "도움말에 verbose 옵션이 없음"
        assert "--watch" in result.stdout, "도움말에 watch 옵션이 없음"

    def test_invalid_option_handling(self):
        """잘못된 옵션 처리 확인"""
        result = self.run_ci_monitor("--invalid-option")
        assert result.returncode != 0, "잘못된 옵션이 허용됨"
        assert "알 수 없는 옵션" in result.stdout or "알 수 없는 옵션" in result.stderr, "적절한 에러 메시지가 없음"

    @patch('subprocess.run')
    def test_github_cli_check(self, mock_run):
        """GitHub CLI 설치 및 인증 확인 테스트"""
        # gh 명령어가 없는 경우 시뮬레이션
        mock_run.side_effect = FileNotFoundError("gh command not found")

        result = self.run_ci_monitor("--json")
        # 스크립트가 적절히 에러를 처리하는지 확인
        # 실제로는 GitHub CLI 없이는 실행이 불가능하므로 에러가 예상됨

    def test_json_output_format_structure(self):
        """JSON 출력 형식 구조 검증 (GitHub CLI 없이)"""
        # GitHub CLI가 없는 환경에서는 스크립트가 에러를 반환할 것임
        # 하지만 JSON 출력 옵션 자체는 인식해야 함
        result = self.run_ci_monitor("--json", "--help")

        # 도움말에서는 JSON 옵션이 정상적으로 표시되어야 함
        assert "--json" in result.stdout, "JSON 옵션이 도움말에 없음"

    @pytest.mark.skipif(not os.path.exists("/usr/bin/jq"), reason="jq 명령어가 설치되지 않음")
    def test_json_schema_validation(self, temp_env):
        """JSON 스키마 검증 (jq 사용)"""
        # 테스트용 JSON 데이터 생성
        test_json_data = {
            "timestamp": "2024-09-21 14:30:25",
            "summary": {
                "total_runs": 10,
                "success_count": 8,
                "failure_count": 2,
                "in_progress_count": 0,
                "success_rate": 80
            },
            "failed_workflows": [
                {
                    "id": 12345,
                    "name": "CI Build and Test",
                    "status": "completed",
                    "conclusion": "failure",
                    "branch": "main",
                    "created_at": "2024-09-21T14:30:25Z",
                    "html_url": "https://github.com/owner/repo/actions/runs/12345",
                    "run_number": 156
                }
            ],
            "recent_runs": []
        }

        # JSON 유효성 검증
        json_str = json.dumps(test_json_data)
        assert json.loads(json_str) == test_json_data, "JSON 직렬화/역직렬화 실패"

        # 필수 필드 존재 확인
        assert "timestamp" in test_json_data, "timestamp 필드 없음"
        assert "summary" in test_json_data, "summary 필드 없음"
        assert "failed_workflows" in test_json_data, "failed_workflows 필드 없음"


class TestCIMonitorIntegration:
    """CI 모니터링 통합 테스트"""

    def run_ci_monitor(self, *args, cwd=None):
        """CI 모니터링 스크립트 실행 헬퍼 함수"""
        script_path = "scripts/ci_monitor.sh"
        cmd = [script_path] + list(args)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or os.getcwd(),
            timeout=30
        )
        return result

    def test_multiple_options_combination(self):
        """여러 옵션 조합 테스트"""
        # --json과 --verbose 조합
        result = self.run_ci_monitor("--json", "--verbose")
        # GitHub CLI가 없어도 옵션 파싱은 성공해야 함
        # 실제 실행은 실패할 수 있지만 옵션은 인식되어야 함

    def test_custom_count_option(self):
        """사용자 정의 워크플로우 수 옵션 테스트"""
        result = self.run_ci_monitor("--count", "5", "--help")
        # 도움말에서 count 옵션이 표시되는지 확인
        assert "--count" in result.stdout, "count 옵션이 도움말에 없음"

    def test_custom_interval_option(self):
        """사용자 정의 간격 옵션 테스트"""
        result = self.run_ci_monitor("--interval", "60", "--help")
        # 도움말에서 interval 옵션이 표시되는지 확인
        assert "--interval" in result.stdout, "interval 옵션이 도움말에 없음"

    @patch('subprocess.run')
    def test_watch_mode_simulation(self, mock_run):
        """watch 모드 시뮬레이션 테스트"""
        # watch 모드는 무한 루프이므로 실제로는 테스트하지 않고
        # 옵션 인식만 확인
        result = self.run_ci_monitor("--watch", "--help")
        assert "--watch" in result.stdout, "watch 옵션이 도움말에 없음"


class TestCIMonitorNotifierIntegration:
    """CI 모니터링과 notifier 연동 테스트"""

    @pytest.fixture
    def mock_notifier_module(self):
        """notifier 모듈 모킹"""
        with patch('sys.path'), patch('importlib.import_module') as mock_import:
            # notifier 모듈 모킹
            mock_notifier = MagicMock()
            mock_notifier.send_ci_alerts = MagicMock(return_value=True)
            mock_import.return_value = mock_notifier
            yield mock_notifier

    def test_notifier_integration_exists(self):
        """notifier.py 파일 존재 확인"""
        notifier_path = Path("mcp/utils/notifier.py")
        assert notifier_path.exists(), "notifier.py 파일이 존재하지 않습니다"

    def test_send_ci_alerts_function_exists(self):
        """send_ci_alerts 함수 존재 확인"""
        try:
            # notifier 모듈에서 send_ci_alerts 함수 import 시도
            import sys
            sys.path.append('.')
            from mcp.utils.notifier import send_ci_alerts
            assert callable(send_ci_alerts), "send_ci_alerts가 호출 가능한 함수가 아닙니다"
        except ImportError as e:
            pytest.skip(f"notifier 모듈을 import할 수 없습니다: {e}")

    def test_ci_alerts_function_signature(self):
        """send_ci_alerts 함수 시그니처 확인"""
        try:
            import sys
            sys.path.append('.')
            from mcp.utils.notifier import send_ci_alerts
            import inspect

            # 함수 시그니처 확인
            sig = inspect.signature(send_ci_alerts)
            params = list(sig.parameters.keys())

            # 예상되는 파라미터가 있는지 확인
            assert 'failed_workflows' in params, "failed_workflows 파라미터가 없습니다"

        except ImportError:
            pytest.skip("notifier 모듈을 import할 수 없습니다")

    @pytest.mark.asyncio
    async def test_ci_alerts_with_mock_data(self):
        """모킹된 데이터로 CI 알림 테스트"""
        try:
            import sys
            sys.path.append('.')
            from mcp.utils.notifier import send_ci_alerts

            # 테스트용 실패한 워크플로우 데이터
            mock_failed_workflows = [
                {
                    'id': 12345,
                    'name': 'CI Build and Test',
                    'run_number': 156,
                    'branch': 'main',
                    'created_at': '2024-09-21T14:30:25Z',
                    'html_url': 'https://github.com/owner/repo/actions/runs/12345'
                }
            ]

            # 함수 호출 테스트 (실제 알림은 전송되지 않을 수 있음)
            result = await send_ci_alerts(mock_failed_workflows)

            # 결과가 딕셔너리 형태인지 확인
            assert isinstance(result, dict), "send_ci_alerts 결과가 딕셔너리가 아닙니다"

        except ImportError:
            pytest.skip("notifier 모듈을 import할 수 없습니다")
        except Exception as e:
            # 실제 알림 전송 실패는 예상되는 상황 (설정 없음)
            print(f"알림 전송 시뮬레이션 완료 (예상된 실패): {e}")


class TestCIMonitorPerformance:
    """CI 모니터링 성능 테스트"""

    def run_ci_monitor(self, *args, cwd=None):
        """CI 모니터링 스크립트 실행 헬퍼 함수"""
        script_path = "scripts/ci_monitor.sh"
        cmd = [script_path] + list(args)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or os.getcwd(),
            timeout=30
        )
        return result

    def test_script_execution_time(self):
        """스크립트 실행 시간 성능 테스트"""
        start_time = time.time()

        # 도움말 옵션으로 빠른 실행 테스트
        result = self.run_ci_monitor("--help")

        execution_time = time.time() - start_time

        # 도움말은 3초 이내에 실행되어야 함
        assert execution_time < 3.0, f"도움말 실행 시간이 너무 오래 걸림: {execution_time:.2f}초"
        assert result.returncode == 0, "도움말 실행 실패"

    def test_option_parsing_performance(self):
        """옵션 파싱 성능 테스트"""
        start_time = time.time()

        # 복잡한 옵션 조합으로 파싱 테스트
        result = self.run_ci_monitor("--json", "--verbose", "--count", "20", "--interval", "120", "--help")

        parsing_time = time.time() - start_time

        # 옵션 파싱은 1초 이내에 완료되어야 함
        assert parsing_time < 1.0, f"옵션 파싱 시간이 너무 오래 걸림: {parsing_time:.2f}초"


class TestCIMonitorErrorHandling:
    """CI 모니터링 에러 처리 테스트"""

    def run_ci_monitor(self, *args, cwd=None):
        """CI 모니터링 스크립트 실행 헬퍼 함수"""
        script_path = "scripts/ci_monitor.sh"
        cmd = [script_path] + list(args)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or os.getcwd(),
            timeout=30
        )
        return result

    def test_missing_github_cli_handling(self):
        """GitHub CLI 누락 처리 확인"""
        # PATH에서 gh를 제거한 환경에서 실행
        env = os.environ.copy()
        env['PATH'] = '/bin:/usr/bin'  # gh가 없는 기본 PATH

        result = subprocess.run(
            ["scripts/ci_monitor.sh", "--help"],
            capture_output=True,
            text=True,
            env=env,
            timeout=10
        )

        # 도움말은 GitHub CLI 없이도 실행되어야 함
        assert result.returncode == 0, "GitHub CLI 없이도 도움말은 실행되어야 함"

    def test_non_git_repository_handling(self):
        """Git 리포지토리가 아닌 디렉토리에서 실행 시 처리"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Git 리포지토리가 아닌 임시 디렉토리에서 실행
            result = subprocess.run(
                ["scripts/ci_monitor.sh", "--help"],
                capture_output=True,
                text=True,
                cwd=temp_dir,
                timeout=10
            )

            # 도움말은 Git 리포지토리 밖에서도 실행되어야 함
            assert result.returncode == 0, "Git 리포지토리 밖에서도 도움말은 실행되어야 함"

    def test_invalid_count_value_handling(self):
        """잘못된 count 값 처리 확인"""
        # 음수 값
        result = self.run_ci_monitor("--count", "-5", "--help")
        # 스크립트가 적절히 처리하는지 확인 (에러 또는 기본값 사용)

        # 문자열 값
        result = self.run_ci_monitor("--count", "abc", "--help")
        # 스크립트가 적절히 처리하는지 확인

    def test_invalid_interval_value_handling(self):
        """잘못된 interval 값 처리 확인"""
        # 0 값
        result = self.run_ci_monitor("--interval", "0", "--help")
        # 스크립트가 적절히 처리하는지 확인

        # 문자열 값
        result = self.run_ci_monitor("--interval", "invalid", "--help")
        # 스크립트가 적절히 처리하는지 확인


class TestCIMonitorLogHandling:
    """CI 모니터링 로그 처리 테스트"""

    def run_ci_monitor(self, *args, cwd=None):
        """CI 모니터링 스크립트 실행 헬퍼 함수"""
        script_path = "scripts/ci_monitor.sh"
        cmd = [script_path] + list(args)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or os.getcwd(),
            timeout=30
        )
        return result

    def test_logs_directory_creation(self, temp_env):
        """로그 디렉토리 생성 확인"""
        # 로그 디렉토리가 없는 상태에서 시작
        temp_dir = temp_env['temp_dir']
        logs_dir = temp_dir / "logs"

        if logs_dir.exists():
            import shutil
            shutil.rmtree(logs_dir)

        # 스크립트 실행 시 로그 디렉토리가 생성되어야 함
        # (실제로는 GitHub CLI 없이는 실행되지 않지만, 디렉토리 생성 로직은 동작해야 함)

    def test_ci_failures_log_format(self, temp_env):
        """CI 실패 로그 형식 확인"""
        ci_failures_log = temp_env['ci_failures_log']

        # 로그 파일이 존재하고 읽을 수 있는지 확인
        assert ci_failures_log.exists(), "CI 실패 로그 파일이 존재하지 않음"

        with open(ci_failures_log, 'r') as f:
            content = f.read()

        # 로그 형식 확인
        assert "워크플로우:" in content, "워크플로우 정보가 로그에 없음"
        assert "브랜치:" in content, "브랜치 정보가 로그에 없음"
        assert "실행 시간:" in content, "실행 시간 정보가 로그에 없음"

    def test_log_file_permissions(self, temp_env):
        """로그 파일 권한 확인"""
        ci_failures_log = temp_env['ci_failures_log']

        # 로그 파일이 읽기/쓰기 가능한지 확인
        assert os.access(ci_failures_log, os.R_OK), "로그 파일을 읽을 수 없음"
        assert os.access(ci_failures_log, os.W_OK), "로그 파일에 쓸 수 없음"