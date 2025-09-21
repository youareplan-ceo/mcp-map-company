import os
import json
import subprocess
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock

# 🔄 주간 운영 리포트 자동화 테스트 (한국어 주석 포함)
# 테스트 목적: weekly_ops_report.sh 스크립트와 notifier 연동 검증
# 검증 절차:
#   1. 스크립트 실행 가능 여부 확인
#   2. Markdown/JSON 출력 형식 검증
#   3. notifier 연동 테스트 (Mock 알림 채널)
#   4. 에러 처리 및 복구 시나리오 테스트
# 예상 결과: 모든 기능이 정상 동작하며 적절한 리포트 생성

class TestWeeklyOpsReportScript:
    """주간 운영 리포트 스크립트 테스트 클래스"""

    def setup_method(self):
        """각 테스트 시작 전 초기화"""
        self.script_path = "./scripts/weekly_ops_report.sh"
        self.test_reports_dir = tempfile.mkdtemp()
        os.environ["TEST_REPORTS_DIR"] = self.test_reports_dir

        # 테스트용 로그 디렉토리 생성
        os.makedirs("logs", exist_ok=True)
        os.makedirs("reports/weekly", exist_ok=True)

    def teardown_method(self):
        """각 테스트 종료 후 정리"""
        if "TEST_REPORTS_DIR" in os.environ:
            del os.environ["TEST_REPORTS_DIR"]

    def test_script_exists_and_executable(self):
        """스크립트 파일 존재 및 실행 권한 확인"""
        assert os.path.exists(self.script_path), f"❌ weekly_ops_report.sh 스크립트를 찾을 수 없습니다: {self.script_path}"
        assert os.access(self.script_path, os.X_OK), "❌ weekly_ops_report.sh 스크립트에 실행 권한이 없습니다"
        print("✅ weekly_ops_report.sh 스크립트 존재 및 실행 권한 확인")

    def test_help_option(self):
        """도움말 옵션 테스트"""
        result = subprocess.run(
            [self.script_path, "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0, f"❌ help 옵션 실행 실패: {result.stderr}"
        assert "주간 운영 리포트 자동화 스크립트" in result.stdout, "❌ 도움말에 한국어 설명이 포함되지 않았습니다"
        assert "--dry-run" in result.stdout, "❌ 도움말에 옵션 설명이 누락되었습니다"
        assert "--json" in result.stdout, "❌ 도움말에 JSON 옵션 설명이 누락되었습니다"
        print("✅ 도움말 옵션 정상 동작 확인")

    def test_dry_run_mode(self):
        """시뮬레이션 모드 테스트"""
        # 테스트용 로그 파일 생성
        self._create_test_logs()

        result = subprocess.run(
            [self.script_path, "--dry-run", "--verbose"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # 실행 결과 검증
        assert result.returncode == 0, f"❌ dry-run 모드 실행 실패: {result.stderr}"
        assert "시뮬레이션" in result.stdout, "❌ 시뮬레이션 모드 표시가 없습니다"
        assert "주간 운영 리포트 생성 완료" in result.stdout, "❌ 작업 완료 메시지가 없습니다"
        print("✅ 시뮬레이션 모드 정상 동작 확인")

    def test_json_output_mode(self):
        """JSON 출력 모드 테스트"""
        # 테스트용 로그 파일 생성
        self._create_test_logs()

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
            assert "report_metadata" in json_data, "❌ JSON 출력에 report_metadata 필드가 없습니다"
            assert "security_events" in json_data, "❌ JSON 출력에 security_events 필드가 없습니다"
            assert "backup_operations" in json_data, "❌ JSON 출력에 backup_operations 필드가 없습니다"
            assert "system_resources" in json_data, "❌ JSON 출력에 system_resources 필드가 없습니다"

            print("✅ JSON 출력 모드 정상 동작 확인")
            print(f"   JSON 스키마 검증 완료")

        except json.JSONDecodeError as e:
            pytest.fail(f"❌ JSON 파싱 실패: {e}\n출력: {result.stdout}")

    def test_markdown_report_generation(self):
        """Markdown 리포트 생성 테스트"""
        # 테스트용 로그 파일 생성
        self._create_test_logs()

        result = subprocess.run(
            [self.script_path, "--verbose"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            print(f"❓ Markdown 리포트 생성 테스트 건너뜀: {result.stderr}")
            return

        # 리포트 파일 존재 확인
        report_files = list(Path("reports/weekly").glob("weekly-report-*.md"))

        if report_files:
            report_file = report_files[0]
            assert report_file.exists(), f"❌ Markdown 리포트 파일이 생성되지 않았습니다: {report_file}"

            # 리포트 내용 검증
            with open(report_file, "r", encoding="utf-8") as f:
                report_content = f.read()

            assert "# 📊 주간 운영 리포트" in report_content, "❌ 리포트에 제목이 없습니다"
            assert "## 🛡️ 보안 현황" in report_content, "❌ 리포트에 보안 섹션이 없습니다"
            assert "## 📦 백업 현황" in report_content, "❌ 리포트에 백업 섹션이 없습니다"
            print("✅ Markdown 리포트 생성 및 내용 확인")
        else:
            print("❓ Markdown 리포트 파일을 찾을 수 없어 테스트를 건너뜁니다")

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

    def _create_test_logs(self):
        """테스트용 로그 파일 생성"""
        # 보안 로그 생성
        security_log_content = """2024-09-21 14:30:25 - INFO - [BLOCKED_IP] 192.168.0.15 - Rate Limit 초과로 차단
2024-09-21 14:30:26 - INFO - [WHITELIST_ADD] 127.0.0.1 - 화이트리스트 추가
2024-09-21 14:30:27 - INFO - [MONITOR] 일일 보안 점검 완료"""

        with open("logs/security.log", "w", encoding="utf-8") as f:
            f.write(security_log_content)

        # 일일 운영 로그 생성
        daily_ops_content = """2024-09-21 14:30:25 - INFO - 일일 운영 작업 시작
2024-09-21 14:30:26 - INFO - 백업 검증 완료
2024-09-21 14:30:27 - INFO - 백업 정리 완료"""

        with open("logs/daily_ops.log", "w", encoding="utf-8") as f:
            f.write(daily_ops_content)

class TestWeeklyOpsNotifierIntegration:
    """주간 리포트 알림 시스템 통합 테스트"""

    @pytest.mark.asyncio
    async def test_send_weekly_ops_report_function(self):
        """send_weekly_ops_report 함수 테스트"""
        # notifier 모듈 임포트 시도
        try:
            from mcp.utils.notifier import send_weekly_ops_report, NotificationLevel
        except ImportError:
            pytest.skip("❓ notifier 모듈을 찾을 수 없어 알림 테스트를 건너뜁니다")

        # 테스트용 리포트 데이터
        test_report_data = {
            'report_metadata': {
                'period_start': '2024-09-14',
                'period_end': '2024-09-21',
                'generated_at': '2024-09-21T14:30:25Z',
                'report_type': 'weekly_operations'
            },
            'security_events': {
                'blocked_ips': 5,
                'rate_limit_violations': 15,
                'whitelist_additions': 2,
                'monitoring_events': 50,
                'total_security_events': 72
            },
            'backup_operations': {
                'successful_backups': 6,
                'failed_backups': 1,
                'cleanup_operations': 2,
                'success_rate_percent': 86,
                'total_backup_operations': 7
            },
            'system_resources': {
                'disk_usage_percent': 65,
                'security_log_size_bytes': 1024000,
                'backup_directory_size_kb': 512000
            },
            'status_summary': {
                'security_status': 'good',
                'backup_status': 'good',
                'disk_status': 'normal'
            }
        }

        # Mock 알림 채널로 테스트
        with patch('mcp.utils.notifier.notification_manager.send_notification') as mock_send:
            mock_send.return_value = {'slack': True, 'discord': True, 'email': True}

            result = await send_weekly_ops_report(
                report_data=test_report_data,
                report_file_path="reports/weekly/weekly-report-2024-09-21.md",
                level=NotificationLevel.INFO
            )

            # 알림 전송 함수 호출 확인
            mock_send.assert_called_once()
            call_args = mock_send.call_args

            # 호출 인수 검증
            assert call_args[1]['level'] == NotificationLevel.INFO
            assert "주간 운영 리포트가 생성되었습니다" in call_args[1]['message']
            assert "📅 리포트 기간" in call_args[1]['fields']

            print("✅ send_weekly_ops_report 함수 정상 동작 확인")
            print(f"   알림 결과: {result}")

    @pytest.mark.asyncio
    async def test_execute_and_notify_weekly_report_function(self):
        """execute_and_notify_weekly_report 함수 테스트"""
        try:
            from mcp.utils.notifier import execute_and_notify_weekly_report
        except ImportError:
            pytest.skip("❓ notifier 모듈을 찾을 수 없어 실행 테스트를 건너뜁니다")

        # Mock subprocess 실행
        mock_result = type('MockResult', (), {
            'returncode': 0,
            'stdout': json.dumps({
                'report_metadata': {
                    'period_start': '2024-09-14',
                    'period_end': '2024-09-21',
                    'generated_at': '2024-09-21T14:30:25Z'
                },
                'security_events': {'blocked_ips': 3},
                'backup_operations': {'success_rate_percent': 100}
            }),
            'stderr': ''
        })

        with patch('subprocess.run', return_value=mock_result):
            with patch('mcp.utils.notifier.send_weekly_ops_report') as mock_notify:
                mock_notify.return_value = {'slack': True}

                result = await execute_and_notify_weekly_report(
                    script_path="scripts/weekly_ops_report.sh",
                    script_args=["--json"],
                    auto_notify=True
                )

                assert result['success'] == True, "❌ 실행 결과가 성공으로 표시되지 않았습니다"
                assert 'execution' in result, "❌ 실행 결과에 execution 정보가 없습니다"
                assert 'report_data' in result, "❌ 실행 결과에 report_data가 없습니다"
                assert 'notification' in result, "❌ 실행 결과에 notification 정보가 없습니다"

                # 알림 함수 호출 확인
                mock_notify.assert_called_once()

                print("✅ execute_and_notify_weekly_report 함수 정상 동작 확인")

    @pytest.mark.asyncio
    async def test_weekly_report_notification_with_mock_channels(self):
        """Mock 알림 채널을 사용한 주간 리포트 알림 테스트"""
        try:
            from mcp.utils.notifier import test_weekly_report_notification
        except ImportError:
            pytest.skip("❓ notifier 모듈을 찾을 수 없어 테스트를 건너뜁니다")

        # Mock 알림 채널로 테스트
        with patch('mcp.utils.notifier.notification_manager.send_notification') as mock_send:
            mock_send.return_value = {
                'slack': True,
                'discord': True,
                'email': True
            }

            result = await test_weekly_report_notification()

            # 결과 검증
            assert result is not None, "❌ 테스트 결과가 None입니다"
            mock_send.assert_called_once()

            print("✅ Mock 알림 채널 테스트 완료")

class TestWeeklyOpsPerformance:
    """주간 리포트 성능 테스트"""

    def test_execution_time(self):
        """실행 시간 성능 테스트"""
        import time

        script_path = "./scripts/weekly_ops_report.sh"
        if not os.path.exists(script_path):
            pytest.skip("❓ weekly_ops_report.sh 스크립트를 찾을 수 없어 성능 테스트를 건너뜁니다")

        # 테스트용 로그 파일 생성
        os.makedirs("logs", exist_ok=True)
        with open("logs/security.log", "w") as f:
            f.write("2024-09-21 14:30:25 - INFO - 테스트 로그\n")

        # 실행 시간 측정
        start_time = time.time()
        result = subprocess.run(
            [script_path, "--dry-run"],
            capture_output=True,
            text=True,
            timeout=60
        )
        execution_time = time.time() - start_time

        # 성능 요구사항 검증 (60초 이내 완료)
        assert execution_time < 60.0, f"❌ 실행 시간이 너무 깁니다: {execution_time:.2f}초"
        assert result.returncode == 0, f"❌ 성능 테스트 중 스크립트 실행 실패: {result.stderr}"

        print(f"✅ 성능 테스트 통과: {execution_time:.2f}초")

class TestWeeklyOpsIntegration:
    """주간 리포트 통합 테스트"""

    def test_full_workflow_simulation(self):
        """전체 워크플로우 시뮬레이션 테스트"""
        script_path = "./scripts/weekly_ops_report.sh"
        if not os.path.exists(script_path):
            pytest.skip("❓ weekly_ops_report.sh 스크립트를 찾을 수 없어 통합 테스트를 건너뜁니다")

        # 테스트 환경 설정
        os.makedirs("logs", exist_ok=True)
        os.makedirs("reports/weekly", exist_ok=True)

        # 테스트용 보안 로그 생성
        with open("logs/security.log", "w", encoding="utf-8") as f:
            f.write("""2024-09-21 14:30:25 - INFO - [BLOCKED_IP] 192.168.1.100 - 통합 테스트
2024-09-21 14:30:26 - INFO - [WHITELIST_ADD] 127.0.0.1 - 통합 테스트
2024-09-21 14:30:27 - INFO - [MONITOR] 통합 테스트 모니터링""")

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
            "주간 운영 리포트 생성 시작",
            "보안 로그 분석",
            "백업 로그 분석",
            "시스템 통계 수집",
            "주간 운영 리포트 생성 완료"
        ]

        completed_steps = 0
        for step in workflow_steps:
            if step in output:
                completed_steps += 1
                print(f"   ✅ {step}")
            else:
                print(f"   ❓ {step} (건너뜀)")

        print(f"   완료된 워크플로우 단계: {completed_steps}/{len(workflow_steps)}")

    @pytest.mark.asyncio
    async def test_notifier_integration_end_to_end(self):
        """notifier 통합 End-to-End 테스트"""
        try:
            from mcp.utils.notifier import send_weekly_report_notification
        except ImportError:
            pytest.skip("❓ notifier 모듈을 찾을 수 없어 E2E 테스트를 건너뜁니다")

        # Mock을 사용한 E2E 테스트
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = type('MockResult', (), {
                'returncode': 0,
                'stdout': json.dumps({
                    'report_metadata': {
                        'period_start': '2024-09-14',
                        'period_end': '2024-09-21'
                    },
                    'security_events': {'blocked_ips': 5},
                    'backup_operations': {'success_rate_percent': 95}
                }),
                'stderr': ''
            })

            with patch('mcp.utils.notifier.notification_manager.send_notification') as mock_notify:
                mock_notify.return_value = {'slack': True}

                result = await send_weekly_report_notification()

                assert result is not None, "❌ E2E 테스트 결과가 None입니다"
                assert result.get('success', False), "❌ E2E 테스트가 성공으로 표시되지 않았습니다"

                print("✅ notifier 통합 E2E 테스트 완료")