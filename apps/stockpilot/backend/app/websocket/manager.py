"""
WebSocket 연결 관리자
클라이언트 연결, 구독 관리, 메시지 브로드캐스트
"""

import json
import asyncio
import time
from typing import Dict, Set, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger
import uuid
from enum import Enum
from asyncio import Queue, Lock
from dataclasses import dataclass, field

from app.models import WebSocketMessage, PriceUpdateMessage
from app.config import get_settings

settings = get_settings()


class ConnectionState(Enum):
    """연결 상태"""
    CONNECTING = "connecting"
    ACTIVE = "active"
    BACKPRESSURE = "backpressure"
    RECONNECTING = "reconnecting"
    DISCONNECTED = "disconnected"


class MessagePriority(Enum):
    """메시지 우선순위"""
    CRITICAL = 1    # 시스템 메시지, 연결 상태
    HIGH = 2        # 실시간 가격, 중요 시그널
    NORMAL = 3      # 일반 업데이트
    LOW = 4         # 배치 데이터, 통계


@dataclass
class QueuedMessage:
    """대기열 메시지"""
    content: Dict[str, Any]
    priority: MessagePriority
    timestamp: float = field(default_factory=time.time)
    retry_count: int = 0
    max_retries: int = 3


@dataclass 
class ConnectionHealth:
    """연결 건강 상태"""
    state: ConnectionState = ConnectionState.CONNECTING
    last_ping: Optional[float] = None
    last_pong: Optional[float] = None
    latency: Optional[float] = None
    failed_sends: int = 0
    message_queue_size: int = 0
    backpressure_start: Optional[float] = None
    reconnect_attempts: int = 0
    last_activity: float = field(default_factory=time.time)


class BackpressureManager:
    """백프레셔 관리"""
    
    def __init__(self, max_queue_size: int = 100, drop_threshold: int = 200):
        self.max_queue_size = max_queue_size
        self.drop_threshold = drop_threshold
        self.message_queues: Dict[str, Queue] = {}
        self.queue_locks: Dict[str, Lock] = {}
    
    async def add_message(self, connection_id: str, message: QueuedMessage) -> bool:
        """메시지를 대기열에 추가 (백프레셔 적용)"""
        if connection_id not in self.message_queues:
            self.message_queues[connection_id] = Queue()
            self.queue_locks[connection_id] = Lock()
        
        queue = self.message_queues[connection_id]
        
        # 드롭 임계치 초과 시 낮은 우선순위 메시지 드롭
        if queue.qsize() >= self.drop_threshold:
            await self._drop_low_priority_messages(queue)
        
        # 여전히 큐가 가득 차면 메시지 거부
        if queue.qsize() >= self.max_queue_size:
            logger.warning(f"메시지 큐 포화: {connection_id}, 메시지 드롭됨")
            return False
        
        await queue.put(message)
        return True
    
    async def _drop_low_priority_messages(self, queue: Queue):
        """낮은 우선순위 메시지 드롭"""
        temp_messages = []
        dropped = 0
        
        # 큐에서 메시지들을 꺼내서 우선순위 확인
        while not queue.empty():
            try:
                message = queue.get_nowait()
                if message.priority in [MessagePriority.CRITICAL, MessagePriority.HIGH]:
                    temp_messages.append(message)
                else:
                    dropped += 1
            except asyncio.QueueEmpty:
                break
        
        # 높은 우선순위 메시지들만 다시 큐에 넣기
        for message in temp_messages:
            await queue.put(message)
        
        if dropped > 0:
            logger.info(f"낮은 우선순위 메시지 {dropped}개 드롭됨")
    
    async def get_message(self, connection_id: str) -> Optional[QueuedMessage]:
        """메시지 큐에서 메시지 가져오기"""
        if connection_id not in self.message_queues:
            return None
        
        queue = self.message_queues[connection_id]
        try:
            return await asyncio.wait_for(queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return None
    
    def cleanup_connection(self, connection_id: str):
        """연결 정리 시 큐 제거"""
        self.message_queues.pop(connection_id, None)
        self.queue_locks.pop(connection_id, None)


class ConnectionManager:
    """WebSocket 연결 관리자 - 향상된 내구성 기능 포함"""
    
    def __init__(self):
        # 활성 연결 관리
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_health: Dict[str, ConnectionHealth] = {}
        
        # 구독 관리
        self.price_subscriptions: Dict[str, Set[str]] = {}  # connection_id -> set of symbols
        self.signal_subscriptions: Dict[str, Set[str]] = {}  # connection_id -> set of symbols
        self.news_subscriptions: Dict[str, Set[str]] = {}   # connection_id -> set of categories
        self.market_subscriptions: Set[str] = set()  # connection_ids for market status
        
        # 사용자별 연결 추적
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> set of connection_ids
        
        # 백프레셔 및 메시지 큐 관리
        self.backpressure_manager = BackpressureManager()
        
        # 통계
        self.connection_count = 0
        self.message_count = 0
        self.failed_message_count = 0
        self.last_heartbeat: Dict[str, datetime] = {}
        
        # 내구성 설정
        self.ping_interval = settings.websocket_heartbeat_interval
        self.pong_timeout = 10  # 초
        self.max_reconnect_attempts = 5
        self.backoff_base = 1.5  # 지수 백오프 기본값
        
        # 백그라운드 작업
        self._health_check_task: Optional[asyncio.Task] = None
        self._message_sender_tasks: Dict[str, asyncio.Task] = {}
        
        logger.info("향상된 WebSocket 연결 관리자 초기화 완료")
    
    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None) -> str:
        """새 WebSocket 연결 수락 - 향상된 내구성 기능 포함"""
        await websocket.accept()
        
        connection_id = str(uuid.uuid4())
        self.active_connections[connection_id] = websocket
        self.connection_count += 1
        
        # 연결 건강 상태 초기화
        self.connection_health[connection_id] = ConnectionHealth(
            state=ConnectionState.ACTIVE,
            last_activity=time.time()
        )
        
        # 사용자별 연결 추적
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
        
        self.last_heartbeat[connection_id] = datetime.now()
        
        # 개별 메시지 발송 태스크 시작
        self._message_sender_tasks[connection_id] = asyncio.create_task(
            self._message_sender_loop(connection_id)
        )
        
        # 헬스 체크 태스크 시작 (처음 연결시에만)
        if self._health_check_task is None or self._health_check_task.done():
            self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info(f"새 WebSocket 연결: {connection_id}, 사용자: {user_id}, 총 연결: {self.connection_count}")
        
        # 연결 확인 메시지 전송
        await self._queue_message(connection_id, {
            "type": "connection_established",
            "connection_id": connection_id,
            "timestamp": datetime.now().isoformat(),
            "features": {
                "backpressure_handling": True,
                "ping_pong": True,
                "message_queue": True
            }
        }, MessagePriority.CRITICAL)
        
        return connection_id
    
    def disconnect(self, connection_id: str, user_id: Optional[str] = None):
        """WebSocket 연결 해제 - 향상된 정리 기능 포함"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            self.connection_count -= 1
            
            # 연결 건강 상태 정리
            self.connection_health.pop(connection_id, None)
            
            # 백프레셔 매니저 정리
            self.backpressure_manager.cleanup_connection(connection_id)
            
            # 메시지 발송 태스크 중단
            if connection_id in self._message_sender_tasks:
                task = self._message_sender_tasks[connection_id]
                if not task.done():
                    task.cancel()
                del self._message_sender_tasks[connection_id]
            
            # 구독 정보 정리
            self.price_subscriptions.pop(connection_id, None)
            self.signal_subscriptions.pop(connection_id, None)
            self.news_subscriptions.pop(connection_id, None)
            self.market_subscriptions.discard(connection_id)
            self.last_heartbeat.pop(connection_id, None)
            
            # 사용자별 연결 추적 정리
            if user_id and user_id in self.user_connections:
                self.user_connections[user_id].discard(connection_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            logger.info(f"WebSocket 연결 해제: {connection_id}, 총 연결: {self.connection_count}")
    
    async def send_message(self, connection_id: str, message: Dict[str, Any], priority: MessagePriority = MessagePriority.NORMAL):
        """특정 연결에 메시지 전송 - 큐 시스템 사용"""
        if connection_id in self.active_connections:
            await self._queue_message(connection_id, message, priority)
    
    async def broadcast_message(self, message: Dict[str, Any], connection_ids: Optional[Set[str]] = None, priority: MessagePriority = MessagePriority.NORMAL):
        """여러 연결에 메시지 브로드캐스트 - 큐 시스템 사용"""
        target_connections = connection_ids or set(self.active_connections.keys())
        
        # 모든 대상 연결에 큐를 통해 메시지 전송
        for connection_id in target_connections:
            if connection_id in self.active_connections:
                await self._queue_message(connection_id, message, priority)
    
    # 구독 관리
    def subscribe_to_prices(self, connection_id: str, symbols: List[str]):
        """주가 실시간 업데이트 구독"""
        if connection_id not in self.price_subscriptions:
            self.price_subscriptions[connection_id] = set()
        
        self.price_subscriptions[connection_id].update(symbols)
        logger.info(f"주가 구독 추가: {connection_id}, 종목: {symbols}")
    
    def unsubscribe_from_prices(self, connection_id: str, symbols: List[str]):
        """주가 실시간 업데이트 구독 해제"""
        if connection_id in self.price_subscriptions:
            self.price_subscriptions[connection_id] -= set(symbols)
            if not self.price_subscriptions[connection_id]:
                del self.price_subscriptions[connection_id]
        
        logger.info(f"주가 구독 해제: {connection_id}, 종목: {symbols}")
    
    def subscribe_to_signals(self, connection_id: str, symbols: List[str]):
        """AI 시그널 업데이트 구독"""
        if connection_id not in self.signal_subscriptions:
            self.signal_subscriptions[connection_id] = set()
        
        self.signal_subscriptions[connection_id].update(symbols)
        logger.info(f"시그널 구독 추가: {connection_id}, 종목: {symbols}")
    
    def subscribe_to_news(self, connection_id: str, categories: List[str]):
        """뉴스 업데이트 구독"""
        if connection_id not in self.news_subscriptions:
            self.news_subscriptions[connection_id] = set()
        
        self.news_subscriptions[connection_id].update(categories)
        logger.info(f"뉴스 구독 추가: {connection_id}, 카테고리: {categories}")
    
    def subscribe_to_market(self, connection_id: str):
        """시장 상태 업데이트 구독"""
        self.market_subscriptions.add(connection_id)
        logger.info(f"시장 상태 구독 추가: {connection_id}")
    
    # 브로드캐스트 메서드
    async def broadcast_price_update(self, symbol: str, price_data: Dict[str, Any]):
        """주가 업데이트 브로드캐스트"""
        # 해당 종목을 구독하는 연결들 찾기
        target_connections = set()
        for connection_id, subscribed_symbols in self.price_subscriptions.items():
            if symbol in subscribed_symbols:
                target_connections.add(connection_id)
        
        if target_connections:
            message = PriceUpdateMessage(
                symbol=symbol,
                price=price_data["price"],
                change_amount=price_data.get("change_amount", 0),
                change_rate=price_data.get("change_rate", 0),
                volume=price_data.get("volume", 0),
                timestamp=datetime.now()
            ).model_dump()
            
            await self.broadcast_message(message, target_connections, MessagePriority.HIGH)
            logger.debug(f"주가 업데이트 브로드캐스트: {symbol}, {len(target_connections)}개 연결")
    
    async def broadcast_signal_update(self, signal_data: Dict[str, Any]):
        """시그널 업데이트 브로드캐스트"""
        symbol = signal_data.get("symbol")
        target_connections = set()
        
        # 해당 종목을 구독하는 연결들 찾기
        if symbol:
            for connection_id, subscribed_symbols in self.signal_subscriptions.items():
                if symbol in subscribed_symbols:
                    target_connections.add(connection_id)
        
        if target_connections:
            message = {
                "type": "signal_update",
                "data": signal_data,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.broadcast_message(message, target_connections, MessagePriority.HIGH)
            logger.info(f"시그널 업데이트 브로드캐스트: {symbol}, {len(target_connections)}개 연결")
    
    async def broadcast_news_update(self, news_data: Dict[str, Any]):
        """뉴스 업데이트 브로드캐스트"""
        category = news_data.get("category")
        target_connections = set()
        
        # 해당 카테고리를 구독하는 연결들 찾기
        if category:
            for connection_id, subscribed_categories in self.news_subscriptions.items():
                if category in subscribed_categories:
                    target_connections.add(connection_id)
        
        if target_connections:
            message = {
                "type": "news_update",
                "data": news_data,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.broadcast_message(message, target_connections, MessagePriority.NORMAL)
            logger.info(f"뉴스 업데이트 브로드캐스트: {category}, {len(target_connections)}개 연결")
    
    async def broadcast_market_status(self, market_data: Dict[str, Any]):
        """시장 상태 브로드캐스트"""
        if self.market_subscriptions:
            message = {
                "type": "market_status",
                "data": market_data,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.broadcast_message(message, self.market_subscriptions, MessagePriority.NORMAL)
            logger.info(f"시장 상태 브로드캐스트: {len(self.market_subscriptions)}개 연결")
    
    async def send_heartbeat(self):
        """하트비트 메시지 전송"""
        message = {
            "type": "heartbeat",
            "timestamp": datetime.now().isoformat(),
            "connection_count": self.connection_count
        }
        
        await self.broadcast_message(message, priority=MessagePriority.LOW)
    
    async def cleanup_stale_connections(self):
        """비활성 연결 정리"""
        current_time = datetime.now()
        stale_connections = []
        
        for connection_id, last_heartbeat in self.last_heartbeat.items():
            if (current_time - last_heartbeat).total_seconds() > settings.websocket_heartbeat_interval * 2:
                stale_connections.append(connection_id)
        
        for connection_id in stale_connections:
            logger.warning(f"비활성 연결 정리: {connection_id}")
            self.disconnect(connection_id)
    
    async def _queue_message(self, connection_id: str, message: Dict[str, Any], priority: MessagePriority = MessagePriority.NORMAL):
        """메시지를 대기열에 추가"""
        queued_message = QueuedMessage(content=message, priority=priority)
        success = await self.backpressure_manager.add_message(connection_id, queued_message)
        
        if not success:
            self.failed_message_count += 1
            
            # 백프레셔 상태로 변경
            if connection_id in self.connection_health:
                health = self.connection_health[connection_id]
                if health.state != ConnectionState.BACKPRESSURE:
                    health.state = ConnectionState.BACKPRESSURE
                    health.backpressure_start = time.time()
                    logger.warning(f"연결 백프레셔 시작: {connection_id}")

    async def _message_sender_loop(self, connection_id: str):
        """개별 연결의 메시지 발송 루프"""
        while connection_id in self.active_connections:
            try:
                message = await self.backpressure_manager.get_message(connection_id)
                if message is None:
                    await asyncio.sleep(0.1)
                    continue
                
                websocket = self.active_connections[connection_id]
                health = self.connection_health[connection_id]
                
                # 메시지 발송 시도
                try:
                    await websocket.send_text(json.dumps(message.content, ensure_ascii=False))
                    self.message_count += 1
                    health.last_activity = time.time()
                    health.failed_sends = 0
                    
                    # 백프레셔 상태 해제
                    if health.state == ConnectionState.BACKPRESSURE:
                        health.state = ConnectionState.ACTIVE
                        health.backpressure_start = None
                        logger.info(f"연결 백프레셔 해제: {connection_id}")
                        
                except Exception as e:
                    logger.error(f"메시지 전송 실패: {connection_id}, 오류: {str(e)}")
                    health.failed_sends += 1
                    
                    # 재시도 로직
                    if message.retry_count < message.max_retries:
                        message.retry_count += 1
                        await self.backpressure_manager.add_message(connection_id, message)
                    else:
                        self.failed_message_count += 1
                        # 연속 실패 시 연결 해제
                        if health.failed_sends >= 5:
                            logger.error(f"연속 메시지 전송 실패로 연결 해제: {connection_id}")
                            self.disconnect(connection_id)
                            break
                            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"메시지 발송 루프 오류: {connection_id}, {str(e)}")
                await asyncio.sleep(1)

    async def _health_check_loop(self):
        """연결 건강 상태 체크 루프"""
        while True:
            try:
                await asyncio.sleep(self.ping_interval)
                await self._ping_all_connections()
                await self._check_connection_health()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"헬스 체크 루프 오류: {str(e)}")

    async def _ping_all_connections(self):
        """모든 연결에 ping 전송"""
        current_time = time.time()
        
        for connection_id in list(self.active_connections.keys()):
            try:
                websocket = self.active_connections[connection_id]
                health = self.connection_health[connection_id]
                
                # ping 메시지 전송
                ping_message = {
                    "type": "ping",
                    "timestamp": current_time
                }
                
                await websocket.send_text(json.dumps(ping_message))
                health.last_ping = current_time
                
            except Exception as e:
                logger.warning(f"Ping 전송 실패: {connection_id}, {str(e)}")

    async def _check_connection_health(self):
        """연결 건강 상태 점검"""
        current_time = time.time()
        unhealthy_connections = []
        
        for connection_id, health in self.connection_health.items():
            # Pong 응답 타임아웃 체크
            if (health.last_ping and 
                (not health.last_pong or health.last_pong < health.last_ping) and
                current_time - health.last_ping > self.pong_timeout):
                
                logger.warning(f"연결 응답 없음 (pong timeout): {connection_id}")
                unhealthy_connections.append(connection_id)
                continue
            
            # 장기간 비활성 체크
            if current_time - health.last_activity > self.ping_interval * 3:
                logger.warning(f"연결 장기간 비활성: {connection_id}")
                unhealthy_connections.append(connection_id)
                continue
            
            # 백프레셔 지속 시간 체크
            if (health.state == ConnectionState.BACKPRESSURE and 
                health.backpressure_start and
                current_time - health.backpressure_start > 60):  # 1분 백프레셔 지속
                
                logger.warning(f"백프레셔 장기 지속으로 연결 해제: {connection_id}")
                unhealthy_connections.append(connection_id)
        
        # 불건전한 연결 해제
        for connection_id in unhealthy_connections:
            self.disconnect(connection_id)

    async def handle_pong(self, connection_id: str, pong_data: Dict[str, Any]):
        """Pong 메시지 처리"""
        if connection_id in self.connection_health:
            health = self.connection_health[connection_id]
            current_time = time.time()
            health.last_pong = current_time
            health.last_activity = current_time
            
            # 지연시간 계산
            if health.last_ping:
                health.latency = current_time - health.last_ping
            
            logger.debug(f"Pong 수신: {connection_id}, 지연시간: {health.latency:.3f}초")

    async def handle_client_message(self, connection_id: str, message_data: Dict[str, Any]):
        """클라이언트 메시지 처리"""
        message_type = message_data.get("type")
        
        if message_type == "pong":
            await self.handle_pong(connection_id, message_data)
        elif message_type == "subscribe_prices":
            symbols = message_data.get("data", {}).get("symbols", [])
            self.subscribe_to_prices(connection_id, symbols)
        elif message_type == "unsubscribe_prices":
            symbols = message_data.get("data", {}).get("symbols", [])
            self.unsubscribe_from_prices(connection_id, symbols)
        # 다른 메시지 타입 처리...
        
        # 활동 시간 업데이트
        if connection_id in self.connection_health:
            self.connection_health[connection_id].last_activity = time.time()

    def get_statistics(self) -> Dict[str, Any]:
        """WebSocket 통계 반환 - 향상된 메트릭스 포함"""
        healthy_connections = sum(
            1 for health in self.connection_health.values() 
            if health.state == ConnectionState.ACTIVE
        )
        
        backpressure_connections = sum(
            1 for health in self.connection_health.values() 
            if health.state == ConnectionState.BACKPRESSURE
        )
        
        avg_latency = None
        latencies = [h.latency for h in self.connection_health.values() if h.latency]
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
        
        return {
            "total_connections": self.connection_count,
            "healthy_connections": healthy_connections,
            "backpressure_connections": backpressure_connections,
            "total_messages_sent": self.message_count,
            "failed_messages": self.failed_message_count,
            "average_latency": avg_latency,
            "price_subscriptions": len(self.price_subscriptions),
            "signal_subscriptions": len(self.signal_subscriptions),
            "news_subscriptions": len(self.news_subscriptions),
            "market_subscriptions": len(self.market_subscriptions),
            "unique_users": len(self.user_connections),
            "uptime": datetime.now().isoformat()
        }


# 전역 연결 관리자 인스턴스
manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """연결 관리자 인스턴스 반환"""
    return manager