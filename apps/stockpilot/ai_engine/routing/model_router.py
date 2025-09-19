"""
스마트 모델 라우터 - 작업 복잡도에 따른 최적 모델 선택
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import json
import hashlib
from collections import defaultdict, deque

from ..config.model_policy import (
    StockPilotModelPolicy, ModelTier, TaskComplexity, ContentType,
    model_policy
)

logger = logging.getLogger(__name__)

@dataclass
class ModelRequest:
    """모델 요청"""
    task_id: str
    task_type: str
    content: str
    content_type: ContentType
    complexity: Optional[TaskComplexity] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 1  # 1: 높음, 2: 중간, 3: 낮음
    max_tokens: Optional[int] = None
    temperature: float = 0.7

@dataclass
class ModelResponse:
    """모델 응답"""
    content: str
    model_tier: ModelTier
    model_name: str
    usage: Dict[str, int]
    cost: float
    processing_time_ms: float
    confidence_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RoutingDecision:
    """라우팅 결정"""
    model_tier: ModelTier
    model_name: str
    reason: str
    estimated_cost: float
    expected_quality: float
    alternatives: List[Tuple[ModelTier, str, float]] = field(default_factory=list)

class ModelLoadBalancer:
    """모델 로드 밸런서"""
    
    def __init__(self):
        self.model_usage = defaultdict(int)  # 모델별 사용량
        self.model_queue_sizes = defaultdict(int)  # 모델별 큐 크기
        self.model_response_times = defaultdict(lambda: deque(maxlen=100))  # 응답시간 히스토리
        self.model_availability = defaultdict(lambda: True)  # 모델 가용성
    
    def get_best_model_for_tier(self, tier: ModelTier) -> str:
        """티어 내에서 최적 모델 선택"""
        # model_policy를 사용하여 사용 가능한 모델 찾기
        policy = model_policy.get_policy(tier)
        model_name = policy.tier.value if policy else tier.value
        
        if not self.model_availability[model_name]:
            logger.warning(f"Model {model_name} not available for tier {tier}")
            return "gpt-4o-mini"  # 기본 모델 반환
            
        return model_name
    
    def update_model_stats(self, model_name: str, response_time_ms: float, success: bool):
        """모델 통계 업데이트"""
        self.model_response_times[model_name].append(response_time_ms)
        if success:
            self.model_usage[model_name] += 1
        else:
            self.model_availability[model_name] = False
            # 일정 시간 후 재활성화 (실제 구현에서는 헬스체크 로직 필요)
    
    def get_queue_position(self, model_name: str) -> int:
        """모델 큐에서의 위치 반환"""
        return self.model_queue_sizes[model_name]
    
    def increment_queue(self, model_name: str):
        """큐 크기 증가"""
        self.model_queue_sizes[model_name] += 1
    
    def decrement_queue(self, model_name: str):
        """큐 크기 감소"""
        self.model_queue_sizes[model_name] = max(0, self.model_queue_sizes[model_name] - 1)

class ComplexityAnalyzer:
    """작업 복잡도 분석기"""
    
    def __init__(self):
        self.complexity_cache = {}
        self.analysis_patterns = {
            # 간단한 패턴
            "simple": [
                r"현재가", r"주가", r"시가", r"종가", r"거래량",
                r"what.*price", r"current.*value"
            ],
            # 중간 복잡도 패턴
            "moderate": [
                r"분석", r"비교", r"계산", r"평가", r"예측",
                r"analyze", r"compare", r"calculate", r"evaluate"
            ],
            # 높은 복잡도 패턴
            "complex": [
                r"전략", r"포트폴리오", r"최적화", r"모델링", r"시뮬레이션",
                r"strategy", r"portfolio", r"optimization", r"modeling"
            ]
        }
    
    def analyze_complexity(self, request: ModelRequest) -> TaskComplexity:
        """작업 복잡도 분석"""
        if request.complexity:
            return request.complexity
        
        # 캐시 확인
        content_hash = hashlib.md5(request.content.encode()).hexdigest()
        if content_hash in self.complexity_cache:
            return self.complexity_cache[content_hash]
        
        # 컨텐츠 길이 기반 복잡도
        length_complexity = self._analyze_length_complexity(request.content)
        
        # 패턴 기반 복잡도
        pattern_complexity = self._analyze_pattern_complexity(request.content)
        
        # 태스크 타입 기반 복잡도
        task_complexity = self._analyze_task_complexity(request.task_type)
        
        # 종합 복잡도 결정
        complexities = [length_complexity, pattern_complexity, task_complexity]
        complexity_weights = [0.3, 0.4, 0.3]
        
        weighted_score = sum(
            self._complexity_to_score(c) * w 
            for c, w in zip(complexities, complexity_weights)
        )
        
        final_complexity = self._score_to_complexity(weighted_score)
        
        # 캐시에 저장
        self.complexity_cache[content_hash] = final_complexity
        
        logger.debug(f"Complexity analysis: {final_complexity} (score: {weighted_score:.2f})")
        return final_complexity
    
    def _analyze_length_complexity(self, content: str) -> TaskComplexity:
        """길이 기반 복잡도 분석"""
        length = len(content)
        
        if length < 100:
            return TaskComplexity.SIMPLE
        elif length < 500:
            return TaskComplexity.MODERATE
        elif length < 1500:
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.HIGHLY_COMPLEX
    
    def _analyze_pattern_complexity(self, content: str) -> TaskComplexity:
        """패턴 기반 복잡도 분석"""
        import re
        
        content_lower = content.lower()
        
        # 복잡도별 패턴 매칭
        for complexity_level in ["complex", "moderate", "simple"]:
            patterns = self.analysis_patterns[complexity_level]
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    if complexity_level == "simple":
                        return TaskComplexity.SIMPLE
                    elif complexity_level == "moderate":
                        return TaskComplexity.MODERATE
                    else:
                        return TaskComplexity.COMPLEX
        
        return TaskComplexity.MODERATE  # 기본값
    
    def _analyze_task_complexity(self, task_type: str) -> TaskComplexity:
        """태스크 타입 기반 복잡도"""
        complexity_map = {
            "data_query": TaskComplexity.SIMPLE,
            "sentiment_analysis": TaskComplexity.MODERATE,
            "technical_analysis": TaskComplexity.MODERATE,
            "signal_generation": TaskComplexity.COMPLEX,
            "portfolio_optimization": TaskComplexity.HIGHLY_COMPLEX,
            "market_prediction": TaskComplexity.HIGHLY_COMPLEX
        }
        
        return complexity_map.get(task_type, TaskComplexity.MODERATE)
    
    def _complexity_to_score(self, complexity: TaskComplexity) -> float:
        """복잡도를 점수로 변환"""
        scores = {
            TaskComplexity.SIMPLE: 1.0,
            TaskComplexity.MODERATE: 2.0,
            TaskComplexity.COMPLEX: 3.0,
            TaskComplexity.HIGHLY_COMPLEX: 4.0
        }
        return scores.get(complexity, 2.0)
    
    def _score_to_complexity(self, score: float) -> TaskComplexity:
        """점수를 복잡도로 변환"""
        if score < 1.5:
            return TaskComplexity.SIMPLE
        elif score < 2.5:
            return TaskComplexity.MODERATE
        elif score < 3.5:
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.HIGHLY_COMPLEX

class SmartModelRouter:
    """스마트 모델 라우터"""
    
    def __init__(self):
        self.policy = StockPilotModelPolicy()
        self.load_balancer = ModelLoadBalancer()
        self.complexity_analyzer = ComplexityAnalyzer()
        self.routing_history = deque(maxlen=1000)
        self.escalation_tracker = defaultdict(int)
    
    async def route_request(self, request: ModelRequest) -> RoutingDecision:
        """요청을 적절한 모델로 라우팅"""
        try:
            # 복잡도 분석
            complexity = self.complexity_analyzer.analyze_complexity(request)
            
            # 정책에 따른 모델 티어 결정
            model_tier = self.policy.get_model_for_task(
                request.task_type, complexity, request.content_type
            )
            
            # 로드밸런서를 통한 최적 모델 선택
            model_name = self.load_balancer.get_best_model_for_tier(model_tier)
            
            # 비용 및 품질 추정
            estimated_cost = self._estimate_cost(request, model_tier)
            expected_quality = self._estimate_quality(complexity, model_tier)
            
            # 대안 모델 제안
            alternatives = self._get_alternatives(model_tier, request)
            
            # 라우팅 결정 생성
            decision = RoutingDecision(
                model_tier=model_tier,
                model_name=model_name,
                reason=f"Task: {request.task_type}, Complexity: {complexity.value}, Content: {request.content_type.value}",
                estimated_cost=estimated_cost,
                expected_quality=expected_quality,
                alternatives=alternatives
            )
            
            # 히스토리 저장
            self.routing_history.append({
                "timestamp": request.timestamp,
                "task_id": request.task_id,
                "task_type": request.task_type,
                "complexity": complexity.value,
                "model_tier": model_tier.value,
                "model_name": model_name,
                "estimated_cost": estimated_cost
            })
            
            logger.info(f"Routed task {request.task_id} to {model_name} ({model_tier.value})")
            return decision
            
        except Exception as e:
            logger.error(f"Routing failed for task {request.task_id}: {e}")
            # 폴백: 기본 모델
            fallback_tier = ModelTier.MINI
            fallback_model = self.load_balancer.get_best_model_for_tier(fallback_tier)
            
            return RoutingDecision(
                model_tier=fallback_tier,
                model_name=fallback_model,
                reason=f"Fallback due to routing error: {str(e)}",
                estimated_cost=0.01,
                expected_quality=0.7,
                alternatives=[]
            )
    
    async def should_escalate(
        self, 
        request: ModelRequest, 
        current_response: ModelResponse
    ) -> Optional[RoutingDecision]:
        """응답 품질에 따른 상위 모델 에스컬레이션 판단"""
        
        # 신뢰도 점수가 낮으면 에스컬레이션
        if (current_response.confidence_score and 
            current_response.confidence_score < 0.7 and
            current_response.model_tier != ModelTier.O3):
            
            # 에스컬레이션 횟수 확인
            escalation_key = f"{request.task_id}_{current_response.model_tier.value}"
            if self.escalation_tracker[escalation_key] >= 2:
                logger.warning(f"Max escalations reached for task {request.task_id}")
                return None
            
            # 다음 티어로 에스컬레이션
            next_tier = self._get_next_tier(current_response.model_tier)
            if next_tier:
                next_model = self.load_balancer.get_best_model_for_tier(next_tier)
                
                self.escalation_tracker[escalation_key] += 1
                
                logger.info(f"Escalating task {request.task_id} from {current_response.model_tier.value} to {next_tier.value}")
                
                return RoutingDecision(
                    model_tier=next_tier,
                    model_name=next_model,
                    reason=f"Escalated due to low confidence: {current_response.confidence_score:.2f}",
                    estimated_cost=self._estimate_cost(request, next_tier),
                    expected_quality=self._estimate_quality(TaskComplexity.COMPLEX, next_tier),
                    alternatives=[]
                )
        
        return None
    
    def _get_next_tier(self, current_tier: ModelTier) -> Optional[ModelTier]:
        """다음 티어 반환"""
        tier_order = [ModelTier.NANO, ModelTier.MINI, ModelTier.STANDARD, ModelTier.O3]
        try:
            current_index = tier_order.index(current_tier)
            if current_index < len(tier_order) - 1:
                return tier_order[current_index + 1]
        except ValueError:
            pass
        return None
    
    def _estimate_cost(self, request: ModelRequest, model_tier: ModelTier) -> float:
        """비용 추정"""
        policy = model_policy.get_policy(model_tier)
        if not policy:
            return 0.01  # 기본 비용
        
        input_tokens = len(request.content.split()) * 1.3  # 토큰 수 근사
        output_tokens = request.max_tokens or 500
        total_tokens = input_tokens + output_tokens
        
        cost = (total_tokens / 1000) * policy.cost_per_1k_tokens
        
        return cost
    
    def _estimate_quality(self, complexity: TaskComplexity, model_tier: ModelTier) -> float:
        """품질 추정"""
        tier_quality = {
            ModelTier.NANO: 0.6,
            ModelTier.MINI: 0.7,
            ModelTier.STANDARD: 0.85,
            ModelTier.O3: 0.95
        }
        
        complexity_factor = {
            TaskComplexity.SIMPLE: 1.0,
            TaskComplexity.MODERATE: 0.9,
            TaskComplexity.COMPLEX: 0.8,
            TaskComplexity.HIGHLY_COMPLEX: 0.7
        }
        
        base_quality = tier_quality.get(model_tier, 0.7)
        adjusted_quality = base_quality * complexity_factor.get(complexity, 0.8)
        
        return min(1.0, adjusted_quality)
    
    def _get_alternatives(self, primary_tier: ModelTier, request: ModelRequest) -> List[Tuple[ModelTier, str, float]]:
        """대안 모델들 반환"""
        alternatives = []
        
        for tier in [ModelTier.NANO, ModelTier.MINI, ModelTier.STANDARD, ModelTier.O3]:
            if tier != primary_tier:
                model_name = self.load_balancer.get_best_model_for_tier(tier)
                cost = self._estimate_cost(request, tier)
                alternatives.append((tier, model_name, cost))
        
        # 비용순 정렬
        alternatives.sort(key=lambda x: x[2])
        return alternatives[:3]  # 상위 3개만 반환
    
    async def get_routing_statistics(self) -> Dict[str, Any]:
        """라우팅 통계 반환"""
        if not self.routing_history:
            return {}
        
        history = list(self.routing_history)
        
        # 모델 티어별 사용 통계
        tier_usage = defaultdict(int)
        total_cost = 0.0
        
        for record in history:
            tier_usage[record["model_tier"]] += 1
            total_cost += record["estimated_cost"]
        
        # 최근 1시간 통계
        recent_threshold = datetime.now() - timedelta(hours=1)
        recent_records = [r for r in history if r["timestamp"] > recent_threshold]
        
        return {
            "total_requests": len(history),
            "recent_requests_1h": len(recent_records),
            "tier_usage_distribution": dict(tier_usage),
            "total_estimated_cost": total_cost,
            "average_cost_per_request": total_cost / len(history) if history else 0,
            "escalation_count": sum(self.escalation_tracker.values()),
            "model_availability": dict(self.load_balancer.model_availability)
        }

# 글로벌 라우터 인스턴스
router = SmartModelRouter()

async def route_to_best_model(request: ModelRequest) -> RoutingDecision:
    """요청을 최적 모델로 라우팅"""
    return await router.route_request(request)

async def check_escalation(request: ModelRequest, response: ModelResponse) -> Optional[RoutingDecision]:
    """에스컬레이션 필요성 검사"""
    return await router.should_escalate(request, response)

async def get_routing_stats() -> Dict[str, Any]:
    """라우팅 통계 조회"""
    return await router.get_routing_statistics()