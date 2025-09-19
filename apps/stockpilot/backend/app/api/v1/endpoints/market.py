"""
시장 관련 API 엔드포인트
한국 주식시장 상태, 지수, 시장 데이터 등을 처리
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from app.models import MarketStatus, MarketIndex, MarketType
from app.config import get_settings
from app.services.market_service import MarketService

router = APIRouter()
settings = get_settings()


@router.get("/status", response_model=MarketStatus)
async def get_market_status() -> MarketStatus:
    """
    한국 주식시장 현재 상태
    장 개장/마감 여부, 다음 개장 시간 등
    """
    try:
        logger.info("시장 상태 조회")
        
        market_service = MarketService()
        status = await market_service.get_market_status()
        
        return status
        
    except Exception as e:
        logger.error(f"시장 상태 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"시장 상태 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/indices", response_model=List[MarketIndex])
async def get_market_indices(
    indices: Optional[str] = Query(None, description="지수 목록 (쉼표로 구분, 예: KOSPI,KOSDAQ)")
) -> List[MarketIndex]:
    """
    주요 시장 지수 정보
    KOSPI, KOSDAQ 등 주요 지수 현재 값
    """
    try:
        logger.info(f"시장 지수 조회: {indices}")
        
        index_list = None
        if indices:
            index_list = [idx.strip() for idx in indices.split(",")]
        
        market_service = MarketService()
        market_indices = await market_service.get_market_indices(index_list)
        
        logger.info(f"시장 지수 {len(market_indices)}개 반환")
        return market_indices
        
    except Exception as e:
        logger.error(f"시장 지수 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"시장 지수 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/hours")
async def get_market_hours():
    """
    한국 시장 거래 시간
    정규 거래, 시간외 거래 시간 정보
    """
    try:
        logger.info("시장 거래 시간 조회")
        
        market_service = MarketService()
        hours = await market_service.get_market_hours()
        
        return {
            "market_hours": hours,
            "timezone": "Asia/Seoul",
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"시장 거래 시간 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"시장 거래 시간 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/holidays")
async def get_market_holidays(
    year: Optional[int] = Query(None, description="조회 연도 (기본값: 올해)")
):
    """
    한국 시장 휴장일
    공휴일 및 시장 휴장 일정
    """
    try:
        current_year = year or datetime.now().year
        logger.info(f"시장 휴장일 조회: {current_year}")
        
        market_service = MarketService()
        holidays = await market_service.get_market_holidays(current_year)
        
        return {
            "year": current_year,
            "holidays": holidays,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"시장 휴장일 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"시장 휴장일 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/statistics")
async def get_market_statistics(
    market: Optional[MarketType] = Query(None, description="시장 구분"),
    days: int = Query(default=30, ge=1, le=365, description="분석 기간")
):
    """
    시장 통계 정보
    거래량, 시가총액, 상장 종목 수 등
    """
    try:
        logger.info(f"시장 통계 조회: 시장={market}, 기간={days}일")
        
        market_service = MarketService()
        statistics = await market_service.get_market_statistics(market, days)
        
        return {
            "market": market,
            "period_days": days,
            "statistics": statistics,
            "generated_at": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"시장 통계 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"시장 통계 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/sectors")
async def get_sector_performance(
    market: Optional[MarketType] = Query(None, description="시장 구분"),
    period: str = Query(default="1d", description="기간 (1d, 1w, 1m, 3m, 1y)")
):
    """
    업종별 수익률
    각 업종별 주가 상승률 순위
    """
    try:
        logger.info(f"업종별 수익률 조회: 시장={market}, 기간={period}")
        
        market_service = MarketService()
        sector_performance = await market_service.get_sector_performance(market, period)
        
        return {
            "market": market,
            "period": period,
            "sector_performance": sector_performance,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"업종별 수익률 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"업종별 수익률 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/volume")
async def get_trading_volume():
    """
    시장 거래량 정보
    전체 시장 및 주요 지수별 거래량
    """
    try:
        logger.info("시장 거래량 조회")
        
        market_service = MarketService()
        volume_data = await market_service.get_trading_volume()
        
        return {
            "trading_volume": volume_data,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"시장 거래량 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"시장 거래량 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/foreign-investor")
async def get_foreign_investor_data(
    days: int = Query(default=30, ge=1, le=365, description="조회 기간")
):
    """
    외국인 투자자 동향
    외국인 순매수/매도 현황
    """
    try:
        logger.info(f"외국인 투자자 동향 조회: {days}일")
        
        market_service = MarketService()
        foreign_data = await market_service.get_foreign_investor_data(days)
        
        return {
            "period_days": days,
            "foreign_investor_data": foreign_data,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"외국인 투자자 동향 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"외국인 투자자 동향 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/institutional-investor")
async def get_institutional_investor_data(
    days: int = Query(default=30, ge=1, le=365, description="조회 기간")
):
    """
    기관 투자자 동향
    기관 투자자 순매수/매도 현황
    """
    try:
        logger.info(f"기관 투자자 동향 조회: {days}일")
        
        market_service = MarketService()
        institutional_data = await market_service.get_institutional_investor_data(days)
        
        return {
            "period_days": days,
            "institutional_investor_data": institutional_data,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"기관 투자자 동향 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"기관 투자자 동향 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/calendar")
async def get_market_calendar(
    year: Optional[int] = Query(None, description="조회 연도"),
    month: Optional[int] = Query(None, description="조회 월")
):
    """
    시장 달력
    거래일, 휴장일, 주요 이벤트 일정
    """
    try:
        current_year = year or datetime.now().year
        logger.info(f"시장 달력 조회: {current_year}년 {month}월")
        
        market_service = MarketService()
        calendar = await market_service.get_market_calendar(current_year, month)
        
        return {
            "year": current_year,
            "month": month,
            "calendar": calendar,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"시장 달력 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"시장 달력 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/economic-indicators")
async def get_economic_indicators():
    """
    경제 지표
    금리, 환율, 유가 등 주요 경제 지표
    """
    try:
        logger.info("경제 지표 조회")
        
        market_service = MarketService()
        indicators = await market_service.get_economic_indicators()
        
        return {
            "economic_indicators": indicators,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"경제 지표 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"경제 지표 조회 중 오류가 발생했습니다: {str(e)}")