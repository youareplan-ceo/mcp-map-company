"""ì¸ô¬$ D¤ - 0ø l"""
from app.models import PortfolioSummary
from typing import List

class PortfolioService:
    async def get_portfolio_summary(self, user_id: str) -> PortfolioSummary:
        return PortfolioSummary(
            total_value=10000000,
            total_investment=9500000,
            total_pnl=500000,
            total_pnl_rate=5.26,
            today_pnl=25000,
            today_pnl_rate=0.25,
            holdings_count=5
        )
    
    async def get_holdings(self, user_id: str, include_sold: bool = False) -> List:
        return []