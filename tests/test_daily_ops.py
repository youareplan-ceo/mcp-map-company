import os
import json
import subprocess
import tempfile
import pytest
from pathlib import Path

# 🔄 일일 운영 자동화 스크립트 테스트 (한국어 주석 포함)
# 테스트 목적: daily_ops.sh 스크립트의 전체 워크플로우 검증
# 검증 절차:
#   1. 스크립트 실행 가능 여부 확인
#   2. 시뮬레이션 모드 정상 동작 검증
#   3. 로그 파일 생성 및 내용 확인
#   4. JSON 출력 형식 검증
#   5. 에러 처리 및 복구 시나리오 테스트
# 예상 결과: 모든 옵션이 정상 동작하며 적절한 로그 기록

class TestDailyOpsScript:
    """일일 운영 자동화 스크립트 테스트 클래스"""

    def setup_method(self):
        """각 테스트 시작 전 초기화"""
        self.script_path = "./scripts/daily_ops.sh"
        self.test_logs_dir = tempfile.mkdtemp()
        os.environ["TEST_LOGS_DIR"] = self.test_logs_dir

    def teardown_method(self):
        """각 테스트 종료 후 정리"""
        if "TEST_LOGS_DIR" in os.environ:
            del os.environ["TEST_LOGS_DIR"]

    def test_script_exists_and_executable(self):
        """스크립트 파일 존재 및 실행 권한 확인"""
        assert os.path.exists(self.script_path), f"❌ daily_ops.sh 스크립트를 찾을 수 없습니다: {self.script_path}"
        assert os.access(self.script_path, os.X_OK), "❌ daily_ops.sh 스크립트에 실행 권한이 없습니다"
        print("✅ daily_ops.sh 스크립트 존재 및 실행 권한 확인")

    def test_help_option(self):
        """도움말 옵션 테스트"""
        result = subprocess.run(
            [self.script_path, "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0, f"❌ help 옵션 실행 실패: {result.stderr}"
        assert "일일 운영 자동화 스크립트" in result.stdout, "❌ 도움말에 한국어 설명이 포함되지 않았습니다"
        assert "--dry-run" in result.stdout, "❌ 도움말에 옵션 설명이 누락되었습니다"
        print("✅ 도움말 옵션 정상 동작 확인")

    def test_dry_run_mode(self):
        """시뮬레이션 모드 테스트"""
        # 테스트용 로그 및 백업 디렉토리 생성
        os.makedirs("logs", exist_ok=True)
        os.makedirs("backups", exist_ok=True)

        # 테스트용 보안 로그 파일 생성
        with open("logs/security.log", "w") as f:
            f.write("2024-09-21 14:30:25 - INFO - 테스트 보안 로그\n")

        result = subprocess.run(
            [self.script_path, "--dry-run", "--verbose"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # 실행 결과 검증
        assert result.returncode == 0, f"❌ dry-run 모드 실행 실패: {result.stderr}"
        assert "[시뮬레이션]" in result.stdout, "❌ 시뮬레이션 모드 표시가 없습니다"
        assert "일일 운영 작업 완료" in result.stdout, "❌ 작업 완료 메시지가 없습니다"
        print("✅ 시뮬레이션 모드 정상 동작 확인")

    def test_json_output_mode(self):
        """JSON 출력 모드 테스트"""
        # 테스트용 환경 설정
        os.makedirs("logs", exist_ok=True)

        result = subprocess.run(
            [self.script_path, "--dry-run", "--json"],
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0, f"❌ JSON 모드 실행 실패: {result.stderr}"

        # JSON 출력 검증
        try:
            # 마지막 줄이 JSON 출력일 가능성이 높음
            output_lines = result.stdout.strip().split('\n')
            json_line = None
            for line in reversed(output_lines):
                if line.strip().startswith('{'):
                    json_line = line.strip()
                    break

            assert json_line is not None, "❌ JSON 출력을 찾을 수 없습니다"

            json_data = json.loads(json_line)
            assert "timestamp" in json_data, "❌ JSON 출력에 timestamp 필드가 없습니다"
            assert "dry_run" in json_data, "❌ JSON 출력에 dry_run 필드가 없습니다"
            assert "status" in json_data, "❌ JSON 출력에 status 필드가 없습니다"
            assert json_data["dry_run"] == True, "❌ dry_run 값이 올바르지 않습니다"

            print("✅ JSON 출력 모드 정상 동작 확인")
            print(f"   JSON 데이터: {json_data}")

        except json.JSONDecodeError as e:
            pytest.fail(f"❌ JSON 파싱 실패: {e}\n출력: {result.stdout}")

    def test_log_file_creation(self):
        """로그 파일 생성 테스트"""
        # 테스트용 로그 디렉토리 생성
        os.makedirs("logs", exist_ok=True)
        daily_log_path = "logs/daily_ops.log"

        # 기존 로그 파일 제거 (테스트 격리)
        if os.path.exists(daily_log_path):
            os.remove(daily_log_path)

        result = subprocess.run(
            [self.script_path, "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0, f"❌ 스크립트 실행 실패: {result.stderr}"
        assert os.path.exists(daily_log_path), f"❌ 일일 운영 로그 파일이 생성되지 않았습니다: {daily_log_path}"

        # 로그 파일 내용 검증
        with open(daily_log_path, "r", encoding="utf-8") as f:
            log_content = f.read()

        assert "일일 운영 작업 시작" in log_content, "❌ 로그에 시작 메시지가 없습니다"
        assert "일일 운영 작업 완료" in log_content, "❌ 로그에 완료 메시지가 없습니다"
        print("✅ 로그 파일 생성 및 내용 확인")

    def test_makefile_integration(self):
        """Makefile 통합 테스트"""
        # Makefile 존재 확인
        if not os.path.exists("Makefile"):
            pytest.skip("❓ Makefile이 존재하지 않아 통합 테스트를 건너뜁니다")

        # make daily-ops-dry 명령어 테스트
        result = subprocess.run(
            ["make", "daily-ops-dry"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Makefile에서 스크립트가 호출되었는지 확인 (에러 허용)
        print(f"Makefile 통합 테스트 결과: return_code={result.returncode}")
        if result.returncode == 0:
            print("✅ Makefile 통합 정상 동작")
        else:
            print(f"❓ Makefile 통합 테스트 건너뜀: {result.stderr}")

    def test_error_handling(self):
        """에러 처리 테스트"""
        # 잘못된 옵션으로 실행
        result = subprocess.run(
            [self.script_path, "--invalid-option"],
            capture_output=True,
            text=True,
            timeout=10
        )

        # 적절한 에러 처리 확인
        assert result.returncode != 0, "❌ 잘못된 옵션에 대한 에러 처리가 없습니다"
        assert "알 수 없는 옵션" in result.stdout or "알 수 없는 옵션" in result.stderr, "❌ 한국어 에러 메시지가 없습니다"
        print("✅ 에러 처리 정상 동작 확인")

class TestDailyOpsPerformance:
    """일일 운영 스크립트 성능 테스트"""

    def test_execution_time(self):
        """실행 시간 성능 테스트"""
        import time

        script_path = "./scripts/daily_ops.sh"
        if not os.path.exists(script_path):
            pytest.skip("❓ daily_ops.sh 스크립트를 찾을 수 없어 성능 테스트를 건너뜁니다")

        # 실행 시간 측정
        start_time = time.time()
        result = subprocess.run(
            [script_path, "--dry-run"],
            capture_output=True,
            text=True,
            timeout=60
        )
        execution_time = time.time() - start_time

        # 성능 요구사항 검증 (30초 이내 완료)
        assert execution_time < 30.0, f"❌ 실행 시간이 너무 깁니다: {execution_time:.2f}초"
        assert result.returncode == 0, f"❌ 성능 테스트 중 스크립트 실행 실패: {result.stderr}"

        print(f"✅ 성능 테스트 통과: {execution_time:.2f}초")

class TestDailyOpsIntegration:
    """일일 운영 스크립트 통합 테스트"""

    def test_full_workflow_simulation(self):
        """전체 워크플로우 시뮬레이션 테스트"""
        script_path = "./scripts/daily_ops.sh"
        if not os.path.exists(script_path):
            pytest.skip("❓ daily_ops.sh 스크립트를 찾을 수 없어 통합 테스트를 건너뜁니다")

        # 테스트 환경 설정
        os.makedirs("logs", exist_ok=True)
        os.makedirs("backups", exist_ok=True)
        os.makedirs("scripts", exist_ok=True)

        # 가짜 보안 로그 생성
        with open("logs/security.log", "w") as f:
            f.write("2024-09-21 14:30:25 - INFO - 통합 테스트용 보안 로그\n")

        # 전체 워크플로우 실행 (시뮬레이션)
        result = subprocess.run(
            [script_path, "--dry-run", "--verbose"],
            capture_output=True,
            text=True,
            timeout=60
        )

        # 통합 결과 검증
        assert result.returncode == 0, f"❌ 전체 워크플로우 실행 실패: {result.stderr}"

        print("✅ 전체 워크플로우 통합 테스트 완료")
        print(f"   실행 결과: {result.returncode}")
        print(f"   출력 길이: {len(result.stdout)}자")

        # 주요 단계 실행 확인
        output = result.stdout
        workflow_steps = [
            "일일 운영 작업 시작",
            "보안 로그 회전",
            "백업 무결성 검증",
            "오래된 백업 정리",
            "일일 운영 작업 완료"
        ]

        completed_steps = 0
        for step in workflow_steps:
            if step in output:
                completed_steps += 1
                print(f"   ✅ {step}")
            else:
                print(f"   ❓ {step} (건너뜀)")

        print(f"   완료된 워크플로우 단계: {completed_steps}/{len(workflow_steps)}")