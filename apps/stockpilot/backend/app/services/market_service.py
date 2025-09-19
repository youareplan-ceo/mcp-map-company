"""시장 서비스 - 기본 구현"""
from app.models import MarketStatus, MarketIndex
from datetime import datetime

class MarketService:
    async def get_market_status(self) -> MarketStatus:
        return MarketStatus(
            is_open=True,
            current_time=datetime.now(),
            trading_session="MARKET_HOURS"
        )