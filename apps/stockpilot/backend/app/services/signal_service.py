"""
AI 시그널 서비스
투자 시그널 생성, 관리, 분석
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
import uuid

from app.models import (
    AISignal, SignalStats, InvestmentSignal, MarketType, SignalStrength,
    PaginatedResponse, StockInfo
)
from app.config import get_settings

settings = get_settings()


class SignalService:
    """AI 시그널 서비스"""
    
    def __init__(self):
        # 샘플 시그널 데이터
        self.sample_signals = self._generate_sample_signals()
        logger.info("시그널 서비스 초기화 완료")
    
    def _generate_sample_signals(self) -> List[AISignal]:
        """샘플 시그널 데이터 생성"""
        signals_data = [
            {
                "stock": ("005930.KS", "삼성전자"),
                "signal": InvestmentSignal.BUY,
                "strength": SignalStrength.HIGH,
                "confidence": 85.5,
                "current_price": 75000,
                "target_price": 85000,
                "reasoning": "반도체 시장 회복과 메모리 가격 상승으로 실적 개선 기대"
            },
            {
                "stock": ("035420.KS", "NAVER"),
                "signal": InvestmentSignal.HOLD,
                "strength": SignalStrength.MEDIUM,
                "confidence": 65.0,
                "current_price": 195000,
                "reasoning": "AI 사업 확장은 긍정적이나 단기적 불확실성 존재"
            }
        ]
        
        signals = []
        for i, data in enumerate(signals_data):
            symbol, name = data["stock"]
            
            stock_info = StockInfo(
                symbol=symbol,
                name=name,
                market=MarketType.KOSPI,
                sector="Technology"
            )
            
            signal = AISignal(
                id=str(uuid.uuid4()),
                stock=stock_info,
                signal=data["signal"],
                strength=data["strength"],
                confidence=data["confidence"],
                current_price=data["current_price"],
                target_price=data.get("target_price"),
                reasoning=data["reasoning"],
                risk_factors=[],
                catalysts=[],
                created_at=datetime.now() - timedelta(minutes=i*30)
            )
            signals.append(signal)
        
        return signals
    
    async def get_signals(
        self,
        signal_type: Optional[InvestmentSignal] = None,
        market: Optional[MarketType] = None,
        strength: Optional[SignalStrength] = None,
        min_confidence: Optional[float] = None,
        symbols: Optional[List[str]] = None,
        hours: int = 24,
        page: int = 1,
        size: int = 20
    ) -> PaginatedResponse:
        """시그널 목록 조회"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            filtered_signals = [
                signal for signal in self.sample_signals
                if signal.created_at >= cutoff_time
            ]
            
            if signal_type:
                filtered_signals = [s for s in filtered_signals if s.signal == signal_type]
            
            if strength:
                filtered_signals = [s for s in filtered_signals if s.strength == strength]
            
            if min_confidence:
                filtered_signals = [s for s in filtered_signals if s.confidence >= min_confidence]
            
            if symbols:
                filtered_signals = [s for s in filtered_signals if s.stock.symbol in symbols]
            
            total = len(filtered_signals)
            start_idx = (page - 1) * size
            end_idx = start_idx + size
            paginated_signals = filtered_signals[start_idx:end_idx]
            
            return PaginatedResponse(
                data=paginated_signals,
                total=total,
                page=page,
                size=size,
                has_next=end_idx < total
            )
            
        except Exception as e:
            logger.error(f"시그널 조회 오류: {str(e)}")
            return PaginatedResponse(data=[], total=0, page=page, size=size)
    
    async def get_recent_signals(self, minutes: int = 5) -> List[AISignal]:
        """최근 생성된 시그널 조회"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [
            signal for signal in self.sample_signals
            if signal.created_at >= cutoff_time
        ]