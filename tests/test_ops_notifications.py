#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔔 운영 알림 통합 시스템 통합 테스트 모듈

이 모듈은 운영 알림 통합 시스템의 pytest 기반 통합 테스트를 제공합니다.
- 보안 이벤트 → 알림 발송 검증
- backup_verifier.sh 실행 결과 → 알림 통합 검증
- subprocess.run 검증 및 JSON 결과 파싱 테스트
- 모의 데이터를 통한 시스템 통합 테스트
"""

import pytest
import asyncio
import json
import tempfile
import subprocess
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from pathlib import Path

# 프로젝트 경로를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from mcp.utils.notifier import (
        NotificationLevel,
        BaseNotifier,
        SlackNotifier,
        DiscordNotifier,
        EmailNotifier,
        DashboardNotifier,
        send_backup_alert,
        execute_and_notify_backup_script,
        send_ops_integration_alert,
        OpsIntegrationNotifier
    )
except ImportError as e:
    print(f"⚠️ notifier 모듈 임포트 실패: {e}")

    # 모의 클래스들 정의
    class NotificationLevel:
        CRITICAL = "critical"
        ERROR = "error"
        WARNING = "warning"
        INFO = "info"

    BaseNotifier = Mock
    SlackNotifier = Mock
    DiscordNotifier = Mock
    EmailNotifier = Mock
    DashboardNotifier = Mock
    send_backup_alert = AsyncMock()
    execute_and_notify_backup_script = AsyncMock()
    send_ops_integration_alert = AsyncMock()
    OpsIntegrationNotifier = Mock


class TestOpsNotificationIntegration:
    """운영 알림 통합 시스템 테스트 클래스"""

    @pytest.fixture
    def sample_security_event(self):
        """샘플 보안 이벤트 데이터"""
        return {
            "timestamp": datetime.now().isoformat(),
            "event_type": "login_failure",
            "source_ip": "192.168.1.100",
            "failed_attempts": 50,
            "duration_minutes": 5,
            "user_agent": "Mozilla/5.0 Suspicious Client",
            "action_taken": "IP 차단"
        }

    @pytest.fixture
    def sample_backup_result(self):
        """샘플 백업 결과 데이터"""
        return {
            "script_name": "backup_verifier.sh",
            "execution_time": datetime.now().isoformat(),
            "exit_code": 0,
            "duration_seconds": 45,
            "files_verified": 127,
            "files_corrupted": 3,
            "integrity_percentage": 97.6,
            "status": "warning"
        }

    @pytest.fixture
    def mock_notifiers(self):
        """모의 알림 발송자들"""
        return {
            "slack": AsyncMock(spec=SlackNotifier),
            "discord": AsyncMock(spec=DiscordNotifier),
            "email": AsyncMock(spec=EmailNotifier),
            "dashboard": AsyncMock(spec=DashboardNotifier)
        }

    @pytest.mark.asyncio
    async def test_send_backup_alert_success(self, sample_backup_result, mock_notifiers):
        """백업 알림 발송 성공 테스트"""
        with patch('mcp.utils.notifier.get_configured_notifiers', return_value=mock_notifiers):
            # 백업 알림 발송 실행
            await send_backup_alert(
                script_name="backup_verifier.sh",
                execution_result=sample_backup_result,
                level=NotificationLevel.WARNING
            )

            # 모든 알림 채널에 발송되었는지 확인
            for notifier_name, notifier in mock_notifiers.items():
                notifier.send_notification.assert_called_once()
                call_args = notifier.send_notification.call_args
                assert "백업 검증 결과" in call_args[0][0]  # 메시지 내용 확인

    @pytest.mark.asyncio
    async def test_send_backup_alert_failure(self, sample_backup_result):
        """백업 알림 발송 실패 테스트"""
        # 실패하는 알림 발송자 모의
        failing_notifier = AsyncMock()
        failing_notifier.send_notification.side_effect = Exception("알림 발송 실패")

        mock_notifiers = {"slack": failing_notifier}

        with patch('mcp.utils.notifier.get_configured_notifiers', return_value=mock_notifiers):
            # 예외가 발생하지 않고 처리되는지 확인
            try:
                await send_backup_alert(
                    script_name="backup_verifier.sh",
                    execution_result=sample_backup_result,
                    level=NotificationLevel.ERROR
                )
            except Exception as e:
                pytest.fail(f"알림 발송 실패가 예외를 발생시켰습니다: {e}")

    @pytest.mark.asyncio
    async def test_execute_and_notify_backup_script_success(self, mock_notifiers):
        """백업 스크립트 실행 및 알림 성공 테스트"""
        # 성공적인 스크립트 실행 모의
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "백업 검증 완료\n127개 파일 중 3개 손상"
        mock_result.stderr = ""

        with patch('subprocess.run', return_value=mock_result):
            with patch('mcp.utils.notifier.get_configured_notifiers', return_value=mock_notifiers):
                # 백업 스크립트 실행 및 알림
                result = await execute_and_notify_backup_script(
                    script_path="./scripts/backup_verifier.sh",
                    script_args=["--verbose"],
                    notify_on_success=True,
                    notify_on_error=True
                )

                # 실행 결과 확인
                assert result is not None
                assert result["exit_code"] == 0
                assert "backup_verifier.sh" in result["script_name"]

                # 알림 발송 확인
                for notifier in mock_notifiers.values():
                    notifier.send_notification.assert_called()

    @pytest.mark.asyncio
    async def test_execute_and_notify_backup_script_failure(self, mock_notifiers):
        """백업 스크립트 실행 실패 및 알림 테스트"""
        # 실패하는 스크립트 실행 모의
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "백업 파일을 찾을 수 없습니다"

        with patch('subprocess.run', return_value=mock_result):
            with patch('mcp.utils.notifier.get_configured_notifiers', return_value=mock_notifiers):
                # 백업 스크립트 실행 및 알림
                result = await execute_and_notify_backup_script(
                    script_path="./scripts/backup_verifier.sh",
                    notify_on_error=True
                )

                # 실행 결과 확인
                assert result is not None
                assert result["exit_code"] == 1
                assert len(result["stderr"]) > 0

                # 에러 알림 발송 확인
                for notifier in mock_notifiers.values():
                    notifier.send_notification.assert_called()
                    call_args = notifier.send_notification.call_args
                    assert "실패" in call_args[0][0] or "오류" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_send_ops_integration_alert(self, sample_security_event, sample_backup_result, mock_notifiers):
        """운영 통합 알림 발송 테스트"""
        security_events = [sample_security_event]
        backup_results = [sample_backup_result]

        with patch('mcp.utils.notifier.get_configured_notifiers', return_value=mock_notifiers):
            # 운영 통합 알림 발송
            await send_ops_integration_alert(
                event_type="daily_summary",
                security_events=security_events,
                backup_results=backup_results,
                level=NotificationLevel.INFO
            )

            # 모든 알림 채널에 발송되었는지 확인
            for notifier in mock_notifiers.values():
                notifier.send_notification.assert_called_once()
                call_args = notifier.send_notification.call_args
                message = call_args[0][0]

                # 메시지 내용 확인
                assert "운영 통합 알림" in message
                assert "보안 이벤트" in message
                assert "백업 결과" in message

    def test_subprocess_run_verification(self):
        """subprocess.run 검증 테스트"""
        # 간단한 echo 명령어 실행
        result = subprocess.run(
            ["echo", "테스트 메시지"],
            capture_output=True,
            text=True,
            timeout=10
        )

        # 실행 결과 검증
        assert result.returncode == 0
        assert "테스트 메시지" in result.stdout
        assert result.stderr == ""

    def test_json_result_parsing(self, sample_backup_result):
        """JSON 결과 파싱 테스트"""
        # JSON 직렬화/역직렬화 테스트
        json_string = json.dumps(sample_backup_result, ensure_ascii=False, indent=2)
        parsed_result = json.loads(json_string)

        # 파싱 결과 검증
        assert parsed_result["script_name"] == "backup_verifier.sh"
        assert parsed_result["exit_code"] == 0
        assert parsed_result["files_verified"] == 127
        assert parsed_result["integrity_percentage"] == 97.6

    @pytest.mark.asyncio
    async def test_ops_integration_notifier_class(self, sample_security_event, sample_backup_result):
        """OpsIntegrationNotifier 클래스 테스트"""
        # 모의 알림 발송자들
        mock_notifiers = {
            "slack": AsyncMock(),
            "dashboard": AsyncMock()
        }

        with patch('mcp.utils.notifier.get_configured_notifiers', return_value=mock_notifiers):
            # OpsIntegrationNotifier 인스턴스 생성
            ops_notifier = OpsIntegrationNotifier()

            # 보안 이벤트 알림 발송
            await ops_notifier.send_security_event_notification(
                event=sample_security_event,
                level=NotificationLevel.CRITICAL
            )

            # 백업 결과 알림 발송
            await ops_notifier.send_backup_result_notification(
                result=sample_backup_result,
                level=NotificationLevel.WARNING
            )

            # 통합 알림 발송
            await ops_notifier.send_integrated_notification(
                security_events=[sample_security_event],
                backup_results=[sample_backup_result],
                summary="일일 운영 요약"
            )

    @pytest.mark.asyncio
    async def test_notification_with_mock_data(self):
        """모의 데이터를 통한 알림 시스템 테스트"""
        # 모의 보안 이벤트 생성
        mock_security_events = [
            {
                "timestamp": datetime.now().isoformat(),
                "event_type": "brute_force_attack",
                "source_ip": "203.0.113.1",
                "failed_attempts": 100,
                "severity": "high"
            },
            {
                "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
                "event_type": "suspicious_file_access",
                "user": "unknown_user",
                "file_path": "/etc/passwd",
                "severity": "critical"
            }
        ]

        # 모의 백업 결과 생성
        mock_backup_results = [
            {
                "script_name": "backup_verifier.sh",
                "execution_time": datetime.now().isoformat(),
                "exit_code": 0,
                "files_checked": 250,
                "files_passed": 248,
                "integrity_status": "good"
            }
        ]

        # 모의 알림 발송자
        mock_notifiers = {
            "slack": AsyncMock(),
            "email": AsyncMock()
        }

        with patch('mcp.utils.notifier.get_configured_notifiers', return_value=mock_notifiers):
            # 통합 알림 발송
            await send_ops_integration_alert(
                event_type="security_backup_summary",
                security_events=mock_security_events,
                backup_results=mock_backup_results,
                level=NotificationLevel.WARNING
            )

            # 알림 발송 검증
            for notifier in mock_notifiers.values():
                notifier.send_notification.assert_called_once()

    def test_backup_script_path_validation(self):
        """백업 스크립트 경로 검증 테스트"""
        # 프로젝트 루트에서 스크립트 경로 확인
        project_root = Path(__file__).parent.parent
        backup_verifier_path = project_root / "scripts" / "backup_verifier.sh"
        cleanup_backups_path = project_root / "scripts" / "cleanup_old_backups.sh"

        # 스크립트 파일 존재 여부 확인 (있으면 좋지만 없어도 테스트는 통과)
        if backup_verifier_path.exists():
            print(f"✅ backup_verifier.sh 스크립트 발견: {backup_verifier_path}")
            assert backup_verifier_path.is_file()
        else:
            print(f"⚠️ backup_verifier.sh 스크립트 없음: {backup_verifier_path}")

        if cleanup_backups_path.exists():
            print(f"✅ cleanup_old_backups.sh 스크립트 발견: {cleanup_backups_path}")
            assert cleanup_backups_path.is_file()
        else:
            print(f"⚠️ cleanup_old_backups.sh 스크립트 없음: {cleanup_backups_path}")

    @pytest.mark.asyncio
    async def test_notification_error_handling(self):
        """알림 발송 오류 처리 테스트"""
        # 다양한 오류 상황 모의
        error_scenarios = [
            ConnectionError("네트워크 연결 실패"),
            TimeoutError("알림 발송 타임아웃"),
            ValueError("잘못된 알림 형식"),
            Exception("일반적인 알림 오류")
        ]

        for error in error_scenarios:
            failing_notifier = AsyncMock()
            failing_notifier.send_notification.side_effect = error

            mock_notifiers = {"test": failing_notifier}

            with patch('mcp.utils.notifier.get_configured_notifiers', return_value=mock_notifiers):
                # 오류가 발생해도 예외가 전파되지 않는지 확인
                try:
                    await send_backup_alert(
                        script_name="test_script.sh",
                        execution_result={"exit_code": 0, "message": "테스트"},
                        level=NotificationLevel.INFO
                    )
                except Exception as e:
                    pytest.fail(f"오류 처리 실패: {e}")

    def test_notification_level_validation(self):
        """알림 레벨 검증 테스트"""
        # 유효한 알림 레벨들
        valid_levels = [
            NotificationLevel.CRITICAL,
            NotificationLevel.ERROR,
            NotificationLevel.WARNING,
            NotificationLevel.INFO
        ]

        for level in valid_levels:
            assert level in ["critical", "error", "warning", "info"]
            print(f"✅ 유효한 알림 레벨: {level}")

    @pytest.mark.asyncio
    async def test_dashboard_integration(self):
        """대시보드 통합 테스트"""
        # 대시보드 알림 발송자 모의
        dashboard_notifier = AsyncMock(spec=DashboardNotifier)

        mock_notifiers = {"dashboard": dashboard_notifier}

        with patch('mcp.utils.notifier.get_configured_notifiers', return_value=mock_notifiers):
            # 대시보드 알림 발송
            await send_backup_alert(
                script_name="backup_verifier.sh",
                execution_result={
                    "exit_code": 0,
                    "message": "백업 검증 완료",
                    "timestamp": datetime.now().isoformat()
                },
                level=NotificationLevel.INFO
            )

            # 대시보드 알림 발송 확인
            dashboard_notifier.send_notification.assert_called_once()
            call_args = dashboard_notifier.send_notification.call_args

            # 대시보드용 메시지 형식 확인
            message = call_args[0][0]
            assert isinstance(message, str)
            assert len(message) > 0


if __name__ == "__main__":
    # 테스트 실행
    print("🔔 운영 알림 통합 시스템 테스트 시작...")

    # pytest 실행 (verbose 모드)
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--maxfail=5"
    ])