"""
대시보드 관련 API 엔드포인트
메인 대시보드에 표시할 요약 데이터 제공
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from app.models import DashboardSummary
from app.config import get_settings
from app.services.dashboard_service import DashboardService

router = APIRouter()
settings = get_settings()


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    user_id: Optional[str] = Query(None, description="사용자 ID (포트폴리오 정보 포함)")
) -> DashboardSummary:
    """
    대시보드 요약 정보
    시장 상태, 지수, 인기 종목, 최근 시그널, 뉴스 등 종합 정보
    """
    try:
        logger.info(f"대시보드 요약 조회: 사용자={user_id}")
        
        dashboard_service = DashboardService()
        summary = await dashboard_service.get_dashboard_summary(user_id)
        
        return summary
        
    except Exception as e:
        logger.error(f"대시보드 요약 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"대시보드 요약 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/quick-stats")
async def get_quick_stats():
    """
    빠른 통계 정보
    주요 지표들의 간단한 요약
    """
    try:
        logger.info("빠른 통계 조회")
        
        dashboard_service = DashboardService()
        quick_stats = await dashboard_service.get_quick_stats()
        
        return {
            "quick_stats": quick_stats,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"빠른 통계 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"빠른 통계 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/market-overview")
async def get_market_overview():
    """
    시장 개요
    현재 시장 상황에 대한 종합적인 정보
    """
    try:
        logger.info("시장 개요 조회")
        
        dashboard_service = DashboardService()
        market_overview = await dashboard_service.get_market_overview()
        
        return {
            "market_overview": market_overview,
            "generated_at": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"시장 개요 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"시장 개요 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/personalized")
async def get_personalized_dashboard(
    user_id: str = Query(..., description="사용자 ID")
):
    """
    개인화된 대시보드
    사용자의 포트폴리오와 관심사에 맞춘 정보
    """
    try:
        logger.info(f"개인화된 대시보드 조회: {user_id}")
        
        dashboard_service = DashboardService()
        personalized_data = await dashboard_service.get_personalized_dashboard(user_id)
        
        return {
            "user_id": user_id,
            "personalized_data": personalized_data,
            "generated_at": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"개인화된 대시보드 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"개인화된 대시보드 조회 중 오류가 발생했습니다: {str(e)}")