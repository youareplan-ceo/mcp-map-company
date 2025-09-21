#!/usr/bin/env python3
"""
분기별 운영 리포트 스크립트 테스트
Quarterly Operations Report Script Tests

이 파일은 scripts/quarterly_ops_report.sh 스크립트와 관련 알림 시스템을 테스트합니다.
Tests the quarterly_ops_report.sh script and related notification systems.
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
        send_quarterly_ops_report,
        notify_quarterly_report,
        NotificationLevel
    )
except ImportError:
    pytest.skip("notifier 모듈을 찾을 수 없습니다", allow_module_level=True)


class TestQuarterlyOpsReportScript:
    """분기별 운영 리포트 스크립트 테스트 클래스"""

    @pytest.fixture
    def project_root(self):
        """프로젝트 루트 디렉토리 반환"""
        return Path(__file__).parent.parent

    @pytest.fixture
    def script_path(self, project_root):
        """분기별 운영 리포트 스크립트 경로"""
        return project_root / "scripts" / "quarterly_ops_report.sh"

    @pytest.fixture
    def sample_report_data(self):
        """테스트용 분기별 리포트 데이터"""
        return {
            "report_metadata": {
                "quarter": "Q1",
                "year": 2024,
                "start_date": "2024-01-01",
                "end_date": "2024-03-31",
                "generated_at": "2024-03-31T23:59:59Z"
            },
            "performance_summary": {
                "total_score": 85,
                "grade": "우수",
                "security_score": 26,
                "backup_score": 28,
                "system_score": 16,
                "ci_score": 15
            },
            "monthly_trends": {
                "month1_score": 82,
                "month2_score": 85,
                "month3_score": 88
            },
            "security_events": {
                "total_events": 156,
                "blocked_ips": 45,
                "rate_limit_violations": 23,
                "whitelist_additions": 8
            },
            "backup_operations": {
                "successful_backups": 270,
                "failed_backups": 3,
                "cleanup_operations": 90,
                "success_rate_percent": 98.9
            },
            "system_performance": {
                "avg_cpu_percent": 25.4,
                "avg_memory_percent": 68.2,
                "avg_disk_percent": 45.8,
                "uptime_days": 89
            },
            "ci_performance": {
                "total_runs": 450,
                "successful_runs": 425,
                "failed_runs": 25,
                "success_rate_percent": 94.4,
                "avg_duration_minutes": 12.5
            },
            "recommendations": [
                "메모리 사용률이 높으므로 시스템 최적화 권장",
                "CI 실패율 개선을 위한 테스트 코드 품질 향상 필요"
            ],
            "critical_periods": [
                {
                    "date": "2024-02-14",
                    "description": "밸런타인 데이 트래픽 증가로 인한 일시적 성능 저하"
                }
            ]
        }

    @pytest.fixture
    def mock_logs_directory(self, tmp_path):
        """모킹된 로그 디렉토리 생성"""
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        # 샘플 로그 파일들 생성
        (logs_dir / "security.log").write_text("""
2024-03-01 10:00:00 [INFO] IP 192.168.1.100 blocked due to rate limit violation
2024-03-15 14:30:00 [WARN] Multiple failed login attempts from 10.0.0.50
2024-03-30 09:15:00 [INFO] New IP 172.16.0.25 added to whitelist
        """.strip())

        (logs_dir / "backup.log").write_text("""
2024-03-01 02:00:00 [SUCCESS] Database backup completed - 2.5GB
2024-03-02 02:00:00 [SUCCESS] Database backup completed - 2.6GB
2024-03-03 02:00:00 [ERROR] Database backup failed - connection timeout
2024-03-04 02:00:00 [SUCCESS] Database backup completed - 2.7GB
        """.strip())

        return logs_dir

    def test_script_exists(self, script_path):
        """스크립트 파일이 존재하는지 테스트"""
        assert script_path.exists(), f"분기별 운영 리포트 스크립트를 찾을 수 없습니다: {script_path}"
        assert script_path.is_file(), "스크립트가 파일이 아닙니다"

    def test_script_executable(self, script_path):
        """스크립트가 실행 가능한지 테스트"""
        assert os.access(script_path, os.X_OK), "스크립트가 실행 권한이 없습니다"

    def test_script_help_output(self, script_path):
        """스크립트 도움말 출력 테스트"""
        try:
            result = subprocess.run(
                [str(script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=30
            )

            # 도움말이 올바르게 출력되는지 확인
            assert "분기별 운영 리포트" in result.stdout
            assert "quarterly" in result.stdout.lower()
            assert "usage" in result.stdout.lower() or "사용법" in result.stdout

        except subprocess.TimeoutExpired:
            pytest.fail("스크립트 도움말 출력이 30초 내에 완료되지 않았습니다")
        except FileNotFoundError:
            pytest.fail(f"스크립트를 실행할 수 없습니다: {script_path}")

    def test_script_syntax_validation(self, script_path):
        """스크립트 구문 유효성 테스트"""
        try:
            # bash 구문 검사
            result = subprocess.run(
                ["bash", "-n", str(script_path)],
                capture_output=True,
                text=True,
                timeout=10
            )

            assert result.returncode == 0, f"스크립트 구문 오류: {result.stderr}"

        except subprocess.TimeoutExpired:
            pytest.fail("스크립트 구문 검사가 10초 내에 완료되지 않았습니다")

    @pytest.mark.parametrize("quarter,expected_days", [
        ("Q1", 90),  # 1-3월 (윤년 아님)
        ("Q2", 91),  # 4-6월
        ("Q3", 92),  # 7-9월
        ("Q4", 92),  # 10-12월
    ])
    def test_quarterly_period_calculation(self, quarter, expected_days):
        """분기별 기간 계산 테스트"""
        # 실제 스크립트에서 분기별 기간이 올바르게 계산되는지 확인하는 로직
        # 이는 스크립트 내부 함수 테스트를 위한 예시입니다
        if quarter == "Q1":
            start_date = datetime(2024, 1, 1)
            end_date = datetime(2024, 3, 31)
        elif quarter == "Q2":
            start_date = datetime(2024, 4, 1)
            end_date = datetime(2024, 6, 30)
        elif quarter == "Q3":
            start_date = datetime(2024, 7, 1)
            end_date = datetime(2024, 9, 30)
        else:  # Q4
            start_date = datetime(2024, 10, 1)
            end_date = datetime(2024, 12, 31)

        actual_days = (end_date - start_date).days + 1
        assert actual_days == expected_days, f"{quarter} 분기 일수가 예상과 다릅니다"

    @pytest.mark.parametrize("total_score,expected_grade", [
        (95, "우수"),
        (85, "우수"),
        (75, "보통"),
        (65, "보통"),
        (55, "개선 필요"),
        (45, "개선 필요"),
    ])
    def test_performance_grading(self, total_score, expected_grade):
        """성과 등급 판정 테스트"""
        # 성과 점수에 따른 등급 판정 로직 테스트
        if total_score >= 80:
            grade = "우수"
        elif total_score >= 60:
            grade = "보통"
        else:
            grade = "개선 필요"

        assert grade == expected_grade, f"점수 {total_score}에 대한 등급이 잘못되었습니다"

    @pytest.mark.parametrize("year,quarter,expected_dates", [
        (2024, 1, ("2024-01-01", "2024-03-31")),
        (2024, 2, ("2024-04-01", "2024-06-30")),
        (2024, 3, ("2024-07-01", "2024-09-30")),
        (2024, 4, ("2024-10-01", "2024-12-31")),
        (2025, 2, ("2025-04-01", "2025-06-30")),
    ])
    def test_year_quarter_options(self, script_path, year, quarter, expected_dates, tmp_path):
        """--year 및 --quarter 옵션 테스트"""
        try:
            result = subprocess.run(
                [str(script_path), "--year", str(year), "--quarter", str(quarter), "--dry-run"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=tmp_path
            )

            # 스크립트가 성공적으로 실행되었는지 확인
            assert result.returncode == 0, f"스크립트 실행 실패: {result.stderr}"

            # 지정된 분기 정보가 출력에 포함되는지 확인
            output = result.stderr  # 로그는 stderr로 출력됨
            assert f"{year}년 {quarter}분기" in output, "지정된 분기 정보가 출력에 없습니다"
            assert expected_dates[0] in output, f"시작 날짜 {expected_dates[0]}가 출력에 없습니다"
            assert expected_dates[1] in output, f"종료 날짜 {expected_dates[1]}가 출력에 없습니다"

        except subprocess.TimeoutExpired:
            pytest.fail("--year --quarter 옵션 테스트가 60초 내에 완료되지 않았습니다")

    def test_invalid_year_option(self, script_path, tmp_path):
        """잘못된 --year 옵션 테스트"""
        try:
            result = subprocess.run(
                [str(script_path), "--year", "abc", "--quarter", "1", "--dry-run"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=tmp_path
            )

            # 에러로 종료되어야 함
            assert result.returncode != 0, "잘못된 연도에 대해 에러가 발생하지 않았습니다"
            assert "잘못된 연도 형식" in result.stderr or "ERROR" in result.stderr

        except subprocess.TimeoutExpired:
            pytest.fail("잘못된 연도 테스트가 30초 내에 완료되지 않았습니다")

    def test_invalid_quarter_option(self, script_path, tmp_path):
        """잘못된 --quarter 옵션 테스트"""
        try:
            result = subprocess.run(
                [str(script_path), "--year", "2024", "--quarter", "5", "--dry-run"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=tmp_path
            )

            # 에러로 종료되어야 함
            assert result.returncode != 0, "잘못된 분기에 대해 에러가 발생하지 않았습니다"
            assert "잘못된 분기 형식" in result.stderr or "ERROR" in result.stderr

        except subprocess.TimeoutExpired:
            pytest.fail("잘못된 분기 테스트가 30초 내에 완료되지 않았습니다")

    def test_markdown_option(self, script_path, tmp_path):
        """--md/--markdown 옵션 테스트"""
        try:
            result = subprocess.run(
                [str(script_path), "--md", "--dry-run"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=tmp_path
            )

            # 스크립트가 성공적으로 실행되었는지 확인
            assert result.returncode == 0, f"--md 옵션 테스트 실패: {result.stderr}"

            # Markdown 리포트 생성 메시지 확인
            output = result.stderr
            assert "Markdown 리포트 생성" in output, "Markdown 리포트 생성 메시지가 없습니다"

        except subprocess.TimeoutExpired:
            pytest.fail("--md 옵션 테스트가 60초 내에 완료되지 않았습니다")


class TestQuarterlyOpsReportNotifications:
    """분기별 운영 리포트 알림 시스템 테스트 클래스"""

    @pytest.fixture
    def sample_excellent_data(self):
        """우수 등급 테스트 데이터"""
        return {
            "report_metadata": {"quarter": "Q1", "year": 2024},
            "performance_summary": {
                "total_score": 92,
                "grade": "우수",
                "security_score": 28,
                "backup_score": 29,
                "system_score": 18,
                "ci_score": 17
            },
            "monthly_trends": {"month1_score": 90, "month2_score": 92, "month3_score": 94},
            "security_events": {"total_events": 50, "blocked_ips": 10, "rate_limit_violations": 5, "whitelist_additions": 2},
            "backup_operations": {"successful_backups": 270, "failed_backups": 0, "cleanup_operations": 90, "success_rate_percent": 100},
            "system_performance": {"avg_cpu_percent": 15.2, "avg_memory_percent": 45.8, "avg_disk_percent": 38.5, "uptime_days": 90},
            "ci_performance": {"total_runs": 500, "successful_runs": 485, "failed_runs": 15, "success_rate_percent": 97.0, "avg_duration_minutes": 8.5},
            "recommendations": [],
            "critical_periods": []
        }

    @pytest.fixture
    def sample_poor_data(self):
        """개선 필요 등급 테스트 데이터"""
        return {
            "report_metadata": {"quarter": "Q2", "year": 2024},
            "performance_summary": {
                "total_score": 45,
                "grade": "개선 필요",
                "security_score": 15,
                "backup_score": 12,
                "system_score": 8,
                "ci_score": 10
            },
            "monthly_trends": {"month1_score": 48, "month2_score": 44, "month3_score": 43},
            "security_events": {"total_events": 200, "blocked_ips": 80, "rate_limit_violations": 50, "whitelist_additions": 1},
            "backup_operations": {"successful_backups": 180, "failed_backups": 90, "cleanup_operations": 30, "success_rate_percent": 66.7},
            "system_performance": {"avg_cpu_percent": 85.5, "avg_memory_percent": 92.1, "avg_disk_percent": 88.3, "uptime_days": 45},
            "ci_performance": {"total_runs": 300, "successful_runs": 200, "failed_runs": 100, "success_rate_percent": 66.7, "avg_duration_minutes": 25.8},
            "recommendations": [
                "시스템 리소스 최적화 긴급 필요",
                "백업 시스템 점검 및 개선 필요",
                "CI/CD 파이프라인 안정성 향상 필요"
            ],
            "critical_periods": [
                {"date": "2024-05-15", "description": "서버 다운타임 8시간"},
                {"date": "2024-06-10", "description": "백업 시스템 장애"}
            ]
        }

    @pytest.mark.asyncio
    async def test_send_quarterly_ops_report_success(self, sample_excellent_data):
        """분기별 운영 리포트 알림 전송 성공 테스트"""
        with patch('mcp.utils.notifier.send_notification') as mock_send:
            mock_send.return_value = True

            result = await send_quarterly_ops_report(sample_excellent_data)

            assert result is True
            assert mock_send.call_count >= 2  # Slack, Discord 최소 2번 호출

    @pytest.mark.asyncio
    async def test_send_quarterly_ops_report_with_poor_performance(self, sample_poor_data):
        """성과 부진 시 분기별 리포트 알림 테스트"""
        with patch('mcp.utils.notifier.send_notification') as mock_send:
            mock_send.return_value = True

            result = await send_quarterly_ops_report(sample_poor_data)

            assert result is True
            # 성과 부진 시 이메일 알림도 포함되어야 함
            assert mock_send.call_count >= 3  # Slack, Discord, Email

    @pytest.mark.asyncio
    async def test_send_quarterly_ops_report_with_invalid_data(self):
        """잘못된 데이터로 분기별 리포트 알림 테스트"""
        result = await send_quarterly_ops_report(None)
        assert result is False

        result = await send_quarterly_ops_report({})
        assert result is False

    @pytest.mark.asyncio
    async def test_notification_level_determination(self, sample_excellent_data, sample_poor_data):
        """알림 레벨 자동 판정 테스트"""
        with patch('mcp.utils.notifier.send_notification') as mock_send:
            mock_send.return_value = True

            # 우수 성과 데이터
            await send_quarterly_ops_report(sample_excellent_data)

            # 첫 번째 호출에서 INFO 레벨 사용 확인
            first_call_args = mock_send.call_args_list[0]
            assert first_call_args[1]['level'] == NotificationLevel.INFO

            mock_send.reset_mock()

            # 부진 성과 데이터
            await send_quarterly_ops_report(sample_poor_data)

            # 첫 번째 호출에서 ERROR 레벨 사용 확인
            first_call_args = mock_send.call_args_list[0]
            assert first_call_args[1]['level'] == NotificationLevel.ERROR

    @pytest.mark.asyncio
    async def test_message_content_structure(self, sample_excellent_data):
        """메시지 내용 구조 테스트"""
        with patch('mcp.utils.notifier.send_notification') as mock_send:
            mock_send.return_value = True

            await send_quarterly_ops_report(sample_excellent_data)

            # 첫 번째 호출 인자 확인
            call_args = mock_send.call_args_list[0]
            message = call_args[1]['message']
            title = call_args[1]['title']

            # 제목에 분기 정보 포함 확인
            assert "Q1" in title
            assert "2024" in title
            assert "분기별 운영 리포트" in title

            # 메시지에 필수 정보 포함 확인
            assert "종합 성과" in message
            assert "92/100점" in message
            assert "우수" in message
            assert "보안:" in message
            assert "백업:" in message
            assert "시스템:" in message
            assert "CI/CD:" in message

    @pytest.mark.asyncio
    async def test_quarterly_convenience_function(self, sample_excellent_data):
        """분기별 리포트 편의 함수 테스트"""
        with patch('mcp.utils.notifier.send_quarterly_ops_report') as mock_send:
            mock_send.return_value = True

            result = await notify_quarterly_report(sample_excellent_data, force_send=True)

            assert result is True
            mock_send.assert_called_once_with(sample_excellent_data, force_send=True)

    @pytest.mark.parametrize("quarter,year", [
        ("Q1", 2024),
        ("Q2", 2024),
        ("Q3", 2023),
        ("Q4", 2023),
    ])
    @pytest.mark.asyncio
    async def test_different_quarters_and_years(self, quarter, year, sample_excellent_data):
        """다양한 분기와 연도 테스트"""
        sample_excellent_data["report_metadata"]["quarter"] = quarter
        sample_excellent_data["report_metadata"]["year"] = year

        with patch('mcp.utils.notifier.send_notification') as mock_send:
            mock_send.return_value = True

            result = await send_quarterly_ops_report(sample_excellent_data)

            assert result is True

            # 제목에 올바른 분기와 연도가 포함되는지 확인
            call_args = mock_send.call_args_list[0]
            title = call_args[1]['title']
            assert quarter in title
            assert str(year) in title

    @pytest.mark.asyncio
    async def test_error_handling_in_notification_sending(self, sample_excellent_data):
        """알림 전송 중 오류 처리 테스트"""
        with patch('mcp.utils.notifier.send_notification') as mock_send:
            # 첫 번째 호출은 실패, 두 번째는 성공
            mock_send.side_effect = [False, True]

            result = await send_quarterly_ops_report(sample_excellent_data)

            # 하나라도 성공하면 전체 성공으로 처리
            assert result is True

    @pytest.mark.asyncio
    async def test_force_send_parameter(self, sample_excellent_data):
        """강제 전송 매개변수 테스트"""
        with patch('mcp.utils.notifier.send_notification') as mock_send:
            mock_send.return_value = True

            await send_quarterly_ops_report(sample_excellent_data, force_send=True)

            # 모든 호출에서 force_send=True가 전달되는지 확인
            for call_args in mock_send.call_args_list:
                assert call_args[1]['force_send'] is True


class TestQuarterlyOpsReportIntegration:
    """분기별 운영 리포트 통합 테스트 클래스"""

    @pytest.mark.integration
    def test_script_with_mock_logs(self, tmp_path):
        """모킹된 로그와 함께 스크립트 실행 테스트"""
        # 임시 로그 디렉토리 생성
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        # 기본 로그 파일들 생성
        security_log = logs_dir / "security.log"
        security_log.write_text("2024-03-01 10:00:00 [INFO] Test security event")

        backup_log = logs_dir / "backup.log"
        backup_log.write_text("2024-03-01 02:00:00 [SUCCESS] Test backup completed")

        # 환경 변수 설정하여 스크립트 실행
        env = os.environ.copy()
        env['TEST_MODE'] = '1'
        env['LOGS_DIR'] = str(logs_dir)

        script_path = Path(__file__).parent.parent / "scripts" / "quarterly_ops_report.sh"

        try:
            result = subprocess.run(
                [str(script_path), "--test"],
                capture_output=True,
                text=True,
                timeout=60,
                env=env
            )

            # 스크립트가 정상적으로 실행되었는지 확인
            assert result.returncode == 0, f"스크립트 실행 실패: {result.stderr}"

            # 출력에 기본적인 리포트 구조가 포함되는지 확인
            output = result.stdout
            assert "분기별 운영 리포트" in output or "Quarterly Operations Report" in output

        except subprocess.TimeoutExpired:
            pytest.fail("스크립트 실행이 60초 내에 완료되지 않았습니다")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_end_to_end_quarterly_report_flow(self, sample_excellent_data):
        """분기별 리포트 전체 플로우 엔드투엔드 테스트"""
        # 실제 알림 시스템을 모킹하되, 전체 플로우를 테스트
        with patch('mcp.utils.notifier.send_notification') as mock_send:
            mock_send.return_value = True

            # 1. 리포트 데이터 생성 및 검증
            assert sample_excellent_data["performance_summary"]["total_score"] > 80

            # 2. 알림 전송
            result = await send_quarterly_ops_report(sample_excellent_data)
            assert result is True

            # 3. 로그 메타데이터 확인 (실제 구현에서는 로그 파일 확인)
            assert mock_send.called

            # 4. 편의 함수를 통한 호출도 테스트
            convenience_result = await notify_quarterly_report(sample_excellent_data)
            assert convenience_result is True


if __name__ == "__main__":
    # 개별 테스트 실행을 위한 메인 함수
    pytest.main([__file__, "-v"])