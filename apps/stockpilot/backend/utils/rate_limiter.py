"""
StockPilot 레이트 리미팅 시스템
클라이언트/채널별 메시지 처리 제한 및 악성 클라이언트 차단
"""

import time
import asyncio
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)

@dataclass
class RateLimitConfig:
    """레이트 리미트 설정"""
    max_requests: int = 10  # 최대 요청 수
    time_window: int = 60   # 시간 윈도우 (초)
    burst_limit: int = 5    # 순간 허용 요청 수
    cooldown_seconds: int = 300  # 제재 시간 (5분)

@dataclass
class ClientRateState:
    """클라이언트 레이트 리미트 상태"""
    requests: deque = field(default_factory=deque)  # 요청 타임스탬프들
    total_requests: int = 0
    blocked_until: Optional[float] = None
    warning_count: int = 0
    first_request: Optional[float] = None
    last_request: Optional[float] = None
    
    def is_blocked(self) -> bool:
        """클라이언트가 차단된 상태인지 확인"""
        if self.blocked_until is None:
            return False
        return time.time() < self.blocked_until

class RateLimiter:
    """레이트 리미터 메인 클래스"""
    
    def __init__(self):
        # 채널별 레이트 리미트 설정
        self.channel_configs = {
            "us_stocks": RateLimitConfig(max_requests=30, time_window=60, burst_limit=10, cooldown_seconds=180),
            "us_indices": RateLimitConfig(max_requests=20, time_window=60, burst_limit=8, cooldown_seconds=180), 
            "exchange_rates": RateLimitConfig(max_requests=15, time_window=60, burst_limit=5, cooldown_seconds=240),
            "us_news": RateLimitConfig(max_requests=10, time_window=60, burst_limit=3, cooldown_seconds=300),
            "ai_signals": RateLimitConfig(max_requests=5, time_window=60, burst_limit=2, cooldown_seconds=600),
            "market_status": RateLimitConfig(max_requests=20, time_window=60, burst_limit=5, cooldown_seconds=120),
            "connection": RateLimitConfig(max_requests=100, time_window=60, burst_limit=20, cooldown_seconds=60),
            "_default": RateLimitConfig(max_requests=15, time_window=60, burst_limit=5, cooldown_seconds=300)
        }
        
        # 클라이언트별 상태 추적
        self.client_states: Dict[str, ClientRateState] = defaultdict(ClientRateState)
        
        # 채널별 클라이언트 상태 추적
        self.channel_client_states: Dict[str, Dict[str, ClientRateState]] = defaultdict(lambda: defaultdict(ClientRateState))
        
        # 글로벌 통계
        self.global_stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "active_clients": 0,
            "blocked_clients": set()
        }
        
        # 정리 작업 스케줄링
        self._cleanup_task = None
        
    async def start_cleanup_task(self):
        """백그라운드 정리 작업 시작"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def stop_cleanup_task(self):
        """백그라운드 정리 작업 중지"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
    
    async def _periodic_cleanup(self):
        """주기적으로 오래된 데이터 정리"""
        while True:
            try:
                await asyncio.sleep(300)  # 5분마다 정리
                self._cleanup_old_data()
                logger.debug(f"레이트 리미터 정리 완료. 활성 클라이언트: {len(self.client_states)}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"레이트 리미터 정리 오류: {e}")
    
    def _cleanup_old_data(self):
        """오래된 요청 데이터 정리"""
        current_time = time.time()
        cleanup_threshold = current_time - 3600  # 1시간 이전 데이터 정리
        
        # 클라이언트 상태 정리
        clients_to_remove = []
        for client_id, state in self.client_states.items():
            # 차단 해제된 클라이언트 확인
            if state.blocked_until and current_time >= state.blocked_until:
                state.blocked_until = None
                state.warning_count = 0
                logger.info(f"클라이언트 {client_id} 차단 해제")
            
            # 오래된 요청 기록 제거
            while state.requests and state.requests[0] < cleanup_threshold:
                state.requests.popleft()
            
            # 비활성 클라이언트 제거
            if (not state.requests and 
                (not state.last_request or current_time - state.last_request > 3600)):
                clients_to_remove.append(client_id)
        
        for client_id in clients_to_remove:
            del self.client_states[client_id]
            self.global_stats["blocked_clients"].discard(client_id)
        
        # 채널별 상태도 정리
        for channel, client_states in list(self.channel_client_states.items()):
            clients_to_remove = []
            for client_id, state in client_states.items():
                while state.requests and state.requests[0] < cleanup_threshold:
                    state.requests.popleft()
                
                if not state.requests and (not state.last_request or current_time - state.last_request > 3600):
                    clients_to_remove.append(client_id)
            
            for client_id in clients_to_remove:
                del client_states[client_id]
    
    def get_config_for_channel(self, channel: str) -> RateLimitConfig:
        """채널에 대한 레이트 리미트 설정 조회"""
        return self.channel_configs.get(channel, self.channel_configs["_default"])
    
    def _update_client_state(self, client_id: str, state: ClientRateState, current_time: float):
        """클라이언트 상태 업데이트"""
        state.requests.append(current_time)
        state.total_requests += 1
        state.last_request = current_time
        if state.first_request is None:
            state.first_request = current_time
    
    def _check_rate_limit(self, client_id: str, state: ClientRateState, config: RateLimitConfig, current_time: float) -> Tuple[bool, str]:
        """레이트 리미트 검사"""
        # 이미 차단된 클라이언트 확인
        if state.is_blocked():
            remaining_time = int(state.blocked_until - current_time)
            return False, f"클라이언트가 차단됨 (남은 시간: {remaining_time}초)"
        
        # 시간 윈도우 내 요청 수 계산
        window_start = current_time - config.time_window
        while state.requests and state.requests[0] < window_start:
            state.requests.popleft()
        
        requests_in_window = len(state.requests)
        
        # 버스트 제한 검사 (최근 10초)
        burst_window_start = current_time - 10
        recent_requests = sum(1 for req_time in state.requests if req_time >= burst_window_start)
        
        if recent_requests >= config.burst_limit:
            # 경고 누적
            state.warning_count += 1
            if state.warning_count >= 3:
                # 3회 경고 후 차단
                state.blocked_until = current_time + config.cooldown_seconds
                self.global_stats["blocked_clients"].add(client_id)
                logger.warning(f"클라이언트 {client_id} 차단됨 (버스트 제한 초과, {config.cooldown_seconds}초)")
                return False, f"버스트 제한 초과로 차단됨 ({config.cooldown_seconds}초)"
            else:
                return False, f"버스트 제한 초과 (경고 {state.warning_count}/3)"
        
        # 시간 윈도우 제한 검사
        if requests_in_window >= config.max_requests:
            state.warning_count += 1
            if state.warning_count >= 2:
                # 2회 경고 후 차단
                state.blocked_until = current_time + config.cooldown_seconds
                self.global_stats["blocked_clients"].add(client_id)
                logger.warning(f"클라이언트 {client_id} 차단됨 (시간 윈도우 제한 초과, {config.cooldown_seconds}초)")
                return False, f"시간 윈도우 제한 초과로 차단됨 ({config.cooldown_seconds}초)"
            else:
                return False, f"시간 윈도우 제한 초과 (경고 {state.warning_count}/2)"
        
        # 통과
        return True, "허용됨"
    
    async def check_rate_limit(self, client_id: str, channel: str = "connection", message_type: str = "message") -> Tuple[bool, str]:
        """레이트 리미트 검사 (메인 함수)"""
        try:
            current_time = time.time()
            config = self.get_config_for_channel(channel)
            
            # 글로벌 통계 업데이트
            self.global_stats["total_requests"] += 1
            
            # 클라이언트별 상태 확인
            client_state = self.client_states[client_id]
            allowed, reason = self._check_rate_limit(client_id, client_state, config, current_time)
            
            if not allowed:
                self.global_stats["blocked_requests"] += 1
                logger.warning(f"레이트 리미트 차단: client={client_id}, channel={channel}, reason={reason}")
                return False, reason
            
            # 채널별 상태 확인
            channel_state = self.channel_client_states[channel][client_id]
            allowed, reason = self._check_rate_limit(client_id, channel_state, config, current_time)
            
            if not allowed:
                self.global_stats["blocked_requests"] += 1
                logger.warning(f"채널 레이트 리미트 차단: client={client_id}, channel={channel}, reason={reason}")
                return False, f"채널 {reason}"
            
            # 모든 검사 통과시 상태 업데이트
            self._update_client_state(client_id, client_state, current_time)
            self._update_client_state(client_id, channel_state, current_time)
            
            return True, "허용됨"
            
        except Exception as e:
            logger.error(f"레이트 리미트 검사 오류: {e}")
            # 오류시 기본적으로 허용
            return True, "오류로 인한 허용"
    
    def get_client_status(self, client_id: str) -> Dict[str, Any]:
        """클라이언트 레이트 리미트 상태 조회"""
        client_state = self.client_states.get(client_id)
        if not client_state:
            return {"status": "unknown", "total_requests": 0}
        
        current_time = time.time()
        return {
            "status": "blocked" if client_state.is_blocked() else "active",
            "total_requests": client_state.total_requests,
            "warning_count": client_state.warning_count,
            "blocked_until": client_state.blocked_until,
            "remaining_block_time": max(0, int(client_state.blocked_until - current_time)) if client_state.blocked_until else 0,
            "requests_in_last_minute": len([req for req in client_state.requests if current_time - req <= 60]),
            "first_request": client_state.first_request,
            "last_request": client_state.last_request
        }
    
    def get_global_stats(self) -> Dict[str, Any]:
        """전역 레이트 리미팅 통계"""
        return {
            "total_requests": self.global_stats["total_requests"],
            "blocked_requests": self.global_stats["blocked_requests"],
            "active_clients": len(self.client_states),
            "blocked_clients_count": len(self.global_stats["blocked_clients"]),
            "blocked_clients": list(self.global_stats["blocked_clients"]),
            "channels_monitored": list(self.channel_configs.keys()),
            "uptime": time.time() - getattr(self, 'start_time', time.time())
        }
    
    def manually_block_client(self, client_id: str, duration_seconds: int = 600, reason: str = "관리자 차단"):
        """관리자 수동 클라이언트 차단"""
        current_time = time.time()
        state = self.client_states[client_id]
        state.blocked_until = current_time + duration_seconds
        self.global_stats["blocked_clients"].add(client_id)
        logger.info(f"관리자가 클라이언트 {client_id}를 {duration_seconds}초 차단: {reason}")
    
    def manually_unblock_client(self, client_id: str, reason: str = "관리자 차단 해제"):
        """관리자 수동 클라이언트 차단 해제"""
        if client_id in self.client_states:
            state = self.client_states[client_id]
            state.blocked_until = None
            state.warning_count = 0
            self.global_stats["blocked_clients"].discard(client_id)
            logger.info(f"관리자가 클라이언트 {client_id} 차단 해제: {reason}")

# 전역 레이트 리미터 인스턴스
_global_rate_limiter: Optional[RateLimiter] = None

def get_rate_limiter() -> RateLimiter:
    """전역 레이트 리미터 인스턴스 반환"""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter()
        _global_rate_limiter.start_time = time.time()
    return _global_rate_limiter

# 데코레이터 함수들
def rate_limit(channel: str = "connection"):
    """레이트 리미팅 데코레이터"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 클라이언트 ID 추출 시도
            client_id = None
            if len(args) > 0:
                # 첫 번째 인수가 self일 경우
                self_obj = args[0]
                if hasattr(self_obj, 'websocket') and hasattr(self_obj.websocket, 'client'):
                    # WebSocket 객체에서 클라이언트 정보 추출
                    client_state = getattr(self_obj.websocket, 'client_state', {})
                    client_id = client_state.get('client_id', 'unknown')
                elif 'client_id' in kwargs:
                    client_id = kwargs['client_id']
            
            if not client_id:
                client_id = f"unknown_{id(args[0])}"
            
            # 레이트 리미트 검사
            rate_limiter = get_rate_limiter()
            allowed, reason = await rate_limiter.check_rate_limit(client_id, channel)
            
            if not allowed:
                logger.warning(f"레이트 리미트 차단: {client_id} - {reason}")
                # 에러 응답 또는 예외 발생
                if hasattr(args[0], 'send_error'):
                    await args[0].send_error("RATE_LIMIT_EXCEEDED", f"레이트 리미트 초과: {reason}")
                    return
                else:
                    raise Exception(f"레이트 리미트 초과: {reason}")
            
            # 원본 함수 실행
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

def connection_rate_limit(func):
    """연결 레이트 리미팅 데코레이터"""
    return rate_limit("connection")(func)

def message_rate_limit(channel: str):
    """메시지 레이트 리미팅 데코레이터"""
    return rate_limit(channel)

# 테스트 함수
async def test_rate_limiter():
    """레이트 리미터 테스트"""
    print("=== 레이트 리미터 테스트 ===")
    
    limiter = get_rate_limiter()
    await limiter.start_cleanup_task()
    
    test_client = "test_client_001"
    
    # 정상 요청 테스트
    print("\n1. 정상 요청 테스트:")
    for i in range(5):
        allowed, reason = await limiter.check_rate_limit(test_client, "us_stocks")
        print(f"요청 {i+1}: {'허용' if allowed else '차단'} - {reason}")
        await asyncio.sleep(0.1)
    
    # 버스트 제한 테스트  
    print("\n2. 버스트 제한 테스트:")
    for i in range(15):
        allowed, reason = await limiter.check_rate_limit(test_client, "us_stocks")
        print(f"버스트 요청 {i+1}: {'허용' if allowed else '차단'} - {reason}")
    
    # 상태 확인
    print(f"\n3. 클라이언트 상태:")
    status = limiter.get_client_status(test_client)
    print(f"상태: {status}")
    
    print(f"\n4. 전역 통계:")
    stats = limiter.get_global_stats()
    print(f"통계: {stats}")
    
    await limiter.stop_cleanup_task()

if __name__ == "__main__":
    asyncio.run(test_rate_limiter())