"""
주식 데이터 수집 및 처리 서비스
Yahoo Finance API를 통한 실시간/과거 주가 데이터 수집과 데이터베이스 저장을 담당
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from ..models.stock import Stock, StockPrice, DataUpdateLog
from ..utils.data_fetcher import DataFetcher, StockData
from ..database.connection import get_db

logger = logging.getLogger(__name__)


class StockDataService:
    """
    주식 데이터 수집 및 관리 서비스
    """
    
    def __init__(self, db: Session, news_api_key: Optional[str] = None):
        """
        초기화
        
        Args:
            db: 데이터베이스 세션
            news_api_key: 뉴스 API 키
        """
        self.db = db
        self.news_api_key = news_api_key
        
    async def add_stock_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        새로운 주식 종목을 데이터베이스에 추가
        
        Args:
            symbol: 주식 심볼
            
        Returns:
            Dict: 추가 결과
        """
        try:
            # 이미 존재하는지 확인
            existing_stock = self.db.query(Stock).filter(Stock.symbol == symbol).first()
            if existing_stock:
                return {
                    'success': False,
                    'message': f'종목 {symbol}이 이미 존재합니다',
                    'stock': existing_stock
                }
            
            # 종목 정보 가져오기
            async with DataFetcher(self.news_api_key) as fetcher:
                stock_info = fetcher.get_stock_info(symbol)
                
                if not stock_info:
                    return {
                        'success': False,
                        'message': f'종목 {symbol}의 정보를 가져올 수 없습니다'
                    }
                
                # 새 종목 생성
                new_stock = Stock(
                    symbol=symbol,
                    name=stock_info.get('name', ''),
                    market=stock_info.get('market', ''),
                    sector=stock_info.get('sector', ''),
                    industry=stock_info.get('industry', ''),
                    currency=stock_info.get('currency', 'USD')
                )
                
                self.db.add(new_stock)
                self.db.commit()
                self.db.refresh(new_stock)
                
                logger.info(f"새 종목 추가 완료: {symbol}")
                return {
                    'success': True,
                    'message': f'종목 {symbol}이 성공적으로 추가되었습니다',
                    'stock': new_stock
                }
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"종목 추가 실패: {symbol} - {str(e)}")
            return {
                'success': False,
                'message': f'종목 추가 중 오류 발생: {str(e)}'
            }
    
    async def update_stock_prices(
        self, 
        symbol: str, 
        period: str = "1d",
        interval: str = "1d"
    ) -> Dict[str, Any]:
        """
        특정 종목의 가격 데이터 업데이트
        
        Args:
            symbol: 주식 심볼
            period: 데이터 기간
            interval: 데이터 간격
            
        Returns:
            Dict: 업데이트 결과
        """
        try:
            # 종목 정보 확인
            stock = self.db.query(Stock).filter(Stock.symbol == symbol).first()
            if not stock:
                return {
                    'success': False,
                    'message': f'종목 {symbol}을 찾을 수 없습니다'
                }
            
            # 데이터 수집
            async with DataFetcher(self.news_api_key) as fetcher:
                stock_data_list = fetcher.get_stock_data(symbol, period, interval)
                
                if not stock_data_list:
                    return {
                        'success': False,
                        'message': f'종목 {symbol}의 가격 데이터를 가져올 수 없습니다'
                    }
                
                # 기존 데이터 확인 (중복 방지)
                updated_count = 0
                for stock_data in stock_data_list:
                    existing_price = self.db.query(StockPrice).filter(
                        and_(
                            StockPrice.stock_id == stock.id,
                            StockPrice.date == stock_data.date,
                            StockPrice.timeframe == interval
                        )
                    ).first()
                    
                    if existing_price:
                        # 기존 데이터 업데이트
                        existing_price.open_price = stock_data.open
                        existing_price.high_price = stock_data.high
                        existing_price.low_price = stock_data.low
                        existing_price.close_price = stock_data.close
                        existing_price.volume = stock_data.volume
                        existing_price.adjusted_close = stock_data.adjusted_close
                    else:
                        # 새 데이터 추가
                        new_price = StockPrice(
                            stock_id=stock.id,
                            date=stock_data.date,
                            timeframe=interval,
                            open_price=stock_data.open,
                            high_price=stock_data.high,
                            low_price=stock_data.low,
                            close_price=stock_data.close,
                            volume=stock_data.volume,
                            adjusted_close=stock_data.adjusted_close
                        )
                        self.db.add(new_price)
                        updated_count += 1
                
                # 업데이트 로그 생성
                update_log = DataUpdateLog(
                    data_type="price",
                    target_id=symbol,
                    last_update=datetime.utcnow(),
                    status="success",
                    records_updated=updated_count
                )
                self.db.add(update_log)
                
                self.db.commit()
                
                logger.info(f"가격 데이터 업데이트 완료: {symbol}, {updated_count}개 레코드")
                return {
                    'success': True,
                    'message': f'{symbol} 가격 데이터가 업데이트되었습니다',
                    'records_updated': updated_count
                }
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"가격 데이터 업데이트 실패: {symbol} - {str(e)}")
            
            # 오류 로그 생성
            error_log = DataUpdateLog(
                data_type="price",
                target_id=symbol,
                last_update=datetime.utcnow(),
                status="error",
                error_message=str(e),
                records_updated=0
            )
            self.db.add(error_log)
            self.db.commit()
            
            return {
                'success': False,
                'message': f'가격 데이터 업데이트 실패: {str(e)}'
            }
    
    async def update_multiple_stocks(
        self, 
        symbols: List[str], 
        period: str = "1d",
        interval: str = "1d"
    ) -> Dict[str, Any]:
        """
        여러 종목의 가격 데이터를 동시에 업데이트
        
        Args:
            symbols: 주식 심볼 리스트
            period: 데이터 기간
            interval: 데이터 간격
            
        Returns:
            Dict: 업데이트 결과
        """
        try:
            logger.info(f"다중 종목 가격 데이터 업데이트 시작: {len(symbols)}개")
            
            results = {}
            success_count = 0
            
            # 각 종목별로 업데이트
            for symbol in symbols:
                try:
                    result = await self.update_stock_prices(symbol, period, interval)
                    results[symbol] = result
                    
                    if result['success']:
                        success_count += 1
                    
                    # API 호출 제한을 위한 지연
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"종목 {symbol} 업데이트 실패: {str(e)}")
                    results[symbol] = {
                        'success': False,
                        'message': f'오류 발생: {str(e)}'
                    }
            
            logger.info(f"다중 종목 업데이트 완료: {success_count}/{len(symbols)}개 성공")
            
            return {
                'success': True,
                'message': f'{success_count}/{len(symbols)}개 종목 업데이트 완료',
                'results': results,
                'success_count': success_count,
                'total_count': len(symbols)
            }
            
        except Exception as e:
            logger.error(f"다중 종목 업데이트 실패: {str(e)}")
            return {
                'success': False,
                'message': f'다중 종목 업데이트 실패: {str(e)}'
            }
    
    def get_stock_prices(
        self, 
        symbol: str, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        interval: str = "1d",
        limit: int = 100
    ) -> List[StockPrice]:
        """
        데이터베이스에서 주식 가격 데이터 조회
        
        Args:
            symbol: 주식 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜
            interval: 데이터 간격
            limit: 최대 조회 개수
            
        Returns:
            List[StockPrice]: 가격 데이터 리스트
        """
        try:
            # 종목 정보 확인
            stock = self.db.query(Stock).filter(Stock.symbol == symbol).first()
            if not stock:
                logger.warning(f"종목을 찾을 수 없음: {symbol}")
                return []
            
            # 쿼리 구성
            query = self.db.query(StockPrice).filter(
                and_(
                    StockPrice.stock_id == stock.id,
                    StockPrice.timeframe == interval
                )
            )
            
            # 날짜 범위 필터
            if start_date:
                query = query.filter(StockPrice.date >= start_date)
            if end_date:
                query = query.filter(StockPrice.date <= end_date)
            
            # 정렬 및 제한
            prices = query.order_by(desc(StockPrice.date)).limit(limit).all()
            
            return prices
            
        except Exception as e:
            logger.error(f"가격 데이터 조회 실패: {symbol} - {str(e)}")
            return []
    
    async def get_realtime_prices(self, symbols: List[str]) -> Dict[str, Any]:
        """
        실시간 주가 정보 조회
        
        Args:
            symbols: 주식 심볼 리스트
            
        Returns:
            Dict: 실시간 주가 정보
        """
        try:
            logger.info(f"실시간 주가 조회: {len(symbols)}개 종목")
            
            realtime_data = {}
            
            async with DataFetcher(self.news_api_key) as fetcher:
                # 각 종목별로 실시간 데이터 수집
                tasks = []
                for symbol in symbols:
                    task = asyncio.create_task(
                        asyncio.to_thread(fetcher.get_realtime_price, symbol)
                    )
                    tasks.append((symbol, task))
                
                # 모든 작업 완료 대기
                for symbol, task in tasks:
                    try:
                        price_data = await task
                        if price_data:
                            realtime_data[symbol] = price_data
                    except Exception as e:
                        logger.error(f"종목 {symbol} 실시간 데이터 수집 실패: {str(e)}")
                        realtime_data[symbol] = None
            
            return {
                'success': True,
                'data': realtime_data,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"실시간 주가 조회 실패: {str(e)}")
            return {
                'success': False,
                'message': f'실시간 주가 조회 실패: {str(e)}'
            }
    
    def get_stock_list(self, market: Optional[str] = None) -> List[Stock]:
        """
        종목 리스트 조회
        
        Args:
            market: 시장 구분 (KOSPI, KOSDAQ, NYSE, NASDAQ)
            
        Returns:
            List[Stock]: 종목 리스트
        """
        try:
            query = self.db.query(Stock).filter(Stock.is_active == True)
            
            if market:
                query = query.filter(Stock.market == market)
            
            stocks = query.order_by(Stock.symbol).all()
            return stocks
            
        except Exception as e:
            logger.error(f"종목 리스트 조회 실패: {str(e)}")
            return []
    
    def get_update_status(self, symbol: str) -> Optional[DataUpdateLog]:
        """
        종목의 마지막 업데이트 상태 조회
        
        Args:
            symbol: 주식 심볼
            
        Returns:
            Optional[DataUpdateLog]: 업데이트 로그
        """
        try:
            last_update = self.db.query(DataUpdateLog).filter(
                and_(
                    DataUpdateLog.data_type == "price",
                    DataUpdateLog.target_id == symbol
                )
            ).order_by(desc(DataUpdateLog.created_at)).first()
            
            return last_update
            
        except Exception as e:
            logger.error(f"업데이트 상태 조회 실패: {symbol} - {str(e)}")
            return None
    
    async def schedule_daily_update(self, symbols: List[str]) -> Dict[str, Any]:
        """
        일일 정기 업데이트 수행
        
        Args:
            symbols: 업데이트할 종목 리스트
            
        Returns:
            Dict: 업데이트 결과
        """
        try:
            logger.info("일일 정기 업데이트 시작")
            
            # 장 마감 후인지 확인 (한국시간 기준 15:30 이후)
            now = datetime.now()
            market_close_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
            
            if now < market_close_time:
                return {
                    'success': False,
                    'message': '장 마감 전에는 일일 업데이트를 수행하지 않습니다'
                }
            
            # 어제 업데이트된 종목 확인
            yesterday = datetime.now() - timedelta(days=1)
            updated_symbols = []
            
            for symbol in symbols:
                last_update = self.get_update_status(symbol)
                
                # 마지막 업데이트가 어제 이전이거나 없으면 업데이트
                if not last_update or last_update.last_update.date() < now.date():
                    updated_symbols.append(symbol)
            
            if not updated_symbols:
                return {
                    'success': True,
                    'message': '모든 종목이 최신 상태입니다',
                    'updated_count': 0
                }
            
            # 일봉 데이터 업데이트
            result = await self.update_multiple_stocks(
                updated_symbols, 
                period="2d",  # 최근 2일 데이터
                interval="1d"
            )
            
            logger.info("일일 정기 업데이트 완료")
            return result
            
        except Exception as e:
            logger.error(f"일일 정기 업데이트 실패: {str(e)}")
            return {
                'success': False,
                'message': f'일일 정기 업데이트 실패: {str(e)}'
            }