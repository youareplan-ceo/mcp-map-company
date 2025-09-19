#!/usr/bin/env python3
"""
Offline Mock Service Provider
오프라인 프리뷰 모드용 모의 서비스 제공자
"""

import json
import os
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class MockService:
    def __init__(self):
        self.base_path = Path(__file__).parent / "mocks"
        self.offline_mode = os.getenv("OFFLINE_MODE", "false").lower() == "true"
        self._data_cache = {}
        
        if self.offline_mode:
            logger.info("🔴 OFFLINE-MOCK: Mock Service initialized")
        
    def _load_mock_data(self, filename: str) -> Dict[str, Any]:
        """모의 데이터 파일 로드"""
        if filename in self._data_cache:
            return self._data_cache[filename]
            
        file_path = self.base_path / filename
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._data_cache[filename] = data
                logger.info(f"🔴 OFFLINE-MOCK: Loaded {filename}")
                return data
        except Exception as e:
            logger.error(f"❌ Failed to load mock data {filename}: {e}")
            return {}
    
    def get_stock_prices(self, symbols: List[str] = None) -> Dict[str, Any]:
        """주식 가격 정보 반환"""
        if not self.offline_mode:
            return {}
            
        logger.info(f"🔴 OFFLINE-MOCK: get_stock_prices called for {symbols}")
        data = self._load_mock_data("prices_snapshot.json")
        
        if not symbols:
            return data
            
        # 요청된 심볼만 필터링
        filtered_data = {"markets": {"kr": {"stocks": []}, "us": {"stocks": []}}}
        
        for market in ["kr", "us"]:
            if market in data.get("markets", {}):
                market_data = data["markets"][market]
                filtered_stocks = [
                    stock for stock in market_data.get("stocks", [])
                    if stock.get("symbol") in symbols
                ]
                filtered_data["markets"][market] = {
                    **market_data,
                    "stocks": filtered_stocks
                }
        
        return filtered_data
    
    def get_news_sentiment(self, limit: int = 10) -> Dict[str, Any]:
        """뉴스 및 감성 분석 정보 반환"""
        if not self.offline_mode:
            return {}
            
        logger.info(f"🔴 OFFLINE-MOCK: get_news_sentiment called (limit={limit})")
        data = self._load_mock_data("news_snapshot.json")
        
        if limit and limit < len(data.get("news_articles", [])):
            data["news_articles"] = data["news_articles"][:limit]
        
        return data
    
    def get_portfolio_data(self) -> Dict[str, Any]:
        """포트폴리오 데이터 반환"""
        if not self.offline_mode:
            return {}
            
        logger.info("🔴 OFFLINE-MOCK: get_portfolio_data called")
        
        # CSV 파일을 JSON으로 변환
        csv_path = self.base_path / "portfolio_example.csv"
        try:
            import pandas as pd
            df = pd.read_csv(csv_path)
            
            portfolio_data = {
                "timestamp": "2025-09-12T13:30:00.000000",
                "total_value": df["market_value"].sum(),
                "total_cost": (df["quantity"] * df["avg_cost"]).sum(),
                "total_pnl": df["unrealized_pnl"].sum(),
                "holdings": df.to_dict("records"),
                "summary": {
                    "total_holdings": len(df),
                    "positive_pnl_count": len(df[df["unrealized_pnl"] > 0]),
                    "negative_pnl_count": len(df[df["unrealized_pnl"] < 0]),
                    "top_holding": df.loc[df["market_value"].idxmax(), "name"],
                    "best_performer": df.loc[df["unrealized_pnl"].idxmax(), "name"],
                    "worst_performer": df.loc[df["unrealized_pnl"].idxmin(), "name"]
                }
            }
            
            return portfolio_data
            
        except Exception as e:
            logger.error(f"❌ Failed to process portfolio CSV: {e}")
            return {"error": "Portfolio data unavailable in offline mode"}
    
    def get_ai_signals(self) -> List[Dict[str, Any]]:
        """AI 시그널 정보 반환"""
        if not self.offline_mode:
            return []
            
        logger.info("🔴 OFFLINE-MOCK: get_ai_signals called")
        
        signals = [
            {
                "id": "mock_signal_001",
                "symbol": "005930",
                "name": "삼성전자",
                "signal_type": "buy",
                "confidence": 0.85,
                "price_target": 75000,
                "current_price": 71500,
                "reasoning": "3분기 반도체 수요 회복과 AI 시장 성장으로 인한 상승 전망",
                "generated_at": "2025-09-12T13:30:00",
                "expires_at": "2025-09-15T13:30:00"
            },
            {
                "id": "mock_signal_002",
                "symbol": "NVDA",
                "name": "NVIDIA Corp",
                "signal_type": "strong_buy", 
                "confidence": 0.92,
                "price_target": 480.00,
                "current_price": 436.58,
                "reasoning": "AI 칩 수요 급증과 데이터센터 시장 확대로 인한 강력한 성장 모멘텀",
                "generated_at": "2025-09-12T13:25:00",
                "expires_at": "2025-09-15T13:25:00"
            },
            {
                "id": "mock_signal_003",
                "symbol": "TSLA",
                "name": "Tesla Inc",
                "signal_type": "hold",
                "confidence": 0.65,
                "price_target": 250.00,
                "current_price": 248.50,
                "reasoning": "자율주행 기술 지연 우려가 있으나 중장기 전망은 여전히 긍정적",
                "generated_at": "2025-09-12T13:20:00",
                "expires_at": "2025-09-15T13:20:00"
            }
        ]
        
        return signals
    
    def search_stocks(self, query: str) -> List[Dict[str, Any]]:
        """주식 검색 결과 반환"""
        if not self.offline_mode:
            return []
            
        logger.info(f"🔴 OFFLINE-MOCK: search_stocks called with query='{query}'")
        
        # 가격 데이터에서 검색
        data = self._load_mock_data("prices_snapshot.json")
        results = []
        
        query_lower = query.lower()
        
        for market in ["kr", "us"]:
            if market in data.get("markets", {}):
                for stock in data["markets"][market].get("stocks", []):
                    symbol = stock.get("symbol", "").lower()
                    name = stock.get("name", "").lower()
                    
                    if query_lower in symbol or query_lower in name:
                        results.append({
                            "symbol": stock.get("symbol"),
                            "name": stock.get("name"),
                            "price": stock.get("price"),
                            "change_percent": stock.get("change_percent"),
                            "market": market
                        })
        
        return results[:10]  # 최대 10개 결과 반환
    
    def get_dashboard_widgets(self) -> Dict[str, Any]:
        """대시보드 위젯 데이터 반환"""
        if not self.offline_mode:
            return {}
            
        logger.info("🔴 OFFLINE-MOCK: get_dashboard_widgets called")
        
        # 여러 소스 데이터를 결합
        prices = self._load_mock_data("prices_snapshot.json")
        news = self._load_mock_data("news_snapshot.json")
        portfolio = self.get_portfolio_data()
        signals = self.get_ai_signals()
        
        dashboard = {
            "timestamp": "2025-09-12T13:30:00.000000",
            "market_summary": {
                "indices": prices.get("indices", {}),
                "exchange_rates": prices.get("exchange_rates", {}),
                "market_status": {
                    "kr": "closed",
                    "us": "pre_market"
                }
            },
            "portfolio_summary": {
                "total_value": portfolio.get("total_value", 0),
                "total_pnl": portfolio.get("total_pnl", 0),
                "holdings_count": portfolio.get("summary", {}).get("total_holdings", 0)
            },
            "news_highlights": news.get("news_articles", [])[:3],
            "ai_signals": signals[:3],
            "trending_stocks": [
                {"symbol": "005930", "name": "삼성전자", "change_percent": 0.70},
                {"symbol": "NVDA", "name": "NVIDIA", "change_percent": 2.94},
                {"symbol": "035420", "name": "NAVER", "change_percent": 1.93}
            ],
            "watermark": "OFFLINE PREVIEW"
        }
        
        return dashboard

# 전역 인스턴스
mock_service = MockService()