"""
한국 주식 데이터 서비스
KOSPI, KOSDAQ 실시간 데이터 수집 및 처리
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, asdict

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class KRStockQuote:
    """한국 주식 시세 데이터 클래스"""
    symbol: str  # 종목코드 (예: 005930)
    company_name: str  # 회사명 (예: 삼성전자)
    market: str  # 시장구분 (KOSPI, KOSDAQ)
    current_price: float  # 현재가
    change: float  # 등락폭
    change_percent: float  # 등락률(%)
    volume: int  # 거래량
    value: int  # 거래대금
    open_price: float  # 시가
    high_price: float  # 고가
    low_price: float  # 저가
    prev_close: float  # 전일종가
    market_cap: Optional[int] = None  # 시가총액
    per: Optional[float] = None  # PER
    pbr: Optional[float] = None  # PBR
    dividend_yield: Optional[float] = None  # 배당수익률
    currency: str = "KRW"
    timestamp: str = ""
    market_state: str = "UNKNOWN"  # OPEN, CLOSED, PRE_MARKET, AFTER_HOURS
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return asdict(self)

class KRStockDataService:
    """한국 주식 데이터 서비스"""
    
    # 주요 한국 주식 종목 목록
    MAJOR_STOCKS = {
        "005930": "삼성전자",
        "000660": "SK하이닉스", 
        "035420": "NAVER",
        "051910": "LG화학",
        "035720": "카카오",
        "006400": "삼성SDI",
        "028260": "삼성물산",
        "096770": "SK이노베이션",
        "105560": "KB금융",
        "055550": "신한지주",
        "017670": "SK텔레콤",
        "030200": "KT",
        "012330": "현대모비스",
        "015760": "한국전력",
        "009150": "삼성전기"
    }
    
    # KOSPI/KOSDAQ 지수 코드
    INDICES = {
        "KOSPI": "코스피",
        "KOSDAQ": "코스닥",
        "KQ100": "코스닥100",
        "KRX100": "KRX100"
    }
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'StockPilot-KR/1.0'}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.session:
            await self.session.close()
    
    def _determine_market_state(self) -> str:
        """한국 시장 상태 판단"""
        now = datetime.now()
        current_time = now.time()
        weekday = now.weekday()
        
        # 주말 체크
        if weekday >= 5:  # 토요일(5), 일요일(6)
            return "CLOSED"
        
        # 한국 시장 시간 (09:00 ~ 15:30)
        market_open = datetime.strptime("09:00", "%H:%M").time()
        market_close = datetime.strptime("15:30", "%H:%M").time()
        
        if market_open <= current_time <= market_close:
            return "OPEN"
        elif current_time < market_open:
            return "PRE_MARKET"
        else:
            return "AFTER_HOURS"
    
    def _generate_mock_stock_data(self, symbol: str) -> KRStockQuote:
        """한국 주식 Mock 데이터 생성"""
        import random
        
        company_name = self.MAJOR_STOCKS.get(symbol, f"한국종목{symbol}")
        base_price = random.randint(50000, 500000)  # 5만원 ~ 50만원
        change_pct = random.uniform(-3.0, 3.0)
        change = base_price * (change_pct / 100)
        current_price = base_price + change
        
        return KRStockQuote(
            symbol=symbol,
            company_name=company_name,
            market="KOSPI" if symbol in ["005930", "000660", "051910"] else "KOSDAQ",
            current_price=current_price,
            change=change,
            change_percent=change_pct,
            volume=random.randint(100000, 10000000),
            value=int(current_price * random.randint(100000, 10000000)),
            open_price=base_price + random.uniform(-20000, 20000),
            high_price=current_price + random.uniform(0, 30000),
            low_price=current_price - random.uniform(0, 30000),
            prev_close=base_price,
            market_cap=int(current_price * random.randint(10000000, 1000000000)),
            per=random.uniform(5.0, 30.0),
            pbr=random.uniform(0.5, 5.0),
            dividend_yield=random.uniform(0.5, 4.0),
            market_state=self._determine_market_state()
        )
    
    async def get_stock_info(self, symbol: str) -> Optional[KRStockQuote]:
        """개별 종목 정보 조회"""
        try:
            logger.debug(f"한국 주식 데이터 조회: {symbol}")
            
            # TODO: 실제 API 연동 시 여기서 구현
            # 현재는 Mock 데이터 사용
            stock_data = self._generate_mock_stock_data(symbol)
            
            logger.info(f"한국 주식 데이터 조회 성공: {symbol} - {stock_data.current_price:,.0f}원")
            return stock_data
            
        except Exception as e:
            logger.error(f"한국 주식 데이터 조회 실패 {symbol}: {e}")
            return None
    
    async def get_multiple_stocks(self, symbols: List[str]) -> List[KRStockQuote]:
        """여러 종목 정보 동시 조회"""
        tasks = [self.get_stock_info(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        stocks = []
        for result in results:
            if isinstance(result, KRStockQuote):
                stocks.append(result)
            elif isinstance(result, Exception):
                logger.error(f"주식 데이터 조회 오류: {result}")
        
        return stocks
    
    async def get_major_stocks(self) -> List[KRStockQuote]:
        """주요 종목 조회"""
        symbols = list(self.MAJOR_STOCKS.keys())[:10]  # 상위 10개
        return await self.get_multiple_stocks(symbols)
    
    async def get_kospi_stocks(self) -> List[KRStockQuote]:
        """KOSPI 주요 종목 조회"""
        kospi_symbols = ["005930", "000660", "035420", "051910", "035720", "006400"]
        return await self.get_multiple_stocks(kospi_symbols)
    
    async def get_kosdaq_stocks(self) -> List[KRStockQuote]:
        """KOSDAQ 주요 종목 조회"""
        kosdaq_symbols = ["035720", "096770", "028260"]
        stocks = await self.get_multiple_stocks(kosdaq_symbols)
        # KOSDAQ으로 마켓 변경
        for stock in stocks:
            stock.market = "KOSDAQ"
        return stocks
    
    def _generate_mock_index_data(self, index_code: str) -> Dict[str, Any]:
        """한국 지수 Mock 데이터 생성"""
        import random
        
        index_name = self.INDICES.get(index_code, index_code)
        
        if index_code == "KOSPI":
            base_value = random.uniform(2400, 2600)
        elif index_code == "KOSDAQ":
            base_value = random.uniform(800, 900)
        else:
            base_value = random.uniform(1000, 1200)
        
        change_pct = random.uniform(-1.5, 1.5)
        change = base_value * (change_pct / 100)
        current_value = base_value + change
        
        return {
            "index_code": index_code,
            "index_name": index_name,
            "current_value": round(current_value, 2),
            "change": round(change, 2),
            "change_percent": round(change_pct, 2),
            "volume": random.randint(100000000, 1000000000),
            "value": random.randint(10000000000, 50000000000),
            "market_state": self._determine_market_state(),
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_indices(self) -> List[Dict[str, Any]]:
        """한국 주요 지수 조회"""
        try:
            indices = []
            for index_code in self.INDICES.keys():
                index_data = self._generate_mock_index_data(index_code)
                indices.append(index_data)
                
            logger.info(f"한국 지수 조회 완료: {len(indices)}개")
            return indices
            
        except Exception as e:
            logger.error(f"한국 지수 조회 실패: {e}")
            return []
    
    def get_market_status(self) -> Dict[str, Any]:
        """한국 시장 상태 조회"""
        market_state = self._determine_market_state()
        now = datetime.now()
        
        return {
            "market": "KR",
            "state": market_state,
            "local_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "timezone": "Asia/Seoul",
            "next_open": self._get_next_market_open(),
            "trading_day": now.weekday() < 5,
            "description": self._get_market_description(market_state)
        }
    
    def _get_next_market_open(self) -> str:
        """다음 시장 개장 시간 계산"""
        now = datetime.now()
        
        # 오늘이 금요일이거나 주말이면 다음 월요일 09:00
        if now.weekday() >= 4:  # 금요일(4), 토요일(5), 일요일(6)
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0:  # 일요일인 경우
                days_until_monday = 1
            next_monday = now + timedelta(days=days_until_monday)
            return next_monday.replace(hour=9, minute=0, second=0, microsecond=0).isoformat()
        
        # 평일이면 오늘 09:00 (이미 지났다면 내일 09:00)
        today_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if now > today_open:
            tomorrow_open = today_open + timedelta(days=1)
            return tomorrow_open.isoformat()
        else:
            return today_open.isoformat()
    
    def _get_market_description(self, state: str) -> str:
        """시장 상태 설명"""
        descriptions = {
            "OPEN": "한국 시장 개장 중 (09:00-15:30)",
            "CLOSED": "한국 시장 폐장",
            "PRE_MARKET": "한국 시장 개장 전",
            "AFTER_HOURS": "한국 시장 폐장 후"
        }
        return descriptions.get(state, "알 수 없는 상태")

# 테스트 함수
async def test_kr_stock_service():
    """한국 주식 서비스 테스트"""
    print("=== 한국 주식 데이터 서비스 테스트 ===")
    
    async with KRStockDataService() as service:
        # 1. 개별 종목 조회
        print("\n1. 삼성전자 주식 정보:")
        samsung = await service.get_stock_info("005930")
        if samsung:
            print(json.dumps(samsung.to_dict(), indent=2, ensure_ascii=False))
        
        # 2. 주요 종목들
        print("\n2. 주요 종목들:")
        major_stocks = await service.get_major_stocks()
        for stock in major_stocks:
            print(f"{stock.company_name}({stock.symbol}): {stock.current_price:,.0f}원 ({stock.change_percent:+.1f}%)")
        
        # 3. 한국 지수
        print("\n3. 한국 주요 지수:")
        indices = await service.get_indices()
        for index in indices:
            print(f"{index['index_name']}: {index['current_value']:.2f} ({index['change_percent']:+.1f}%)")
        
        # 4. 시장 상태
        print(f"\n4. 한국 시장 상태:")
        market_status = service.get_market_status()
        print(json.dumps(market_status, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(test_kr_stock_service())