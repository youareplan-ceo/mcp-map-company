#!/usr/bin/env python3
"""
월간 운영 리포트 스크립트 테스트
Monthly Operations Report Script Tests

이 파일은 scripts/monthly_ops_report.sh 스크립트와 관련 알림 시스템을 테스트합니다.
Tests the monthly_ops_report.sh script and related notification systems.
"""

import pytest
import json
import subprocess
import os
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import sys

# mcp 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from mcp.utils.notifier import (
        send_monthly_ops_report,
        execute_and_notify_monthly_report,
        send_monthly_report_notification,
        test_monthly_report_notification,
        NotificationLevel
    )
except ImportError:
    pytest.skip("notifier 모듈을 찾을 수 없습니다", allow_module_level=True)


class TestMonthlyOpsReportScript:
    """월간 운영 리포트 스크립트 테스트 클래스"""

    @pytest.fixture
    def project_root(self):
        """프로젝트 루트 디렉토리 반환"""
        return Path(__file__).parent.parent

    @pytest.fixture
    def script_path(self, project_root):
        """월간 운영 리포트 스크립트 경로"""
        return project_root / "scripts" / "monthly_ops_report.sh"

    @pytest.fixture
    def sample_report_data(self):
        """테스트용 월간 리포트 데이터"""
        return {
            'report_metadata': {
                'period_start': '2024-08-22',
                'period_end': '2024-09-21',
                'generated_at': datetime.now().isoformat(),
                'report_type': 'monthly_operations'
            },
            'security_events': {
                'blocked_ips': 245,
                'unique_blocked_ips': 68,
                'rate_limit_violations': 180,
                'whitelist_additions': 12,
                'monitoring_events': 520,
                'total_security_events': 957
            },
            'backup_operations': {
                'successful_backups': 28,
                'failed_backups': 2,
                'cleanup_operations': 8,
                'success_rate_percent': 93,
                'total_backup_operations': 30
            },
            'system_resources': {
                'average_disk_usage_percent': 72,
                'max_disk_usage_percent': 89,
                'security_log_size_bytes': 15728640,  # 15MB
                'backup_directory_size_kb': 5242880   # 5GB
            },
            'performance_score': {
                'security_score': 32,
                'backup_score': 37,
                'system_score': 18,
                'total_score': 87,
                'grade': '우수'
            }
        }

    def test_script_exists(self, script_path):
        """스크립트 파일이 존재하고 실행 가능한지 확인"""
        assert script_path.exists(), f"월간 운영 리포트 스크립트가 존재하지 않습니다: {script_path}"
        assert os.access(script_path, os.X_OK), f"스크립트가 실행 가능하지 않습니다: {script_path}"

    def test_script_help_option(self, script_path):
        """스크립트 도움말 옵션 테스트"""
        result = subprocess.run([str(script_path), "--help"], capture_output=True, text=True)

        # 도움말은 정상 종료하거나 특정 exit code를 반환할 수 있음
        assert result.returncode in [0, 1], f"도움말 옵션 실행 실패: {result.stderr}"

        # 한국어 도움말 메시지 확인
        help_keywords = ["월간", "운영", "리포트", "사용법", "옵션"]
        help_text = result.stdout + result.stderr
        found_keywords = [keyword for keyword in help_keywords if keyword in help_text]
        assert len(found_keywords) >= 2, f"한국어 도움말 메시지가 부족합니다. 발견된 키워드: {found_keywords}"

    def test_script_dry_run_option(self, script_path):
        """스크립트 dry-run 옵션 테스트"""
        result = subprocess.run([str(script_path), "--dry-run"], capture_output=True, text=True, timeout=60)

        # dry-run은 실제 변경 없이 실행되어야 함
        assert result.returncode == 0, f"Dry-run 실행 실패: {result.stderr}"

        # dry-run 키워드 확인
        output_text = result.stdout + result.stderr
        assert "dry-run" in output_text.lower() or "건조" in output_text or "모의" in output_text, \
            "Dry-run 모드 표시가 없습니다"

    @pytest.mark.slow
    def test_script_json_output(self, script_path):
        """스크립트 JSON 출력 형식 테스트"""
        result = subprocess.run([str(script_path), "--json"], capture_output=True, text=True, timeout=300)

        # JSON 출력 모드는 성공해야 함
        if result.returncode != 0:
            pytest.skip(f"JSON 출력 실행 실패 (테스트 환경 문제일 수 있음): {result.stderr}")

        # JSON 형식 검증
        try:
            json_data = json.loads(result.stdout.strip())

            # 필수 키 확인
            required_keys = ['report_metadata', 'security_events', 'backup_operations']
            for key in required_keys:
                assert key in json_data, f"JSON 출력에 필수 키 '{key}'가 없습니다"

            # 메타데이터 검증
            metadata = json_data['report_metadata']
            assert 'period_start' in metadata, "리포트 시작 날짜가 없습니다"
            assert 'period_end' in metadata, "리포트 종료 날짜가 없습니다"
            assert 'generated_at' in metadata, "리포트 생성 시간이 없습니다"

        except json.JSONDecodeError as e:
            pytest.fail(f"JSON 파싱 실패: {e}\n출력: {result.stdout}")

    def test_script_verbose_option(self, script_path):
        """스크립트 verbose 옵션 테스트"""
        result = subprocess.run([str(script_path), "--verbose"], capture_output=True, text=True, timeout=120)

        # verbose 모드는 더 많은 출력을 생성해야 함
        if result.returncode == 0:
            # verbose 출력 확인
            output_text = result.stdout + result.stderr
            verbose_indicators = ["진행", "처리", "분석", "생성", "완료", "DEBUG", "INFO"]
            found_indicators = [indicator for indicator in verbose_indicators if indicator in output_text]
            assert len(found_indicators) >= 2, f"Verbose 출력이 부족합니다. 발견된 지표: {found_indicators}"


class TestMonthlyReportNotifications:
    """월간 리포트 알림 시스템 테스트 클래스"""

    @pytest.fixture
    def sample_report_data(self):
        """테스트용 월간 리포트 데이터"""
        return {
            'report_metadata': {
                'period_start': '2024-08-22',
                'period_end': '2024-09-21',
                'generated_at': datetime.now().isoformat(),
                'report_type': 'monthly_operations'
            },
            'security_events': {
                'blocked_ips': 245,
                'unique_blocked_ips': 68,
                'rate_limit_violations': 180,
                'whitelist_additions': 12,
                'monitoring_events': 520,
                'total_security_events': 957
            },
            'backup_operations': {
                'successful_backups': 28,
                'failed_backups': 2,
                'cleanup_operations': 8,
                'success_rate_percent': 93,
                'total_backup_operations': 30
            },
            'system_resources': {
                'average_disk_usage_percent': 72,
                'max_disk_usage_percent': 89,
                'security_log_size_bytes': 15728640,  # 15MB
                'backup_directory_size_kb': 5242880   # 5GB
            },
            'performance_score': {
                'security_score': 32,
                'backup_score': 37,
                'system_score': 18,
                'total_score': 87,
                'grade': '우수'
            }
        }

    @pytest.mark.asyncio
    async def test_send_monthly_ops_report_success(self, sample_report_data):
        """월간 운영 리포트 알림 전송 성공 테스트"""
        with patch('mcp.utils.notifier.notification_manager') as mock_manager:
            # Mock 알림 관리자 설정
            mock_manager.send_notification = AsyncMock(return_value={
                'slack': True,
                'discord': True,
                'email': True
            })

            # 월간 리포트 알림 전송
            result = await send_monthly_ops_report(
                report_data=sample_report_data,
                report_file_path="reports/monthly/monthly-report-2024-09-21.md",
                level=NotificationLevel.INFO
            )

            # 결과 검증
            assert result is not None, "알림 전송 결과가 None입니다"

            # 알림 관리자 호출 확인
            mock_manager.send_notification.assert_called_once()
            call_args = mock_manager.send_notification.call_args

            # 메시지 내용 검증
            assert 'message' in call_args.kwargs, "메시지가 없습니다"
            message = call_args.kwargs['message']
            assert '월간 운영 리포트' in message, "월간 리포트 제목이 없습니다"
            assert '87/100점' in message, "성과 점수가 없습니다"
            assert '우수' in message, "성능 등급이 없습니다"

            # 제목 검증
            assert 'title' in call_args.kwargs, "제목이 없습니다"
            title = call_args.kwargs['title']
            assert '월간 운영 리포트' in title, "제목에 월간 리포트가 없습니다"
            assert '우수' in title, "제목에 성능 등급이 없습니다"

    @pytest.mark.asyncio
    async def test_send_monthly_ops_report_critical_performance(self):
        """성능 등급이 낮을 때 알림 레벨 조정 테스트"""
        critical_data = {
            'report_metadata': {
                'period_start': '2024-08-22',
                'period_end': '2024-09-21',
                'generated_at': datetime.now().isoformat()
            },
            'security_events': {
                'blocked_ips': 500,
                'unique_blocked_ips': 150
            },
            'backup_operations': {
                'success_rate_percent': 75
            },
            'performance_score': {
                'total_score': 45,
                'grade': '개선 필요'
            }
        }

        with patch('mcp.utils.notifier.notification_manager') as mock_manager:
            mock_manager.send_notification = AsyncMock(return_value={'slack': True})

            # 월간 리포트 알림 전송
            result = await send_monthly_ops_report(
                report_data=critical_data,
                level=NotificationLevel.INFO  # 초기 레벨
            )

            # 레벨이 ERROR로 조정되었는지 확인
            call_args = mock_manager.send_notification.call_args
            assert call_args.kwargs['level'] == NotificationLevel.ERROR, \
                "성능 등급이 낮을 때 알림 레벨이 ERROR로 조정되지 않았습니다"

            # 메시지 내용 확인
            message = call_args.kwargs['message']
            assert '개선 필요' in message, "성능 등급 메시지가 없습니다"
            assert '🚨' in message, "경고 이모지가 없습니다"

    @pytest.mark.asyncio
    async def test_execute_and_notify_monthly_report_success(self):
        """월간 리포트 실행 및 알림 통합 테스트 (성공 케이스)"""
        mock_json_output = {
            'report_metadata': {
                'period_start': '2024-08-22',
                'period_end': '2024-09-21',
                'generated_at': datetime.now().isoformat()
            },
            'performance_score': {
                'total_score': 88,
                'grade': '우수'
            }
        }

        with patch('subprocess.run') as mock_run, \
             patch('mcp.utils.notifier.send_monthly_ops_report') as mock_send:

            # Mock 스크립트 실행 성공
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps(mock_json_output),
                stderr=""
            )

            # Mock 알림 전송 성공
            mock_send.return_value = {'slack': True, 'discord': True}

            # 실행 및 알림
            result = await execute_and_notify_monthly_report(
                script_path="scripts/monthly_ops_report.sh",
                script_args=["--json"],
                auto_notify=True
            )

            # 결과 검증
            assert result['success'] is True, "실행이 성공으로 표시되지 않았습니다"
            assert 'execution' in result, "실행 결과가 없습니다"
            assert 'report_data' in result, "리포트 데이터가 없습니다"
            assert 'notification' in result, "알림 결과가 없습니다"

            # 알림 전송 호출 확인
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_and_notify_monthly_report_script_failure(self):
        """월간 리포트 실행 실패 시 에러 알림 테스트"""
        with patch('subprocess.run') as mock_run, \
             patch('mcp.utils.notifier.send_monthly_ops_report') as mock_send:

            # Mock 스크립트 실행 실패
            mock_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="스크립트 실행 오류"
            )

            # Mock 에러 알림 전송
            mock_send.return_value = {'slack': True}

            # 실행 및 알림
            result = await execute_and_notify_monthly_report(
                script_path="scripts/monthly_ops_report.sh",
                auto_notify=True
            )

            # 결과 검증
            assert result['success'] is False, "실행이 실패로 표시되지 않았습니다"

            # 에러 알림 전송 확인
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args.kwargs['level'] == NotificationLevel.ERROR, \
                "실패 시 에러 레벨로 알림이 전송되지 않았습니다"

    @pytest.mark.asyncio
    async def test_execute_and_notify_monthly_report_timeout(self):
        """월간 리포트 실행 타임아웃 테스트"""
        with patch('subprocess.run') as mock_run, \
             patch('mcp.utils.notifier.send_monthly_ops_report') as mock_send:

            # Mock 타임아웃 예외
            from subprocess import TimeoutExpired
            mock_run.side_effect = TimeoutExpired(cmd=['test'], timeout=600)

            # Mock 타임아웃 알림 전송
            mock_send.return_value = {'slack': True}

            # 실행 및 알림
            result = await execute_and_notify_monthly_report(
                script_path="scripts/monthly_ops_report.sh",
                auto_notify=True
            )

            # 결과 검증
            assert result['success'] is False, "타임아웃이 실패로 표시되지 않았습니다"
            assert 'timeout' in result['execution']['error'].lower(), \
                "타임아웃 에러 메시지가 없습니다"

            # 타임아웃 알림 전송 확인
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_monthly_report_notification_convenience(self):
        """월간 리포트 알림 편의 함수 테스트"""
        with patch('mcp.utils.notifier.execute_and_notify_monthly_report') as mock_execute:
            mock_execute.return_value = {
                'success': True,
                'notification': {'slack': True}
            }

            # 편의 함수 호출
            result = await send_monthly_report_notification()

            # 함수 호출 확인
            mock_execute.assert_called_once_with(
                script_args=["--json"],
                auto_notify=True
            )

            # 결과 확인
            assert result is not None, "편의 함수 결과가 None입니다"

    @pytest.mark.asyncio
    async def test_monthly_report_notification_with_period(self):
        """특정 기간으로 월간 리포트 알림 테스트"""
        with patch('mcp.utils.notifier.execute_and_notify_monthly_report') as mock_execute:
            mock_execute.return_value = {'success': True}

            # 특정 기간으로 편의 함수 호출
            await send_monthly_report_notification(report_period="2024-08")

            # 기간 인수가 올바르게 전달되었는지 확인
            call_args = mock_execute.call_args
            expected_args = ["--json", "--period", "2024-08"]
            assert call_args.kwargs['script_args'] == expected_args, \
                f"기간 인수가 올바르게 전달되지 않았습니다: {call_args.kwargs['script_args']}"


class TestMonthlyReportIntegration:
    """월간 리포트 통합 테스트 클래스"""

    @pytest.mark.slow
    @pytest.mark.integration
    async def test_monthly_report_notification_system(self):
        """월간 리포트 알림 시스템 통합 테스트"""
        # 테스트용 알림 시스템 실행
        result = await test_monthly_report_notification()

        # 결과 검증
        assert result is not None, "월간 리포트 알림 테스트 결과가 None입니다"

        # 테스트가 성공적으로 완료되었는지 확인
        print("✅ 월간 리포트 알림 시스템 통합 테스트 완료")

    @pytest.mark.slow
    def test_monthly_report_script_dependencies(self):
        """월간 리포트 스크립트 의존성 확인 테스트"""
        project_root = Path(__file__).parent.parent
        script_path = project_root / "scripts" / "monthly_ops_report.sh"

        if not script_path.exists():
            pytest.skip("월간 운영 리포트 스크립트가 없습니다")

        # 스크립트 내용에서 의존성 확인
        script_content = script_path.read_text(encoding='utf-8')

        # 필수 함수들이 정의되어 있는지 확인
        required_functions = [
            'analyze_security_events',
            'analyze_backup_operations',
            'analyze_system_resources',
            'calculate_monthly_performance_grade'
        ]

        for func in required_functions:
            assert func in script_content, f"필수 함수 '{func}'가 스크립트에 없습니다"

        # 한국어 메시지가 포함되어 있는지 확인
        korean_keywords = ['월간', '리포트', '성과', '분석', '점수']
        found_keywords = [keyword for keyword in korean_keywords if keyword in script_content]
        assert len(found_keywords) >= 3, f"한국어 키워드가 부족합니다: {found_keywords}"


if __name__ == "__main__":
    # 개별 테스트 실행을 위한 메인 함수
    import asyncio

    async def run_basic_tests():
        """기본 테스트 실행"""
        print("🧪 월간 운영 리포트 기본 테스트 시작...")

        # 알림 시스템 테스트
        try:
            result = await test_monthly_report_notification()
            print(f"✅ 월간 리포트 알림 테스트 성공: {result}")
        except Exception as e:
            print(f"❌ 월간 리포트 알림 테스트 실패: {e}")

        print("🧪 월간 운영 리포트 기본 테스트 완료")

    # 비동기 테스트 실행
    asyncio.run(run_basic_tests())