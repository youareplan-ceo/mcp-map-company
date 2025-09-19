"""
미국 주식 실시간 데이터 수집 서비스
Yahoo Finance API를 사용하여 NASDAQ, NYSE 실시간 데이터 수집
"""

import asyncio
import aiohttp
import yfinance as yf
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, asdict
import json

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class USStockQuote:
    """미국 주식 시세 데이터 클래스"""
    symbol: str
    company_name: str
    current_price: float
    change: float
    change_percent: float
    volume: int
    market_cap: Optional[float]
    pe_ratio: Optional[float]
    day_high: float
    day_low: float
    open_price: float
    previous_close: float
    avg_volume: Optional[int]
    dividend_yield: Optional[float]
    market_state: str  # REGULAR, PRE, POST, CLOSED
    currency: str = "USD"
    exchange: str = "NASDAQ/NYSE"
    updated_at: str = ""

    def __post_init__(self):
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return asdict(self)

class USStockDataService:
    """미국 주식 데이터 수집 서비스"""
    
    # 미국 주요 종목 리스트 (시가총액 기준 상위 종목들)
    MAJOR_US_STOCKS = [
        # 기술주 (Tech Giants)
        "AAPL",    # Apple Inc.
        "MSFT",    # Microsoft Corporation
        "GOOGL",   # Alphabet Inc. (Class A)
        "GOOG",    # Alphabet Inc. (Class C)
        "AMZN",    # Amazon.com Inc.
        "TSLA",    # Tesla Inc.
        "META",    # Meta Platforms Inc.
        "NVDA",    # NVIDIA Corporation
        "NFLX",    # Netflix Inc.
        "ADBE",    # Adobe Inc.
        
        # 금융주
        "JPM",     # JPMorgan Chase & Co.
        "BAC",     # Bank of America Corporation
        "WFC",     # Wells Fargo & Company
        "GS",      # Goldman Sachs Group Inc.
        
        # 산업주
        "JNJ",     # Johnson & Johnson
        "PG",      # Procter & Gamble Company
        "KO",      # Coca-Cola Company
        "PEP",     # PepsiCo Inc.
        "WMT",     # Walmart Inc.
        "HD",      # Home Depot Inc.
        
        # 에너지
        "XOM",     # Exxon Mobil Corporation
        "CVX",     # Chevron Corporation
        
        # ETF
        "SPY",     # SPDR S&P 500 ETF
        "QQQ",     # Invesco QQQ Trust ETF
        "IWM",     # iShares Russell 2000 ETF
    ]
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.cache: Dict[str, USStockQuote] = {}
        self.cache_ttl = 30  # 30초 캐시
        self.last_update: Dict[str, datetime] = {}
        
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.session:
            await self.session.close()

    def get_market_state(self) -> str:
        """현재 미국 시장 상태 반환"""
        try:
            from datetime import timezone
            import pytz
            
            # 미국 동부시간 기준
            eastern = pytz.timezone('US/Eastern')
            now_et = datetime.now(eastern)
            current_time = now_et.time()
            weekday = now_et.weekday()
            
            # 주말 체크 (토요일=5, 일요일=6)
            if weekday >= 5:
                return "CLOSED"
            
            # 장전: 04:00 - 09:30 ET
            if current_time >= datetime.strptime("04:00", "%H:%M").time() and \
               current_time < datetime.strptime("09:30", "%H:%M").time():
                return "PRE"
            
            # 정규장: 09:30 - 16:00 ET
            elif current_time >= datetime.strptime("09:30", "%H:%M").time() and \
                 current_time < datetime.strptime("16:00", "%H:%M").time():
                return "REGULAR"
            
            # 장후: 16:00 - 20:00 ET
            elif current_time >= datetime.strptime("16:00", "%H:%M").time() and \
                 current_time < datetime.strptime("20:00", "%H:%M").time():
                return "POST"
            
            else:
                return "CLOSED"
                
        except Exception as e:
            logger.error(f"시장 상태 확인 오류: {e}")
            return "UNKNOWN"

    def get_stock_info_sync(self, symbol: str) -> Optional[USStockQuote]:
        """동기 방식으로 주식 정보 조회 (yfinance 사용)"""
        try:
            # 캐시 체크
            if symbol in self.cache and symbol in self.last_update:
                cache_age = datetime.now() - self.last_update[symbol]
                if cache_age.total_seconds() < self.cache_ttl:
                    return self.cache[symbol]
            
            # yfinance로 데이터 조회
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="1d", interval="1m")
            
            if hist.empty or not info:
                logger.warning(f"데이터 없음: {symbol}")
                return None
                
            # 현재 가격 (최근 데이터에서)
            current_price = float(hist['Close'].iloc[-1])
            open_price = float(hist['Open'].iloc[0])
            day_high = float(hist['High'].max())
            day_low = float(hist['Low'].min())
            volume = int(hist['Volume'].sum())
            
            # 전일 종가
            previous_close = info.get('previousClose', current_price)
            change = current_price - previous_close
            change_percent = (change / previous_close) * 100 if previous_close > 0 else 0.0
            
            # 기본 정보
            company_name = info.get('longName', info.get('shortName', symbol))
            market_cap = info.get('marketCap', None)
            pe_ratio = info.get('forwardPE', info.get('trailingPE', None))
            avg_volume = info.get('averageVolume', None)
            dividend_yield = info.get('dividendYield', None)
            if dividend_yield:
                dividend_yield *= 100  # 퍼센트로 변환
            
            # 시장 상태
            market_state = self.get_market_state()
            
            quote = USStockQuote(
                symbol=symbol,
                company_name=company_name,
                current_price=round(current_price, 2),
                change=round(change, 2),
                change_percent=round(change_percent, 2),
                volume=volume,
                market_cap=market_cap,
                pe_ratio=round(pe_ratio, 2) if pe_ratio else None,
                day_high=round(day_high, 2),
                day_low=round(day_low, 2),
                open_price=round(open_price, 2),
                previous_close=round(previous_close, 2),
                avg_volume=avg_volume,
                dividend_yield=round(dividend_yield, 2) if dividend_yield else None,
                market_state=market_state
            )
            
            # 캐시 저장
            self.cache[symbol] = quote
            self.last_update[symbol] = datetime.now()
            
            logger.info(f"주식 데이터 조회 성공: {symbol} - ${current_price}")
            return quote
            
        except Exception as e:
            logger.error(f"주식 데이터 조회 실패 {symbol}: {e}")
            return None

    async def get_stock_info(self, symbol: str) -> Optional[USStockQuote]:
        """비동기 방식으로 주식 정보 조회"""
        # 실제로는 동기 방식을 비동기로 래핑
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_stock_info_sync, symbol)

    async def get_multiple_stocks(self, symbols: List[str]) -> List[USStockQuote]:
        """여러 종목 동시 조회"""
        tasks = [self.get_stock_info(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        quotes = []
        for result in results:
            if isinstance(result, USStockQuote):
                quotes.append(result)
            elif isinstance(result, Exception):
                logger.error(f"종목 조회 오류: {result}")
        
        return quotes

    async def get_major_stocks(self) -> List[USStockQuote]:
        """주요 미국 종목 조회"""
        return await self.get_multiple_stocks(self.MAJOR_US_STOCKS[:10])  # 상위 10개

    def get_trending_stocks(self, limit: int = 5) -> List[USStockQuote]:
        """인기 종목 조회 (거래량 기준)"""
        try:
            # 주요 종목들을 동기로 빠르게 조회
            quotes = []
            for symbol in self.MAJOR_US_STOCKS[:limit * 2]:  # 여유있게 조회
                quote = self.get_stock_info_sync(symbol)
                if quote and quote.volume > 0:
                    quotes.append(quote)
                    
            # 거래량 기준 정렬
            quotes.sort(key=lambda x: x.volume if x.volume else 0, reverse=True)
            return quotes[:limit]
            
        except Exception as e:
            logger.error(f"인기 종목 조회 오류: {e}")
            return []

    def search_stocks(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """종목 검색 (심볼 + 회사명)"""
        try:
            # 기본 리스트에서 검색
            results = []
            query_upper = query.upper()
            
            # 주요 종목에서 검색
            for symbol in self.MAJOR_US_STOCKS:
                if query_upper in symbol:
                    # 회사 정보 조회
                    try:
                        ticker = yf.Ticker(symbol)
                        info = ticker.info
                        company_name = info.get('longName', info.get('shortName', symbol))
                        
                        results.append({
                            "symbol": symbol,
                            "name": company_name,
                            "exchange": "NASDAQ/NYSE",
                            "market": "US"
                        })
                        
                        if len(results) >= limit:
                            break
                            
                    except Exception:
                        continue
            
            return results
            
        except Exception as e:
            logger.error(f"종목 검색 오류: {e}")
            return []

# 전역 인스턴스
us_stock_service = USStockDataService()

# 테스트 함수
async def test_us_stock_service():
    """미국 주식 서비스 테스트"""
    async with USStockDataService() as service:
        print("=== 미국 주식 데이터 서비스 테스트 ===")
        
        # 1. 개별 종목 조회
        print("\n1. AAPL 종목 조회:")
        aapl = await service.get_stock_info("AAPL")
        if aapl:
            print(json.dumps(aapl.to_dict(), indent=2, ensure_ascii=False))
        
        # 2. 다중 종목 조회
        print("\n2. 주요 종목 조회:")
        stocks = await service.get_multiple_stocks(["AAPL", "MSFT", "GOOGL"])
        for stock in stocks:
            print(f"{stock.symbol}: ${stock.current_price} ({stock.change_percent:+.2f}%)")
        
        # 3. 시장 상태
        print(f"\n3. 현재 시장 상태: {service.get_market_state()}")
        
        # 4. 종목 검색
        print(f"\n4. 'APP' 검색 결과:")
        search_results = service.search_stocks("APP")
        for result in search_results:
            print(f"{result['symbol']}: {result['name']}")

if __name__ == "__main__":
    asyncio.run(test_us_stock_service())