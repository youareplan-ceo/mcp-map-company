"""
사용량 추적 미들웨어 테스트
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, date

from app.middleware.usage_tracker import (
    OpenAIUsageTracker, 
    UsageRecord, 
    DailyUsage, 
    AlertHook,
    LoggerAlertHook,
    get_usage_tracker
)


class TestUsageRecord:
    """UsageRecord 데이터클래스 테스트"""

    def test_usage_record_creation(self):
        """UsageRecord 생성 테스트"""
        record = UsageRecord(
            timestamp=datetime.now(),
            model="gpt-4",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost=0.005,
            task_type="analysis",
            endpoint="/api/v1/analyze"
        )
        
        assert record.model == "gpt-4"
        assert record.total_tokens == 150
        assert record.cost == 0.005
        assert record.status_code == 200  # 기본값
        assert record.error_code is None
        assert record.request_id is not None  # UUID가 생성되었는지 확인

    def test_usage_record_with_extended_metrics(self):
        """확장된 메트릭스를 포함한 UsageRecord 테스트"""
        record = UsageRecord(
            timestamp=datetime.now(),
            model="gpt-4",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost=0.005,
            task_type="analysis",
            endpoint="/api/v1/analyze",
            status_code=200,
            error_code=None,
            response_time_ms=250.5,
            user_id="user123",
            request_id="req456"
        )
        
        assert record.response_time_ms == 250.5
        assert record.user_id == "user123"
        assert record.request_id == "req456"


class TestDailyUsage:
    """DailyUsage 데이터클래스 테스트"""

    def test_daily_usage_creation(self):
        """DailyUsage 생성 테스트"""
        usage = DailyUsage(date="2024-01-01")
        
        assert usage.date == "2024-01-01"
        assert usage.total_requests == 0
        assert usage.total_tokens == 0
        assert usage.total_cost == 0.0
        assert isinstance(usage.model_usage, dict)
        assert isinstance(usage.cost_by_model, dict)
        assert isinstance(usage.endpoint_usage, dict)
        assert isinstance(usage.error_breakdown, dict)

    def test_daily_usage_with_data(self):
        """데이터가 있는 DailyUsage 테스트"""
        usage = DailyUsage(
            date="2024-01-01",
            total_requests=100,
            total_tokens=5000,
            total_cost=2.5,
            success_requests=95,
            failed_requests=5,
            avg_response_time_ms=150.0
        )
        
        assert usage.total_requests == 100
        assert usage.success_requests == 95
        assert usage.failed_requests == 5
        assert usage.avg_response_time_ms == 150.0


class TestAlertHooks:
    """알림 훅 테스트"""

    @pytest.mark.asyncio
    async def test_base_alert_hook(self):
        """기본 AlertHook 인터페이스 테스트"""
        hook = AlertHook()
        
        # 기본 구현은 아무것도 하지 않음
        await hook.send_alert("test", "Test message", {})

    @pytest.mark.asyncio
    async def test_logger_alert_hook(self):
        """LoggerAlertHook 테스트"""
        hook = LoggerAlertHook()
        
        with patch('app.middleware.usage_tracker.logger') as mock_logger:
            await hook.send_alert("cost_warning", "Test alert message", {"cost": 10.0})
            mock_logger.warning.assert_called_once()


class TestUsageTracker:
    """OpenAIUsageTracker 테스트"""

    def test_usage_tracker_initialization(self):
        """사용량 추적기 초기화 테스트"""
        tracker = OpenAIUsageTracker()
        
        assert isinstance(tracker.daily_usage, dict)
        assert isinstance(tracker.monthly_usage, dict)
        assert len(tracker.alert_hooks) > 0  # LoggerAlertHook이 기본으로 포함
        assert tracker.cost_per_1k_tokens is not None

    def test_cost_calculation(self):
        """비용 계산 테스트"""
        with patch('app.config.get_settings') as mock_settings:
            # Mock 설정
            mock_config = Mock()
            mock_config.model_gpt4 = "gpt-4"
            mock_config.cost_per_1k_tokens_gpt4_input = 0.03
            mock_config.cost_per_1k_tokens_gpt4_output = 0.06
            mock_settings.return_value = mock_config
            
            tracker = OpenAIUsageTracker()
            tracker.cost_per_1k_tokens = {
                "gpt-4": {
                    "input": 0.03,
                    "output": 0.06
                }
            }
            
            cost = tracker.calculate_cost("gpt-4", 1000, 500)
            expected_cost = (1000 / 1000) * 0.03 + (500 / 1000) * 0.06  # 0.03 + 0.03 = 0.06
            assert cost == expected_cost

    def test_cost_calculation_unknown_model(self):
        """알려지지 않은 모델 비용 계산 테스트"""
        tracker = OpenAIUsageTracker()
        
        cost = tracker.calculate_cost("unknown-model", 1000, 500)
        assert cost == 0.0

    @pytest.mark.asyncio
    async def test_record_usage(self):
        """사용량 기록 테스트"""
        with patch('app.config.get_settings') as mock_settings:
            mock_config = Mock()
            mock_config.enable_usage_tracking = True
            mock_settings.return_value = mock_config
            
            tracker = OpenAIUsageTracker()
            tracker.cost_per_1k_tokens = {
                "gpt-4": {"input": 0.03, "output": 0.06}
            }
            
            with patch.object(tracker, '_write_usage_log', new_callable=AsyncMock):
                cost = await tracker.record_usage(
                    model="gpt-4",
                    prompt_tokens=100,
                    completion_tokens=50,
                    task_type="analysis",
                    endpoint="/api/v1/analyze"
                )
                
                assert cost > 0
                today = date.today().isoformat()
                assert today in tracker.daily_usage
                daily = tracker.daily_usage[today]
                assert daily.total_requests == 1
                assert daily.total_tokens == 150
                assert daily.success_requests == 1

    @pytest.mark.asyncio
    async def test_check_cost_limits(self):
        """비용 한도 체크 테스트"""
        with patch('app.config.get_settings') as mock_settings:
            mock_config = Mock()
            mock_config.daily_cost_limit = 10.0
            mock_config.monthly_cost_limit = 300.0
            mock_settings.return_value = mock_config
            
            tracker = OpenAIUsageTracker()
            
            # 정상 상황
            can_proceed, message = await tracker.check_cost_limits()
            assert can_proceed is True
            assert message == "정상"
            
            # 일일 한도 초과
            today = date.today().isoformat()
            tracker.daily_usage[today] = DailyUsage(date=today, total_cost=15.0)
            
            can_proceed, message = await tracker.check_cost_limits()
            assert can_proceed is False
            assert "일일 비용 한도 초과" in message

    @pytest.mark.asyncio
    async def test_get_usage_stats(self):
        """사용량 통계 조회 테스트"""
        with patch('app.config.get_settings') as mock_settings:
            mock_config = Mock()
            mock_config.daily_cost_limit = 10.0
            mock_config.monthly_cost_limit = 300.0
            mock_config.cost_alert_threshold = 0.8
            mock_settings.return_value = mock_config
            
            tracker = OpenAIUsageTracker()
            
            # 테스트 데이터 추가
            today = date.today().isoformat()
            tracker.daily_usage[today] = DailyUsage(
                date=today,
                total_requests=50,
                total_cost=5.0,
                success_requests=48,
                failed_requests=2,
                total_response_time_ms=7500.0,
                avg_response_time_ms=150.0
            )
            
            stats = await tracker.get_usage_stats(days=7)
            
            assert "daily_usage" in stats
            assert "monthly_usage" in stats
            assert "current_limits" in stats
            assert "summary" in stats
            assert today in stats["daily_usage"]

    @pytest.mark.asyncio
    async def test_cost_alerts(self):
        """비용 경고 알림 테스트"""
        with patch('app.config.get_settings') as mock_settings:
            mock_config = Mock()
            mock_config.daily_cost_limit = 10.0
            mock_config.monthly_cost_limit = 300.0
            mock_config.cost_alert_threshold = 0.8
            mock_settings.return_value = mock_config
            
            tracker = OpenAIUsageTracker()
            
            # Mock alert hook
            mock_hook = Mock(spec=AlertHook)
            mock_hook.send_alert = AsyncMock()
            tracker.alert_hooks = [mock_hook]
            
            today = date.today().isoformat()
            daily_usage = DailyUsage(date=today, total_cost=8.5)  # 85% 사용
            
            await tracker._check_cost_alerts(daily_usage, today)
            
            # 80% 임계치 초과로 알림이 전송되었는지 확인
            mock_hook.send_alert.assert_called()

    @pytest.mark.asyncio
    async def test_error_rate_alerts(self):
        """에러율 경고 알림 테스트"""
        with patch('app.config.get_settings') as mock_settings:
            mock_config = Mock()
            mock_settings.return_value = mock_config
            
            tracker = OpenAIUsageTracker()
            
            # Mock alert hook
            mock_hook = Mock(spec=AlertHook)
            mock_hook.send_alert = AsyncMock()
            tracker.alert_hooks = [mock_hook]
            
            today = date.today().isoformat()
            daily_usage = DailyUsage(
                date=today,
                success_requests=8,
                failed_requests=3,  # 27% 실패율
                error_breakdown={"timeout": 2, "auth_error": 1}
            )
            
            await tracker._check_cost_alerts(daily_usage, today)
            
            # 20% 에러율 임계치 초과로 알림이 전송되었는지 확인
            mock_hook.send_alert.assert_called()


class TestUsageTrackerIntegration:
    """사용량 추적기 통합 테스트"""

    def test_get_usage_tracker_singleton(self):
        """사용량 추적기 싱글톤 패턴 테스트"""
        tracker1 = get_usage_tracker()
        tracker2 = get_usage_tracker()
        
        assert tracker1 is tracker2  # 같은 인스턴스인지 확인

    @pytest.mark.asyncio
    async def test_usage_tracker_workflow(self):
        """사용량 추적기 전체 워크플로우 테스트"""
        tracker = get_usage_tracker()
        
        # 초기 상태 확인
        initial_stats = await tracker.get_usage_stats()
        assert "daily_usage" in initial_stats
        
        # 비용 한도 체크
        can_proceed, _ = await tracker.check_cost_limits()
        assert can_proceed is True
        
        # 사용량 기록 가능한지 확인
        assert hasattr(tracker, 'record_usage')
        assert callable(tracker.record_usage)