"""
주식 관련 API 엔드포인트
종목 검색, 주가 정보, AI 분석 등을 처리
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from loguru import logger

from app.models import (
    StockInfo, StockPrice, StockSearchResult, AIAnalysis, TechnicalIndicator,
    InvestmentSignal, MarketType, BaseResponse, StockAnalysisRequest
)
from app.config import get_settings
from app.services.stock_service import StockService
from app.services.ai_service import AIService

router = APIRouter()
settings = get_settings()


@router.get("/search", response_model=List[StockSearchResult])
async def search_stocks(
    q: str = Query(..., description="검색어 (종목명 또는 코드)"),
    market: Optional[MarketType] = Query(None, description="시장 필터"),
    limit: int = Query(default=20, ge=1, le=50, description="결과 개수")
) -> List[StockSearchResult]:
    """
    종목 검색
    한국어 종목명과 종목 코드로 검색 지원
    """
    try:
        logger.info(f"종목 검색 요청: {q}, 시장: {market}, 제한: {limit}")
        
        stock_service = StockService()
        results = await stock_service.search_stocks(
            query=q,
            market=market,
            limit=limit
        )
        
        logger.info(f"검색 결과 {len(results)}개 반환")
        return results
        
    except Exception as e:
        logger.error(f"종목 검색 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"종목 검색 중 오류가 발생했습니다: {str(e)}")


@router.get("/{symbol}/info", response_model=StockInfo)
async def get_stock_info(
    symbol: str,
    include_price: bool = Query(default=True, description="현재가 포함 여부")
) -> StockInfo:
    """
    종목 기본 정보 조회
    """
    try:
        logger.info(f"종목 정보 조회: {symbol}")
        
        stock_service = StockService()
        stock_info = await stock_service.get_stock_info(symbol, include_price)
        
        if not stock_info:
            raise HTTPException(status_code=404, detail=f"종목을 찾을 수 없습니다: {symbol}")
        
        return stock_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"종목 정보 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"종목 정보 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/{symbol}/price", response_model=StockPrice)
async def get_stock_price(symbol: str) -> StockPrice:
    """
    실시간 주가 정보 조회
    """
    try:
        logger.info(f"주가 정보 조회: {symbol}")
        
        stock_service = StockService()
        price_info = await stock_service.get_current_price(symbol)
        
        if not price_info:
            raise HTTPException(status_code=404, detail=f"주가 정보를 찾을 수 없습니다: {symbol}")
        
        return price_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"주가 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"주가 조회 중 오류가 발생했습니다: {str(e)}")


@router.post("/{symbol}/analysis", response_model=AIAnalysis)
async def get_ai_analysis(
    symbol: str,
    request: Optional[StockAnalysisRequest] = None
) -> AIAnalysis:
    """
    종목 AI 분석
    기술적 분석, 뉴스 감정분석, GPT 기반 투자 추천
    """
    try:
        logger.info(f"AI 분석 요청: {symbol}")
        
        # 기본 요청 객체 생성
        if not request:
            request = StockAnalysisRequest(symbol=symbol)
        
        # AI 서비스를 통한 종합 분석
        ai_service = AIService()
        analysis = await ai_service.analyze_stock(
            symbol=symbol,
            include_news=request.include_news,
            analysis_type=request.analysis_type
        )
        
        logger.info(f"AI 분석 완료: {symbol}, 시그널: {analysis.signal}")
        return analysis
        
    except Exception as e:
        logger.error(f"AI 분석 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI 분석 중 오류가 발생했습니다: {str(e)}")


@router.get("/{symbol}/technical", response_model=List[TechnicalIndicator])
async def get_technical_indicators(symbol: str) -> List[TechnicalIndicator]:
    """
    기술적 지표 조회
    RSI, MACD, 볼린저 밴드 등 주요 기술적 지표
    """
    try:
        logger.info(f"기술적 지표 조회: {symbol}")
        
        stock_service = StockService()
        indicators = await stock_service.get_technical_indicators(symbol)
        
        return indicators
        
    except Exception as e:
        logger.error(f"기술적 지표 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"기술적 지표 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/{symbol}/chart")
async def get_chart_data(
    symbol: str,
    period: str = Query(default="1d", description="기간 (1d, 5d, 1mo, 3mo, 6mo, 1y)"),
    interval: str = Query(default="1h", description="간격 (1m, 5m, 15m, 30m, 1h, 1d)")
):
    """
    차트 데이터 조회
    """
    try:
        logger.info(f"차트 데이터 조회: {symbol}, 기간: {period}, 간격: {interval}")
        
        stock_service = StockService()
        chart_data = await stock_service.get_chart_data(
            symbol=symbol,
            period=period,
            interval=interval
        )
        
        return {"data": chart_data, "symbol": symbol, "period": period, "interval": interval}
        
    except Exception as e:
        logger.error(f"차트 데이터 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"차트 데이터 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/trending", response_model=List[StockSearchResult])
async def get_trending_stocks(
    market: Optional[MarketType] = Query(None, description="시장 필터"),
    limit: int = Query(default=20, ge=1, le=50, description="결과 개수")
) -> List[StockSearchResult]:
    """
    인기 종목 조회
    거래량, 상승률 기준 인기 종목
    """
    try:
        logger.info(f"인기 종목 조회: 시장={market}, 제한={limit}")
        
        stock_service = StockService()
        trending = await stock_service.get_trending_stocks(market=market, limit=limit)
        
        return trending
        
    except Exception as e:
        logger.error(f"인기 종목 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"인기 종목 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/movers")
async def get_market_movers(
    direction: str = Query(default="gainers", description="방향 (gainers, losers)"),
    market: Optional[MarketType] = Query(None, description="시장 필터"),
    limit: int = Query(default=20, ge=1, le=50, description="결과 개수")
):
    """
    상승/하락 종목 조회
    """
    try:
        logger.info(f"상승/하락 종목 조회: 방향={direction}, 시장={market}")
        
        stock_service = StockService()
        movers = await stock_service.get_market_movers(
            direction=direction,
            market=market,
            limit=limit
        )
        
        return {"direction": direction, "market": market, "data": movers}
        
    except Exception as e:
        logger.error(f"상승/하락 종목 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"상승/하락 종목 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/sectors")
async def get_sector_performance():
    """
    업종별 수익률 조회
    """
    try:
        logger.info("업종별 수익률 조회")
        
        stock_service = StockService()
        sectors = await stock_service.get_sector_performance()
        
        return {"data": sectors, "timestamp": datetime.now()}
        
    except Exception as e:
        logger.error(f"업종별 수익률 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"업종별 수익률 조회 중 오류가 발생했습니다: {str(e)}")