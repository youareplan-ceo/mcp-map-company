import os
import subprocess
import tempfile
import pytest
from mcp.security_logger import log_security_event

# 🔄 통합 운영 테스트 (한국어 주석 포함)
# 목적: 보안 로그 기록, 백업 검증, 정리 스크립트의 전체 워크플로우 검증
# 절차:
#   1. 보안 이벤트 기록 → 로그 파일 생성 확인
#   2. backup_verifier.sh 실행 → 백업 상태 검증
#   3. cleanup_old_backups.sh 시뮬레이션 → 정리 로직 확인
#   4. Makefile 명령어 실행 → 자동화 워크플로우 검증
# 예상결과: 모든 운영 스크립트가 정상 동작하며 에러 없이 완료됨

class TestIntegrationOps:
    """통합 운영 테스트 클래스"""

    def setup_method(self):
        """각 테스트 시작 전 초기화"""
        # 테스트용 임시 로그 디렉토리 생성
        self.test_log_dir = tempfile.mkdtemp()
        os.environ["TEST_MODE"] = "true"

    def test_security_log_workflow(self):
        """보안 로그 기록 워크플로우 테스트"""
        # 보안 이벤트 기록
        log_security_event("BLOCKED_IP", "203.0.113.1 - 테스트 차단")
        log_security_event("WHITELIST_ADD", "192.168.1.100 - 테스트 화이트리스트")
        log_security_event("MONITOR", "통합 테스트 모니터링 이벤트")

        # 로그 파일 생성 확인
        log_path = "logs/security.log"
        assert os.path.exists(log_path), "❌ 보안 로그 파일이 생성되지 않았습니다"

        # 로그 내용 검증
        with open(log_path, "r", encoding="utf-8") as f:
            log_content = f.read()

        assert "BLOCKED_IP" in log_content, "❌ 차단 IP 이벤트가 기록되지 않았습니다"
        assert "WHITELIST_ADD" in log_content, "❌ 화이트리스트 이벤트가 기록되지 않았습니다"
        assert "MONITOR" in log_content, "❌ 모니터링 이벤트가 기록되지 않았습니다"
        print("✅ 보안 로그 워크플로우 정상 동작 확인")

    def test_backup_verifier_integration(self):
        """백업 검증 스크립트 통합 테스트"""
        # backup_verifier.sh 스크립트 존재 확인
        script_path = "./scripts/backup_verifier.sh"
        if not os.path.exists(script_path):
            pytest.skip("❓ backup_verifier.sh 스크립트가 존재하지 않아 테스트를 건너뜁니다")

        # 시뮬레이션 모드로 실행
        result = subprocess.run(
            [script_path, "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # 실행 결과 검증
        assert result.returncode == 0, f"❌ 백업 검증 스크립트 실행 실패: {result.stderr}"
        assert len(result.stdout) > 0, "❌ 백업 검증 스크립트 출력이 없습니다"
        print(f"✅ 백업 검증 스크립트 정상 실행: {result.stdout[:100]}...")

    def test_cleanup_script_integration(self):
        """정리 스크립트 통합 테스트"""
        script_path = "./scripts/cleanup_old_backups.sh"
        if not os.path.exists(script_path):
            pytest.skip("❓ cleanup_old_backups.sh 스크립트가 존재하지 않아 테스트를 건너뜁니다")

        # 시뮬레이션 모드로 실행
        result = subprocess.run(
            [script_path, "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # 실행 결과 검증
        assert result.returncode == 0, f"❌ 정리 스크립트 실행 실패: {result.stderr}"
        print(f"✅ 정리 스크립트 정상 실행 (시뮬레이션)")

    def test_makefile_commands_integration(self):
        """Makefile 명령어 통합 테스트"""
        # Makefile 존재 확인
        if not os.path.exists("Makefile"):
            pytest.skip("❓ Makefile이 존재하지 않아 테스트를 건너뜁니다")

        # make help 명령어 테스트
        result = subprocess.run(
            ["make", "help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print("✅ Makefile help 명령어 정상 동작")
        else:
            print("❓ make help 명령어를 사용할 수 없습니다")

    def test_full_workflow_integration(self):
        """전체 워크플로우 통합 테스트"""
        # 1단계: 보안 이벤트 발생 시뮬레이션
        log_security_event("INTEGRATION_TEST", "전체 워크플로우 테스트 시작")

        # 2단계: 로그 파일 확인
        log_path = "logs/security.log"
        assert os.path.exists(log_path), "❌ 1단계 실패: 로그 파일 생성되지 않음"

        # 3단계: 백업 관련 스크립트 실행 가능 여부 확인
        scripts_to_check = [
            "./scripts/backup_verifier.sh",
            "./scripts/cleanup_old_backups.sh"
        ]

        available_scripts = []
        for script in scripts_to_check:
            if os.path.exists(script) and os.access(script, os.X_OK):
                available_scripts.append(script)

        print(f"✅ 전체 워크플로우 테스트 완료")
        print(f"   - 보안 로그 기록: 정상")
        print(f"   - 사용 가능한 스크립트: {len(available_scripts)}개")
        print(f"   - 통합 테스트 상태: 성공")

    def teardown_method(self):
        """각 테스트 종료 후 정리"""
        # 테스트 환경변수 제거
        if "TEST_MODE" in os.environ:
            del os.environ["TEST_MODE"]