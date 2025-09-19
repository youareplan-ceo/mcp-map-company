"""
FastAPI 애플리케이션 설정
환경 변수 및 전역 설정 관리
"""

import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 기본 설정
    app_name: str = "StockPilot AI API"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # 서버 설정
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    reload: bool = Field(default=False, env="RELOAD")
    
    # CORS 설정
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        env="ALLOWED_ORIGINS"
    )
    allowed_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allowed_headers: List[str] = ["*"]
    
    # API 키 설정
    openai_api_key: str = Field(env="OPENAI_API_KEY")
    
    # 데이터베이스 설정 (선택사항)
    database_url: str = Field(
        default="postgresql://localhost/stockpilot",
        env="DATABASE_URL"
    )
    
    # Redis 설정 (캐시용)
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )
    
    # 로깅 설정
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # 미국 시장 설정 (우선)
    market_timezone: str = "US/Eastern"  # 미국 동부시간 (NYSE, NASDAQ)
    market_open_time: str = "09:30"  # 미국 장 시작 (ET)
    market_close_time: str = "16:00"  # 미국 장 마감 (ET)
    default_market: str = "US"  # 기본 시장을 미국으로 설정
    default_currency: str = "USD"  # 기본 통화를 달러로 설정
    
    # 한국 시장 설정 (2차 지원)
    korea_market_timezone: str = "Asia/Seoul"
    korea_market_open_time: str = "09:00"
    korea_market_close_time: str = "15:30"
    
    # API 제한 설정
    max_stocks_per_request: int = 50
    max_signals_per_page: int = 100
    max_news_per_request: int = 100
    
    # WebSocket 설정
    websocket_max_connections: int = 1000
    websocket_heartbeat_interval: int = 30  # 초
    
    # 외부 API 설정
    yahoo_finance_timeout: int = 30  # 초
    news_api_timeout: int = 30  # 초
    
    # AI 분석 설정
    ai_analysis_timeout: int = 60  # 초
    default_gpt_model: str = "gpt-3.5-turbo"
    max_gpt_tokens: int = 2000
    
    # 모델 라우팅 정책 v2 설정
    model_nano: str = Field(default="gpt-4o-mini-2024-07-18", env="MODEL_NANO")
    model_mini: str = Field(default="gpt-4o-mini", env="MODEL_MINI")
    model_gpt4: str = Field(default="gpt-4-turbo-2024-04-09", env="MODEL_GPT4")
    model_gpt5: str = Field(default="gpt-4o", env="MODEL_GPT5")
    model_o3: str = Field(default="o1-preview", env="MODEL_O3")
    
    # 모델별 토큰 제한
    token_limit_nano: int = Field(default=512, env="TOKEN_LIMIT_NANO")
    token_limit_mini: int = Field(default=1024, env="TOKEN_LIMIT_MINI")
    token_limit_gpt4: int = Field(default=2048, env="TOKEN_LIMIT_GPT4")
    token_limit_gpt5: int = Field(default=4096, env="TOKEN_LIMIT_GPT5")
    token_limit_o3: int = Field(default=8192, env="TOKEN_LIMIT_O3")
    
    # 비용 관리 설정
    daily_cost_limit: float = Field(default=50.0, env="DAILY_COST_LIMIT")
    monthly_cost_limit: float = Field(default=1000.0, env="MONTHLY_COST_LIMIT")
    cost_alert_threshold: float = Field(default=0.8, env="COST_ALERT_THRESHOLD")  # 80% 도달시 알림
    
    # 모델별 비용 (USD per 1K tokens - 2024년 기준 추정치)
    cost_per_1k_tokens_nano_input: float = Field(default=0.00015, env="COST_NANO_INPUT")
    cost_per_1k_tokens_nano_output: float = Field(default=0.0006, env="COST_NANO_OUTPUT")
    cost_per_1k_tokens_mini_input: float = Field(default=0.00015, env="COST_MINI_INPUT")
    cost_per_1k_tokens_mini_output: float = Field(default=0.0006, env="COST_MINI_OUTPUT")
    cost_per_1k_tokens_gpt4_input: float = Field(default=0.01, env="COST_GPT4_INPUT")
    cost_per_1k_tokens_gpt4_output: float = Field(default=0.03, env="COST_GPT4_OUTPUT")
    cost_per_1k_tokens_gpt5_input: float = Field(default=0.005, env="COST_GPT5_INPUT")
    cost_per_1k_tokens_gpt5_output: float = Field(default=0.015, env="COST_GPT5_OUTPUT")
    cost_per_1k_tokens_o3_input: float = Field(default=0.015, env="COST_O3_INPUT")
    cost_per_1k_tokens_o3_output: float = Field(default=0.06, env="COST_O3_OUTPUT")
    
    # 사용량 추적 설정
    enable_usage_tracking: bool = Field(default=True, env="ENABLE_USAGE_TRACKING")
    usage_log_file: str = Field(default="logs/openai_usage.log", env="USAGE_LOG_FILE")
    usage_database_url: str = Field(default="", env="USAGE_DATABASE_URL")  # 별도 DB 사용시
    
    # 캐시 설정 (초 단위)
    cache_stock_price: int = 5  # 주가 데이터
    cache_market_status: int = 60  # 시장 상태
    cache_news: int = 300  # 뉴스 데이터
    cache_ai_analysis: int = 1800  # AI 분석 결과
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 전역 설정 인스턴스
settings = Settings()


def get_settings() -> Settings:
    """설정 인스턴스 반환"""
    return settings