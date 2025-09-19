"""
실시간 환율 처리 시스템
USD/KRW 환율 데이터 수집 및 변환 서비스
"""

import asyncio
import aiohttp
import yfinance as yf
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, asdict
import json

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ExchangeRate:
    """환율 데이터 클래스"""
    from_currency: str
    to_currency: str
    rate: float
    change: float
    change_percent: float
    updated_at: str
    source: str = "Yahoo Finance"
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return asdict(self)

class CurrencyExchangeService:
    """환율 서비스"""
    
    # 지원 통화 쌍
    SUPPORTED_PAIRS = {
        "USD/KRW": "USDKRW=X",  # 달러/원
        "KRW/USD": "USDKRW=X",  # 원/달러 (역산)
        "EUR/USD": "EURUSD=X",  # 유로/달러
        "GBP/USD": "GBPUSD=X",  # 파운드/달러
        "JPY/USD": "JPYUSD=X",  # 엔/달러
    }
    
    def __init__(self):
        self.cache: Dict[str, ExchangeRate] = {}
        self.cache_ttl = 300  # 5분 캐시
        self.last_update: Dict[str, datetime] = {}
        
    def get_yahoo_symbol(self, from_currency: str, to_currency: str) -> Optional[str]:
        """Yahoo Finance 환율 심볼 반환"""
        pair_key = f"{from_currency}/{to_currency}"
        return self.SUPPORTED_PAIRS.get(pair_key)

    def get_exchange_rate_sync(self, from_currency: str, to_currency: str) -> Optional[ExchangeRate]:
        """동기 방식 환율 조회"""
        try:
            # 같은 통화면 1.0 반환
            if from_currency == to_currency:
                return ExchangeRate(
                    from_currency=from_currency,
                    to_currency=to_currency,
                    rate=1.0,
                    change=0.0,
                    change_percent=0.0,
                    updated_at=datetime.now().isoformat()
                )
            
            # 캐시 체크
            cache_key = f"{from_currency}/{to_currency}"
            if cache_key in self.cache and cache_key in self.last_update:
                cache_age = datetime.now() - self.last_update[cache_key]
                if cache_age.total_seconds() < self.cache_ttl:
                    return self.cache[cache_key]
            
            # Yahoo Finance 심볼 조회
            yahoo_symbol = self.get_yahoo_symbol(from_currency, to_currency)
            if not yahoo_symbol:
                logger.warning(f"지원하지 않는 통화 쌍: {from_currency}/{to_currency}")
                return None
            
            # yfinance로 환율 데이터 조회
            ticker = yf.Ticker(yahoo_symbol)
            hist = ticker.history(period="2d", interval="1d")
            info = ticker.info
            
            if hist.empty:
                logger.warning(f"환율 데이터 없음: {yahoo_symbol}")
                return None
            
            # 현재 환율 (최근 종가)
            current_rate = float(hist['Close'].iloc[-1])
            
            # 전일 대비 변화
            if len(hist) > 1:
                previous_rate = float(hist['Close'].iloc[-2])
                change = current_rate - previous_rate
                change_percent = (change / previous_rate) * 100 if previous_rate > 0 else 0.0
            else:
                change = 0.0
                change_percent = 0.0
            
            # KRW/USD의 경우 역산 처리
            if from_currency == "KRW" and to_currency == "USD":
                current_rate = 1.0 / current_rate
                change = -change / (current_rate * current_rate)
                change_percent = -change_percent
            
            exchange_rate = ExchangeRate(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=round(current_rate, 4),
                change=round(change, 4),
                change_percent=round(change_percent, 2),
                updated_at=datetime.now().isoformat()
            )
            
            # 캐시 저장
            self.cache[cache_key] = exchange_rate
            self.last_update[cache_key] = datetime.now()
            
            logger.info(f"환율 조회 성공: {from_currency}/{to_currency} = {current_rate:.4f}")
            return exchange_rate
            
        except Exception as e:
            logger.error(f"환율 조회 실패 {from_currency}/{to_currency}: {e}")
            return None

    async def get_exchange_rate(self, from_currency: str, to_currency: str) -> Optional[ExchangeRate]:
        """비동기 방식 환율 조회"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_exchange_rate_sync, from_currency, to_currency)

    def convert_amount(self, amount: float, from_currency: str, to_currency: str) -> Optional[Dict[str, Any]]:
        """금액 환율 변환"""
        try:
            rate_info = self.get_exchange_rate_sync(from_currency, to_currency)
            if not rate_info:
                return None
            
            converted_amount = amount * rate_info.rate
            
            return {
                "original_amount": amount,
                "original_currency": from_currency,
                "converted_amount": round(converted_amount, 2),
                "converted_currency": to_currency,
                "exchange_rate": rate_info.rate,
                "conversion_time": rate_info.updated_at
            }
            
        except Exception as e:
            logger.error(f"금액 변환 실패: {e}")
            return None

    async def convert_amount_async(self, amount: float, from_currency: str, to_currency: str) -> Optional[Dict[str, Any]]:
        """비동기 금액 환율 변환"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.convert_amount, amount, from_currency, to_currency)

    def get_major_rates(self) -> List[ExchangeRate]:
        """주요 환율 조회"""
        try:
            major_pairs = ["USD/KRW", "EUR/USD", "GBP/USD"]
            rates = []
            
            for pair in major_pairs:
                from_curr, to_curr = pair.split("/")
                rate = self.get_exchange_rate_sync(from_curr, to_curr)
                if rate:
                    rates.append(rate)
            
            return rates
            
        except Exception as e:
            logger.error(f"주요 환율 조회 오류: {e}")
            return []

    async def get_major_rates_async(self) -> List[ExchangeRate]:
        """비동기 주요 환율 조회"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_major_rates)

    def format_currency_display(self, amount: float, currency: str, 
                              show_krw: bool = False) -> Dict[str, str]:
        """통화 표시 포맷팅"""
        try:
            # 기본 표시
            if currency == "USD":
                formatted = f"${amount:,.2f}"
            elif currency == "KRW":
                formatted = f"₩{amount:,.0f}"
            else:
                formatted = f"{amount:,.2f} {currency}"
            
            result = {"primary": formatted}
            
            # KRW 병행 표시 요청시
            if show_krw and currency == "USD":
                krw_conversion = self.convert_amount(amount, "USD", "KRW")
                if krw_conversion:
                    krw_amount = krw_conversion["converted_amount"]
                    result["secondary"] = f"₩{krw_amount:,.0f}"
            elif show_krw and currency == "KRW":
                usd_conversion = self.convert_amount(amount, "KRW", "USD")
                if usd_conversion:
                    usd_amount = usd_conversion["converted_amount"]
                    result["secondary"] = f"${usd_amount:,.2f}"
            
            return result
            
        except Exception as e:
            logger.error(f"통화 포맷팅 오류: {e}")
            return {"primary": f"{amount} {currency}"}

# 전역 인스턴스
currency_service = CurrencyExchangeService()

# 테스트 함수
async def test_currency_service():
    """환율 서비스 테스트"""
    service = CurrencyExchangeService()
    
    print("=== 환율 서비스 테스트 ===")
    
    # 1. USD/KRW 환율 조회
    print("\n1. USD/KRW 환율:")
    usd_krw = await service.get_exchange_rate("USD", "KRW")
    if usd_krw:
        print(json.dumps(usd_krw.to_dict(), indent=2, ensure_ascii=False))
    
    # 2. KRW/USD 환율 조회 (역산)
    print("\n2. KRW/USD 환율:")
    krw_usd = await service.get_exchange_rate("KRW", "USD")
    if krw_usd:
        print(json.dumps(krw_usd.to_dict(), indent=2, ensure_ascii=False))
    
    # 3. 금액 변환
    print("\n3. 금액 변환 (100 USD → KRW):")
    conversion = await service.convert_amount_async(100, "USD", "KRW")
    if conversion:
        print(json.dumps(conversion, indent=2, ensure_ascii=False))
    
    # 4. 주요 환율
    print("\n4. 주요 환율:")
    major_rates = await service.get_major_rates_async()
    for rate in major_rates:
        print(f"{rate.from_currency}/{rate.to_currency}: {rate.rate:.4f} ({rate.change_percent:+.2f}%)")
    
    # 5. 통화 표시 포맷팅
    print("\n5. 통화 표시 포맷:")
    usd_format = service.format_currency_display(1234.56, "USD", show_krw=True)
    print(f"USD: {usd_format}")
    
    krw_format = service.format_currency_display(1500000, "KRW", show_krw=True)
    print(f"KRW: {krw_format}")

if __name__ == "__main__":
    asyncio.run(test_currency_service())