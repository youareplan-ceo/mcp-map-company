import os
import subprocess
import pytest
from mcp.security_logger import log_security_event

# 🧪 백업 검증 + 보안 로그 통합 테스트
# 1. 보안 이벤트 기록 후 로그 파일 생성 확인
# 2. backup_verifier.sh 스크립트 실행 결과 확인
# 3. cleanup_old_backups.sh 시뮬레이션 모드 검증

def test_security_log_creation(tmp_path):
    log_path = tmp_path / "security.log"
    os.environ["SECURITY_LOG_PATH"] = str(log_path)

    log_security_event("BLOCKED_IP", "127.0.0.1 차단")
    assert log_path.exists()
    with open(log_path) as f:
        data = f.read()
    assert "BLOCKED_IP" in data

def test_backup_verifier_script():
    result = subprocess.run(["./scripts/backup_verifier.sh", "--dry-run"],
                            capture_output=True, text=True)
    assert result.returncode == 0
    assert "백업" in result.stdout or "backup" in result.stdout

def test_cleanup_script_dry_run():
    result = subprocess.run(["./scripts/cleanup_old_backups.sh", "--dry-run"],
                            capture_output=True, text=True)
    assert result.returncode == 0
    assert "시뮬레이션" in result.stdout or "dry-run" in result.stdout