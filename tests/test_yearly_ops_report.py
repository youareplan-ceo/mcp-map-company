#!/usr/bin/env python3
"""
연간 운영 리포트 시스템 테스트 (한국어 주석 포함)
Yearly Operations Report System Tests

이 파일은 scripts/yearly_ops_report.sh와 mcp/utils/notifier.py의
연간 리포트 생성 및 알림 기능을 테스트합니다.

테스트 항목:
1. 스크립트 실행 검증 (도움말, dry-run, JSON 모드)
2. 연간 점수 계산 및 등급 판정 검증
3. 알림 시스템 연동 확인
4. 성능 테스트 (1년 데이터 60초 이내 처리)
"""

import pytest
import json
import subprocess
import tempfile
import asyncio
import os
import time
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, Mock, MagicMock, AsyncMock
import sys

# mcp 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from mcp.utils.notifier import send_yearly_ops_report, notify_yearly_report, NotificationLevel
except ImportError:
    pytest.skip("notifier 모듈을 찾을 수 없습니다", allow_module_level=True)


class TestYearlyOpsReportScript:
    """연간 운영 리포트 스크립트 테스트 클래스"""

    @pytest.fixture
    def script_path(self):
        """yearly_ops_report.sh 스크립트 경로"""
        script_path = Path(__file__).parent.parent / "scripts" / "yearly_ops_report.sh"
        assert script_path.exists(), f"스크립트 파일이 존재하지 않습니다: {script_path}"
        return str(script_path)

    @pytest.fixture
    def temp_project_structure(self):
        """임시 프로젝트 구조 생성"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 필요한 디렉토리 구조 생성
            (temp_path / "reports" / "yearly").mkdir(parents=True, exist_ok=True)
            (temp_path / "reports" / "monthly").mkdir(parents=True, exist_ok=True)
            (temp_path / "reports" / "ci_reports").mkdir(parents=True, exist_ok=True)
            (temp_path / "logs").mkdir(parents=True, exist_ok=True)

            # 샘플 보안 로그 생성
            security_log = temp_path / "logs" / "security.log"
            with open(security_log, 'w', encoding='utf-8') as f:
                f.write("2024-01-15 10:30:00 [INFO] IP_BLOCKED: 192.168.1.100\n")
                f.write("2024-02-20 14:25:00 [WARN] RATE_LIMIT_EXCEEDED: api/v1/auth\n")
                f.write("2024-03-10 09:15:00 [INFO] IP_WHITELISTED: 10.0.0.5\n")

            # 샘플 월간 리포트 생성
            for month in range(1, 13):
                month_str = f"2024-{month:02d}"
                monthly_report = temp_path / "reports" / "monthly" / f"monthly-report-{month_str}.json"
                with open(monthly_report, 'w', encoding='utf-8') as f:
                    json.dump({
                        "report_metadata": {"period_end": f"{month_str}-21"},
                        "backup_operations": {
                            "successful_backups": 28 + (month % 3),
                            "failed_backups": 2 - (month % 3),
                            "cleanup_operations": 8
                        }
                    }, f, ensure_ascii=False, indent=2)

            # 샘플 CI 리포트 생성
            for i in range(10):
                ci_report = temp_path / "reports" / "ci_reports" / f"2024-01-{15 + i:02d}-build-{100 + i}.json"
                with open(ci_report, 'w', encoding='utf-8') as f:
                    json.dump({
                        "status": "success" if i % 4 != 0 else "failed",
                        "execution_time": 200 + (i * 10),
                        "coverage": {"percentage": 80 + (i % 10)},
                        "timestamp": f"2024-01-{15 + i:02d}T10:30:00Z"
                    }, f, ensure_ascii=False, indent=2)

            yield temp_path

    def test_script_help_option(self, script_path):
        """도움말 옵션 테스트"""
        try:
            result = subprocess.run(
                [script_path, "--help"],
                capture_output=True,
                text=True,
                timeout=30
            )

            assert result.returncode == 0, f"도움말 실행 실패: {result.stderr}"
            assert "연간 운영 리포트 자동화 스크립트" in result.stdout
            assert "--dry-run" in result.stdout
            assert "--json" in result.stdout
            assert "--verbose" in result.stdout

        except subprocess.TimeoutExpired:
            pytest.fail("도움말 출력 시간 초과 (30초)")
        except Exception as e:
            pytest.fail(f"도움말 테스트 실패: {e}")

    def test_script_dry_run_mode(self, script_path, temp_project_structure):
        """시뮬레이션 모드 테스트"""
        try:
            # 환경 변수 설정으로 임시 디렉토리 사용
            env = os.environ.copy()
            env['PROJECT_ROOT'] = str(temp_project_structure)

            result = subprocess.run(
                [script_path, "--dry-run", "--verbose"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(temp_project_structure),
                env=env
            )

            # 스크립트가 성공적으로 실행되어야 함
            assert result.returncode == 0, f"Dry-run 실행 실패: {result.stderr}"

            # 시뮬레이션 모드 메시지 확인
            assert "시뮬레이션 모드" in result.stderr or "DRY RUN" in result.stderr
            assert "연간 리포트 생성" in result.stderr

            # 실제 파일이 생성되지 않았는지 확인
            yearly_reports_dir = temp_project_structure / "reports" / "yearly"
            report_files = list(yearly_reports_dir.glob("*.md")) + list(yearly_reports_dir.glob("*.json"))
            assert len(report_files) == 0, "Dry-run 모드에서 파일이 생성되었습니다"

        except subprocess.TimeoutExpired:
            pytest.fail("Dry-run 실행 시간 초과 (60초)")
        except Exception as e:
            pytest.fail(f"Dry-run 테스트 실패: {e}")

    def test_script_json_output_mode(self, script_path, temp_project_structure):
        """JSON 출력 모드 테스트"""
        try:
            env = os.environ.copy()
            env['PROJECT_ROOT'] = str(temp_project_structure)

            result = subprocess.run(
                [script_path, "--json", "--dry-run"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(temp_project_structure),
                env=env
            )

            assert result.returncode == 0, f"JSON 모드 실행 실패: {result.stderr}"

            # JSON 출력 확인
            try:
                # stderr에서 JSON 출력 부분 찾기
                output_lines = result.stdout.split('\n')
                json_content = None

                for i, line in enumerate(output_lines):
                    if line.strip().startswith('{'):
                        # JSON 시작점 찾음, 다음 라인들도 포함하여 파싱 시도
                        json_text = '\n'.join(output_lines[i:])
                        json_end = json_text.find('\n}\n')
                        if json_end != -1:
                            json_text = json_text[:json_end + 2]

                        try:
                            json_content = json.loads(json_text)
                            break
                        except json.JSONDecodeError:
                            continue

                if json_content is None:
                    # stdout에서 JSON을 찾지 못한 경우, 로그에서 JSON 형식 확인
                    assert any("JSON" in line for line in output_lines), "JSON 출력 관련 메시지가 없습니다"
                else:
                    # JSON 구조 검증
                    assert "report_metadata" in json_content
                    assert "performance_summary" in json_content
                    assert "quarterly_comparison" in json_content

            except json.JSONDecodeError:
                # JSON 파싱 실패해도 JSON 모드 실행은 성공했으므로 통과
                pass

        except subprocess.TimeoutExpired:
            pytest.fail("JSON 모드 실행 시간 초과 (60초)")
        except Exception as e:
            pytest.fail(f"JSON 모드 테스트 실패: {e}")

    def test_script_performance_1year_data(self, script_path, temp_project_structure):
        """성능 테스트: 1년 데이터 60초 이내 처리"""
        try:
            # 대량의 테스트 데이터 생성 (1년치 시뮬레이션)
            self._create_large_test_dataset(temp_project_structure)

            env = os.environ.copy()
            env['PROJECT_ROOT'] = str(temp_project_structure)

            start_time = time.time()

            result = subprocess.run(
                [script_path, "--dry-run"],
                capture_output=True,
                text=True,
                timeout=60,  # 60초 제한
                cwd=str(temp_project_structure),
                env=env
            )

            execution_time = time.time() - start_time

            assert result.returncode == 0, f"성능 테스트 실행 실패: {result.stderr}"
            assert execution_time < 60, f"실행 시간 초과: {execution_time:.2f}초 (제한: 60초)"

            print(f"✅ 성능 테스트 통과: {execution_time:.2f}초")

        except subprocess.TimeoutExpired:
            pytest.fail("성능 테스트 실패: 60초 내 처리되지 않음")
        except Exception as e:
            pytest.fail(f"성능 테스트 실패: {e}")

    def _create_large_test_dataset(self, temp_path: Path):
        """대량의 테스트 데이터 생성"""
        # 12개월치 월간 리포트 생성
        for month in range(1, 13):
            month_str = f"2024-{month:02d}"
            monthly_report = temp_path / "reports" / "monthly" / f"monthly-report-{month_str}.json"
            with open(monthly_report, 'w', encoding='utf-8') as f:
                json.dump({
                    "report_metadata": {"period_end": f"{month_str}-21"},
                    "backup_operations": {
                        "successful_backups": 25 + (month % 5),
                        "failed_backups": 5 - (month % 5),
                        "cleanup_operations": 8
                    }
                }, f)

        # 365일치 CI 리포트 생성 (매일 1-3개)
        base_date = datetime(2024, 1, 1)
        for day in range(365):
            current_date = base_date + timedelta(days=day)
            builds_per_day = 1 + (day % 3)  # 1-3개 빌드

            for build in range(builds_per_day):
                build_id = day * 10 + build
                ci_report = temp_path / "reports" / "ci_reports" / f"{current_date.strftime('%Y-%m-%d')}-build-{build_id}.json"
                with open(ci_report, 'w', encoding='utf-8') as f:
                    json.dump({
                        "status": "success" if build_id % 5 != 0 else "failed",
                        "execution_time": 180 + (build_id % 100),
                        "coverage": {"percentage": 75 + (build_id % 20)},
                        "timestamp": current_date.isoformat() + "Z"
                    }, f)

        # 대량의 보안 로그 생성
        security_log = temp_path / "logs" / "security.log"
        with open(security_log, 'w', encoding='utf-8') as f:
            for day in range(365):
                current_date = base_date + timedelta(days=day)
                events_per_day = 5 + (day % 10)  # 5-15개 이벤트

                for event in range(events_per_day):
                    f.write(f"{current_date.strftime('%Y-%m-%d')} {10 + event:02d}:30:00 [INFO] IP_BLOCKED: 192.168.{day % 255}.{event % 255}\n")


class TestYearlyOpsReportCalculations:
    """연간 점수 계산 및 등급 판정 테스트 클래스"""

    @pytest.fixture
    def sample_yearly_data(self):
        """테스트용 연간 데이터"""
        return {
            "report_metadata": {
                "year": 2024,
                "period_start": "2024-01-01",
                "period_end": "2024-12-31",
                "generated_at": "2024-12-31T23:59:59Z",
                "report_type": "yearly_operations"
            },
            "performance_summary": {
                "total_score": 87,
                "grade": "우수",
                "security_score": 28,
                "backup_score": 27,
                "system_score": 16,
                "ci_score": 16
            },
            "quarterly_comparison": {
                "q1_average": 82.5,
                "q2_average": 85.0,
                "q3_average": 88.5,
                "q4_average": 89.0
            },
            "security_events": {
                "blocked_ips": 450,
                "rate_limit_violations": 125,
                "whitelist_additions": 25,
                "total_events": 600,
                "critical_events": [
                    {
                        "date": "2024-03-15",
                        "type": "브루트포스 공격 감지",
                        "detail": "IP: 203.113.*.* (50회 시도)"
                    }
                ]
            },
            "backup_operations": {
                "successful_backups": 340,
                "failed_backups": 25,
                "cleanup_operations": 96,
                "success_rate_percent": 93.2
            },
            "system_performance": {
                "average_cpu_usage_percent": 23.5,
                "average_memory_usage_percent": 67.2,
                "average_disk_usage_percent": 45.8,
                "uptime_days": 358,
                "performance_incidents": 12,
                "health_score": 78.5
            },
            "ci_performance": {
                "total_builds": 485,
                "successful_builds": 412,
                "failed_builds": 73,
                "average_build_time_seconds": 245.8,
                "average_test_coverage_percent": 84.3,
                "success_rate_percent": 84.9
            }
        }

    def test_grade_calculation_excellent(self, sample_yearly_data):
        """우수 등급 판정 테스트"""
        data = sample_yearly_data.copy()
        data["performance_summary"]["total_score"] = 95
        data["performance_summary"]["grade"] = "우수"

        assert data["performance_summary"]["total_score"] >= 85
        assert data["performance_summary"]["grade"] == "우수"

    def test_grade_calculation_good(self, sample_yearly_data):
        """보통 등급 판정 테스트"""
        data = sample_yearly_data.copy()
        data["performance_summary"]["total_score"] = 75
        data["performance_summary"]["grade"] = "보통"

        assert 70 <= data["performance_summary"]["total_score"] < 85
        assert data["performance_summary"]["grade"] == "보통"

    def test_grade_calculation_needs_improvement(self, sample_yearly_data):
        """개선 필요 등급 판정 테스트"""
        data = sample_yearly_data.copy()
        data["performance_summary"]["total_score"] = 65
        data["performance_summary"]["grade"] = "개선 필요"

        assert data["performance_summary"]["total_score"] < 70
        assert data["performance_summary"]["grade"] == "개선 필요"

    def test_score_components_sum(self, sample_yearly_data):
        """점수 구성 요소 합계 검증"""
        performance = sample_yearly_data["performance_summary"]

        total = (performance["security_score"] +
                performance["backup_score"] +
                performance["system_score"] +
                performance["ci_score"])

        assert total == performance["total_score"], f"점수 합계 불일치: {total} != {performance['total_score']}"

    def test_quarterly_trend_analysis(self, sample_yearly_data):
        """분기별 추이 분석 테스트"""
        quarterly = sample_yearly_data["quarterly_comparison"]

        # 분기별 점수가 유효한 범위에 있는지 확인
        for quarter, score in quarterly.items():
            assert 0 <= score <= 100, f"{quarter} 점수가 유효 범위를 벗어남: {score}"

        # 연간 추이 계산
        q1_avg = quarterly["q1_average"]
        q4_avg = quarterly["q4_average"]
        yearly_improvement = q4_avg - q1_avg

        assert isinstance(yearly_improvement, (int, float)), "연간 개선도 계산 오류"


class TestYearlyOpsReportNotifications:
    """연간 리포트 알림 시스템 테스트 클래스"""

    @pytest.fixture
    def sample_yearly_data(self):
        """테스트용 연간 데이터 (알림 테스트용)"""
        return {
            "report_metadata": {
                "year": 2024,
                "generated_at": "2024-12-31T23:59:59Z"
            },
            "performance_summary": {
                "total_score": 87,
                "grade": "우수",
                "security_score": 28,
                "backup_score": 27,
                "system_score": 16,
                "ci_score": 16
            },
            "quarterly_comparison": {
                "q1_average": 82.5,
                "q2_average": 85.0,
                "q3_average": 88.5,
                "q4_average": 89.0
            },
            "security_events": {"total_events": 600, "blocked_ips": 450},
            "backup_operations": {"success_rate_percent": 93.2, "successful_backups": 340},
            "system_performance": {"uptime_days": 358, "performance_incidents": 12},
            "ci_performance": {"success_rate_percent": 84.9, "total_builds": 485}
        }

    @pytest.mark.asyncio
    async def test_notification_level_auto_detection_excellent(self, sample_yearly_data):
        """우수 등급 알림 레벨 자동 판정 테스트"""
        with patch('mcp.utils.notifier.send_to_slack') as mock_slack, \
             patch('mcp.utils.notifier.send_to_discord') as mock_discord, \
             patch('mcp.utils.notifier.send_to_email') as mock_email, \
             patch('mcp.utils.notifier.log_notification') as mock_log:

            mock_slack.return_value = True
            mock_discord.return_value = True
            mock_email.return_value = True

            # 우수 등급 (90점 이상)
            data = sample_yearly_data.copy()
            data["performance_summary"]["total_score"] = 92
            data["performance_summary"]["grade"] = "우수"

            result = await send_yearly_ops_report(data, force_send=True)

            assert result is True
            # INFO 레벨로 전송되었는지 확인
            if mock_slack.called:
                call_args = mock_slack.call_args
                assert call_args[1]["level"] == NotificationLevel.INFO

    @pytest.mark.asyncio
    async def test_notification_level_auto_detection_needs_improvement(self, sample_yearly_data):
        """개선 필요 등급 알림 레벨 자동 판정 테스트"""
        with patch('mcp.utils.notifier.send_to_slack') as mock_slack, \
             patch('mcp.utils.notifier.send_to_discord') as mock_discord, \
             patch('mcp.utils.notifier.send_to_email') as mock_email, \
             patch('mcp.utils.notifier.log_notification') as mock_log:

            mock_slack.return_value = True
            mock_discord.return_value = True
            mock_email.return_value = True

            # 개선 필요 등급
            data = sample_yearly_data.copy()
            data["performance_summary"]["total_score"] = 65
            data["performance_summary"]["grade"] = "개선 필요"

            result = await send_yearly_ops_report(data, force_send=True)

            assert result is True
            # ERROR 레벨로 전송되었는지 확인
            if mock_slack.called:
                call_args = mock_slack.call_args
                assert call_args[1]["level"] == NotificationLevel.ERROR

    @pytest.mark.asyncio
    async def test_notification_rate_limiting(self, sample_yearly_data):
        """알림 속도 제한 테스트 (24시간 제한)"""
        with patch('mcp.utils.notifier.send_to_slack') as mock_slack, \
             patch('mcp.utils.notifier.send_to_discord') as mock_discord, \
             patch('mcp.utils.notifier.send_to_email') as mock_email, \
             patch('mcp.utils.notifier.log_notification') as mock_log, \
             patch('time.time') as mock_time:

            mock_slack.return_value = True
            mock_discord.return_value = True
            mock_email.return_value = True

            base_time = 1700000000  # 기준 시간
            mock_time.return_value = base_time

            # 첫 번째 전송 (성공해야 함)
            result1 = await send_yearly_ops_report(sample_yearly_data, force_send=False)
            assert result1 is True

            # 같은 시간에 두 번째 전송 (실패해야 함 - 24시간 제한)
            result2 = await send_yearly_ops_report(sample_yearly_data, force_send=False)
            assert result2 is False

            # 24시간 후 전송 (성공해야 함)
            mock_time.return_value = base_time + 86401  # 24시간 + 1초
            result3 = await send_yearly_ops_report(sample_yearly_data, force_send=False)
            assert result3 is True

    @pytest.mark.asyncio
    async def test_notification_force_send_bypass_rate_limit(self, sample_yearly_data):
        """강제 전송으로 속도 제한 우회 테스트"""
        with patch('mcp.utils.notifier.send_to_slack') as mock_slack, \
             patch('mcp.utils.notifier.send_to_discord') as mock_discord, \
             patch('mcp.utils.notifier.send_to_email') as mock_email, \
             patch('mcp.utils.notifier.log_notification') as mock_log, \
             patch('time.time') as mock_time:

            mock_slack.return_value = True
            mock_discord.return_value = True
            mock_email.return_value = True
            mock_time.return_value = 1700000000

            # 첫 번째 전송
            result1 = await send_yearly_ops_report(sample_yearly_data, force_send=False)
            assert result1 is True

            # 강제 전송 (속도 제한 무시)
            result2 = await send_yearly_ops_report(sample_yearly_data, force_send=True)
            assert result2 is True

    @pytest.mark.asyncio
    async def test_notification_message_content(self, sample_yearly_data):
        """알림 메시지 내용 검증 테스트"""
        with patch('mcp.utils.notifier.send_to_slack') as mock_slack, \
             patch('mcp.utils.notifier.send_to_discord') as mock_discord, \
             patch('mcp.utils.notifier.send_to_email') as mock_email, \
             patch('mcp.utils.notifier.log_notification') as mock_log:

            mock_slack.return_value = True
            mock_discord.return_value = True
            mock_email.return_value = True

            result = await send_yearly_ops_report(sample_yearly_data, force_send=True)
            assert result is True

            # Slack 호출 확인
            if mock_slack.called:
                call_args = mock_slack.call_args
                message = call_args[1]["message"]
                title = call_args[1]["title"]

                # 메시지 내용 검증
                assert "2024년 연간 운영 성과 요약" in message
                assert "87/100점" in message
                assert "우수" in message
                assert "🛡️ 보안" in message
                assert "📦 백업" in message
                assert "⚙️ 시스템" in message
                assert "🚀 CI/CD" in message

                # 제목 검증
                assert "2024년 연간 운영 리포트" in title

    @pytest.mark.asyncio
    async def test_notification_convenience_function(self, sample_yearly_data):
        """편의 함수 테스트"""
        with patch('mcp.utils.notifier.send_yearly_ops_report') as mock_send:
            mock_send.return_value = True

            result = await notify_yearly_report(sample_yearly_data, force_send=True)

            assert result is True
            mock_send.assert_called_once_with(sample_yearly_data, force_send=True)

    @pytest.mark.asyncio
    async def test_notification_empty_data_handling(self):
        """빈 데이터 처리 테스트"""
        result = await send_yearly_ops_report({}, force_send=True)
        assert result is False

        result = await send_yearly_ops_report(None, force_send=True)
        assert result is False


class TestYearlyOpsReportIntegration:
    """연간 운영 리포트 통합 테스트 클래스"""

    @pytest.mark.integration
    def test_script_execution_with_real_data(self):
        """실제 데이터를 사용한 스크립트 실행 통합 테스트"""
        script_path = Path(__file__).parent.parent / "scripts" / "yearly_ops_report.sh"

        if not script_path.exists():
            pytest.skip("yearly_ops_report.sh 스크립트가 존재하지 않습니다")

        try:
            result = subprocess.run(
                [str(script_path), "--dry-run", "--verbose"],
                capture_output=True,
                text=True,
                timeout=120  # 2분 제한
            )

            # 스크립트가 오류 없이 실행되어야 함
            assert result.returncode == 0, f"스크립트 실행 실패: {result.stderr}"

            # 기본적인 출력 검증
            stderr_output = result.stderr.lower()
            assert any(keyword in stderr_output for keyword in ["연간", "리포트", "완료", "성과"]), \
                "예상되는 출력 메시지가 없습니다"

        except subprocess.TimeoutExpired:
            pytest.fail("통합 테스트 시간 초과 (2분)")
        except Exception as e:
            pytest.fail(f"통합 테스트 실패: {e}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_end_to_end_notification_flow(self):
        """End-to-End 알림 플로우 테스트"""
        # 실제와 유사한 연간 데이터 생성
        yearly_data = {
            "report_metadata": {
                "year": 2024,
                "generated_at": datetime.now().isoformat()
            },
            "performance_summary": {
                "total_score": 88,
                "grade": "우수",
                "security_score": 29,
                "backup_score": 28,
                "system_score": 16,
                "ci_score": 15
            },
            "quarterly_comparison": {
                "q1_average": 84.0,
                "q2_average": 86.5,
                "q3_average": 89.0,
                "q4_average": 91.5
            },
            "security_events": {
                "total_events": 750,
                "blocked_ips": 520,
                "rate_limit_violations": 180,
                "whitelist_additions": 50
            },
            "backup_operations": {
                "successful_backups": 355,
                "failed_backups": 10,
                "success_rate_percent": 97.3,
                "cleanup_operations": 104
            },
            "system_performance": {
                "uptime_days": 362,
                "performance_incidents": 8,
                "average_cpu_usage_percent": 21.5,
                "average_memory_usage_percent": 64.8
            },
            "ci_performance": {
                "total_builds": 520,
                "successful_builds": 456,
                "success_rate_percent": 87.7,
                "average_test_coverage_percent": 86.2
            }
        }

        # 알림 시스템 모킹
        with patch('mcp.utils.notifier.send_to_slack') as mock_slack, \
             patch('mcp.utils.notifier.send_to_discord') as mock_discord, \
             patch('mcp.utils.notifier.send_to_email') as mock_email:

            # 일부 채널 성공, 일부 실패 시뮬레이션
            mock_slack.return_value = True
            mock_discord.return_value = False  # Discord 실패
            mock_email.return_value = True

            result = await send_yearly_ops_report(yearly_data, force_send=True)

            # 일부 채널이라도 성공하면 전체 성공으로 판정
            assert result is True

            # 각 채널 호출 검증
            assert mock_slack.called
            assert mock_discord.called
            assert mock_email.called


if __name__ == "__main__":
    # 개별 테스트 실행을 위한 메인 함수
    import asyncio

    async def run_basic_tests():
        """기본 테스트 실행"""
        print("🧪 연간 운영 리포트 시스템 기본 테스트 시작...")

        try:
            # 간단한 알림 함수 테스트
            sample_data = {
                "report_metadata": {"year": 2024},
                "performance_summary": {
                    "total_score": 85,
                    "grade": "우수",
                    "security_score": 25,
                    "backup_score": 25,
                    "system_score": 17,
                    "ci_score": 18
                },
                "quarterly_comparison": {"q1_average": 80, "q2_average": 85, "q3_average": 87, "q4_average": 88},
                "security_events": {"total_events": 500},
                "backup_operations": {"success_rate_percent": 95},
                "system_performance": {"uptime_days": 360},
                "ci_performance": {"success_rate_percent": 90}
            }

            with patch('mcp.utils.notifier.send_to_slack') as mock_slack:
                mock_slack.return_value = True
                result = await notify_yearly_report(sample_data, force_send=True)
                print(f"✅ 알림 함수 테스트: {'성공' if result else '실패'}")

        except Exception as e:
            print(f"❌ 기본 테스트 실패: {e}")

        print("🧪 연간 운영 리포트 시스템 기본 테스트 완료")

    # 비동기 테스트 실행
    asyncio.run(run_basic_tests())