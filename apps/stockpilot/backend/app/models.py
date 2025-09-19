"""
Pydantic 모델 정의
API 요청/응답 데이터 구조 및 검증
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

# 헬스체크 모델 import
from app.models.health_models import *


# 열거형 정의
class InvestmentSignal(str, Enum):
    """투자 시그널 타입"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class MarketType(str, Enum):
    """시장 구분"""
    KOSPI = "KOSPI"
    KOSDAQ = "KOSDAQ"
    KONEX = "KONEX"


class NewsSentiment(str, Enum):
    """뉴스 감정 분석 결과"""
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"


class SignalStrength(str, Enum):
    """시그널 강도"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class NewsCategory(str, Enum):
    """뉴스 카테고리"""
    MARKET = "MARKET"
    ECONOMY = "ECONOMY"
    CORPORATE = "CORPORATE"
    POLICY = "POLICY"
    INTERNATIONAL = "INTERNATIONAL"


# 기본 응답 모델
class BaseResponse(BaseModel):
    """기본 응답 형식"""
    success: bool = True
    message: str = "OK"
    timestamp: datetime = Field(default_factory=datetime.now)


class PaginatedResponse(BaseModel):
    """페이지네이션 응답"""
    data: List[Any]
    total: int
    page: int = 1
    size: int = 20
    has_next: bool = False


# 주식 관련 모델
class StockInfo(BaseModel):
    """기본 주식 정보"""
    symbol: str = Field(..., description="종목 코드 (예: 005930.KS)")
    name: str = Field(..., description="종목명")
    market: MarketType = Field(..., description="시장 구분")
    sector: Optional[str] = Field(None, description="업종")
    current_price: Optional[float] = Field(None, description="현재가")
    currency: str = Field(default="KRW", description="통화")


class StockPrice(BaseModel):
    """주식 가격 정보"""
    symbol: str
    current_price: float
    change_amount: float
    change_rate: float
    volume: int
    market_cap: Optional[float] = None
    timestamp: datetime


class StockSearchResult(StockInfo):
    """주식 검색 결과"""
    change_rate: Optional[float] = None
    volume: Optional[int] = None


class TechnicalIndicator(BaseModel):
    """기술적 지표"""
    name: str
    value: float
    signal: InvestmentSignal
    description: str


class AIAnalysis(BaseModel):
    """AI 분석 결과"""
    symbol: str
    signal: InvestmentSignal
    confidence: float = Field(..., ge=0, le=100, description="신뢰도 (0-100)")
    target_price: Optional[float] = None
    reasoning: str = Field(..., description="분석 근거")
    technical_indicators: List[TechnicalIndicator] = []
    risk_level: str = Field(..., description="리스크 수준")
    time_horizon: str = Field(..., description="투자 기간 추천")
    created_at: datetime = Field(default_factory=datetime.now)


# 시장 관련 모델
class MarketStatus(BaseModel):
    """시장 상태"""
    is_open: bool
    current_time: datetime
    next_open: Optional[datetime] = None
    next_close: Optional[datetime] = None
    timezone: str = "Asia/Seoul"
    trading_session: str  # "PRE_MARKET", "MARKET_HOURS", "AFTER_HOURS", "CLOSED"


class MarketIndex(BaseModel):
    """시장 지수"""
    name: str
    symbol: str
    value: float
    change_amount: float
    change_rate: float
    timestamp: datetime


# 포트폴리오 관련 모델
class PortfolioHolding(BaseModel):
    """포트폴리오 보유 종목"""
    id: str
    stock: StockInfo
    quantity: int
    average_price: float
    current_value: float
    unrealized_pnl: float
    unrealized_pnl_rate: float
    purchase_date: date


class PortfolioSummary(BaseModel):
    """포트폴리오 요약"""
    total_value: float
    total_investment: float
    total_pnl: float
    total_pnl_rate: float
    today_pnl: float
    today_pnl_rate: float
    holdings_count: int
    cash_balance: float = 0


class PortfolioRecommendation(BaseModel):
    """포트폴리오 추천사항"""
    type: str  # "BUY", "SELL", "REBALANCE"
    title: str
    description: str
    confidence: float
    expected_return: Optional[float] = None
    risk_level: str
    created_at: datetime


# AI 시그널 관련 모델
class AISignal(BaseModel):
    """AI 투자 시그널"""
    id: str
    stock: StockInfo
    signal: InvestmentSignal
    strength: SignalStrength
    confidence: float = Field(..., ge=0, le=100)
    current_price: float
    target_price: Optional[float] = None
    expected_return: Optional[float] = None
    reasoning: str
    risk_factors: List[str] = []
    catalysts: List[str] = []
    created_at: datetime
    expires_at: Optional[datetime] = None


class SignalStats(BaseModel):
    """시그널 통계"""
    total_signals: int
    buy_signals: int
    sell_signals: int
    hold_signals: int
    average_confidence: float
    period: str


# 뉴스 관련 모델
class NewsArticle(BaseModel):
    """뉴스 기사"""
    id: str
    title: str
    summary: str
    content: Optional[str] = None
    url: str
    source: str
    author: Optional[str] = None
    published_at: datetime
    sentiment: NewsSentiment
    sentiment_score: float = Field(..., ge=-1, le=1)
    category: NewsCategory
    related_stocks: List[StockInfo] = []
    impact_score: Optional[float] = Field(None, ge=0, le=10)
    keywords: List[str] = []
    image_url: Optional[str] = None


class TrendingKeyword(BaseModel):
    """트렌딩 키워드"""
    word: str
    count: int
    sentiment: NewsSentiment
    related_stocks: List[str] = []


# 대시보드 관련 모델
class DashboardSummary(BaseModel):
    """대시보드 요약 데이터"""
    market_status: MarketStatus
    market_indices: List[MarketIndex]
    trending_stocks: List[Dict[str, Any]]
    recent_signals: List[AISignal]
    latest_news: List[NewsArticle]
    portfolio_summary: Optional[PortfolioSummary] = None


# WebSocket 메시지 모델
class WebSocketMessage(BaseModel):
    """WebSocket 메시지"""
    type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)


class PriceUpdateMessage(BaseModel):
    """실시간 가격 업데이트 메시지"""
    type: str = "price_update"
    symbol: str
    price: float
    change_amount: float
    change_rate: float
    volume: int
    timestamp: datetime


# API 요청 모델
class StockAnalysisRequest(BaseModel):
    """주식 분석 요청"""
    symbol: str = Field(..., description="종목 코드")
    analysis_type: str = Field(default="comprehensive", description="분석 유형")
    include_news: bool = Field(default=True, description="뉴스 분석 포함 여부")


class SignalRequest(BaseModel):
    """시그널 조회 요청"""
    signal_type: Optional[InvestmentSignal] = None
    market: Optional[MarketType] = None
    strength: Optional[SignalStrength] = None
    min_confidence: Optional[float] = Field(None, ge=0, le=100)
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class NewsRequest(BaseModel):
    """뉴스 조회 요청"""
    category: Optional[NewsCategory] = None
    sentiment: Optional[NewsSentiment] = None
    symbols: Optional[List[str]] = None
    hours: int = Field(default=24, ge=1, le=168, description="최근 몇 시간")
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class PortfolioRequest(BaseModel):
    """포트폴리오 요청"""
    action: str  # "add", "update", "remove"
    symbol: Optional[str] = None
    quantity: Optional[int] = None
    price: Optional[float] = None


# 설정 모델
class APIConfig(BaseModel):
    """API 설정"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }
    )