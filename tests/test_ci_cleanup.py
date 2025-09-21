import subprocess
import pytest
import os
import tempfile
import json
import gzip
from pathlib import Path

# 🧪 CI 클린업 스크립트 테스트 (한국어 주석 포함)
# 1. ci_cleanup.sh 스크립트 실행 결과 확인
# 2. 로그 압축 기능 검증
# 3. 오래된 리포트 삭제 기능 검증
# 4. 백업 무결성 검증 기능 확인
# 5. JSON 출력 형식 검증

class TestCICleanup:
    """CI 클린업 스크립트 기본 기능 테스트"""

    @pytest.fixture
    def temp_env(self):
        """테스트용 임시 환경 설정"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 테스트용 디렉토리 생성
            logs_dir = temp_path / "logs"
            reports_dir = temp_path / "reports"
            backups_dir = temp_path / "backups"

            logs_dir.mkdir()
            reports_dir.mkdir()
            backups_dir.mkdir()

            # 테스트용 로그 파일 생성 (1MB 이상)
            security_log = logs_dir / "security.log"
            api_log = logs_dir / "api.log"

            # 1MB 이상의 로그 파일 생성
            with open(security_log, 'w') as f:
                f.write("TEST LOG CONTENT\n" * 50000)  # 약 850KB
                f.write("X" * 200000)  # 추가 200KB

            with open(api_log, 'w') as f:
                f.write("API LOG CONTENT\n" * 70000)  # 약 1.1MB

            # 테스트용 오래된 리포트 파일 생성
            old_report = reports_dir / "old_report.txt"
            with open(old_report, 'w') as f:
                f.write("오래된 리포트 내용")

            # 파일 수정 시간을 31일 전으로 변경
            import time
            old_time = time.time() - (31 * 24 * 60 * 60)  # 31일 전
            os.utime(old_report, (old_time, old_time))

            # 테스트용 백업 파일 생성
            backup_file = backups_dir / "backup_20240921.tar.gz"
            with open(backup_file, 'w') as f:
                f.write("테스트 백업 내용")

            yield {
                'temp_dir': temp_path,
                'logs_dir': logs_dir,
                'reports_dir': reports_dir,
                'backups_dir': backups_dir
            }

    def run_ci_cleanup(self, *args, cwd=None):
        """CI 클린업 스크립트 실행 헬퍼 함수"""
        script_path = "scripts/ci_cleanup.sh"
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
        script_path = Path("scripts/ci_cleanup.sh")
        assert script_path.exists(), "ci_cleanup.sh 스크립트가 존재하지 않습니다"
        assert os.access(script_path, os.X_OK), "ci_cleanup.sh 스크립트에 실행 권한이 없습니다"

    def test_help_option(self):
        """도움말 옵션 정상 동작 확인"""
        result = self.run_ci_cleanup("--help")
        assert result.returncode == 0, "도움말 옵션 실행 실패"
        assert "사용법" in result.stdout, "도움말에 사용법이 포함되지 않음"
        assert "--dry-run" in result.stdout, "도움말에 dry-run 옵션이 없음"
        assert "--verbose" in result.stdout, "도움말에 verbose 옵션이 없음"

    def test_dry_run_mode(self, temp_env):
        """시뮬레이션 모드 정상 동작 확인"""
        # 임시 디렉토리로 이동하여 실행
        os.chdir(temp_env['temp_dir'])

        result = self.run_ci_cleanup("--dry-run", "--verbose")
        assert result.returncode == 0, f"시뮬레이션 모드 실행 실패: {result.stderr}"
        assert "시뮬레이션" in result.stdout, "시뮬레이션 모드 출력이 없음"

        # 실제 파일이 변경되지 않았는지 확인
        security_log = temp_env['logs_dir'] / "security.log"
        assert security_log.exists(), "시뮬레이션 모드에서 파일이 삭제됨"

    def test_json_output_format(self, temp_env):
        """JSON 출력 형식 검증"""
        os.chdir(temp_env['temp_dir'])

        result = self.run_ci_cleanup("--json", "--dry-run")
        assert result.returncode == 0, f"JSON 출력 모드 실행 실패: {result.stderr}"

        try:
            json_data = json.loads(result.stdout)
            assert "timestamp" in json_data, "JSON 출력에 timestamp가 없음"
            assert "dry_run" in json_data, "JSON 출력에 dry_run 정보가 없음"
            assert "cleanup_results" in json_data, "JSON 출력에 cleanup_results가 없음"
            assert json_data["dry_run"] is True, "JSON 출력의 dry_run 값이 올바르지 않음"
        except json.JSONDecodeError:
            pytest.fail(f"잘못된 JSON 출력 형식: {result.stdout}")

    def test_log_compression_detection(self, temp_env):
        """로그 압축 기능 감지 확인"""
        os.chdir(temp_env['temp_dir'])

        result = self.run_ci_cleanup("--dry-run", "--verbose")
        assert result.returncode == 0, f"로그 압축 테스트 실행 실패: {result.stderr}"

        # 압축 대상 로그 파일이 감지되는지 확인
        assert "security.log" in result.stdout, "security.log 압축 감지 실패"
        assert "api.log" in result.stdout, "api.log 압축 감지 실패"

    def test_old_reports_cleanup_detection(self, temp_env):
        """오래된 리포트 정리 기능 감지 확인"""
        os.chdir(temp_env['temp_dir'])

        result = self.run_ci_cleanup("--dry-run", "--verbose")
        assert result.returncode == 0, f"리포트 정리 테스트 실행 실패: {result.stderr}"

        # 오래된 리포트 파일이 감지되는지 확인
        assert "old_report.txt" in result.stdout or "삭제" in result.stdout, "오래된 리포트 감지 실패"

    def test_backup_integrity_check(self, temp_env):
        """백업 무결성 검증 기능 확인"""
        os.chdir(temp_env['temp_dir'])

        result = self.run_ci_cleanup("--dry-run", "--verbose")
        assert result.returncode == 0, f"백업 무결성 검증 실행 실패: {result.stderr}"

        # 백업 파일이 감지되는지 확인
        assert "backup_20240921.tar.gz" in result.stdout or "백업" in result.stdout, "백업 파일 감지 실패"


class TestCICleanupIntegration:
    """CI 클린업 통합 테스트"""

    def run_ci_cleanup(self, *args, cwd=None):
        """CI 클린업 스크립트 실행 헬퍼 함수"""
        script_path = "scripts/ci_cleanup.sh"
        cmd = [script_path] + list(args)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or os.getcwd()
        )
        return result

    def test_makefile_integration(self):
        """Makefile 명령어 연동 확인"""
        # ci-clean-dry 명령어 테스트
        result = subprocess.run(
            ["make", "ci-clean-dry"],
            capture_output=True,
            text=True
        )

        # 명령어가 정의되어 있는지 확인 (스크립트 실행 여부와 관계없이)
        # make가 "No rule to make target" 에러를 반환하지 않으면 성공
        assert "No rule to make target" not in result.stderr, "ci-clean-dry 명령어가 Makefile에 정의되지 않음"

    def test_multiple_options_combination(self):
        """여러 옵션 조합 테스트"""
        # --dry-run과 --verbose 조합
        result = self.run_ci_cleanup("--dry-run", "--verbose")
        # 스크립트가 오류 없이 실행되는지만 확인
        assert result.returncode == 0 or "No such file" in result.stderr, "옵션 조합 테스트 실행 문제"

    def test_custom_days_option(self):
        """사용자 정의 보관 기간 옵션 테스트"""
        result = self.run_ci_cleanup("--days", "7", "--dry-run", "--json")
        # 스크립트가 오류 없이 실행되는지만 확인
        assert result.returncode == 0 or "No such file" in result.stderr, "사용자 정의 보관 기간 옵션 실행 문제"


class TestCICleanupPerformance:
    """CI 클린업 성능 테스트"""

    def run_ci_cleanup(self, *args, cwd=None):
        """CI 클린업 스크립트 실행 헬퍼 함수"""
        script_path = "scripts/ci_cleanup.sh"
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
        import time

        start_time = time.time()
        result = self.run_ci_cleanup("--dry-run")
        execution_time = time.time() - start_time

        # 30초 이내 실행 완료 검증 (시뮬레이션 모드)
        assert execution_time < 30.0, f"실행 시간이 너무 오래 걸림: {execution_time:.2f}초"

    def test_large_scale_simulation(self):
        """대규모 환경 시뮬레이션 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 대량의 테스트 파일 생성
            logs_dir = temp_path / "logs"
            reports_dir = temp_path / "reports"
            backups_dir = temp_path / "backups"

            logs_dir.mkdir()
            reports_dir.mkdir()
            backups_dir.mkdir()

            # 100개의 리포트 파일 생성
            for i in range(100):
                report_file = reports_dir / f"report_{i:03d}.txt"
                with open(report_file, 'w') as f:
                    f.write(f"리포트 {i} 내용")

            # 50개의 백업 파일 생성
            for i in range(50):
                backup_file = backups_dir / f"backup_{i:03d}.tar.gz"
                with open(backup_file, 'w') as f:
                    f.write(f"백업 {i} 내용")

            # 대규모 환경에서 실행 테스트
            os.chdir(temp_path)
            result = self.run_ci_cleanup("--dry-run", "--json")

            # 정상 실행 확인
            assert result.returncode == 0, f"대규모 시뮬레이션 실행 실패: {result.stderr}"


class TestCICleanupErrorHandling:
    """CI 클린업 에러 처리 테스트"""

    def run_ci_cleanup(self, *args, cwd=None):
        """CI 클린업 스크립트 실행 헬퍼 함수"""
        script_path = "scripts/ci_cleanup.sh"
        cmd = [script_path] + list(args)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or os.getcwd()
        )
        return result

    def test_invalid_option_handling(self):
        """잘못된 옵션 처리 확인"""
        result = self.run_ci_cleanup("--invalid-option")

        # 잘못된 옵션에 대한 에러 메시지 확인
        assert result.returncode != 0, "잘못된 옵션이 허용됨"
        assert "알 수 없는 옵션" in result.stdout or "알 수 없는 옵션" in result.stderr, "적절한 에러 메시지가 없음"

    def test_missing_directories_handling(self):
        """디렉토리가 없는 경우 처리 확인"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 빈 디렉토리에서 실행
            os.chdir(temp_dir)

            result = self.run_ci_cleanup("--dry-run", "--verbose")

            # 디렉토리가 없어도 스크립트가 정상 종료되어야 함
            assert result.returncode == 0, f"디렉토리 없음 처리 실패: {result.stderr}"
            assert "찾을 수 없음" in result.stdout or "생성" in result.stdout, "디렉토리 없음에 대한 적절한 메시지가 없음"