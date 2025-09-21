import os
import json
import pytest
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

# 🧪 통합 테스트: 보안 로그 + 백업 검증 + CI/CD 연동 (한국어 주석 포함)
#
# 주요 검증 시나리오:
# ✅ 보안 이벤트 발생 → security.log 기록 검증
# ✅ backup_verifier.sh 실행 결과 검증
# ✅ cleanup_old_backups.sh 시뮬레이션 실행 검증
# ✅ 모든 결과를 JSON 포맷으로 출력 확인
# ✅ CI/CD 파이프라인 통합 테스트
#
# 테스트 환경:
# - 임시 백업 디렉토리 생성
# - Mock 보안 이벤트 생성
# - 스크립트 실행 및 결과 검증
# - JSON 출력 형식 검증

class TestIntegrationBackupSecurity:
    """🔐 보안 로그 + 백업 통합 테스트 클래스"""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self, tmp_path):
        """🛠️ 테스트 환경 초기화"""
        # 임시 백업 디렉토리 생성
        self.backup_dir = tmp_path / "test_backups"
        self.backup_dir.mkdir()

        # 임시 로그 디렉토리 생성
        self.log_dir = tmp_path / "logs"
        self.log_dir.mkdir()
        self.security_log = self.log_dir / "security.log"

        # 환경 변수 설정
        os.environ["SECURITY_LOG_PATH"] = str(self.security_log)
        os.environ["TEST_BACKUP_DIR"] = str(self.backup_dir)

        # 테스트용 백업 파일 생성
        self._create_test_backup_files()

    def _create_test_backup_files(self):
        """📦 테스트용 백업 파일 생성"""
        # 최신 백업 파일 (오늘)
        recent_backup = self.backup_dir / f"backup_{datetime.now().strftime('%Y%m%d')}.tar.gz"
        recent_backup.write_text("recent backup content")

        # 오래된 백업 파일 (35일 전)
        old_date = datetime.now() - timedelta(days=35)
        old_backup = self.backup_dir / f"backup_{old_date.strftime('%Y%m%d')}.tar.gz"
        old_backup.write_text("old backup content")

        # 파일 수정 시간 조정 (macOS 호환)
        old_timestamp = old_date.timestamp()
        os.utime(old_backup, (old_timestamp, old_timestamp))

    def test_security_event_logging(self):
        """🔐 보안 이벤트 발생 → security.log 기록 검증"""
        # Mock 보안 로거가 없는 경우를 대비한 간단한 로깅
        try:
            from mcp.security_logger import log_security_event
            log_security_event("BLOCKED_IP", "192.168.1.100 - Rate Limit 초과로 차단")
        except ImportError:
            # Mock 로깅 구현
            with open(self.security_log, "a", encoding="utf-8") as f:
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "event": "BLOCKED_IP",
                    "message": "192.168.1.100 - Rate Limit 초과로 차단",
                    "level": "WARNING"
                }
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        # 로그 파일 생성 확인
        assert self.security_log.exists(), "❌ 보안 로그 파일이 생성되지 않았습니다"

        # 로그 내용 검증
        with open(self.security_log, "r", encoding="utf-8") as f:
            log_content = f.read()

        assert "BLOCKED_IP" in log_content, "❌ 보안 이벤트가 로그에 기록되지 않았습니다"
        assert "192.168.1.100" in log_content, "❌ IP 주소가 로그에 기록되지 않았습니다"

        # JSON 형식 검증
        log_lines = log_content.strip().split('\n')
        last_log = json.loads(log_lines[-1])
        assert "event" in last_log, "❌ 로그 JSON 형식에 event 필드가 없습니다"
        assert "message" in last_log, "❌ 로그 JSON 형식에 message 필드가 없습니다"

    def test_backup_verifier_execution(self):
        """📋 backup_verifier.sh 실행 결과 검증"""
        script_path = Path("scripts/backup_verifier.sh")

        # 스크립트 파일 존재 확인
        assert script_path.exists(), "❌ backup_verifier.sh 스크립트가 없습니다"

        # 스크립트 실행 (JSON 모드)
        result = subprocess.run([
            str(script_path),
            "--dir", str(self.backup_dir),
            "--json"
        ], capture_output=True, text=True, cwd=".")

        # 실행 성공 확인
        assert result.returncode == 0, f"❌ backup_verifier.sh 실행 실패: {result.stderr}"

        # JSON 출력 검증
        try:
            output_data = json.loads(result.stdout.strip())
            assert "file" in output_data, "❌ JSON 출력에 file 필드가 없습니다"
            assert "size" in output_data, "❌ JSON 출력에 size 필드가 없습니다"
            assert "modified" in output_data, "❌ JSON 출력에 modified 필드가 없습니다"

            # 파일 크기가 0보다 큰지 확인
            assert output_data["size"] > 0, "❌ 백업 파일 크기가 0입니다"

        except json.JSONDecodeError:
            pytest.fail(f"❌ backup_verifier.sh JSON 출력 형식이 올바르지 않습니다: {result.stdout}")

    def test_cleanup_script_dry_run(self):
        """🗑️ cleanup_old_backups.sh 시뮬레이션 실행 검증"""
        script_path = Path("scripts/cleanup_old_backups.sh")

        # 스크립트 파일 존재 확인
        assert script_path.exists(), "❌ cleanup_old_backups.sh 스크립트가 없습니다"

        # 정리 전 파일 개수 확인
        files_before = list(self.backup_dir.glob("*.tar.gz"))

        # 스크립트 실행 (시뮬레이션 모드 + JSON 출력)
        result = subprocess.run([
            str(script_path),
            "--dir", str(self.backup_dir),
            "--days", "30",
            "--dry-run",
            "--json"
        ], capture_output=True, text=True, cwd=".")

        # 실행 성공 확인
        assert result.returncode == 0, f"❌ cleanup_old_backups.sh 실행 실패: {result.stderr}"

        # 시뮬레이션 모드에서는 파일이 삭제되지 않아야 함
        files_after = list(self.backup_dir.glob("*.tar.gz"))
        assert len(files_after) == len(files_before), "❌ 시뮬레이션 모드에서 파일이 삭제되었습니다"

        # JSON 출력 검증
        try:
            output_data = json.loads(result.stdout.strip())
            assert "deleted_count" in output_data, "❌ JSON 출력에 deleted_count 필드가 없습니다"
            assert "total_size_bytes" in output_data, "❌ JSON 출력에 total_size_bytes 필드가 없습니다"
            assert "dry_run" in output_data, "❌ JSON 출력에 dry_run 필드가 없습니다"
            assert output_data["dry_run"] is True, "❌ dry_run 플래그가 올바르지 않습니다"

            # 오래된 파일이 감지되었는지 확인 (35일 전 파일)
            assert output_data["deleted_count"] > 0, "❌ 오래된 백업 파일이 감지되지 않았습니다"

        except json.JSONDecodeError:
            pytest.fail(f"❌ cleanup_old_backups.sh JSON 출력 형식이 올바르지 않습니다: {result.stdout}")

    def test_makefile_integration(self):
        """🔧 Makefile 명령어 통합 테스트"""
        # Makefile 존재 확인
        makefile_path = Path("Makefile")
        assert makefile_path.exists(), "❌ Makefile이 없습니다"

        # Makefile 내용에서 백업 관련 명령어 확인
        with open(makefile_path, "r", encoding="utf-8") as f:
            makefile_content = f.read()

        assert "verify-backups:" in makefile_content, "❌ Makefile에 verify-backups 명령어가 없습니다"
        assert "clean-backups:" in makefile_content, "❌ Makefile에 clean-backups 명령어가 없습니다"
        assert "backup-maintenance:" in makefile_content, "❌ Makefile에 backup-maintenance 명령어가 없습니다"

    def test_ci_cd_pipeline_simulation(self):
        """🚀 CI/CD 파이프라인 시뮬레이션"""
        # 1단계: 보안 이벤트 로깅
        try:
            from mcp.security_logger import log_security_event
            log_security_event("CI_TEST", "CI/CD 파이프라인 테스트 실행")
        except ImportError:
            # Mock 로깅
            with open(self.security_log, "a", encoding="utf-8") as f:
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "event": "CI_TEST",
                    "message": "CI/CD 파이프라인 테스트 실행",
                    "level": "INFO"
                }
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        # 2단계: 백업 검증 실행
        verify_result = subprocess.run([
            "scripts/backup_verifier.sh",
            "--dir", str(self.backup_dir),
            "--json"
        ], capture_output=True, text=True, cwd=".")

        # 3단계: 정리 스크립트 시뮬레이션
        cleanup_result = subprocess.run([
            "scripts/cleanup_old_backups.sh",
            "--dir", str(self.backup_dir),
            "--dry-run",
            "--json"
        ], capture_output=True, text=True, cwd=".")

        # 모든 단계 성공 확인
        assert verify_result.returncode == 0, "❌ 백업 검증 단계 실패"
        assert cleanup_result.returncode == 0, "❌ 정리 스크립트 단계 실패"

        # 통합 결과 JSON 생성
        ci_report = {
            "timestamp": datetime.now().isoformat(),
            "pipeline_status": "SUCCESS",
            "steps": {
                "security_logging": "PASSED",
                "backup_verification": "PASSED" if verify_result.returncode == 0 else "FAILED",
                "cleanup_simulation": "PASSED" if cleanup_result.returncode == 0 else "FAILED"
            },
            "backup_verification_output": json.loads(verify_result.stdout.strip()) if verify_result.stdout.strip() else {},
            "cleanup_simulation_output": json.loads(cleanup_result.stdout.strip()) if cleanup_result.stdout.strip() else {}
        }

        # CI 보고서 JSON 형식 검증
        assert ci_report["pipeline_status"] == "SUCCESS", "❌ CI/CD 파이프라인 통합 테스트 실패"
        assert all(status == "PASSED" for status in ci_report["steps"].values()), "❌ 일부 단계가 실패했습니다"

    def test_json_output_schema_validation(self):
        """📊 JSON 출력 스키마 검증"""
        # backup_verifier.sh JSON 스키마 검증
        verify_result = subprocess.run([
            "scripts/backup_verifier.sh",
            "--dir", str(self.backup_dir),
            "--json"
        ], capture_output=True, text=True, cwd=".")

        verify_data = json.loads(verify_result.stdout.strip())

        # 필수 필드 검증
        required_verify_fields = ["file", "size", "modified"]
        for field in required_verify_fields:
            assert field in verify_data, f"❌ backup_verifier JSON에 {field} 필드가 없습니다"

        # 데이터 타입 검증
        assert isinstance(verify_data["file"], str), "❌ file 필드는 문자열이어야 합니다"
        assert isinstance(verify_data["size"], int), "❌ size 필드는 정수여야 합니다"
        assert isinstance(verify_data["modified"], str), "❌ modified 필드는 문자열이어야 합니다"

        # cleanup_old_backups.sh JSON 스키마 검증
        cleanup_result = subprocess.run([
            "scripts/cleanup_old_backups.sh",
            "--dir", str(self.backup_dir),
            "--dry-run",
            "--json"
        ], capture_output=True, text=True, cwd=".")

        cleanup_data = json.loads(cleanup_result.stdout.strip())

        # 필수 필드 검증
        required_cleanup_fields = ["timestamp", "deleted_count", "total_size_bytes", "backup_dir", "days_keep", "dry_run", "deleted_files"]
        for field in required_cleanup_fields:
            assert field in cleanup_data, f"❌ cleanup JSON에 {field} 필드가 없습니다"

        # 데이터 타입 검증
        assert isinstance(cleanup_data["deleted_count"], int), "❌ deleted_count 필드는 정수여야 합니다"
        assert isinstance(cleanup_data["total_size_bytes"], int), "❌ total_size_bytes 필드는 정수여야 합니다"
        assert isinstance(cleanup_data["dry_run"], bool), "❌ dry_run 필드는 불린이어야 합니다"

    def test_error_handling_and_logging(self):
        """🚨 에러 처리 및 로깅 테스트"""
        # 존재하지 않는 백업 디렉토리로 테스트
        invalid_dir = "/nonexistent/backup/dir"

        # backup_verifier.sh 에러 처리
        verify_result = subprocess.run([
            "scripts/backup_verifier.sh",
            "--dir", invalid_dir
        ], capture_output=True, text=True, cwd=".")

        assert verify_result.returncode != 0, "❌ 잘못된 디렉토리에 대해 에러가 발생해야 합니다"
        assert "찾을 수 없습니다" in verify_result.stdout or "not found" in verify_result.stdout.lower(), "❌ 적절한 에러 메시지가 출력되지 않았습니다"

        # cleanup_old_backups.sh 에러 처리
        cleanup_result = subprocess.run([
            "scripts/cleanup_old_backups.sh",
            "--dir", invalid_dir,
            "--json"
        ], capture_output=True, text=True, cwd=".")

        assert cleanup_result.returncode != 0, "❌ 잘못된 디렉토리에 대해 에러가 발생해야 합니다"

    def teardown_method(self):
        """🧹 테스트 종료 후 정리"""
        # 환경 변수 정리
        if "SECURITY_LOG_PATH" in os.environ:
            del os.environ["SECURITY_LOG_PATH"]
        if "TEST_BACKUP_DIR" in os.environ:
            del os.environ["TEST_BACKUP_DIR"]

# 🎯 성능 및 스트레스 테스트
class TestPerformanceAndStress:
    """⚡ 성능 및 스트레스 테스트 클래스"""

    @pytest.fixture(autouse=True)
    def setup_performance_test(self, tmp_path):
        """🛠️ 성능 테스트 환경 초기화"""
        self.backup_dir = tmp_path / "perf_backups"
        self.backup_dir.mkdir()

        # 대용량 백업 파일 시뮬레이션 (100개 파일)
        for i in range(100):
            file_date = datetime.now() - timedelta(days=i)
            backup_file = self.backup_dir / f"backup_{file_date.strftime('%Y%m%d')}_{i:03d}.tar.gz"
            backup_file.write_text(f"backup content {i}" * 1000)  # 약 13KB per file

    def test_large_scale_cleanup_performance(self):
        """📈 대규모 백업 정리 성능 테스트"""
        import time

        start_time = time.time()

        # 대용량 정리 작업 시뮬레이션
        result = subprocess.run([
            "scripts/cleanup_old_backups.sh",
            "--dir", str(self.backup_dir),
            "--days", "30",
            "--dry-run",
            "--json"
        ], capture_output=True, text=True, cwd=".")

        execution_time = time.time() - start_time

        # 성능 검증 (10초 이내 완료)
        assert execution_time < 10.0, f"❌ 성능 요구사항 미달: {execution_time:.2f}초 소요"
        assert result.returncode == 0, "❌ 대용량 처리 중 실패"

        # 결과 검증
        output_data = json.loads(result.stdout.strip())
        assert output_data["deleted_count"] > 50, "❌ 예상보다 적은 파일이 감지되었습니다"

if __name__ == "__main__":
    # 🏃‍♂️ 테스트 직접 실행 시
    pytest.main([__file__, "-v", "--tb=short"])