"""
OpenAI 사용량 및 비용 추적 미들웨어
API 호출시 토큰 사용량 모니터링, 일일/월간 비용 한도 체크
"""

import json
import asyncio
from datetime import datetime, date
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from loguru import logger

from app.config import get_settings

settings = get_settings()


@dataclass
class UsageRecord:
    """사용량 기록 - 확장된 메트릭스"""
    timestamp: datetime
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    task_type: str
    endpoint: str
    # 추가 메트릭스
    status_code: int = 200
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    response_time_ms: Optional[float] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None


@dataclass
class DailyUsage:
    """일일 사용량 집계 - 확장된 메트릭스"""
    date: str
    total_requests: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    model_usage: Dict[str, int] = None
    cost_by_model: Dict[str, float] = None
    # 추가 메트릭스
    endpoint_usage: Dict[str, int] = None
    error_breakdown: Dict[str, int] = None
    success_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: float = 0.0
    total_response_time_ms: float = 0.0

    def __post_init__(self):
        if self.model_usage is None:
            self.model_usage = {}
        if self.cost_by_model is None:
            self.cost_by_model = {}
        if self.endpoint_usage is None:
            self.endpoint_usage = {}
        if self.error_breakdown is None:
            self.error_breakdown = {}


class AlertHook:
    """알림 훅 인터페이스"""
    
    async def send_alert(self, alert_type: str, message: str, data: dict):
        """알림 전송 (서브클래스에서 구현)"""
        pass


class LoggerAlertHook(AlertHook):
    """로거 알림 훅"""
    
    async def send_alert(self, alert_type: str, message: str, data: dict):
        """로그로 알림 전송"""
        logger.warning(f"[{alert_type.upper()}] {message} - 데이터: {data}")


class OpenAIUsageTracker:
    """OpenAI 사용량 추적 및 비용 관리 - 확장된 메트릭스"""
    
    def __init__(self):
        self.daily_usage: Dict[str, DailyUsage] = {}
        self.monthly_usage: Dict[str, float] = {}  # YYYY-MM -> cost
        self.usage_log_file = Path(settings.usage_log_file)
        self.usage_log_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        
        # 알림 시스템
        self.alert_hooks: List[AlertHook] = [LoggerAlertHook()]
        self.alert_sent_today: set = set()  # 중복 알림 방지
        
        # 성능 메트릭스 추적
        self.response_times: List[float] = []  # 최근 응답 시간들
        self.error_counts: Dict[str, int] = {}  # 에러 코드별 카운트
        
        # 모델별 비용 매핑
        self.cost_per_1k_tokens = {
            settings.model_nano: {
                'input': settings.cost_per_1k_tokens_nano_input,
                'output': settings.cost_per_1k_tokens_nano_output
            },
            settings.model_mini: {
                'input': settings.cost_per_1k_tokens_mini_input,
                'output': settings.cost_per_1k_tokens_mini_output
            },
            settings.model_gpt4: {
                'input': settings.cost_per_1k_tokens_gpt4_input,
                'output': settings.cost_per_1k_tokens_gpt4_output
            },
            settings.model_gpt5: {
                'input': settings.cost_per_1k_tokens_gpt5_input,
                'output': settings.cost_per_1k_tokens_gpt5_output
            },
            settings.model_o3: {
                'input': settings.cost_per_1k_tokens_o3_input,
                'output': settings.cost_per_1k_tokens_o3_output
            }
        }
    
    def calculate_cost(
        self, 
        model: str, 
        prompt_tokens: int, 
        completion_tokens: int
    ) -> float:
        """모델별 비용 계산"""
        if model not in self.cost_per_1k_tokens:
            logger.warning(f"Unknown model for cost calculation: {model}")
            return 0.0
        
        input_cost = (prompt_tokens / 1000) * self.cost_per_1k_tokens[model]['input']
        output_cost = (completion_tokens / 1000) * self.cost_per_1k_tokens[model]['output']
        
        return input_cost + output_cost
    
    async def check_cost_limits(self) -> Tuple[bool, str]:
        """비용 한도 체크"""
        async with self._lock:
            today = date.today().isoformat()
            current_month = datetime.now().strftime("%Y-%m")
            
            # 일일 한도 체크
            daily_cost = self.daily_usage.get(today, DailyUsage(today)).total_cost
            if daily_cost >= settings.daily_cost_limit:
                return False, f"일일 비용 한도 초과: ${daily_cost:.2f}/{settings.daily_cost_limit}"
            
            # 월간 한도 체크
            monthly_cost = self.monthly_usage.get(current_month, 0.0)
            if monthly_cost >= settings.monthly_cost_limit:
                return False, f"월간 비용 한도 초과: ${monthly_cost:.2f}/{settings.monthly_cost_limit}"
            
            # 알림 임계치 체크
            daily_threshold = settings.daily_cost_limit * settings.cost_alert_threshold
            monthly_threshold = settings.monthly_cost_limit * settings.cost_alert_threshold
            
            if daily_cost >= daily_threshold:
                logger.warning(f"일일 비용 임계치 도달: ${daily_cost:.2f}/{settings.daily_cost_limit}")
            
            if monthly_cost >= monthly_threshold:
                logger.warning(f"월간 비용 임계치 도달: ${monthly_cost:.2f}/{settings.monthly_cost_limit}")
            
            return True, "정상"
    
    async def record_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        task_type: str = "unknown",
        endpoint: str = "unknown",
        status_code: int = 200,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        response_time_ms: Optional[float] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> float:
        """사용량 기록 및 비용 계산 - 확장된 메트릭스"""
        total_tokens = prompt_tokens + completion_tokens
        cost = self.calculate_cost(model, prompt_tokens, completion_tokens)
        
        record = UsageRecord(
            timestamp=datetime.now(),
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            task_type=task_type,
            endpoint=endpoint,
            status_code=status_code,
            error_code=error_code,
            error_message=error_message,
            response_time_ms=response_time_ms,
            user_id=user_id,
            request_id=request_id
        )
        
        async with self._lock:
            # 일일 사용량 업데이트 - 확장된 메트릭스
            today = date.today().isoformat()
            if today not in self.daily_usage:
                self.daily_usage[today] = DailyUsage(today)
            
            daily = self.daily_usage[today]
            daily.total_requests += 1
            daily.total_tokens += total_tokens
            daily.total_cost += cost
            daily.model_usage[model] = daily.model_usage.get(model, 0) + 1
            daily.cost_by_model[model] = daily.cost_by_model.get(model, 0.0) + cost
            
            # 엔드포인트별 사용량
            daily.endpoint_usage[endpoint] = daily.endpoint_usage.get(endpoint, 0) + 1
            
            # 성공/실패 카운트
            if status_code < 400:
                daily.success_requests += 1
            else:
                daily.failed_requests += 1
                
            # 에러 코드별 집계
            if error_code:
                daily.error_breakdown[error_code] = daily.error_breakdown.get(error_code, 0) + 1
                
            # 응답 시간 집계
            if response_time_ms:
                daily.total_response_time_ms += response_time_ms
                if daily.total_requests > 0:
                    daily.avg_response_time_ms = daily.total_response_time_ms / daily.total_requests
            
            # 월간 사용량 업데이트
            current_month = datetime.now().strftime("%Y-%m")
            self.monthly_usage[current_month] = self.monthly_usage.get(current_month, 0.0) + cost
            
            # 80% 경고 알림 체크
            await self._check_cost_alerts(daily, today)
            
            # 로그 기록
            if settings.enable_usage_tracking:
                await self._write_usage_log(record)
        
        logger.info(f"OpenAI 사용 기록: {model} | {total_tokens} tokens | ${cost:.4f} | {endpoint}")
        return cost
    
    async def _check_cost_alerts(self, daily: DailyUsage, today: str):
        """80% 경고 알림 체크"""
        daily_percentage = (daily.total_cost / settings.daily_cost_limit) * 100
        monthly_cost = self.monthly_usage.get(datetime.now().strftime("%Y-%m"), 0.0)
        monthly_percentage = (monthly_cost / settings.monthly_cost_limit) * 100
        
        # 일일 비용 80% 경고
        if daily_percentage >= 80 and f"daily_80_{today}" not in self.alert_sent_today:
            await self._send_alert(
                "cost_warning",
                f"일일 비용 사용량 80% 초과: {daily_percentage:.1f}%",
                {
                    "type": "daily_cost_warning",
                    "percentage": daily_percentage,
                    "current_cost": daily.total_cost,
                    "limit": settings.daily_cost_limit,
                    "date": today
                }
            )
            self.alert_sent_today.add(f"daily_80_{today}")
        
        # 월간 비용 80% 경고  
        if monthly_percentage >= 80 and f"monthly_80_{datetime.now().strftime('%Y-%m')}" not in self.alert_sent_today:
            await self._send_alert(
                "cost_warning",
                f"월간 비용 사용량 80% 초과: {monthly_percentage:.1f}%",
                {
                    "type": "monthly_cost_warning",
                    "percentage": monthly_percentage,
                    "current_cost": monthly_cost,
                    "limit": settings.monthly_cost_limit,
                    "month": datetime.now().strftime("%Y-%m")
                }
            )
            self.alert_sent_today.add(f"monthly_80_{datetime.now().strftime('%Y-%m')}")
            
        # 에러율 경고
        total_requests = daily.success_requests + daily.failed_requests
        if total_requests > 10:  # 최소 10회 요청 이후부터 체크
            error_rate = (daily.failed_requests / total_requests) * 100
            if error_rate >= 20 and f"error_rate_{today}" not in self.alert_sent_today:  # 20% 에러율
                await self._send_alert(
                    "error_warning",
                    f"API 에러율이 높습니다: {error_rate:.1f}%",
                    {
                        "type": "error_rate_warning", 
                        "error_rate": error_rate,
                        "failed_requests": daily.failed_requests,
                        "total_requests": total_requests,
                        "error_breakdown": daily.error_breakdown,
                        "date": today
                    }
                )
                self.alert_sent_today.add(f"error_rate_{today}")
    
    async def _send_alert(self, alert_type: str, message: str, data: dict):
        """알림 전송"""
        for hook in self.alert_hooks:
            try:
                await hook.send_alert(alert_type, message, data)
            except Exception as e:
                logger.error(f"알림 전송 실패: {str(e)}")
    
    def add_alert_hook(self, hook: AlertHook):
        """알림 훅 추가"""
        self.alert_hooks.append(hook)
    
    async def _write_usage_log(self, record: UsageRecord):
        """사용량 로그 파일에 기록"""
        try:
            log_data = {
                **asdict(record),
                'timestamp': record.timestamp.isoformat()
            }
            
            with open(self.usage_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
                
        except Exception as e:
            logger.error(f"사용량 로그 기록 실패: {e}")
    
    async def get_usage_stats(self, days: int = 7) -> Dict:
        """사용량 통계 조회 - 확장된 메트릭스"""
        async with self._lock:
            stats = {
                'daily_usage': {},
                'monthly_usage': dict(self.monthly_usage),
                'current_limits': {
                    'daily_limit': settings.daily_cost_limit,
                    'monthly_limit': settings.monthly_cost_limit,
                    'alert_threshold': settings.cost_alert_threshold
                },
                'summary': {
                    'total_days_tracked': len(self.daily_usage),
                    'total_cost_to_date': sum(usage.total_cost for usage in self.daily_usage.values()),
                    'total_requests_to_date': sum(usage.total_requests for usage in self.daily_usage.values()),
                    'avg_daily_cost': 0.0,
                    'avg_success_rate': 0.0
                }
            }
            
            # 최근 N일 데이터 - 확장된 정보 포함
            recent_usage = list(self.daily_usage.items())[-days:]
            for date_str, usage in recent_usage:
                usage_data = asdict(usage)
                
                # 성공률 계산
                total_requests = usage.success_requests + usage.failed_requests
                success_rate = (usage.success_requests / total_requests * 100) if total_requests > 0 else 0
                usage_data['success_rate_percent'] = round(success_rate, 1)
                
                # 비용 사용률 계산
                cost_usage_percent = (usage.total_cost / settings.daily_cost_limit * 100) if settings.daily_cost_limit > 0 else 0
                usage_data['cost_usage_percent'] = round(cost_usage_percent, 1)
                
                stats['daily_usage'][date_str] = usage_data
            
            # 요약 통계 계산
            if recent_usage:
                total_cost = sum(usage.total_cost for _, usage in recent_usage)
                total_success = sum(usage.success_requests for _, usage in recent_usage)
                total_failed = sum(usage.failed_requests for _, usage in recent_usage)
                total_all_requests = total_success + total_failed
                
                stats['summary']['avg_daily_cost'] = total_cost / len(recent_usage)
                stats['summary']['avg_success_rate'] = (total_success / total_all_requests * 100) if total_all_requests > 0 else 0
            
            return stats
    
    async def reset_daily_usage(self, date_str: Optional[str] = None):
        """일일 사용량 초기화 (테스트용)"""
        if date_str is None:
            date_str = date.today().isoformat()
        
        async with self._lock:
            if date_str in self.daily_usage:
                del self.daily_usage[date_str]
                logger.info(f"일일 사용량 초기화: {date_str}")


# 전역 인스턴스
usage_tracker = OpenAIUsageTracker()


async def get_usage_tracker() -> OpenAIUsageTracker:
    """사용량 추적기 인스턴스 반환"""
    return usage_tracker