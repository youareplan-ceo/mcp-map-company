"""
AI 투자 시그널 관련 API 엔드포인트
실시간 매수/매도 신호, 시그널 통계 등을 처리
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from loguru import logger

from app.models import (
    AISignal, SignalStats, InvestmentSignal, MarketType, SignalStrength,
    PaginatedResponse, SignalRequest
)
from app.config import get_settings
from app.services.signal_service import SignalService

router = APIRouter()
settings = get_settings()


@router.get("/", response_model=PaginatedResponse)
async def get_signals(
    signal_type: Optional[InvestmentSignal] = Query(None, description="시그널 타입 필터"),
    market: Optional[MarketType] = Query(None, description="시장 필터"),
    strength: Optional[SignalStrength] = Query(None, description="강도 필터"),
    min_confidence: Optional[float] = Query(None, ge=0, le=100, description="최소 신뢰도"),
    symbols: Optional[str] = Query(None, description="종목 필터 (쉼표로 구분)"),
    hours: int = Query(default=24, ge=1, le=168, description="최근 몇 시간"),
    page: int = Query(default=1, ge=1, description="페이지 번호"),
    size: int = Query(default=20, ge=1, le=100, description="페이지 크기")
) -> PaginatedResponse:
    """
    AI 투자 시그널 목록 조회
    다양한 필터 옵션으로 시그널 검색
    """
    try:
        logger.info(f"시그널 목록 조회 - 타입: {signal_type}, 시장: {market}, 페이지: {page}")
        
        # 필터 파라미터 구성
        symbol_list = None
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(",")]
        
        signal_service = SignalService()
        result = await signal_service.get_signals(
            signal_type=signal_type,
            market=market,
            strength=strength,
            min_confidence=min_confidence,
            symbols=symbol_list,
            hours=hours,
            page=page,
            size=size
        )
        
        logger.info(f"시그널 {len(result.data)}개 반환 (전체 {result.total}개)")
        return result
        
    except Exception as e:
        logger.error(f"시그널 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"시그널 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/{signal_id}", response_model=AISignal)
async def get_signal_detail(signal_id: str) -> AISignal:
    """
    특정 시그널 상세 정보 조회
    """
    try:
        logger.info(f"시그널 상세 조회: {signal_id}")
        
        signal_service = SignalService()
        signal = await signal_service.get_signal_by_id(signal_id)
        
        if not signal:
            raise HTTPException(status_code=404, detail=f"시그널을 찾을 수 없습니다: {signal_id}")
        
        return signal
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"시그널 상세 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"시그널 상세 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/stats/summary", response_model=SignalStats)
async def get_signal_stats(
    period: str = Query(default="1d", description="통계 기간 (1d, 3d, 1w, 1m)"),
    market: Optional[MarketType] = Query(None, description="시장 필터")
) -> SignalStats:
    """
    시그널 통계 조회
    기간별 시그널 분포 및 성과 통계
    """
    try:
        logger.info(f"시그널 통계 조회 - 기간: {period}, 시장: {market}")
        
        signal_service = SignalService()
        stats = await signal_service.get_signal_stats(period=period, market=market)
        
        return stats
        
    except Exception as e:
        logger.error(f"시그널 통계 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"시그널 통계 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/performance/accuracy")
async def get_signal_accuracy(
    days: int = Query(default=30, ge=1, le=365, description="분석 기간 (일)"),
    signal_type: Optional[InvestmentSignal] = Query(None, description="시그널 타입")
):
    """
    시그널 정확도 분석
    과거 시그널의 실제 수익률 대비 정확도
    """
    try:
        logger.info(f"시그널 정확도 분석 - 기간: {days}일, 타입: {signal_type}")
        
        signal_service = SignalService()
        accuracy = await signal_service.analyze_signal_accuracy(
            days=days,
            signal_type=signal_type
        )
        
        return {
            "period_days": days,
            "signal_type": signal_type,
            "accuracy_data": accuracy,
            "generated_at": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"시그널 정확도 분석 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"시그널 정확도 분석 중 오류가 발생했습니다: {str(e)}")


@router.get("/watchlist/{user_id}")
async def get_user_watchlist(
    user_id: str,
    include_signals: bool = Query(default=True, description="최근 시그널 포함 여부")
):
    """
    사용자 관심 종목 시그널 조회
    """
    try:
        logger.info(f"관심 종목 시그널 조회: {user_id}")
        
        signal_service = SignalService()
        watchlist_signals = await signal_service.get_watchlist_signals(
            user_id=user_id,
            include_signals=include_signals
        )
        
        return {
            "user_id": user_id,
            "watchlist": watchlist_signals,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"관심 종목 시그널 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"관심 종목 시그널 조회 중 오류가 발생했습니다: {str(e)}")


@router.post("/watchlist/{user_id}")
async def update_watchlist(
    user_id: str,
    symbols: List[str],
    action: str = Query(..., description="액션 (add, remove, replace)")
):
    """
    관심 종목 업데이트
    """
    try:
        logger.info(f"관심 종목 업데이트: {user_id}, 액션: {action}, 종목: {symbols}")
        
        if action not in ["add", "remove", "replace"]:
            raise HTTPException(status_code=400, detail="유효하지 않은 액션입니다")
        
        signal_service = SignalService()
        result = await signal_service.update_watchlist(
            user_id=user_id,
            symbols=symbols,
            action=action
        )
        
        return {
            "user_id": user_id,
            "action": action,
            "symbols": symbols,
            "success": result,
            "timestamp": datetime.now()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관심 종목 업데이트 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"관심 종목 업데이트 중 오류가 발생했습니다: {str(e)}")


@router.get("/alerts/{user_id}")
async def get_signal_alerts(user_id: str):
    """
    사용자 시그널 알림 설정 조회
    """
    try:
        logger.info(f"시그널 알림 조회: {user_id}")
        
        signal_service = SignalService()
        alerts = await signal_service.get_user_alerts(user_id)
        
        return {
            "user_id": user_id,
            "alerts": alerts,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"시그널 알림 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"시그널 알림 조회 중 오류가 발생했습니다: {str(e)}")


@router.post("/alerts/{user_id}")
async def create_signal_alert(
    user_id: str,
    symbol: str,
    signal_type: InvestmentSignal,
    min_confidence: float = Query(..., ge=0, le=100)
):
    """
    시그널 알림 생성
    """
    try:
        logger.info(f"시그널 알림 생성: {user_id}, {symbol}, {signal_type}")
        
        signal_service = SignalService()
        alert_id = await signal_service.create_alert(
            user_id=user_id,
            symbol=symbol,
            signal_type=signal_type,
            min_confidence=min_confidence
        )
        
        return {
            "alert_id": alert_id,
            "user_id": user_id,
            "symbol": symbol,
            "signal_type": signal_type,
            "min_confidence": min_confidence,
            "created_at": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"시그널 알림 생성 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"시그널 알림 생성 중 오류가 발생했습니다: {str(e)}")


@router.get("/backtest/{symbol}")
async def backtest_signals(
    symbol: str,
    days: int = Query(default=90, ge=7, le=365, description="백테스트 기간"),
    initial_capital: float = Query(default=1000000, description="초기 투자금액")
):
    """
    시그널 백테스트
    과거 시그널 기반 투자 시뮬레이션
    """
    try:
        logger.info(f"시그널 백테스트: {symbol}, 기간: {days}일")
        
        signal_service = SignalService()
        backtest_result = await signal_service.run_backtest(
            symbol=symbol,
            days=days,
            initial_capital=initial_capital
        )
        
        return {
            "symbol": symbol,
            "period_days": days,
            "initial_capital": initial_capital,
            "backtest_result": backtest_result,
            "generated_at": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"시그널 백테스트 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"시그널 백테스트 중 오류가 발생했습니다: {str(e)}")