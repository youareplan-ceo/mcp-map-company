"""
애플리케이션 설정 관리
환경변수를 통한 설정값 관리
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """
    애플리케이션 설정 클래스
    """
    # API 서버 설정
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False
    
    # 데이터베이스 설정
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "stockpilot_db"
    DB_USER: str = "stockpilot_user"
    DB_PASSWORD: str = ""
    
    # Redis 설정
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    
    # JWT 보안 설정
    SECRET_KEY: str = "your_super_secret_jwt_key_here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS 설정
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # 외부 API 키
    ALPHA_VANTAGE_API_KEY: str = ""
    IEX_CLOUD_API_KEY: str = ""
    FINNHUB_API_KEY: str = ""
    NEWS_API_KEY: str = ""
    
    # 이메일 설정
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    
    # AI 모델 설정
    MODEL_PATH: str = "./ai_engine/models/"
    USE_GPU: bool = False
    BATCH_SIZE: int = 32
    
    # 로깅 설정
    LOG_LEVEL: str = "INFO"
    
    # Celery 설정
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # 기타 설정
    ENVIRONMENT: str = "development"
    TIMEZONE: str = "US/Eastern"  # 미국 동부시간 (NYSE, NASDAQ 기준)
    DEFAULT_CURRENCY: str = "USD"  # 기본 통화를 미국 달러로 변경
    DEFAULT_MARKET: str = "US"  # 기본 시장을 미국으로 설정
    
    @property
    def database_url(self) -> str:
        """
        데이터베이스 연결 URL 생성
        """
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def redis_url(self) -> str:
        """
        Redis 연결 URL 생성
        """
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"

    class Config:
        env_file = ".env"
        case_sensitive = True


# 설정 인스턴스 생성
settings = Settings()