"""
OpenAI API 비용 제어 시스템
API 호출 최적화, 캐싱, 백오프 로직, 비용 모니터링
"""

import asyncio
import time
import json
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import os

logger = logging.getLogger(__name__)

class Priority(Enum):
    """API 호출 우선순위"""
    HIGH = 1      # 실시간 시그널 (즉시 실행)
    MEDIUM = 2    # 뉴스 분석 (5분 간격)
    LOW = 3       # 배치 분석 (15분 간격)

@dataclass
class APICall:
    """API 호출 정보"""
    id: str
    model: str
    tokens_estimate: int
    priority: Priority
    created_at: datetime
    cache_key: Optional[str] = None
    retries: int = 0
    max_retries: int = 3

@dataclass
class CostMetrics:
    """비용 메트릭"""
    total_calls: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    rate_limited: int = 0
    failed_calls: int = 0
    last_reset: datetime = datetime.now()

class OpenAICostController:
    """OpenAI API 비용 제어 관리자"""
    
    # GPT-4o-mini 가격 (토큰당 USD)
    MODEL_COSTS = {
        "gpt-4o-mini": {
            "input": 0.00000015,   # $0.15 / 1M tokens
            "output": 0.00000060   # $0.60 / 1M tokens  
        }
    }
    
    def __init__(self, 
                 daily_budget: float = 10.0,    # 일일 예산 (USD)
                 cache_ttl: int = 300,          # 캐시 TTL (초)
                 rate_limit_window: int = 60,   # 레이트 제한 윈도우 (초)
                 max_calls_per_window: int = 20): # 윈도우당 최대 호출
        
        self.daily_budget = daily_budget
        self.cache_ttl = cache_ttl
        self.rate_limit_window = rate_limit_window
        self.max_calls_per_window = max_calls_per_window
        
        # 상태 관리
        self.metrics = CostMetrics()
        self.call_cache: Dict[str, Tuple[Any, datetime]] = {}
        self.call_queue: List[APICall] = []
        self.call_history: List[Tuple[datetime, str]] = []
        self.is_paused = False
        
        # 백오프 설정
        self.backoff_base = 1.0      # 기본 백오프 (초)
        self.backoff_multiplier = 2.0 # 백오프 증가 배수
        self.max_backoff = 300.0     # 최대 백오프 (초)
        
        # 로깅
        logger.info(f"OpenAI 비용 제어 시스템 초기화 - 일일예산: ${daily_budget}")

    def _generate_cache_key(self, model: str, messages: List[Dict], **kwargs) -> str:
        """캐시 키 생성"""
        cache_data = {
            "model": model,
            "messages": messages,
            "kwargs": {k: v for k, v in kwargs.items() if k in ['temperature', 'max_tokens']}
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()

    def _is_cache_valid(self, timestamp: datetime) -> bool:
        """캐시 유효성 확인"""
        return datetime.now() - timestamp < timedelta(seconds=self.cache_ttl)

    def _estimate_tokens(self, messages: List[Dict], max_tokens: int = 500) -> int:
        """토큰 수 추정 (대략적)"""
        text = ""
        for msg in messages:
            text += msg.get("content", "")
        
        # 영어: ~4글자당 1토큰, 한국어: ~2글자당 1토큰으로 추정
        char_count = len(text)
        estimated_input = char_count // 3  # 평균
        estimated_output = max_tokens
        
        return estimated_input + estimated_output

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """비용 계산"""
        if model not in self.MODEL_COSTS:
            logger.warning(f"알 수 없는 모델: {model}")
            return 0.0
        
        costs = self.MODEL_COSTS[model]
        total_cost = (input_tokens * costs["input"]) + (output_tokens * costs["output"])
        return total_cost

    def _is_rate_limited(self) -> bool:
        """레이트 제한 확인"""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.rate_limit_window)
        
        # 윈도우 내 호출 수 계산
        recent_calls = [ts for ts, _ in self.call_history if ts > cutoff]
        
        if len(recent_calls) >= self.max_calls_per_window:
            self.metrics.rate_limited += 1
            return True
        
        return False

    def _is_budget_exceeded(self) -> bool:
        """예산 초과 확인"""
        # 일일 예산 확인
        today = datetime.now().date()
        if self.metrics.last_reset.date() < today:
            # 새로운 날이면 메트릭 리셋
            self._reset_daily_metrics()
        
        return self.metrics.total_cost >= self.daily_budget

    def _reset_daily_metrics(self):
        """일일 메트릭 리셋"""
        logger.info(f"일일 메트릭 리셋 - 총 비용: ${self.metrics.total_cost:.4f}")
        self.metrics = CostMetrics()

    def _get_backoff_delay(self, retries: int) -> float:
        """백오프 지연 시간 계산"""
        delay = self.backoff_base * (self.backoff_multiplier ** retries)
        return min(delay, self.max_backoff)

    async def _execute_with_backoff(self, api_call: APICall, actual_call_func) -> Any:
        """백오프를 적용한 API 호출 실행"""
        for attempt in range(api_call.max_retries + 1):
            try:
                result = await actual_call_func()
                return result
                
            except Exception as e:
                api_call.retries = attempt
                
                if attempt >= api_call.max_retries:
                    logger.error(f"API 호출 최종 실패 ({api_call.id}): {e}")
                    self.metrics.failed_calls += 1
                    raise
                
                # 백오프 지연
                delay = self._get_backoff_delay(attempt)
                logger.warning(f"API 호출 실패, {delay:.1f}초 후 재시도 ({attempt + 1}/{api_call.max_retries + 1}): {e}")
                await asyncio.sleep(delay)

    async def request_api_call(self, 
                             model: str, 
                             messages: List[Dict], 
                             priority: Priority = Priority.MEDIUM,
                             **kwargs) -> str:
        """API 호출 요청 (큐에 추가)"""
        
        # 예산 확인
        if self._is_budget_exceeded():
            logger.warning("일일 예산 초과로 API 호출 차단")
            raise Exception("Daily budget exceeded")
        
        # 캐시 키 생성
        cache_key = self._generate_cache_key(model, messages, **kwargs)
        
        # 캐시 확인
        if cache_key in self.call_cache:
            cached_result, cached_time = self.call_cache[cache_key]
            if self._is_cache_valid(cached_time):
                self.metrics.cache_hits += 1
                logger.info(f"캐시 히트: {cache_key[:8]}")
                return cached_result
            else:
                # 만료된 캐시 제거
                del self.call_cache[cache_key]
        
        self.metrics.cache_misses += 1
        
        # API 호출 생성
        call_id = f"call_{int(time.time() * 1000)}"
        tokens_estimate = self._estimate_tokens(messages, kwargs.get('max_tokens', 500))
        
        api_call = APICall(
            id=call_id,
            model=model,
            tokens_estimate=tokens_estimate,
            priority=priority,
            created_at=datetime.now(),
            cache_key=cache_key
        )
        
        # 우선순위 큐에 추가
        self.call_queue.append(api_call)
        self.call_queue.sort(key=lambda x: x.priority.value)
        
        logger.info(f"API 호출 요청 큐 추가: {call_id} (우선순위: {priority.name}, 예상토큰: {tokens_estimate})")
        
        return call_id

    async def execute_queued_calls(self, openai_client) -> Dict[str, Any]:
        """큐된 API 호출들 실행"""
        if not self.call_queue:
            return {"executed": 0, "skipped": 0}
        
        executed = 0
        skipped = 0
        
        # 우선순위별로 호출 실행
        for api_call in self.call_queue[:]:  # 복사본으로 순회
            
            # 레이트 제한 확인
            if self._is_rate_limited():
                logger.info("레이트 제한으로 인한 API 호출 지연")
                break
            
            # 예산 재확인
            if self._is_budget_exceeded():
                logger.warning("예산 초과로 나머지 API 호출 스킵")
                skipped += len(self.call_queue) - executed
                break
            
            try:
                # 실제 OpenAI API 호출 함수
                async def make_api_call():
                    response = await openai_client.chat.completions.create(
                        model=api_call.model,
                        messages=[{"role": "user", "content": "test"}],  # 실제 메시지로 교체 필요
                        max_tokens=500,
                        temperature=0.3
                    )
                    return response
                
                # 백오프와 함께 실행
                result = await self._execute_with_backoff(api_call, make_api_call)
                
                # 메트릭 업데이트
                self.metrics.total_calls += 1
                usage = result.usage
                
                if usage:
                    input_tokens = usage.prompt_tokens
                    output_tokens = usage.completion_tokens
                    cost = self._calculate_cost(api_call.model, input_tokens, output_tokens)
                    
                    self.metrics.total_tokens += input_tokens + output_tokens
                    self.metrics.total_cost += cost
                    
                    logger.info(f"API 호출 성공: {api_call.id} (토큰: {input_tokens + output_tokens}, 비용: ${cost:.6f})")
                
                # 캐시 저장
                if api_call.cache_key:
                    self.call_cache[api_call.cache_key] = (result.choices[0].message.content, datetime.now())
                
                # 호출 히스토리 업데이트
                self.call_history.append((datetime.now(), api_call.id))
                
                # 큐에서 제거
                self.call_queue.remove(api_call)
                executed += 1
                
            except Exception as e:
                logger.error(f"API 호출 실행 실패: {api_call.id} - {e}")
                self.call_queue.remove(api_call)
                skipped += 1
        
        return {"executed": executed, "skipped": skipped}

    def get_metrics(self) -> Dict[str, Any]:
        """현재 메트릭 반환"""
        return {
            "cost_metrics": asdict(self.metrics),
            "queue_size": len(self.call_queue),
            "cache_size": len(self.call_cache),
            "budget_utilization": self.metrics.total_cost / self.daily_budget * 100,
            "cache_hit_rate": self.metrics.cache_hits / max(self.metrics.cache_hits + self.metrics.cache_misses, 1) * 100,
            "is_rate_limited": self._is_rate_limited(),
            "is_budget_exceeded": self._is_budget_exceeded()
        }

    def cleanup_cache(self):
        """만료된 캐시 정리"""
        now = datetime.now()
        expired_keys = []
        
        for cache_key, (_, timestamp) in self.call_cache.items():
            if not self._is_cache_valid(timestamp):
                expired_keys.append(cache_key)
        
        for key in expired_keys:
            del self.call_cache[key]
        
        if expired_keys:
            logger.info(f"만료된 캐시 {len(expired_keys)}개 정리 완료")

    def cleanup_history(self):
        """오래된 호출 히스토리 정리"""
        cutoff = datetime.now() - timedelta(hours=24)
        self.call_history = [(ts, call_id) for ts, call_id in self.call_history if ts > cutoff]

# 전역 비용 제어 인스턴스
_cost_controller = None

def get_cost_controller() -> OpenAICostController:
    """전역 비용 제어 인스턴스 반환"""
    global _cost_controller
    if _cost_controller is None:
        daily_budget = float(os.getenv('OPENAI_DAILY_BUDGET', '10.0'))
        _cost_controller = OpenAICostController(daily_budget=daily_budget)
    return _cost_controller

# 스케줄러용 정리 함수들
async def scheduled_cleanup():
    """정기 정리 작업"""
    controller = get_cost_controller()
    controller.cleanup_cache()
    controller.cleanup_history()
    logger.info("정기 정리 작업 완료")

async def scheduled_metrics_log():
    """정기 메트릭 로깅"""
    controller = get_cost_controller()
    metrics = controller.get_metrics()
    
    logger.info(f"OpenAI 비용 모니터링:")
    logger.info(f"  총 호출: {metrics['cost_metrics']['total_calls']}회")
    logger.info(f"  총 토큰: {metrics['cost_metrics']['total_tokens']:,}")
    logger.info(f"  총 비용: ${metrics['cost_metrics']['total_cost']:.4f}")
    logger.info(f"  예산 사용률: {metrics['budget_utilization']:.1f}%")
    logger.info(f"  캐시 적중률: {metrics['cache_hit_rate']:.1f}%")
    logger.info(f"  큐 크기: {metrics['queue_size']}")

# 테스트 함수
async def test_cost_controller():
    """비용 제어 시스템 테스트"""
    controller = get_cost_controller()
    
    print("=== OpenAI 비용 제어 시스템 테스트 ===")
    
    # 테스트 메시지
    test_messages = [
        {"role": "user", "content": "AAPL 주식에 대한 간단한 분석을 해주세요."}
    ]
    
    try:
        # API 호출 요청
        call_id = await controller.request_api_call(
            model="gpt-4o-mini",
            messages=test_messages,
            priority=Priority.HIGH
        )
        
        print(f"API 호출 요청 완료: {call_id}")
        
        # 메트릭 출력
        metrics = controller.get_metrics()
        print(f"현재 메트릭: {json.dumps(metrics, indent=2)}")
        
    except Exception as e:
        print(f"테스트 실패: {e}")

if __name__ == "__main__":
    asyncio.run(test_cost_controller())