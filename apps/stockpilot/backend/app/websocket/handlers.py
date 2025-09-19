"""
WebSocket 이벤트 핸들러
클라이언트 메시지 처리, 구독 관리, 실시간 데이터 전송
"""

import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from app.websocket.manager import ConnectionManager, get_connection_manager
from app.services.stock_service import StockService
from app.services.signal_service import SignalService
from app.services.news_service import NewsService
from app.services.market_service import MarketService


class WebSocketHandler:
    """WebSocket 이벤트 처리기"""
    
    def __init__(self):
        self.manager = get_connection_manager()
        self.stock_service = StockService()
        self.signal_service = SignalService()
        self.news_service = NewsService()
        self.market_service = MarketService()
        
        # 실시간 데이터 업데이트 태스크
        self.update_tasks: Dict[str, asyncio.Task] = {}
        
        logger.info("WebSocket 핸들러 초기화 완료")
    
    async def handle_client_connection(self, websocket: WebSocket, user_id: Optional[str] = None):
        """클라이언트 연결 처리"""
        connection_id = await self.manager.connect(websocket, user_id)
        
        try:
            while True:
                # 클라이언트로부터 메시지 수신
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # 메시지 타입별 처리
                await self.manager.handle_client_message(connection_id, message)
                
                # 하트비트 업데이트
                self.manager.last_heartbeat[connection_id] = datetime.now()
                
        except WebSocketDisconnect:
            logger.info(f"클라이언트 연결 해제: {connection_id}")
        except Exception as e:
            logger.error(f"WebSocket 오류: {connection_id}, {str(e)}")
        finally:
            self.manager.disconnect(connection_id, user_id)
    
    async def handle_message(self, connection_id: str, message: Dict[str, Any], user_id: Optional[str] = None):
        """클라이언트 메시지 처리"""
        message_type = message.get("type")
        data = message.get("data", {})
        
        logger.debug(f"메시지 처리: {connection_id}, 타입: {message_type}")
        
        try:
            if message_type == "subscribe_prices":
                await self.handle_price_subscription(connection_id, data)
            
            elif message_type == "unsubscribe_prices":
                await self.handle_price_unsubscription(connection_id, data)
            
            elif message_type == "subscribe_signals":
                await self.handle_signal_subscription(connection_id, data)
            
            elif message_type == "subscribe_news":
                await self.handle_news_subscription(connection_id, data)
            
            elif message_type == "subscribe_market":
                await self.handle_market_subscription(connection_id)
            
            elif message_type == "get_current_price":
                await self.handle_current_price_request(connection_id, data)
            
            elif message_type == "ping":
                await self.handle_ping(connection_id)
            
            else:
                logger.warning(f"알 수 없는 메시지 타입: {message_type}")
                await self.send_error(connection_id, f"알 수 없는 메시지 타입: {message_type}")
                
        except Exception as e:
            logger.error(f"메시지 처리 오류: {str(e)}")
            await self.send_error(connection_id, f"메시지 처리 중 오류: {str(e)}")
    
    async def handle_price_subscription(self, connection_id: str, data: Dict[str, Any]):
        """주가 구독 처리"""
        symbols = data.get("symbols", [])
        if not symbols:
            await self.send_error(connection_id, "구독할 종목이 없습니다")
            return
        
        # 구독 추가
        self.manager.subscribe_to_prices(connection_id, symbols)
        
        # 현재 가격 전송
        for symbol in symbols:
            try:
                price_data = await self.stock_service.get_current_price(symbol)
                if price_data:
                    await self.manager.send_message(connection_id, {
                        "type": "price_update",
                        "symbol": symbol,
                        "price": price_data.current_price,
                        "change_amount": price_data.change_amount,
                        "change_rate": price_data.change_rate,
                        "volume": price_data.volume,
                        "timestamp": price_data.timestamp.isoformat()
                    })
            except Exception as e:
                logger.error(f"초기 가격 조회 실패: {symbol}, {str(e)}")
        
        # 응답 메시지
        await self.manager.send_message(connection_id, {
            "type": "subscription_confirmed",
            "subscription_type": "prices",
            "symbols": symbols,
            "timestamp": datetime.now().isoformat()
        })
    
    async def handle_price_unsubscription(self, connection_id: str, data: Dict[str, Any]):
        """주가 구독 해제 처리"""
        symbols = data.get("symbols", [])
        if not symbols:
            await self.send_error(connection_id, "구독 해제할 종목이 없습니다")
            return
        
        self.manager.unsubscribe_from_prices(connection_id, symbols)
        
        await self.manager.send_message(connection_id, {
            "type": "unsubscription_confirmed",
            "subscription_type": "prices",
            "symbols": symbols,
            "timestamp": datetime.now().isoformat()
        })
    
    async def handle_signal_subscription(self, connection_id: str, data: Dict[str, Any]):
        """시그널 구독 처리"""
        symbols = data.get("symbols", [])
        if symbols:
            self.manager.subscribe_to_signals(connection_id, symbols)
        
        await self.manager.send_message(connection_id, {
            "type": "subscription_confirmed",
            "subscription_type": "signals",
            "symbols": symbols,
            "timestamp": datetime.now().isoformat()
        })
    
    async def handle_news_subscription(self, connection_id: str, data: Dict[str, Any]):
        """뉴스 구독 처리"""
        categories = data.get("categories", [])
        if categories:
            self.manager.subscribe_to_news(connection_id, categories)
        
        await self.manager.send_message(connection_id, {
            "type": "subscription_confirmed",
            "subscription_type": "news",
            "categories": categories,
            "timestamp": datetime.now().isoformat()
        })
    
    async def handle_market_subscription(self, connection_id: str):
        """시장 상태 구독 처리"""
        self.manager.subscribe_to_market(connection_id)
        
        # 현재 시장 상태 전송
        try:
            market_status = await self.market_service.get_market_status()
            await self.manager.send_message(connection_id, {
                "type": "market_status",
                "data": market_status.model_dump(),
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"시장 상태 조회 실패: {str(e)}")
        
        await self.manager.send_message(connection_id, {
            "type": "subscription_confirmed",
            "subscription_type": "market",
            "timestamp": datetime.now().isoformat()
        })
    
    async def handle_current_price_request(self, connection_id: str, data: Dict[str, Any]):
        """현재 가격 요청 처리"""
        symbol = data.get("symbol")
        if not symbol:
            await self.send_error(connection_id, "종목 코드가 없습니다")
            return
        
        try:
            price_data = await self.stock_service.get_current_price(symbol)
            if price_data:
                await self.manager.send_message(connection_id, {
                    "type": "current_price_response",
                    "symbol": symbol,
                    "data": price_data.model_dump(),
                    "timestamp": datetime.now().isoformat()
                })
            else:
                await self.send_error(connection_id, f"가격 정보를 찾을 수 없습니다: {symbol}")
        
        except Exception as e:
            logger.error(f"가격 조회 오류: {str(e)}")
            await self.send_error(connection_id, f"가격 조회 중 오류: {str(e)}")
    
    async def handle_ping(self, connection_id: str):
        """Ping 메시지 처리"""
        await self.manager.send_message(connection_id, {
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        })
    
    async def send_error(self, connection_id: str, error_message: str):
        """오류 메시지 전송"""
        await self.manager.send_message(connection_id, {
            "type": "error",
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        })


class RealTimeDataUpdater:
    """실시간 데이터 업데이트 서비스"""
    
    def __init__(self):
        self.manager = get_connection_manager()
        self.stock_service = StockService()
        self.signal_service = SignalService()
        self.news_service = NewsService()
        self.market_service = MarketService()
        
        self.is_running = False
        self.update_tasks: Dict[str, asyncio.Task] = {}
        
        logger.info("실시간 데이터 업데이터 초기화 완료")
    
    async def start_updates(self):
        """실시간 업데이트 시작"""
        if self.is_running:
            logger.warning("실시간 업데이트가 이미 실행 중입니다")
            return
        
        self.is_running = True
        
        # 각종 업데이트 태스크 시작
        self.update_tasks["price"] = asyncio.create_task(self.update_prices())
        self.update_tasks["signals"] = asyncio.create_task(self.update_signals())
        self.update_tasks["market"] = asyncio.create_task(self.update_market_status())
        self.update_tasks["heartbeat"] = asyncio.create_task(self.send_heartbeat())
        self.update_tasks["cleanup"] = asyncio.create_task(self.cleanup_connections())
        
        logger.info("실시간 데이터 업데이트 시작")
    
    async def stop_updates(self):
        """실시간 업데이트 중지"""
        self.is_running = False
        
        for task_name, task in self.update_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info(f"{task_name} 업데이트 태스크 중지")
        
        self.update_tasks.clear()
        logger.info("실시간 데이터 업데이트 중지")
    
    async def update_prices(self):
        """주가 실시간 업데이트"""
        while self.is_running:
            try:
                # 구독된 모든 종목 수집
                all_symbols = set()
                for subscribed_symbols in self.manager.price_subscriptions.values():
                    all_symbols.update(subscribed_symbols)
                
                if not all_symbols:
                    await asyncio.sleep(5)
                    continue
                
                # 각 종목의 현재 가격 조회 및 브로드캐스트
                for symbol in all_symbols:
                    try:
                        price_data = await self.stock_service.get_current_price(symbol)
                        if price_data:
                            await self.manager.broadcast_price_update(symbol, {
                                "price": price_data.current_price,
                                "change_amount": price_data.change_amount,
                                "change_rate": price_data.change_rate,
                                "volume": price_data.volume
                            })
                    except Exception as e:
                        logger.error(f"가격 업데이트 오류: {symbol}, {str(e)}")
                
                await asyncio.sleep(5)  # 5초마다 업데이트
                
            except Exception as e:
                logger.error(f"가격 업데이트 루프 오류: {str(e)}")
                await asyncio.sleep(10)
    
    async def update_signals(self):
        """시그널 실시간 업데이트"""
        while self.is_running:
            try:
                # 새로운 시그널 확인 (최근 5분)
                new_signals = await self.signal_service.get_recent_signals(minutes=5)
                
                for signal in new_signals:
                    await self.manager.broadcast_signal_update(signal.model_dump())
                
                await asyncio.sleep(30)  # 30초마다 확인
                
            except Exception as e:
                logger.error(f"시그널 업데이트 오류: {str(e)}")
                await asyncio.sleep(60)
    
    async def update_market_status(self):
        """시장 상태 실시간 업데이트"""
        while self.is_running:
            try:
                market_status = await self.market_service.get_market_status()
                await self.manager.broadcast_market_status(market_status.model_dump())
                
                await asyncio.sleep(60)  # 1분마다 업데이트
                
            except Exception as e:
                logger.error(f"시장 상태 업데이트 오류: {str(e)}")
                await asyncio.sleep(60)
    
    async def send_heartbeat(self):
        """하트비트 전송"""
        while self.is_running:
            try:
                await self.manager.send_heartbeat()
                await asyncio.sleep(30)  # 30초마다 하트비트
                
            except Exception as e:
                logger.error(f"하트비트 전송 오류: {str(e)}")
                await asyncio.sleep(30)
    
    async def cleanup_connections(self):
        """비활성 연결 정리"""
        while self.is_running:
            try:
                await self.manager.cleanup_stale_connections()
                await asyncio.sleep(300)  # 5분마다 정리
                
            except Exception as e:
                logger.error(f"연결 정리 오류: {str(e)}")
                await asyncio.sleep(300)


# 전역 인스턴스
websocket_handler = WebSocketHandler()
data_updater = RealTimeDataUpdater()


def get_websocket_handler() -> WebSocketHandler:
    """WebSocket 핸들러 반환"""
    return websocket_handler


def get_data_updater() -> RealTimeDataUpdater:
    """데이터 업데이터 반환"""
    return data_updater