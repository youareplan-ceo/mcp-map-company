"""
OpenAI 사용량 및 비용 관리 API 엔드포인트
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.middleware.usage_tracker import get_usage_tracker

router = APIRouter()


class UsageStatsResponse(BaseModel):
    """사용량 통계 응답 모델"""
    daily_usage: dict
    monthly_usage: dict
    current_limits: dict


class CostLimitCheckResponse(BaseModel):
    """비용 한도 체크 응답 모델"""
    can_proceed: bool
    message: str
    current_usage: dict


@router.get("/stats", response_model=UsageStatsResponse)
async def get_usage_stats(
    days: int = Query(default=7, ge=1, le=30, description="조회할 일수")
):
    """사용량 통계 조회"""
    try:
        usage_tracker = await get_usage_tracker()
        stats = await usage_tracker.get_usage_stats(days=days)
        return UsageStatsResponse(**stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"사용량 통계 조회 실패: {str(e)}")


@router.get("/cost-check", response_model=CostLimitCheckResponse)
async def check_cost_limits():
    """현재 비용 한도 상태 체크"""
    try:
        usage_tracker = await get_usage_tracker()
        can_proceed, message = await usage_tracker.check_cost_limits()
        
        # 현재 사용량 정보 포함
        current_stats = await usage_tracker.get_usage_stats(days=1)
        
        return CostLimitCheckResponse(
            can_proceed=can_proceed,
            message=message,
            current_usage=current_stats
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"비용 한도 체크 실패: {str(e)}")


@router.post("/reset-daily")
async def reset_daily_usage(
    date: Optional[str] = Query(default=None, description="초기화할 날짜 (YYYY-MM-DD), 미지정시 오늘")
):
    """일일 사용량 초기화 (관리자용)"""
    try:
        usage_tracker = await get_usage_tracker()
        await usage_tracker.reset_daily_usage(date)
        
        return {
            "message": f"일일 사용량 초기화 완료",
            "date": date or "today"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"사용량 초기화 실패: {str(e)}")


@router.get("/models/cost")
async def get_model_costs():
    """모델별 비용 정보 조회"""
    try:
        usage_tracker = await get_usage_tracker()
        
        return {
            "cost_per_1k_tokens": usage_tracker.cost_per_1k_tokens,
            "currency": "USD",
            "note": "비용은 1000 토큰당 USD 기준입니다"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모델 비용 정보 조회 실패: {str(e)}")


@router.get("/health")
async def usage_tracker_health():
    """사용량 추적기 상태 확인"""
    try:
        usage_tracker = await get_usage_tracker()
        can_proceed, message = await usage_tracker.check_cost_limits()
        
        return {
            "status": "healthy",
            "tracking_enabled": True,
            "cost_limits_ok": can_proceed,
            "message": message
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상태 확인 실패: {str(e)}")