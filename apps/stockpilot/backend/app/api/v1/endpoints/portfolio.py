"""
포트폴리오 관리 관련 API 엔드포인트
보유 종목, 수익률, AI 추천사항 등을 처리
"""

from datetime import datetime, date
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from loguru import logger

from app.models import (
    PortfolioSummary, PortfolioHolding, PortfolioRecommendation,
    PortfolioRequest, BaseResponse
)
from app.config import get_settings
from app.services.portfolio_service import PortfolioService

router = APIRouter()
settings = get_settings()


@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    user_id: str = Query(..., description="사용자 ID")
) -> PortfolioSummary:
    """
    포트폴리오 요약 정보
    총 자산, 수익률, 오늘 수익 등
    """
    try:
        logger.info(f"포트폴리오 요약 조회: {user_id}")
        
        portfolio_service = PortfolioService()
        summary = await portfolio_service.get_portfolio_summary(user_id)
        
        return summary
        
    except Exception as e:
        logger.error(f"포트폴리오 요약 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"포트폴리오 요약 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/holdings", response_model=List[PortfolioHolding])
async def get_holdings(
    user_id: str = Query(..., description="사용자 ID"),
    include_sold: bool = Query(default=False, description="매도된 종목 포함 여부")
) -> List[PortfolioHolding]:
    """
    포트폴리오 보유 종목 목록
    """
    try:
        logger.info(f"보유 종목 조회: {user_id}")
        
        portfolio_service = PortfolioService()
        holdings = await portfolio_service.get_holdings(user_id, include_sold)
        
        logger.info(f"보유 종목 {len(holdings)}개 반환")
        return holdings
        
    except Exception as e:
        logger.error(f"보유 종목 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"보유 종목 조회 중 오류가 발생했습니다: {str(e)}")


@router.post("/holdings", response_model=BaseResponse)
async def add_holding(
    user_id: str = Query(..., description="사용자 ID"),
    symbol: str = Query(..., description="종목 코드"),
    quantity: int = Query(..., description="수량"),
    price: float = Query(..., description="매수 가격"),
    transaction_date: Optional[date] = Query(None, description="거래일 (기본값: 오늘)")
) -> BaseResponse:
    """
    포트폴리오에 종목 추가
    """
    try:
        logger.info(f"종목 추가: {user_id}, {symbol}, {quantity}주, {price}원")
        
        if quantity <= 0:
            raise HTTPException(status_code=400, detail="수량은 0보다 커야 합니다")
        if price <= 0:
            raise HTTPException(status_code=400, detail="가격은 0보다 커야 합니다")
        
        portfolio_service = PortfolioService()
        success = await portfolio_service.add_holding(
            user_id=user_id,
            symbol=symbol,
            quantity=quantity,
            price=price,
            transaction_date=transaction_date or date.today()
        )
        
        return BaseResponse(
            success=success,
            message=f"종목 추가 완료: {symbol}" if success else "종목 추가 실패"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"종목 추가 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"종목 추가 중 오류가 발생했습니다: {str(e)}")


@router.put("/holdings/{holding_id}", response_model=BaseResponse)
async def update_holding(
    holding_id: str,
    user_id: str = Query(..., description="사용자 ID"),
    quantity: Optional[int] = Query(None, description="수량"),
    average_price: Optional[float] = Query(None, description="평균 단가")
) -> BaseResponse:
    """
    보유 종목 수정
    """
    try:
        logger.info(f"종목 수정: {holding_id}, 수량: {quantity}, 단가: {average_price}")
        
        if quantity is not None and quantity <= 0:
            raise HTTPException(status_code=400, detail="수량은 0보다 커야 합니다")
        if average_price is not None and average_price <= 0:
            raise HTTPException(status_code=400, detail="평균 단가는 0보다 커야 합니다")
        
        portfolio_service = PortfolioService()
        success = await portfolio_service.update_holding(
            holding_id=holding_id,
            user_id=user_id,
            quantity=quantity,
            average_price=average_price
        )
        
        return BaseResponse(
            success=success,
            message="종목 수정 완료" if success else "종목 수정 실패"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"종목 수정 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"종목 수정 중 오류가 발생했습니다: {str(e)}")


@router.delete("/holdings/{holding_id}", response_model=BaseResponse)
async def delete_holding(
    holding_id: str,
    user_id: str = Query(..., description="사용자 ID")
) -> BaseResponse:
    """
    보유 종목 삭제
    """
    try:
        logger.info(f"종목 삭제: {holding_id}")
        
        portfolio_service = PortfolioService()
        success = await portfolio_service.delete_holding(holding_id, user_id)
        
        return BaseResponse(
            success=success,
            message="종목 삭제 완료" if success else "종목 삭제 실패"
        )
        
    except Exception as e:
        logger.error(f"종목 삭제 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"종목 삭제 중 오류가 발생했습니다: {str(e)}")


@router.get("/performance", response_model=List[dict])
async def get_portfolio_performance(
    user_id: str = Query(..., description="사용자 ID"),
    days: int = Query(default=30, ge=1, le=365, description="조회 기간 (일)")
) -> List[dict]:
    """
    포트폴리오 수익률 추이
    """
    try:
        logger.info(f"포트폴리오 수익률 조회: {user_id}, {days}일")
        
        portfolio_service = PortfolioService()
        performance = await portfolio_service.get_performance_history(user_id, days)
        
        return performance
        
    except Exception as e:
        logger.error(f"포트폴리오 수익률 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"포트폴리오 수익률 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/analysis", response_model=List[PortfolioRecommendation])
async def get_portfolio_analysis(
    user_id: str = Query(..., description="사용자 ID"),
    include_expired: bool = Query(default=False, description="만료된 분석 포함 여부")
) -> List[PortfolioRecommendation]:
    """
    포트폴리오 AI 분석 정보 (투자 권유 아님)
    리밸런싱 제안, 시장 분석, 기술적 지표 등
    """
    try:
        logger.info(f"포트폴리오 분석 조회: {user_id}")

        portfolio_service = PortfolioService()
        analysis_results = await portfolio_service.get_analysis(user_id, include_expired)

        logger.info(f"분석 결과 {len(analysis_results)}개 반환")
        return analysis_results
        
    except Exception as e:
        logger.error(f"포트폴리오 분석 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"포트폴리오 분석 조회 중 오류가 발생했습니다: {str(e)}")


@router.post("/analyze", response_model=dict)
async def analyze_portfolio(
    user_id: str = Query(..., description="사용자 ID"),
    include_risk_analysis: bool = Query(default=True, description="리스크 분석 포함"),
    include_sector_analysis: bool = Query(default=True, description="섹터 분석 포함")
):
    """
    포트폴리오 AI 분석
    리스크, 섹터 분산, 개선사항 등 종합 분석
    """
    try:
        logger.info(f"포트폴리오 AI 분석: {user_id}")
        
        portfolio_service = PortfolioService()
        analysis = await portfolio_service.analyze_portfolio(
            user_id=user_id,
            include_risk_analysis=include_risk_analysis,
            include_sector_analysis=include_sector_analysis
        )
        
        return {
            "user_id": user_id,
            "analysis": analysis,
            "generated_at": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"포트폴리오 AI 분석 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"포트폴리오 AI 분석 중 오류가 발생했습니다: {str(e)}")


@router.get("/allocation", response_model=dict)
async def get_asset_allocation(
    user_id: str = Query(..., description="사용자 ID"),
    by_sector: bool = Query(default=True, description="섹터별 분류"),
    by_market_cap: bool = Query(default=True, description="시가총액별 분류")
):
    """
    자산 배분 현황
    섹터별, 시가총액별 포트폴리오 구성
    """
    try:
        logger.info(f"자산 배분 조회: {user_id}")
        
        portfolio_service = PortfolioService()
        allocation = await portfolio_service.get_asset_allocation(
            user_id=user_id,
            by_sector=by_sector,
            by_market_cap=by_market_cap
        )
        
        return {
            "user_id": user_id,
            "allocation": allocation,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"자산 배분 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"자산 배분 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/rebalancing", response_model=dict)
async def get_rebalancing_suggestions(
    user_id: str = Query(..., description="사용자 ID"),
    target_allocation: Optional[str] = Query(None, description="목표 배분 전략")
):
    """
    리밸런싱 제안
    목표 자산 배분 대비 현재 포트폴리오 조정 방안
    """
    try:
        logger.info(f"리밸런싱 제안: {user_id}, 전략: {target_allocation}")
        
        portfolio_service = PortfolioService()
        suggestions = await portfolio_service.get_rebalancing_suggestions(
            user_id=user_id,
            target_allocation=target_allocation
        )
        
        return {
            "user_id": user_id,
            "target_allocation": target_allocation,
            "suggestions": suggestions,
            "generated_at": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"리밸런싱 제안 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"리밸런싱 제안 중 오류가 발생했습니다: {str(e)}")


@router.get("/benchmark")
async def compare_with_benchmark(
    user_id: str = Query(..., description="사용자 ID"),
    benchmark: str = Query(default="KOSPI", description="벤치마크 (KOSPI, KOSDAQ)"),
    days: int = Query(default=90, ge=7, le=365, description="비교 기간")
):
    """
    벤치마크 대비 성과 비교
    """
    try:
        logger.info(f"벤치마크 비교: {user_id}, {benchmark}, {days}일")
        
        portfolio_service = PortfolioService()
        comparison = await portfolio_service.compare_with_benchmark(
            user_id=user_id,
            benchmark=benchmark,
            days=days
        )
        
        return {
            "user_id": user_id,
            "benchmark": benchmark,
            "period_days": days,
            "comparison": comparison,
            "generated_at": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"벤치마크 비교 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"벤치마크 비교 중 오류가 발생했습니다: {str(e)}")


@router.get("/dividend")
async def get_dividend_info(
    user_id: str = Query(..., description="사용자 ID"),
    year: Optional[int] = Query(None, description="조회 연도")
):
    """
    배당금 정보
    보유 종목의 배당금 내역 및 예상 배당금
    """
    try:
        logger.info(f"배당금 정보 조회: {user_id}, 연도: {year}")
        
        portfolio_service = PortfolioService()
        dividend_info = await portfolio_service.get_dividend_info(user_id, year)
        
        return {
            "user_id": user_id,
            "year": year or datetime.now().year,
            "dividend_info": dividend_info,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"배당금 정보 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"배당금 정보 조회 중 오류가 발생했습니다: {str(e)}")