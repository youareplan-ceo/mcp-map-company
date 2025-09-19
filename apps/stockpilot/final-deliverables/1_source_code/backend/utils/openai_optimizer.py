#!/usr/bin/env python3
"""
OpenAI API 호출 최적화기
- LRU 캐시를 통한 중복 요청 방지
- 지수 백오프를 통한 Rate Limit 처리
- 실시간 비용 모니터링 및 임계치 제어
- 프로덕션용 고성능 최적화
"""

import asyncio
import hashlib
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from functools import lru_cache
import json

# 로깅 설정
logger = logging.getLogger(__name__)

@dataclass
class OpenAICost:
    """OpenAI API 비용 정보"""
    model: str
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    timestamp: str

class OpenAIOptimizer:
    """OpenAI API 호출 최적화기"""
    
    # 모델별 비용 (USD per token)
    MODEL_COSTS = {
        "gpt-4o-mini": {
            "input": 0.00000015,   # $0.15 / 1M tokens
            "output": 0.00000060   # $0.60 / 1M tokens
        },
        "gpt-4o": {
            "input": 0.0000025,    # $2.50 / 1M tokens  
            "output": 0.00001      # $10.00 / 1M tokens
        }
    }
    
    def __init__(self, 
                 daily_budget: float = 10.0,  # 일일 예산 ($10)
                 cache_ttl: int = 300,         # 캐시 유효시간 (5분)
                 max_retries: int = 5):        # 최대 재시도 횟수
        """
        최적화기 초기화
        
        Args:
            daily_budget: 일일 예산 (USD)
            cache_ttl: 캐시 유효시간 (초)  
            max_retries: 최대 재시도 횟수
        """
        self.daily_budget = daily_budget
        self.cache_ttl = cache_ttl
        self.max_retries = max_retries
        
        # 비용 추적
        self.daily_costs: List[OpenAICost] = []
        self.total_daily_cost = 0.0
        self.last_reset_date = datetime.now().date()
        
        # 캐시 시스템
        self.response_cache: Dict[str, Tuple[Any, float]] = {}  # {request_hash: (response, timestamp)}
        
        # Rate Limit 추적
        self.rate_limit_resets: Dict[str, float] = {}  # {model: reset_timestamp}
        self.request_counts: Dict[str, int] = {}       # {model: count}
        
        # 백오프 상태
        self.backoff_delays: Dict[str, float] = {}     # {model: delay_seconds}
        
        logger.info(f"✅ OpenAI 최적화기 초기화 (예산: ${daily_budget}/day, 캐시: {cache_ttl}초)")
    
    def _reset_daily_costs(self):
        """일일 비용 리셋 (자정에)"""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            logger.info(f"🔄 일일 비용 리셋: ${self.total_daily_cost:.4f} -> $0.00")
            self.daily_costs.clear()
            self.total_daily_cost = 0.0
            self.last_reset_date = current_date
    
    def _generate_cache_key(self, model: str, messages: List[Dict], **kwargs) -> str:
        """캐시 키 생성"""
        # 메시지와 설정을 해시로 변환
        cache_data = {
            "model": model,
            "messages": messages,
            **kwargs
        }
        
        cache_str = json.dumps(cache_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(cache_str.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[Any]:
        """캐시된 응답 조회"""
        if cache_key in self.response_cache:
            response, timestamp = self.response_cache[cache_key]
            
            # TTL 확인
            if time.time() - timestamp <= self.cache_ttl:
                logger.info(f"💡 캐시 히트: {cache_key[:8]}...")
                return response
            else:
                # 만료된 캐시 삭제
                del self.response_cache[cache_key]
                logger.debug(f"🗑️ 만료된 캐시 삭제: {cache_key[:8]}...")
        
        return None
    
    def _cache_response(self, cache_key: str, response: Any):
        """응답 캐시 저장"""
        self.response_cache[cache_key] = (response, time.time())
        logger.debug(f"💾 캐시 저장: {cache_key[:8]}...")
        
        # 캐시 크기 제한 (최대 1000개)
        if len(self.response_cache) > 1000:
            # 가장 오래된 캐시 10개 삭제
            sorted_cache = sorted(
                self.response_cache.items(),
                key=lambda x: x[1][1]  # timestamp로 정렬
            )
            
            for i in range(10):
                if i < len(sorted_cache):
                    del self.response_cache[sorted_cache[i][0]]
            
            logger.info(f"🧹 캐시 정리: {len(self.response_cache)}개 유지")
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> OpenAICost:
        """API 호출 비용 계산"""
        if model not in self.MODEL_COSTS:
            logger.warning(f"⚠️ 알 수 없는 모델 비용: {model}")
            model = "gpt-4o-mini"  # 기본값
        
        costs = self.MODEL_COSTS[model]
        input_cost = input_tokens * costs["input"]
        output_cost = output_tokens * costs["output"]
        total_cost = input_cost + output_cost
        
        cost_info = OpenAICost(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            timestamp=datetime.now().isoformat()
        )
        
        return cost_info
    
    def _track_cost(self, cost_info: OpenAICost):
        """비용 추적 및 예산 관리"""
        self._reset_daily_costs()
        
        self.daily_costs.append(cost_info)
        self.total_daily_cost += cost_info.total_cost
        
        logger.info(
            f"💰 API 비용: ${cost_info.total_cost:.6f} "
            f"({cost_info.input_tokens}→{cost_info.output_tokens} tokens) "
            f"일일 누적: ${self.total_daily_cost:.4f}"
        )
        
        # 예산 경고
        if self.total_daily_cost >= self.daily_budget * 0.8:
            logger.warning(f"⚠️ 일일 예산 80% 도달: ${self.total_daily_cost:.4f}/${self.daily_budget}")
        
        if self.total_daily_cost >= self.daily_budget:
            logger.error(f"🚨 일일 예산 초과: ${self.total_daily_cost:.4f}/${self.daily_budget}")
            raise Exception("일일 OpenAI 예산 초과")
    
    def _should_throttle(self, model: str) -> bool:
        """Rate Limit 확인"""
        # 예산 체크
        if self.total_daily_cost >= self.daily_budget:
            return True
        
        # 백오프 체크
        if model in self.backoff_delays:
            if time.time() < self.backoff_delays[model]:
                return True
            else:
                del self.backoff_delays[model]
        
        return False
    
    def _handle_rate_limit(self, model: str, retry_count: int):
        """Rate Limit 처리 (지수 백오프)"""
        base_delay = 2 ** retry_count  # 2, 4, 8, 16, 32초
        jitter = base_delay * 0.1 * (0.5 - asyncio.get_event_loop().time() % 1)  # 랜덤 지터
        delay = base_delay + jitter
        
        self.backoff_delays[model] = time.time() + delay
        
        logger.warning(f"⏳ Rate Limit - 백오프 대기: {delay:.1f}초 (재시도 {retry_count}/{self.max_retries})")
        return delay
    
    async def optimize_chat_completion(self, 
                                     openai_client,
                                     model: str,
                                     messages: List[Dict],
                                     **kwargs) -> Any:
        """
        최적화된 OpenAI Chat Completion 호출
        
        Args:
            openai_client: OpenAI 클라이언트
            model: 모델명
            messages: 메시지 리스트
            **kwargs: 추가 파라미터
            
        Returns:
            OpenAI API 응답
        """
        # 캐시 키 생성
        cache_key = self._generate_cache_key(model, messages, **kwargs)
        
        # 캐시된 응답 확인
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            return cached_response
        
        # Rate Limit 확인
        if self._should_throttle(model):
            raise Exception("API 호출 제한 (예산 초과 또는 Rate Limit)")
        
        # 재시도 로직
        last_exception = None
        
        for retry_count in range(self.max_retries + 1):
            try:
                logger.info(f"🤖 OpenAI API 호출: {model} (재시도: {retry_count})")
                
                # API 호출
                response = await openai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    **kwargs
                )
                
                # 비용 계산 및 추적
                usage = response.usage
                if usage:
                    cost_info = self._calculate_cost(
                        model, 
                        usage.prompt_tokens, 
                        usage.completion_tokens
                    )
                    self._track_cost(cost_info)
                
                # 응답 캐시 저장
                self._cache_response(cache_key, response)
                
                logger.info(f"✅ OpenAI API 성공: {model}")
                return response
                
            except Exception as e:
                last_exception = e
                error_str = str(e).lower()
                
                if "rate limit" in error_str or "429" in error_str:
                    if retry_count < self.max_retries:
                        delay = self._handle_rate_limit(model, retry_count + 1)
                        await asyncio.sleep(delay)
                        continue
                else:
                    # Rate Limit이 아닌 다른 오류는 즉시 실패
                    logger.error(f"❌ OpenAI API 오류: {e}")
                    break
        
        # 모든 재시도 실패
        logger.error(f"❌ OpenAI API 최종 실패: {last_exception}")
        raise last_exception
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """비용 요약 정보 반환"""
        self._reset_daily_costs()
        
        summary = {
            "daily_budget": self.daily_budget,
            "total_daily_cost": self.total_daily_cost,
            "remaining_budget": max(0, self.daily_budget - self.total_daily_cost),
            "budget_utilization": (self.total_daily_cost / self.daily_budget) * 100,
            "total_requests": len(self.daily_costs),
            "cache_size": len(self.response_cache),
            "cache_hit_rate": 0.0  # TODO: 계산 구현
        }
        
        if self.daily_costs:
            model_costs = {}
            for cost in self.daily_costs:
                model = cost.model
                if model not in model_costs:
                    model_costs[model] = {
                        "requests": 0,
                        "total_cost": 0.0,
                        "total_tokens": 0
                    }
                
                model_costs[model]["requests"] += 1
                model_costs[model]["total_cost"] += cost.total_cost
                model_costs[model]["total_tokens"] += cost.input_tokens + cost.output_tokens
            
            summary["model_breakdown"] = model_costs
        
        return summary
    
    def clear_cache(self):
        """캐시 전체 삭제"""
        cache_size = len(self.response_cache)
        self.response_cache.clear()
        logger.info(f"🧹 캐시 전체 삭제: {cache_size}개 항목")

# 전역 최적화기 인스턴스
_global_optimizer = None

def get_openai_optimizer(daily_budget: float = 10.0) -> OpenAIOptimizer:
    """전역 OpenAI 최적화기 인스턴스 반환"""
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = OpenAIOptimizer(daily_budget=daily_budget)
    return _global_optimizer

# 테스트 함수
async def test_openai_optimizer():
    """OpenAI 최적화기 테스트"""
    print("=== OpenAI API 호출 최적화기 테스트 ===")
    
    optimizer = OpenAIOptimizer(daily_budget=5.0)
    
    # Mock OpenAI 클라이언트 응답
    class MockResponse:
        def __init__(self):
            self.usage = MockUsage()
    
    class MockUsage:
        def __init__(self):
            self.prompt_tokens = 50
            self.completion_tokens = 30
    
    class MockClient:
        async def create(self, **kwargs):
            await asyncio.sleep(0.1)  # API 호출 시뮬레이션
            return MockResponse()
    
    class MockCompletions:
        def __init__(self):
            self.create = MockClient().create
    
    class MockChat:
        def __init__(self):
            self.completions = MockCompletions()
    
    class MockOpenAIClient:
        def __init__(self):
            self.chat = MockChat()
    
    mock_client = MockOpenAIClient()
    
    # 테스트 메시지
    test_messages = [
        {"role": "user", "content": "Hello, world!"}
    ]
    
    try:
        print("\n🧪 테스트 1: 일반 API 호출")
        response1 = await optimizer.optimize_chat_completion(
            mock_client, 
            "gpt-4o-mini", 
            test_messages
        )
        print("✅ 성공")
        
        print("\n🧪 테스트 2: 캐시된 요청 (같은 요청)")
        response2 = await optimizer.optimize_chat_completion(
            mock_client, 
            "gpt-4o-mini", 
            test_messages
        )
        print("✅ 캐시 히트 성공")
        
        print("\n📊 비용 요약:")
        summary = optimizer.get_cost_summary()
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")

if __name__ == "__main__":
    asyncio.run(test_openai_optimizer())