"""
AI 엔진 공통 타입 정의
모든 모듈에서 사용하는 Enum 및 타입들을 정의
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime

class ContentType(Enum):
    """콘텐츠 유형 분류"""
    TEXT = "text"                    # 순수 텍스트
    JSON = "json"                    # JSON 데이터
    MIXED = "mixed"                  # 혼합 콘텐츠
    PRICE_DATA = "price_data"        # 주가 데이터
    NEWS_ANALYSIS = "news_analysis"  # 뉴스 분석
    TECHNICAL_ANALYSIS = "technical" # 기술적 분석
    FUNDAMENTAL = "fundamental"      # 기본적 분석
    STRATEGY = "strategy"           # 투자 전략
    RISK_ASSESSMENT = "risk"        # 리스크 평가

class TaskType(Enum):
    """작업 유형 분류"""
    # 데이터 처리
    DATA_EXTRACTION = "data_extraction"
    DATA_QUERY = "data_query"
    PRICE_FORMATTING = "price_formatting"
    BASIC_CALCULATION = "basic_calculation"
    SIMPLE_CLASSIFICATION = "simple_classification"
    
    # 분석 작업
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    NEWS_SUMMARIZATION = "news_summarization"  
    TREND_DETECTION = "trend_detection"
    PATTERN_RECOGNITION = "pattern_recognition"
    
    # 고급 분석
    TECHNICAL_ANALYSIS = "technical_analysis"
    FUNDAMENTAL_ANALYSIS = "fundamental_analysis"
    RISK_ASSESSMENT = "risk_assessment"
    PORTFOLIO_OPTIMIZATION = "portfolio_optimization"
    STOCK_ANALYSIS = "stock_analysis"
    
    # 전략적 판단
    INVESTMENT_STRATEGY = "investment_strategy"
    MARKET_PREDICTION = "market_prediction"
    CRISIS_ANALYSIS = "crisis_analysis"
    COMPLEX_REASONING = "complex_reasoning"

class ModelTierLevel(Enum):
    """모델 티어 레벨 (테스트 호환성)"""
    NANO = "nano"
    MINI = "mini" 
    STANDARD = "standard"
    PREMIUM = "premium"

class QualityLevel(Enum):
    """품질 수준"""
    LOW = "low"
    MEDIUM = "medium"  
    HIGH = "high"
    PREMIUM = "premium"

class CostLevel(Enum):
    """비용 수준"""
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

@dataclass
class ModelCapabilities:
    """모델 능력 정의"""
    max_tokens: int
    context_window: int
    supports_korean: bool = True
    supports_json: bool = True
    supports_function_calling: bool = False
    reasoning_level: QualityLevel = QualityLevel.MEDIUM
    
@dataclass
class TaskRequirements:
    """작업 요구사항"""
    min_quality: QualityLevel
    max_cost: CostLevel
    requires_reasoning: bool = False
    requires_korean: bool = False
    content_types: List[ContentType] = None
    
    def __post_init__(self):
        if self.content_types is None:
            self.content_types = [ContentType.TEXT]

@dataclass
class ModelPerformanceMetrics:
    """모델 성능 지표"""
    model_name: str
    avg_response_time: float = 0.0
    success_rate: float = 1.0
    avg_cost_per_request: float = 0.0
    quality_score: float = 0.0
    last_updated: datetime = None
    total_requests: int = 0
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()

# 테스트 호환성을 위한 상수들
DEFAULT_MODEL_CONFIGS = {
    "gpt-4o-mini": {
        "tier": ModelTierLevel.NANO,
        "max_tokens": 4000,
        "cost_per_1k_tokens": 0.00015,
        "capabilities": ModelCapabilities(
            max_tokens=4000,
            context_window=128000,
            reasoning_level=QualityLevel.LOW
        )
    },
    "gpt-4o": {
        "tier": ModelTierLevel.STANDARD, 
        "max_tokens": 8000,
        "cost_per_1k_tokens": 0.0025,
        "capabilities": ModelCapabilities(
            max_tokens=8000,
            context_window=128000,
            reasoning_level=QualityLevel.HIGH
        )
    },
    "o1": {
        "tier": ModelTierLevel.PREMIUM,
        "max_tokens": 32000, 
        "cost_per_1k_tokens": 0.015,
        "capabilities": ModelCapabilities(
            max_tokens=32000,
            context_window=200000,
            reasoning_level=QualityLevel.PREMIUM,
            supports_function_calling=True
        )
    }
}

# 작업별 기본 라우팅 규칙
DEFAULT_TASK_ROUTING = {
    # 간단한 작업들
    TaskType.DATA_EXTRACTION: ModelTierLevel.NANO,
    TaskType.DATA_QUERY: ModelTierLevel.NANO,
    TaskType.PRICE_FORMATTING: ModelTierLevel.NANO,
    TaskType.BASIC_CALCULATION: ModelTierLevel.NANO,
    TaskType.SIMPLE_CLASSIFICATION: ModelTierLevel.NANO,
    
    # 표준 분석
    TaskType.SENTIMENT_ANALYSIS: ModelTierLevel.MINI,
    TaskType.NEWS_SUMMARIZATION: ModelTierLevel.MINI,
    TaskType.TREND_DETECTION: ModelTierLevel.MINI,
    TaskType.PATTERN_RECOGNITION: ModelTierLevel.MINI,
    
    # 고급 분석
    TaskType.TECHNICAL_ANALYSIS: ModelTierLevel.STANDARD,
    TaskType.FUNDAMENTAL_ANALYSIS: ModelTierLevel.STANDARD,
    TaskType.RISK_ASSESSMENT: ModelTierLevel.STANDARD,
    TaskType.PORTFOLIO_OPTIMIZATION: ModelTierLevel.STANDARD,
    TaskType.STOCK_ANALYSIS: ModelTierLevel.STANDARD,
    
    # 전략적 판단
    TaskType.INVESTMENT_STRATEGY: ModelTierLevel.PREMIUM,
    TaskType.MARKET_PREDICTION: ModelTierLevel.PREMIUM,
    TaskType.CRISIS_ANALYSIS: ModelTierLevel.PREMIUM,
    TaskType.COMPLEX_REASONING: ModelTierLevel.PREMIUM,
}

# 콘텐츠 타입별 모델 선호도
CONTENT_TYPE_PREFERENCES = {
    ContentType.TEXT: [ModelTierLevel.MINI, ModelTierLevel.NANO],
    ContentType.JSON: [ModelTierLevel.STANDARD, ModelTierLevel.MINI],
    ContentType.MIXED: [ModelTierLevel.STANDARD, ModelTierLevel.PREMIUM],
    ContentType.PRICE_DATA: [ModelTierLevel.NANO, ModelTierLevel.MINI],
    ContentType.NEWS_ANALYSIS: [ModelTierLevel.MINI, ModelTierLevel.STANDARD],
    ContentType.TECHNICAL_ANALYSIS: [ModelTierLevel.STANDARD, ModelTierLevel.PREMIUM],
    ContentType.FUNDAMENTAL: [ModelTierLevel.STANDARD, ModelTierLevel.PREMIUM], 
    ContentType.STRATEGY: [ModelTierLevel.PREMIUM, ModelTierLevel.STANDARD],
    ContentType.RISK_ASSESSMENT: [ModelTierLevel.STANDARD, ModelTierLevel.PREMIUM],
}