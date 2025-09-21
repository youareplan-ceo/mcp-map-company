import subprocess
import pytest

# 🧪 Makefile 기반 백업 관리 통합 테스트
# 1. verify-backups 실행 결과 확인
# 2. clean-backups 실행 결과 확인 (dry-run 모드)
# 3. backup-maintenance 실행 결과 확인

def run_make_command(cmd):
    result = subprocess.run(["make", cmd], capture_output=True, text=True)
    return result

def test_verify_backups():
    result = run_make_command("verify-backups")
    assert result.returncode == 0
    assert "백업" in result.stdout or "backup" in result.stdout

def test_clean_backups_dry_run():
    result = run_make_command("clean-backups-dry")
    assert result.returncode == 0
    assert "시뮬레이션" in result.stdout or "dry-run" in result.stdout

def test_backup_maintenance():
    result = run_make_command("backup-maintenance")
    assert result.returncode == 0
    assert "백업" in result.stdout or "backup" in result.stdout