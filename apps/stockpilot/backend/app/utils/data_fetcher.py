"""
데이터 수집을 위한 API 호출 유틸리티
Yahoo Finance, 뉴스 API, 환율 API 등 외부 데이터 소스와의 통신을 담당
"""

import asyncio
import aiohttp
import yfinance as yf
import pandas as pd
import requests
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging
from urllib.parse import urlencode
import time

logger = logging.getLogger(__name__)


@dataclass
class StockData:
    """주식 데이터 구조체"""
    symbol: str
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    adjusted_close: Optional[float] = None


@dataclass
class NewsData:
    """뉴스 데이터 구조체"""
    title: str
    content: str
    source: str
    url: str
    published_at: datetime
    sentiment_score: Optional[float] = None


class DataFetcher:
    """
    외부 API를 통한 데이터 수집 클래스
    Yahoo Finance, 뉴스 API, 환율 정보 등을 수집
    """

    def __init__(self, news_api_key: Optional[str] = None):
        """
        초기화
        
        Args:
            news_api_key: 뉴스 API 키
        """
        self.news_api_key = news_api_key
        self.session = None
        self.rate_limit_delay = 0.1  # API 호출 간 지연 시간 (초)

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.session:
            await self.session.close()

    def get_stock_data(
        self, 
        symbol: str, 
        period: str = "1y", 
        interval: str = "1d"
    ) -> List[StockData]:
        """
        Yahoo Finance에서 주식 데이터 가져오기
        
        Args:
            symbol: 주식 심볼 (예: "005930.KS", "AAPL")
            period: 기간 ("1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y")
            interval: 간격 ("1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo")
            
        Returns:
            List[StockData]: 주식 데이터 리스트
        """
        try:
            logger.info(f"주식 데이터 수집 시작: {symbol}, period={period}, interval={interval}")
            
            # yfinance를 사용하여 데이터 가져오기
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)
            
            if hist.empty:
                logger.warning(f"데이터를 찾을 수 없음: {symbol}")
                return []
            
            # 데이터 변환
            stock_data_list = []
            for date, row in hist.iterrows():
                stock_data = StockData(
                    symbol=symbol,
                    date=date.to_pydatetime() if hasattr(date, 'to_pydatetime') else date,
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=int(row['Volume']),
                    adjusted_close=float(row['Close'])  # yfinance는 이미 수정주가를 제공
                )
                stock_data_list.append(stock_data)
            
            logger.info(f"주식 데이터 수집 완료: {symbol}, {len(stock_data_list)}개 레코드")
            return stock_data_list
            
        except Exception as e:
            logger.error(f"주식 데이터 수집 실패: {symbol} - {str(e)}")
            return []

    def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """
        주식 기본 정보 가져오기
        
        Args:
            symbol: 주식 심볼
            
        Returns:
            Dict: 주식 정보
        """
        try:
            logger.info(f"주식 정보 수집: {symbol}")
            
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # 필요한 정보만 추출
            stock_info = {
                'symbol': symbol,
                'name': info.get('longName', info.get('shortName', '')),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'market_cap': info.get('marketCap', 0),
                'currency': info.get('currency', 'USD'),
                'exchange': info.get('exchange', ''),
                'country': info.get('country', ''),
                'website': info.get('website', ''),
                'business_summary': info.get('longBusinessSummary', '')
            }
            
            # 한국 주식 시장 구분
            if symbol.endswith('.KS'):
                stock_info['market'] = 'KOSPI'
            elif symbol.endswith('.KQ'):
                stock_info['market'] = 'KOSDAQ'
            elif info.get('exchange') in ['NMS', 'NASDAQ']:
                stock_info['market'] = 'NASDAQ'
            elif info.get('exchange') in ['NYQ', 'NYSE']:
                stock_info['market'] = 'NYSE'
            else:
                stock_info['market'] = info.get('exchange', 'UNKNOWN')
            
            return stock_info
            
        except Exception as e:
            logger.error(f"주식 정보 수집 실패: {symbol} - {str(e)}")
            return {}

    async def get_news_data(
        self, 
        query: str, 
        language: str = "ko", 
        page_size: int = 20
    ) -> List[NewsData]:
        """
        뉴스 데이터 수집 (News API 사용)
        
        Args:
            query: 검색 쿼리
            language: 언어 코드 (ko, en)
            page_size: 페이지 크기
            
        Returns:
            List[NewsData]: 뉴스 데이터 리스트
        """
        if not self.news_api_key:
            logger.warning("뉴스 API 키가 설정되지 않음")
            return []

        try:
            logger.info(f"뉴스 데이터 수집: {query}")
            
            # News API 엔드포인트
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': query,
                'language': language,
                'sortBy': 'publishedAt',
                'pageSize': page_size,
                'apiKey': self.news_api_key
            }
            
            if not self.session:
                logger.error("aiohttp 세션이 초기화되지 않음")
                return []
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"뉴스 API 호출 실패: {response.status}")
                    return []
                
                data = await response.json()
                articles = data.get('articles', [])
                
                news_data_list = []
                for article in articles:
                    # 날짜 파싱
                    published_at_str = article.get('publishedAt', '')
                    try:
                        published_at = datetime.strptime(
                            published_at_str, 
                            "%Y-%m-%dT%H:%M:%SZ"
                        )
                    except ValueError:
                        published_at = datetime.utcnow()
                    
                    news_data = NewsData(
                        title=article.get('title', ''),
                        content=article.get('description', ''),
                        source=article.get('source', {}).get('name', ''),
                        url=article.get('url', ''),
                        published_at=published_at
                    )
                    news_data_list.append(news_data)
                
                logger.info(f"뉴스 데이터 수집 완료: {len(news_data_list)}개 기사")
                return news_data_list
                
        except Exception as e:
            logger.error(f"뉴스 데이터 수집 실패: {str(e)}")
            return []

    def get_exchange_rate(self, from_currency: str, to_currency: str) -> Optional[float]:
        """
        환율 정보 가져오기 (Yahoo Finance 사용)
        
        Args:
            from_currency: 기준 통화 (USD, KRW, EUR 등)
            to_currency: 대상 통화
            
        Returns:
            Optional[float]: 환율
        """
        try:
            # 환율 심볼 생성 (예: USDKRW=X)
            symbol = f"{from_currency}{to_currency}=X"
            
            logger.info(f"환율 정보 수집: {symbol}")
            
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            
            if hist.empty:
                logger.warning(f"환율 데이터를 찾을 수 없음: {symbol}")
                return None
            
            # 최신 종가 반환
            latest_rate = float(hist['Close'].iloc[-1])
            logger.info(f"환율 수집 완료: {from_currency}/{to_currency} = {latest_rate}")
            
            return latest_rate
            
        except Exception as e:
            logger.error(f"환율 데이터 수집 실패: {from_currency}/{to_currency} - {str(e)}")
            return None

    def get_market_index(self, index_symbol: str) -> List[StockData]:
        """
        시장 지수 데이터 가져오기
        
        Args:
            index_symbol: 지수 심볼 (^KS11, ^IXIC, ^GSPC 등)
            
        Returns:
            List[StockData]: 지수 데이터
        """
        # 주요 지수 매핑
        index_mapping = {
            'KOSPI': '^KS11',
            'KOSDAQ': '^KQ11', 
            'NASDAQ': '^IXIC',
            'SP500': '^GSPC',
            'DOW': '^DJI',
            'NIKKEI': '^N225'
        }
        
        # 심볼 변환
        if index_symbol in index_mapping:
            symbol = index_mapping[index_symbol]
        else:
            symbol = index_symbol
        
        try:
            logger.info(f"시장 지수 데이터 수집: {symbol}")
            
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1y")  # 1년 데이터
            
            if hist.empty:
                logger.warning(f"지수 데이터를 찾을 수 없음: {symbol}")
                return []
            
            # StockData 형식으로 변환
            index_data_list = []
            for date, row in hist.iterrows():
                index_data = StockData(
                    symbol=symbol,
                    date=date.to_pydatetime() if hasattr(date, 'to_pydatetime') else date,
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=int(row['Volume']) if row['Volume'] > 0 else 0
                )
                index_data_list.append(index_data)
            
            logger.info(f"지수 데이터 수집 완료: {symbol}, {len(index_data_list)}개 레코드")
            return index_data_list
            
        except Exception as e:
            logger.error(f"지수 데이터 수집 실패: {symbol} - {str(e)}")
            return []

    async def get_multiple_stocks(
        self, 
        symbols: List[str], 
        period: str = "1d",
        interval: str = "1d"
    ) -> Dict[str, List[StockData]]:
        """
        여러 종목의 주식 데이터를 동시에 가져오기
        
        Args:
            symbols: 주식 심볼 리스트
            period: 기간
            interval: 간격
            
        Returns:
            Dict[str, List[StockData]]: 종목별 데이터
        """
        try:
            logger.info(f"다중 주식 데이터 수집 시작: {len(symbols)}개 종목")
            
            # 비동기 작업을 위한 태스크 생성
            tasks = []
            for symbol in symbols:
                # 동기 함수를 비동기로 실행
                task = asyncio.create_task(
                    asyncio.to_thread(
                        self.get_stock_data, 
                        symbol, 
                        period, 
                        interval
                    )
                )
                tasks.append((symbol, task))
                
                # API 호출 제한을 위한 지연
                await asyncio.sleep(self.rate_limit_delay)
            
            # 모든 작업 완료 대기
            results = {}
            for symbol, task in tasks:
                try:
                    data = await task
                    results[symbol] = data
                except Exception as e:
                    logger.error(f"종목 {symbol} 데이터 수집 실패: {str(e)}")
                    results[symbol] = []
            
            logger.info(f"다중 주식 데이터 수집 완료: {len(results)}개 종목")
            return results
            
        except Exception as e:
            logger.error(f"다중 주식 데이터 수집 실패: {str(e)}")
            return {}

    def validate_symbol(self, symbol: str) -> bool:
        """
        주식 심볼 유효성 검사
        
        Args:
            symbol: 주식 심볼
            
        Returns:
            bool: 유효성 여부
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # 기본 정보가 있는지 확인
            return bool(info.get('symbol') or info.get('longName'))
            
        except Exception as e:
            logger.warning(f"심볼 유효성 검사 실패: {symbol} - {str(e)}")
            return False

    def get_realtime_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        실시간 주가 정보 가져오기
        
        Args:
            symbol: 주식 심볼
            
        Returns:
            Optional[Dict]: 실시간 주가 정보
        """
        try:
            logger.info(f"실시간 주가 수집: {symbol}")
            
            ticker = yf.Ticker(symbol)
            
            # 최근 1일 데이터 가져오기
            hist = ticker.history(period="1d", interval="1m")
            
            if hist.empty:
                return None
            
            # 최신 데이터 
            latest = hist.iloc[-1]
            
            # 종목 정보
            info = ticker.info
            
            realtime_data = {
                'symbol': symbol,
                'current_price': float(latest['Close']),
                'open_price': float(latest['Open']),
                'high_price': float(latest['High']),
                'low_price': float(latest['Low']),
                'volume': int(latest['Volume']),
                'timestamp': latest.name.to_pydatetime() if hasattr(latest.name, 'to_pydatetime') else latest.name,
                'previous_close': info.get('previousClose', 0),
                'change': 0,
                'change_percent': 0
            }
            
            # 변동률 계산
            if realtime_data['previous_close'] > 0:
                change = realtime_data['current_price'] - realtime_data['previous_close']
                change_percent = (change / realtime_data['previous_close']) * 100
                realtime_data['change'] = round(change, 2)
                realtime_data['change_percent'] = round(change_percent, 2)
            
            return realtime_data
            
        except Exception as e:
            logger.error(f"실시간 주가 수집 실패: {symbol} - {str(e)}")
            return None