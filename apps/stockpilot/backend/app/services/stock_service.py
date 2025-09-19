"""
주식 데이터 서비스
Yahoo Finance API를 통한 한국 주식 데이터 수집 및 처리
"""

import yfinance as yf
import pandas as pd
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
import asyncio
import aiohttp

from app.models import (
    StockInfo, StockPrice, StockSearchResult, TechnicalIndicator,
    MarketType, InvestmentSignal
)
from app.config import get_settings

settings = get_settings()


class StockService:
    """주식 데이터 서비스"""
    
    def __init__(self):
        # 한국 주요 종목 매핑 (예시)
        self.korean_stocks = {
            "삼성전자": "005930.KS",
            "SK하이닉스": "000660.KS", 
            "NAVER": "035420.KS",
            "카카오": "035720.KS",
            "LG화학": "051910.KS",
            "삼성SDI": "006400.KS",
            "현대차": "005380.KS",
            "기아": "000270.KS",
            "POSCO홀딩스": "005490.KS",
            "LG전자": "066570.KS"
        }
        
        # 역방향 매핑
        self.symbol_to_name = {v: k for k, v in self.korean_stocks.items()}
        
        logger.info("주식 서비스 초기화 완료")
    
    def _get_market_type(self, symbol: str) -> MarketType:
        """종목 코드로 시장 구분 판단"""
        if symbol.endswith('.KS'):
            return MarketType.KOSPI
        elif symbol.endswith('.KQ'):
            return MarketType.KOSDAQ
        else:
            return MarketType.KOSPI  # 기본값
    
    def _normalize_symbol(self, symbol: str) -> str:
        """종목 코드 정규화"""
        # 한국어 종목명을 코드로 변환
        if symbol in self.korean_stocks:
            return self.korean_stocks[symbol]
        
        # 이미 올바른 형식인지 확인
        if not (symbol.endswith('.KS') or symbol.endswith('.KQ')):
            # 숫자로만 구성된 경우 .KS 추가
            if symbol.isdigit() and len(symbol) == 6:
                return f"{symbol}.KS"
        
        return symbol
    
    async def search_stocks(
        self, 
        query: str, 
        market: Optional[MarketType] = None, 
        limit: int = 20
    ) -> List[StockSearchResult]:
        """종목 검색"""
        try:
            results = []
            
            # 한국어 이름으로 검색
            for name, symbol in self.korean_stocks.items():
                if query.lower() in name.lower() or query in symbol:
                    # 시장 필터 적용
                    stock_market = self._get_market_type(symbol)
                    if market and stock_market != market:
                        continue
                    
                    try:
                        # Yahoo Finance에서 데이터 조회
                        ticker = yf.Ticker(symbol)
                        info = ticker.info
                        hist = ticker.history(period="1d")
                        
                        if not hist.empty:
                            current_price = hist['Close'].iloc[-1]
                            prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
                            change_rate = ((current_price - prev_close) / prev_close) * 100
                            volume = int(hist['Volume'].iloc[-1])
                            
                            result = StockSearchResult(
                                symbol=symbol,
                                name=name,
                                market=stock_market,
                                sector=info.get('sector', 'Unknown'),
                                current_price=float(current_price),
                                change_rate=float(change_rate),
                                volume=volume,
                                currency="KRW"
                            )
                            results.append(result)
                            
                    except Exception as e:
                        logger.error(f"종목 데이터 조회 실패: {symbol}, {str(e)}")
                        # 기본 정보만으로 결과 생성
                        result = StockSearchResult(
                            symbol=symbol,
                            name=name,
                            market=stock_market,
                            sector="Unknown",
                            currency="KRW"
                        )
                        results.append(result)
            
            # 코드로도 검색
            if query.isdigit() or '.' in query:
                normalized_symbol = self._normalize_symbol(query)
                if normalized_symbol not in [r.symbol for r in results]:
                    try:
                        ticker = yf.Ticker(normalized_symbol)
                        info = ticker.info
                        hist = ticker.history(period="1d")
                        
                        if not hist.empty:
                            name = self.symbol_to_name.get(normalized_symbol, info.get('longName', normalized_symbol))
                            stock_market = self._get_market_type(normalized_symbol)
                            
                            if not market or stock_market == market:
                                current_price = hist['Close'].iloc[-1]
                                prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
                                change_rate = ((current_price - prev_close) / prev_close) * 100
                                volume = int(hist['Volume'].iloc[-1])
                                
                                result = StockSearchResult(
                                    symbol=normalized_symbol,
                                    name=name,
                                    market=stock_market,
                                    sector=info.get('sector', 'Unknown'),
                                    current_price=float(current_price),
                                    change_rate=float(change_rate),
                                    volume=volume,
                                    currency="KRW"
                                )
                                results.append(result)
                    
                    except Exception as e:
                        logger.error(f"코드 검색 실패: {normalized_symbol}, {str(e)}")
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"종목 검색 오류: {str(e)}")
            return []
    
    async def get_stock_info(self, symbol: str, include_price: bool = True) -> Optional[StockInfo]:
        """종목 기본 정보 조회"""
        try:
            normalized_symbol = self._normalize_symbol(symbol)
            ticker = yf.Ticker(normalized_symbol)
            info = ticker.info
            
            # 한국어 이름 우선 사용
            name = self.symbol_to_name.get(normalized_symbol, info.get('longName', normalized_symbol))
            market = self._get_market_type(normalized_symbol)
            
            current_price = None
            if include_price:
                try:
                    hist = ticker.history(period="1d")
                    if not hist.empty:
                        current_price = float(hist['Close'].iloc[-1])
                except Exception as e:
                    logger.error(f"가격 조회 실패: {normalized_symbol}, {str(e)}")
            
            stock_info = StockInfo(
                symbol=normalized_symbol,
                name=name,
                market=market,
                sector=info.get('sector', 'Unknown'),
                current_price=current_price,
                currency="KRW"
            )
            
            return stock_info
            
        except Exception as e:
            logger.error(f"종목 정보 조회 오류: {symbol}, {str(e)}")
            return None
    
    async def get_current_price(self, symbol: str) -> Optional[StockPrice]:
        """현재 주가 정보 조회"""
        try:
            normalized_symbol = self._normalize_symbol(symbol)
            ticker = yf.Ticker(normalized_symbol)
            hist = ticker.history(period="2d")  # 전일 대비 계산을 위해 2일
            
            if hist.empty:
                return None
            
            current_price = float(hist['Close'].iloc[-1])
            volume = int(hist['Volume'].iloc[-1])
            
            # 전일 대비 계산
            if len(hist) > 1:
                prev_close = float(hist['Close'].iloc[-2])
                change_amount = current_price - prev_close
                change_rate = (change_amount / prev_close) * 100
            else:
                change_amount = 0
                change_rate = 0
            
            # 시가총액 계산 시도
            try:
                info = ticker.info
                shares_outstanding = info.get('sharesOutstanding', 0)
                market_cap = current_price * shares_outstanding if shares_outstanding else None
            except:
                market_cap = None
            
            price_info = StockPrice(
                symbol=normalized_symbol,
                current_price=current_price,
                change_amount=change_amount,
                change_rate=change_rate,
                volume=volume,
                market_cap=market_cap,
                timestamp=datetime.now()
            )
            
            return price_info
            
        except Exception as e:
            logger.error(f"주가 조회 오류: {symbol}, {str(e)}")
            return None
    
    async def get_technical_indicators(self, symbol: str) -> List[TechnicalIndicator]:
        """기술적 지표 계산"""
        try:
            normalized_symbol = self._normalize_symbol(symbol)
            ticker = yf.Ticker(normalized_symbol)
            hist = ticker.history(period="3mo")  # 3개월 데이터
            
            if hist.empty:
                return []
            
            indicators = []
            
            # RSI 계산
            try:
                delta = hist['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                
                current_rsi = float(rsi.iloc[-1])
                
                # RSI 시그널 판단
                if current_rsi > 70:
                    rsi_signal = InvestmentSignal.SELL
                    rsi_desc = "과매수 구간"
                elif current_rsi < 30:
                    rsi_signal = InvestmentSignal.BUY
                    rsi_desc = "과매도 구간"
                else:
                    rsi_signal = InvestmentSignal.HOLD
                    rsi_desc = "중립 구간"
                
                indicators.append(TechnicalIndicator(
                    name="RSI",
                    value=current_rsi,
                    signal=rsi_signal,
                    description=rsi_desc
                ))
                
            except Exception as e:
                logger.error(f"RSI 계산 오류: {str(e)}")
            
            # 이동평균 계산
            try:
                ma20 = hist['Close'].rolling(window=20).mean()
                ma50 = hist['Close'].rolling(window=50).mean()
                
                current_price = float(hist['Close'].iloc[-1])
                current_ma20 = float(ma20.iloc[-1])
                current_ma50 = float(ma50.iloc[-1])
                
                # 이동평균 시그널
                if current_price > current_ma20 > current_ma50:
                    ma_signal = InvestmentSignal.BUY
                    ma_desc = "상승 추세"
                elif current_price < current_ma20 < current_ma50:
                    ma_signal = InvestmentSignal.SELL
                    ma_desc = "하락 추세"
                else:
                    ma_signal = InvestmentSignal.HOLD
                    ma_desc = "횡보 구간"
                
                indicators.append(TechnicalIndicator(
                    name="MA20",
                    value=current_ma20,
                    signal=ma_signal,
                    description=f"20일 이동평균: {ma_desc}"
                ))
                
                indicators.append(TechnicalIndicator(
                    name="MA50",
                    value=current_ma50,
                    signal=ma_signal,
                    description=f"50일 이동평균: {ma_desc}"
                ))
                
            except Exception as e:
                logger.error(f"이동평균 계산 오류: {str(e)}")
            
            return indicators
            
        except Exception as e:
            logger.error(f"기술적 지표 계산 오류: {symbol}, {str(e)}")
            return []
    
    async def get_chart_data(self, symbol: str, period: str = "1d", interval: str = "1h") -> List[Dict[str, Any]]:
        """차트 데이터 조회"""
        try:
            normalized_symbol = self._normalize_symbol(symbol)
            ticker = yf.Ticker(normalized_symbol)
            hist = ticker.history(period=period, interval=interval)
            
            if hist.empty:
                return []
            
            chart_data = []
            for index, row in hist.iterrows():
                chart_data.append({
                    "timestamp": index.isoformat(),
                    "open": float(row['Open']),
                    "high": float(row['High']),
                    "low": float(row['Low']),
                    "close": float(row['Close']),
                    "volume": int(row['Volume'])
                })
            
            return chart_data
            
        except Exception as e:
            logger.error(f"차트 데이터 조회 오류: {symbol}, {str(e)}")
            return []
    
    async def get_trending_stocks(self, market: Optional[MarketType] = None, limit: int = 20) -> List[StockSearchResult]:
        """인기 종목 조회 (거래량 기준)"""
        try:
            results = []
            
            # 주요 종목들의 거래량 확인
            for name, symbol in list(self.korean_stocks.items())[:limit * 2]:  # 더 많이 확인 후 필터링
                try:
                    stock_market = self._get_market_type(symbol)
                    if market and stock_market != market:
                        continue
                    
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="1d")
                    
                    if not hist.empty:
                        current_price = float(hist['Close'].iloc[-1])
                        volume = int(hist['Volume'].iloc[-1])
                        
                        # 거래량이 있는 종목만 포함
                        if volume > 0:
                            prev_close = float(hist['Open'].iloc[-1])
                            change_rate = ((current_price - prev_close) / prev_close) * 100
                            
                            result = StockSearchResult(
                                symbol=symbol,
                                name=name,
                                market=stock_market,
                                current_price=current_price,
                                change_rate=change_rate,
                                volume=volume,
                                currency="KRW"
                            )
                            results.append(result)
                
                except Exception as e:
                    logger.error(f"인기 종목 데이터 조회 실패: {symbol}, {str(e)}")
            
            # 거래량 기준 정렬
            results.sort(key=lambda x: x.volume or 0, reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"인기 종목 조회 오류: {str(e)}")
            return []
    
    async def get_market_movers(self, direction: str = "gainers", market: Optional[MarketType] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """상승/하락 종목 조회"""
        try:
            results = []
            
            # 주요 종목들의 등락률 확인
            for name, symbol in self.korean_stocks.items():
                try:
                    stock_market = self._get_market_type(symbol)
                    if market and stock_market != market:
                        continue
                    
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="2d")
                    
                    if len(hist) >= 2:
                        current_price = float(hist['Close'].iloc[-1])
                        prev_close = float(hist['Close'].iloc[-2])
                        change_rate = ((current_price - prev_close) / prev_close) * 100
                        volume = int(hist['Volume'].iloc[-1])
                        
                        results.append({
                            "symbol": symbol,
                            "name": name,
                            "market": stock_market.value,
                            "current_price": current_price,
                            "change_rate": change_rate,
                            "volume": volume
                        })
                
                except Exception as e:
                    logger.error(f"상승/하락 종목 데이터 조회 실패: {symbol}, {str(e)}")
            
            # 등락률 기준 정렬
            if direction == "gainers":
                results.sort(key=lambda x: x['change_rate'], reverse=True)
            else:  # losers
                results.sort(key=lambda x: x['change_rate'])
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"상승/하락 종목 조회 오류: {str(e)}")
            return []
    
    async def get_sector_performance(self) -> List[Dict[str, Any]]:
        """업종별 수익률 조회 (모의 데이터)"""
        # 실제로는 업종 분류 데이터가 필요하지만, 여기서는 간단한 예시
        sectors = [
            {"sector": "기술", "change_rate": 2.5, "volume": 1500000},
            {"sector": "금융", "change_rate": -1.2, "volume": 800000},
            {"sector": "제조", "change_rate": 0.8, "volume": 1200000},
            {"sector": "유통", "change_rate": 1.5, "volume": 600000},
            {"sector": "에너지", "change_rate": -0.5, "volume": 400000}
        ]
        
        return sectors