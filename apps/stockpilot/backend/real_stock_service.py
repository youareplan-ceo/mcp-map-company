"""
실제 주식 데이터 연동 서비스 - Yahoo Finance API 사용
실시간 주가, 차트 데이터, 기업 정보 제공
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import logging
from dataclasses import dataclass
import asyncio
import aiohttp
import time

# 심플한 메모리 캐시
_cache = {}
_cache_expiry = 60  # 60초 캐시

@dataclass
class RealStockData:
    """실제 주식 데이터 구조체"""
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    volume: int
    market_cap: Optional[float]
    pe_ratio: Optional[float]
    high_52w: Optional[float]
    low_52w: Optional[float]
    dividend_yield: Optional[float]
    timestamp: str

@dataclass
class ChartData:
    """차트 데이터 구조체"""
    timestamps: List[str]
    prices: List[float]
    volumes: List[int]
    period: str

class RealStockService:
    """실제 주식 데이터 서비스"""
    
    def __init__(self):
        # 주요 미국 주식 심볼 리스트
        self.popular_symbols = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA',
            'META', 'NVDA', 'NFLX', 'BABA', 'V',
            'JPM', 'JNJ', 'WMT', 'PG', 'UNH',
            'DIS', 'ADBE', 'PYPL', 'INTC', 'CRM'
        ]
        
        # 한국 주요 주식 심볼 (KRX)
        self.korean_symbols = [
            '005930.KS',  # 삼성전자
            '000660.KS',  # SK하이닉스
            '035420.KS',  # NAVER
            '005380.KS',  # 현대차
            '068270.KS',  # 셀트리온
            '035720.KS',  # 카카오
            '051910.KS',  # LG화학
            '006400.KS',  # 삼성SDI
            '028260.KS',  # 삼성물산
            '012330.KS'   # 현대모비스
        ]
        
        self.logger = logging.getLogger(__name__)
        
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """캐시에서 데이터 조회"""
        if key in _cache:
            timestamp, data = _cache[key]
            if time.time() - timestamp < _cache_expiry:
                return data
        return None
    
    def _set_cache(self, key: str, data: Any):
        """캐시에 데이터 저장"""
        _cache[key] = (time.time(), data)
    
    def get_stock_data(self, symbol: str) -> Optional[RealStockData]:
        """개별 종목 실시간 데이터 조회"""
        try:
            # 캐시 확인
            cache_key = f"stock_{symbol}"
            cached_data = self._get_from_cache(cache_key)
            if cached_data:
                return cached_data
            
            # yfinance 티커 생성 (세션 없이)
            ticker = yf.Ticker(symbol)
            
            # 기본 정보 조회
            info = ticker.info
            history = ticker.history(period="1d", interval="1m")
            
            if history.empty:
                return None
                
            # 최신 가격 정보
            latest_price = history['Close'].iloc[-1]
            previous_close = info.get('previousClose', latest_price)
            
            change = latest_price - previous_close
            change_percent = (change / previous_close) * 100 if previous_close > 0 else 0
            
            # 회사명 추출
            company_name = info.get('longName', info.get('shortName', symbol))
            
            stock_data = RealStockData(
                symbol=symbol,
                name=company_name,
                price=float(latest_price),
                change=float(change),
                change_percent=float(change_percent),
                volume=int(history['Volume'].iloc[-1]),
                market_cap=info.get('marketCap'),
                pe_ratio=info.get('trailingPE'),
                high_52w=info.get('fiftyTwoWeekHigh'),
                low_52w=info.get('fiftyTwoWeekLow'),
                dividend_yield=info.get('dividendYield'),
                timestamp=datetime.now().isoformat()
            )
            
            # 캐시에 저장
            self._set_cache(cache_key, stock_data)
            return stock_data
            
        except Exception as e:
            self.logger.error(f"주식 데이터 조회 실패 - {symbol}: {e}")
            return None
    
    def get_multiple_stocks(self, symbols: List[str]) -> List[RealStockData]:
        """다중 종목 데이터 조회"""
        results = []
        for symbol in symbols:
            stock_data = self.get_stock_data(symbol)
            if stock_data:
                results.append(stock_data)
        return results
    
    def get_trending_stocks(self, limit: int = 10) -> List[RealStockData]:
        """인기 종목 조회"""
        # 미국 주요 종목 조회
        us_stocks = self.get_multiple_stocks(self.popular_symbols[:limit//2])
        # 한국 주요 종목 조회
        kr_stocks = self.get_multiple_stocks(self.korean_symbols[:limit//2])
        
        all_stocks = us_stocks + kr_stocks
        
        # 변동률 기준으로 정렬
        return sorted(all_stocks, key=lambda x: abs(x.change_percent), reverse=True)[:limit]
    
    def get_chart_data(self, symbol: str, period: str = "1d", interval: str = "5m") -> Optional[ChartData]:
        """차트 데이터 조회"""
        try:
            ticker = yf.Ticker(symbol)
            
            # 기간별 매핑
            period_map = {
                "1d": "1d",
                "1w": "5d", 
                "1m": "1mo",
                "3m": "3mo",
                "6m": "6mo",
                "1y": "1y"
            }
            
            # 인터벌 매핑
            interval_map = {
                "1d": "5m",
                "1w": "30m",
                "1m": "1d",
                "3m": "1d",
                "6m": "1d", 
                "1y": "1wk"
            }
            
            yf_period = period_map.get(period, "1d")
            yf_interval = interval_map.get(period, "5m")
            
            history = ticker.history(period=yf_period, interval=yf_interval)
            
            if history.empty:
                return None
            
            # 타임스탬프와 가격 데이터 추출
            timestamps = [ts.isoformat() for ts in history.index]
            prices = history['Close'].tolist()
            volumes = history['Volume'].astype(int).tolist()
            
            return ChartData(
                timestamps=timestamps,
                prices=prices,
                volumes=volumes,
                period=period
            )
            
        except Exception as e:
            self.logger.error(f"차트 데이터 조회 실패 - {symbol}: {e}")
            return None
    
    def search_stocks(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """종목 검색"""
        try:
            # 기본 검색 - 일부 주요 종목만 지원
            search_results = []
            
            # 미국 주식 검색
            for symbol in self.popular_symbols:
                if query.upper() in symbol or (query.lower() in self._get_company_name(symbol).lower()):
                    stock_data = self.get_stock_data(symbol)
                    if stock_data:
                        search_results.append({
                            'symbol': stock_data.symbol,
                            'name': stock_data.name,
                            'price': stock_data.price,
                            'change': stock_data.change,
                            'change_percent': stock_data.change_percent
                        })
            
            # 한국 주식 검색
            for symbol in self.korean_symbols:
                if query.upper() in symbol or (query.lower() in self._get_company_name(symbol).lower()):
                    stock_data = self.get_stock_data(symbol)
                    if stock_data:
                        search_results.append({
                            'symbol': stock_data.symbol,
                            'name': stock_data.name,
                            'price': stock_data.price,
                            'change': stock_data.change,
                            'change_percent': stock_data.change_percent
                        })
            
            return search_results[:limit]
            
        except Exception as e:
            self.logger.error(f"종목 검색 실패 - {query}: {e}")
            return []
    
    def _get_company_name(self, symbol: str) -> str:
        """회사명 조회 (캐시된 버전)"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return info.get('longName', info.get('shortName', symbol))
        except:
            return symbol
    
    def get_market_summary(self) -> Dict[str, Any]:
        """시장 현황 요약"""
        try:
            # 주요 지수 조회
            indices = {
                'SPY': 'S&P 500',
                '^IXIC': 'NASDAQ',
                '^DJI': 'Dow Jones',
                '^KS11': 'KOSPI',
                '^KQ11': 'KOSDAQ'
            }
            
            market_data = {}
            
            for symbol, name in indices.items():
                try:
                    ticker = yf.Ticker(symbol)
                    history = ticker.history(period="1d")
                    
                    if not history.empty:
                        latest_price = history['Close'].iloc[-1]
                        previous_close = ticker.info.get('previousClose', latest_price)
                        change = latest_price - previous_close
                        change_percent = (change / previous_close) * 100 if previous_close > 0 else 0
                        
                        market_data[symbol] = {
                            'name': name,
                            'price': float(latest_price),
                            'change': float(change),
                            'change_percent': float(change_percent)
                        }
                except Exception as e:
                    self.logger.error(f"지수 데이터 조회 실패 - {symbol}: {e}")
                    continue
            
            return {
                'timestamp': datetime.now().isoformat(),
                'indices': market_data
            }
            
        except Exception as e:
            self.logger.error(f"시장 현황 조회 실패: {e}")
            return {}

# 전역 서비스 인스턴스
real_stock_service = RealStockService()

# 테스트 함수
def test_real_stock_service():
    """실제 데이터 서비스 테스트"""
    print("🔥 실제 주식 데이터 서비스 테스트")
    
    # 1. 개별 종목 조회
    print("\n1. Apple 주식 데이터:")
    apple_data = real_stock_service.get_stock_data('AAPL')
    if apple_data:
        print(f"   종목: {apple_data.name} ({apple_data.symbol})")
        print(f"   현재가: ${apple_data.price:.2f}")
        print(f"   변동: ${apple_data.change:.2f} ({apple_data.change_percent:.2f}%)")
        print(f"   거래량: {apple_data.volume:,}")
    
    # 2. 인기 종목 조회
    print("\n2. 인기 종목:")
    trending = real_stock_service.get_trending_stocks(5)
    for i, stock in enumerate(trending, 1):
        print(f"   {i}. {stock.name} ({stock.symbol}): ${stock.price:.2f} ({stock.change_percent:+.2f}%)")
    
    # 3. 차트 데이터 조회
    print("\n3. TSLA 차트 데이터:")
    chart_data = real_stock_service.get_chart_data('TSLA', '1d')
    if chart_data:
        print(f"   데이터 포인트: {len(chart_data.prices)}개")
        print(f"   최신 가격: ${chart_data.prices[-1]:.2f}")
    
    # 4. 시장 현황
    print("\n4. 시장 현황:")
    market_summary = real_stock_service.get_market_summary()
    if market_summary.get('indices'):
        for symbol, data in market_summary['indices'].items():
            print(f"   {data['name']}: {data['price']:.2f} ({data['change_percent']:+.2f}%)")

if __name__ == "__main__":
    test_real_stock_service()