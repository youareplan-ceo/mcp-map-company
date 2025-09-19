"""
StockPilot Model Policy v2 구현
AI 모델 선택, 비용 최적화, 품질 게이트 정책을 정의
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class ModelTier(Enum):
    """모델 티어 정의"""
    NANO = "gpt-4o-mini"         # 기본 처리용 경량 모델
    MINI = "gpt-4o-mini"         # 표준 분석용 모델  
    STANDARD = "gpt-4o"          # 고급 분석용 모델
    PREMIUM = "o1"               # 최고급 전략 분석용 모델


class TaskComplexity(Enum):
    """작업 복잡도 분류"""
    SIMPLE = "simple"            # 단순 데이터 처리
    MODERATE = "moderate"        # 표준 분석 작업
    COMPLEX = "complex"          # 복합 분석 작업
    HIGHLY_COMPLEX = "highly_complex"  # 매우 복잡한 분석
    CRITICAL = "critical"        # 중요한 전략적 판단


class ContentType(Enum):
    """콘텐츠 유형 분류"""
    PRICE_DATA = "price_data"           # 주가 데이터
    NEWS_ANALYSIS = "news_analysis"     # 뉴스 분석
    TECHNICAL_ANALYSIS = "technical"    # 기술적 분석
    FUNDAMENTAL = "fundamental"         # 기본적 분석
    STRATEGY = "strategy"              # 투자 전략
    RISK_ASSESSMENT = "risk"           # 리스크 평가


@dataclass
class ModelPolicy:
    """모델 정책 설정"""
    tier: ModelTier
    max_tokens: int
    temperature: float
    cost_per_1k_tokens: float
    context_window: int
    use_cache: bool = True
    cache_ttl: int = 3600  # 1시간
    retry_count: int = 3
    timeout: int = 30


@dataclass 
class QualityGate:
    """품질 게이트 기준"""
    min_confidence: float = 0.7     # 최소 신뢰도
    max_cost_per_query: float = 0.10  # 쿼리당 최대 비용 ($)
    max_response_time: int = 10     # 최대 응답시간 (초)
    require_citation: bool = True   # 인용 필수 여부
    validate_format: bool = True    # 출력 형식 검증


class StockPilotModelPolicy:
    """StockPilot AI 모델 정책 관리 클래스"""
    
    def __init__(self):
        """정책 초기화"""
        self.policies = self._initialize_policies()
        self.routing_rules = self._initialize_routing_rules()
        self.quality_gates = self._initialize_quality_gates()
        self.cost_limits = self._initialize_cost_limits()
        
        # 테스트 호환성을 위한 속성들
        self.model_tiers = list(self.policies.keys())
        self.task_complexities = list(TaskComplexity)
        self.content_types = list(ContentType)
        
    def _initialize_policies(self) -> Dict[ModelTier, ModelPolicy]:
        """모델별 정책 초기화"""
        return {
            ModelTier.NANO: ModelPolicy(
                tier=ModelTier.NANO,
                max_tokens=1000,
                temperature=0.3,
                cost_per_1k_tokens=0.000150,  # $0.15/1M tokens
                context_window=128000,
                use_cache=True,
                cache_ttl=7200,  # 2시간
                retry_count=3,
                timeout=15
            ),
            ModelTier.MINI: ModelPolicy(
                tier=ModelTier.MINI,
                max_tokens=2000,
                temperature=0.5,
                cost_per_1k_tokens=0.000150,  # $0.15/1M tokens
                context_window=128000,
                use_cache=True,
                cache_ttl=3600,  # 1시간
                retry_count=3,
                timeout=30
            ),
            ModelTier.STANDARD: ModelPolicy(
                tier=ModelTier.STANDARD,
                max_tokens=4000,
                temperature=0.7,
                cost_per_1k_tokens=0.0025,    # $2.50/1M tokens
                context_window=128000,
                use_cache=True,
                cache_ttl=1800,  # 30분
                retry_count=2,
                timeout=45
            ),
            ModelTier.PREMIUM: ModelPolicy(
                tier=ModelTier.PREMIUM,
                max_tokens=8000,
                temperature=0.8,
                cost_per_1k_tokens=0.015,     # $15/1M tokens
                context_window=200000,
                use_cache=False,  # 항상 최신 분석
                cache_ttl=0,
                retry_count=1,
                timeout=60
            )
        }
    
    def _initialize_routing_rules(self) -> Dict[str, ModelTier]:
        """작업 유형별 모델 라우팅 규칙"""
        return {
            # 단순 데이터 처리 - NANO 모델 사용
            "data_extraction": ModelTier.NANO,
            "price_formatting": ModelTier.NANO,
            "basic_calculation": ModelTier.NANO,
            "simple_classification": ModelTier.NANO,
            
            # 표준 분석 작업 - MINI 모델 사용  
            "sentiment_analysis": ModelTier.MINI,
            "news_summarization": ModelTier.MINI,
            "trend_detection": ModelTier.MINI,
            "pattern_recognition": ModelTier.MINI,
            
            # 복합 분석 작업 - STANDARD 모델 사용
            "technical_analysis": ModelTier.STANDARD,
            "fundamental_analysis": ModelTier.STANDARD,
            "risk_assessment": ModelTier.STANDARD,
            "portfolio_optimization": ModelTier.STANDARD,
            
            # 전략적 판단 - PREMIUM 모델 사용
            "investment_strategy": ModelTier.PREMIUM,
            "market_prediction": ModelTier.PREMIUM,
            "crisis_analysis": ModelTier.PREMIUM,
            "complex_reasoning": ModelTier.PREMIUM
        }
    
    def _initialize_quality_gates(self) -> Dict[ModelTier, QualityGate]:
        """모델별 품질 게이트 기준"""
        return {
            ModelTier.NANO: QualityGate(
                min_confidence=0.6,
                max_cost_per_query=0.01,
                max_response_time=5,
                require_citation=False,
                validate_format=True
            ),
            ModelTier.MINI: QualityGate(
                min_confidence=0.7,
                max_cost_per_query=0.03,
                max_response_time=10,
                require_citation=True,
                validate_format=True
            ),
            ModelTier.STANDARD: QualityGate(
                min_confidence=0.8,
                max_cost_per_query=0.10,
                max_response_time=15,
                require_citation=True,
                validate_format=True
            ),
            ModelTier.PREMIUM: QualityGate(
                min_confidence=0.9,
                max_cost_per_query=0.50,
                max_response_time=30,
                require_citation=True,
                validate_format=True
            )
        }
    
    def _initialize_cost_limits(self) -> Dict[str, float]:
        """비용 제한 설정"""
        return {
            "daily_limit": 100.0,        # 일일 한도 ($)
            "hourly_limit": 10.0,        # 시간당 한도 ($)
            "query_limit": 1.0,          # 쿼리당 한도 ($)
            "user_daily_limit": 5.0,     # 사용자별 일일 한도 ($)
            "emergency_reserve": 20.0     # 긴급 상황 대비 예약 ($)
        }
    
    def get_model_for_task(
        self, 
        task_type: str, 
        complexity: TaskComplexity = TaskComplexity.MODERATE,
        content_type: ContentType = ContentType.PRICE_DATA
    ) -> ModelTier:
        """
        작업 유형에 따른 최적 모델 선택
        
        Args:
            task_type: 작업 유형
            complexity: 복잡도
            content_type: 콘텐츠 유형
            
        Returns:
            ModelTier: 선택된 모델 티어
        """
        try:
            # 기본 라우팅 규칙 적용
            base_model = self.routing_rules.get(task_type, ModelTier.MINI)
            
            # 복잡도에 따른 모델 승급/강등
            if complexity == TaskComplexity.SIMPLE:
                # 단순 작업은 한 단계 하위 모델 사용
                if base_model == ModelTier.MINI:
                    return ModelTier.NANO
                elif base_model == ModelTier.STANDARD:
                    return ModelTier.MINI
                    
            elif complexity == TaskComplexity.HIGHLY_COMPLEX:
                # 매우 복잡한 작업은 고급 모델 사용
                if base_model in [ModelTier.NANO, ModelTier.MINI]:
                    return ModelTier.STANDARD
                
            elif complexity == TaskComplexity.CRITICAL:
                # 중요한 작업은 최고급 모델 사용
                return ModelTier.PREMIUM
                
            # 콘텐츠 유형에 따른 추가 고려사항
            if content_type in [ContentType.STRATEGY, ContentType.RISK_ASSESSMENT]:
                # 전략 및 리스크 분석은 고급 모델 사용
                if base_model in [ModelTier.NANO, ModelTier.MINI]:
                    return ModelTier.STANDARD
                    
            return base_model
            
        except Exception as e:
            logger.error(f"모델 선택 실패: {str(e)}")
            return ModelTier.MINI  # 안전한 기본값
    
    def get_policy(self, model_tier: ModelTier) -> ModelPolicy:
        """모델 티어에 해당하는 정책 반환"""
        return self.policies.get(model_tier, self.policies[ModelTier.MINI])
    
    def get_quality_gate(self, model_tier: ModelTier) -> QualityGate:
        """모델 티어에 해당하는 품질 게이트 반환"""
        return self.quality_gates.get(model_tier, self.quality_gates[ModelTier.MINI])
    
    def validate_request(
        self, 
        model_tier: ModelTier, 
        estimated_tokens: int,
        current_cost: float
    ) -> Dict[str, Any]:
        """
        요청 검증 및 승인/거부 판단
        
        Args:
            model_tier: 사용할 모델 티어
            estimated_tokens: 예상 토큰 수
            current_cost: 현재 누적 비용
            
        Returns:
            Dict: 검증 결과
        """
        try:
            policy = self.get_policy(model_tier)
            quality_gate = self.get_quality_gate(model_tier)
            
            # 예상 비용 계산
            estimated_cost = (estimated_tokens / 1000) * policy.cost_per_1k_tokens
            
            # 검증 결과
            validation_result = {
                "approved": True,
                "model_tier": model_tier,
                "estimated_cost": estimated_cost,
                "estimated_tokens": estimated_tokens,
                "warnings": [],
                "recommendations": []
            }
            
            # 비용 한도 검증
            if estimated_cost > quality_gate.max_cost_per_query:
                validation_result["approved"] = False
                validation_result["warnings"].append(
                    f"예상 비용 ${estimated_cost:.4f}가 한도 ${quality_gate.max_cost_per_query}를 초과"
                )
                
            # 토큰 한도 검증
            if estimated_tokens > policy.max_tokens:
                validation_result["warnings"].append(
                    f"예상 토큰 {estimated_tokens}가 모델 한도 {policy.max_tokens}를 초과"
                )
                validation_result["recommendations"].append("더 높은 티어의 모델 사용 권장")
                
            # 일일 비용 한도 검증
            daily_limit = self.cost_limits["daily_limit"]
            if current_cost + estimated_cost > daily_limit:
                validation_result["approved"] = False
                validation_result["warnings"].append(
                    f"일일 비용 한도 ${daily_limit} 초과 위험"
                )
            
            return validation_result
            
        except Exception as e:
            logger.error(f"요청 검증 실패: {str(e)}")
            return {
                "approved": False,
                "error": str(e),
                "warnings": ["검증 과정에서 오류 발생"],
                "recommendations": ["시스템 관리자에게 문의"]
            }
    
    def suggest_optimization(
        self, 
        task_type: str, 
        current_model: ModelTier,
        performance_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        성능 지표를 바탕으로 최적화 제안
        
        Args:
            task_type: 작업 유형
            current_model: 현재 사용 모델
            performance_metrics: 성능 지표
            
        Returns:
            Dict: 최적화 제안
        """
        try:
            suggestions = {
                "current_model": current_model,
                "recommended_model": current_model,
                "optimization_type": "none",
                "expected_savings": 0.0,
                "trade_offs": [],
                "action_required": False
            }
            
            # 성능 지표 분석
            response_time = performance_metrics.get("response_time", 0)
            cost_per_query = performance_metrics.get("cost_per_query", 0)
            quality_score = performance_metrics.get("quality_score", 1.0)
            
            current_policy = self.get_policy(current_model)
            current_gate = self.get_quality_gate(current_model)
            
            # 오버엔지니어링 감지 (품질은 충분하지만 비용이 높은 경우)
            if (quality_score >= 0.95 and 
                cost_per_query > current_gate.max_cost_per_query * 0.5):
                
                # 더 저렴한 모델 제안
                if current_model == ModelTier.PREMIUM:
                    suggested_model = ModelTier.STANDARD
                elif current_model == ModelTier.STANDARD:
                    suggested_model = ModelTier.MINI
                elif current_model == ModelTier.MINI:
                    suggested_model = ModelTier.NANO
                else:
                    suggested_model = current_model
                    
                if suggested_model != current_model:
                    suggested_policy = self.get_policy(suggested_model)
                    potential_savings = cost_per_query * (1 - suggested_policy.cost_per_1k_tokens / current_policy.cost_per_1k_tokens)
                    
                    suggestions.update({
                        "recommended_model": suggested_model,
                        "optimization_type": "cost_reduction",
                        "expected_savings": potential_savings,
                        "trade_offs": ["약간의 품질 저하 가능성"],
                        "action_required": True
                    })
            
            # 언더퍼포먼스 감지 (품질이 낮거나 응답이 느린 경우)
            elif (quality_score < 0.7 or 
                  response_time > current_gate.max_response_time):
                
                # 더 강력한 모델 제안
                if current_model == ModelTier.NANO:
                    suggested_model = ModelTier.MINI
                elif current_model == ModelTier.MINI:
                    suggested_model = ModelTier.STANDARD
                elif current_model == ModelTier.STANDARD:
                    suggested_model = ModelTier.PREMIUM
                else:
                    suggested_model = current_model
                    
                if suggested_model != current_model:
                    suggestions.update({
                        "recommended_model": suggested_model,
                        "optimization_type": "quality_improvement",
                        "expected_savings": 0.0,
                        "trade_offs": ["비용 증가"],
                        "action_required": True
                    })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"최적화 제안 생성 실패: {str(e)}")
            return {
                "current_model": current_model,
                "recommended_model": current_model,
                "optimization_type": "error",
                "error": str(e)
            }


    def should_escalate_model(self, current_tier: ModelTier = None, confidence: float = None, 
                            response_time: float = None, cost_budget: float = None,
                            confidence_score: float = None, task_complexity: TaskComplexity = None) -> bool:
        """모델 에스컬레이션 필요 여부 판단"""
        try:
            # 테스트 호환성을 위한 매개변수 처리
            if confidence_score is not None:
                confidence = confidence_score
            
            if current_tier is None:
                return False
                
            quality_gate = self.get_quality_gate(current_tier)
            
            # 신뢰도가 낮으면 에스컬레이션
            if confidence is not None and confidence < quality_gate.min_confidence:
                return True
                
            # 복잡도가 높으면 에스컬레이션 고려
            if task_complexity in [TaskComplexity.HIGHLY_COMPLEX, TaskComplexity.CRITICAL]:
                return True
                
            # 응답 시간이 너무 느리면 에스컬레이션 고려
            if response_time is not None and response_time > quality_gate.max_response_time * 1.5:
                return True
                
            # 예산이 충분하고 품질이 중요한 경우
            if cost_budget is not None and cost_budget > quality_gate.max_cost_per_query * 2:
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"에스컬레이션 판단 실패: {str(e)}")
            return False
    
    def get_token_limit_for_model(self, model_name: str) -> int:
        """모델별 토큰 한도 반환"""
        try:
            for tier, policy in self.policies.items():
                if tier.value == model_name or policy.tier.value == model_name:
                    return policy.max_tokens
            return 4000  # 기본값
        except Exception as e:
            logger.error(f"토큰 한도 조회 실패: {str(e)}")
            return 4000
    
    def get_model_for_content_type(self, content_type: str) -> ModelTier:
        """콘텐츠 타입에 따른 최적 모델 선택"""
        try:
            # 콘텐츠 타입별 매핑
            content_mapping = {
                "text": ModelTier.MINI,
                "json": ModelTier.STANDARD, 
                "mixed": ModelTier.STANDARD,
                "price_data": ModelTier.NANO,
                "news_analysis": ModelTier.MINI,
                "technical": ModelTier.STANDARD,
                "fundamental": ModelTier.STANDARD,
                "strategy": ModelTier.PREMIUM,
                "risk": ModelTier.STANDARD
            }
            
            return content_mapping.get(content_type, ModelTier.MINI)
            
        except Exception as e:
            logger.error(f"콘텐츠 타입별 모델 선택 실패: {str(e)}")
            return ModelTier.MINI
    
    def get_optimal_model(self, task_type: str, quality_requirement: float = 0.8, 
                         budget_limit: Optional[float] = None) -> ModelTier:
        """품질 요구사항과 예산을 고려한 최적 모델 선택"""
        try:
            # 기본 모델 선택
            base_model = self.routing_rules.get(task_type, ModelTier.MINI)
            
            # 품질 요구사항에 따른 모델 승급
            if quality_requirement >= 0.95:
                recommended_model = ModelTier.PREMIUM
            elif quality_requirement >= 0.85:
                recommended_model = ModelTier.STANDARD
            elif quality_requirement >= 0.75:
                recommended_model = ModelTier.MINI
            else:
                recommended_model = ModelTier.NANO
            
            # 예산 제약 고려
            if budget_limit is not None:
                recommended_policy = self.get_policy(recommended_model)
                estimated_cost = recommended_policy.cost_per_1k_tokens * 2  # 평균 2k 토큰 가정
                
                if estimated_cost > budget_limit:
                    # 예산에 맞는 하위 모델 선택
                    for tier in [ModelTier.STANDARD, ModelTier.MINI, ModelTier.NANO]:
                        tier_policy = self.get_policy(tier)
                        tier_cost = tier_policy.cost_per_1k_tokens * 2
                        if tier_cost <= budget_limit:
                            return tier
                    return ModelTier.NANO  # 최후 수단
            
            return max(base_model, recommended_model, key=lambda x: list(ModelTier).index(x))
            
        except Exception as e:
            logger.error(f"최적 모델 선택 실패: {str(e)}")
            return ModelTier.MINI


# 테스트 호환성을 위한 헬퍼 함수들
def get_model_for_task(task_type: str, complexity: str = "moderate", 
                      content_type: str = "text") -> str:
    """작업 유형에 따른 모델 선택 (테스트 호환용)"""
    try:
        complexity_enum = TaskComplexity.MODERATE
        if complexity.lower() == "simple":
            complexity_enum = TaskComplexity.SIMPLE
        elif complexity.lower() == "complex":
            complexity_enum = TaskComplexity.COMPLEX
        elif complexity.lower() == "highly_complex":
            complexity_enum = TaskComplexity.HIGHLY_COMPLEX
        elif complexity.lower() == "critical":
            complexity_enum = TaskComplexity.CRITICAL
            
        content_enum = ContentType.PRICE_DATA
        if content_type.lower() == "news_analysis":
            content_enum = ContentType.NEWS_ANALYSIS
        elif content_type.lower() == "technical":
            content_enum = ContentType.TECHNICAL_ANALYSIS
        elif content_type.lower() == "fundamental":
            content_enum = ContentType.FUNDAMENTAL
        elif content_type.lower() == "strategy":
            content_enum = ContentType.STRATEGY
        elif content_type.lower() == "risk":
            content_enum = ContentType.RISK_ASSESSMENT
            
        model_tier = model_policy.get_model_for_task(task_type, complexity_enum, content_enum)
        return model_tier.value
        
    except Exception as e:
        logger.error(f"작업별 모델 선택 실패: {str(e)}")
        return "gpt-4o-mini"

def get_model_for_content_type(content_type: str) -> str:
    """콘텐츠 타입별 모델 선택 (테스트 호환용)"""
    try:
        model_tier = model_policy.get_model_for_content_type(content_type)
        return model_tier.value
    except Exception as e:
        logger.error(f"콘텐츠 타입별 모델 선택 실패: {str(e)}")
        return "gpt-4o-mini"

def get_token_limit_for_model(model_name: str) -> int:
    """모델별 토큰 한도 반환 (테스트 호환용)"""
    return model_policy.get_token_limit_for_model(model_name)


# 전역 정책 인스턴스
model_policy = StockPilotModelPolicy()