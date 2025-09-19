"""
AI 엔진 설정 패키지
모든 설정, 정책, 타입 정의 모듈들을 통합 관리
"""

# 핵심 타입 정의 re-export
from .types import (
    ContentType, TaskType, ModelTierLevel, QualityLevel, CostLevel,
    ModelCapabilities, TaskRequirements, ModelPerformanceMetrics,
    DEFAULT_MODEL_CONFIGS, DEFAULT_TASK_ROUTING, CONTENT_TYPE_PREFERENCES
)

# 모델 정책 re-export  
from .model_policy import (
    StockPilotModelPolicy, ModelTier, TaskComplexity, ModelPolicy, QualityGate,
    model_policy, get_model_for_task, get_model_for_content_type, get_token_limit_for_model
)

# API 설정 re-export
from .api_config import (
    APIConfiguration, APIProvider, OpenAIClientManager
)

# 한국 시장 설정 re-export
from .korean_market_config import (
    KoreanMarketConfig, KoreanStockInfo, KoreanMarket, SectorKR,
    korean_market_config, validate_stock_symbol, get_yfinance_symbol,
    analyze_korean_sentiment, extract_stock_symbols, is_market_open
)

# 한국어 프롬프트 템플릿 re-export
from .prompt_templates_kr import (
    KoreanPromptTemplates, PromptType, PromptTemplate, korean_prompts,
    analyze_stock_kr, analyze_sentiment_kr, technical_analysis_kr
)

__all__ = [
    # 타입 정의
    'ContentType', 'TaskType', 'ModelTierLevel', 'QualityLevel', 'CostLevel',
    'ModelCapabilities', 'TaskRequirements', 'ModelPerformanceMetrics',
    'DEFAULT_MODEL_CONFIGS', 'DEFAULT_TASK_ROUTING', 'CONTENT_TYPE_PREFERENCES',
    
    # 모델 정책
    'StockPilotModelPolicy', 'ModelTier', 'TaskComplexity', 'ModelPolicy', 'QualityGate',
    'model_policy', 'get_model_for_task', 'get_model_for_content_type', 'get_token_limit_for_model',
    
    # API 설정
    'APIConfiguration', 'APIProvider', 'OpenAIClientManager',
    
    # 한국 시장 설정
    'KoreanMarketConfig', 'KoreanStockInfo', 'KoreanMarket', 'SectorKR',
    'korean_market_config', 'validate_stock_symbol', 'get_yfinance_symbol',
    'analyze_korean_sentiment', 'extract_stock_symbols', 'is_market_open',
    
    # 한국어 프롬프트
    'KoreanPromptTemplates', 'PromptType', 'PromptTemplate', 'korean_prompts',
    'analyze_stock_kr', 'analyze_sentiment_kr', 'technical_analysis_kr',
]