#!/usr/bin/env python3
"""
WebSocket 인증 및 권한 관리 시스템
- JWT 토큰 기반 인증 (짧은 TTL)
- 구독 채널별 권한 분기
- 클라이언트 연결 제한 및 모니터링
- 프로덕션용 보안 강화
"""

import jwt
import time
import logging
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from enum import Enum
import hashlib
import secrets

# 로깅 설정
logger = logging.getLogger(__name__)

class UserRole(Enum):
    """사용자 역할"""
    GUEST = "guest"           # 기본 사용자 (주식 데이터만)
    BASIC = "basic"           # 기본 구독 (주식 + 환율)
    PREMIUM = "premium"       # 프리미엄 (주식 + 환율 + 뉴스)
    ADMIN = "admin"           # 관리자 (모든 기능 + AI 시그널)

class ChannelPermission(Enum):
    """채널 권한 레벨"""
    PUBLIC = "public"         # 누구나 접근 가능
    BASIC = "basic"           # BASIC 이상 필요
    PREMIUM = "premium"       # PREMIUM 이상 필요
    ADMIN = "admin"           # ADMIN만 접근 가능

@dataclass
class ClientInfo:
    """클라이언트 정보"""
    client_id: str
    user_id: str
    role: UserRole
    ip_address: str
    connected_at: datetime
    last_activity: datetime
    subscription_channels: Set[str]
    message_count: int = 0
    is_authenticated: bool = False

class WebSocketAuthManager:
    """WebSocket 인증 및 권한 관리자"""
    
    # JWT 설정
    JWT_ALGORITHM = "HS256"
    TOKEN_EXPIRY_MINUTES = 15  # 짧은 TTL (15분)
    
    # 채널별 권한 매핑
    CHANNEL_PERMISSIONS = {
        "us_stocks": ChannelPermission.PUBLIC,      # 기본 주식 데이터
        "us_indices": ChannelPermission.BASIC,      # 인덱스 데이터
        "exchange_rates": ChannelPermission.BASIC,   # 환율 데이터
        "market_status": ChannelPermission.PUBLIC,   # 시장 상태
        "us_news": ChannelPermission.PREMIUM,       # 뉴스 분석
        "ai_signals": ChannelPermission.ADMIN,      # AI 투자 시그널 (관리자 전용)
    }
    
    # 연결 제한 설정
    MAX_CONNECTIONS_PER_IP = 5      # IP당 최대 연결 수
    MAX_CONNECTIONS_PER_USER = 3    # 사용자당 최대 연결 수
    MAX_MESSAGES_PER_MINUTE = 60    # 분당 최대 메시지 수
    
    def __init__(self, jwt_secret_key: Optional[str] = None):
        """
        인증 관리자 초기화
        
        Args:
            jwt_secret_key: JWT 서명용 비밀키 (None이면 자동 생성)
        """
        self.jwt_secret = jwt_secret_key or secrets.token_hex(32)
        self.connected_clients: Dict[str, ClientInfo] = {}  # client_id -> ClientInfo
        self.ip_connections: Dict[str, Set[str]] = {}       # ip -> {client_ids}
        self.user_connections: Dict[str, Set[str]] = {}     # user_id -> {client_ids}
        
        logger.info("✅ WebSocket 인증 관리자 초기화 완료")
    
    def generate_token(self, user_id: str, role: UserRole, 
                      expires_in_minutes: int = None) -> str:
        """
        JWT 토큰 생성
        
        Args:
            user_id: 사용자 ID
            role: 사용자 역할
            expires_in_minutes: 만료 시간 (분, 기본값: TOKEN_EXPIRY_MINUTES)
            
        Returns:
            JWT 토큰 문자열
        """
        try:
            expires_in = expires_in_minutes or self.TOKEN_EXPIRY_MINUTES
            exp_time = datetime.now(timezone.utc) + timedelta(minutes=expires_in)
            
            payload = {
                "user_id": user_id,
                "role": role.value,
                "iat": datetime.now(timezone.utc),
                "exp": exp_time,
                "jti": secrets.token_hex(8)  # JWT ID for uniqueness
            }
            
            token = jwt.encode(payload, self.jwt_secret, algorithm=self.JWT_ALGORITHM)
            
            logger.info(f"🎫 토큰 생성: user={user_id}, role={role.value}, exp={expires_in}분")
            return token
            
        except Exception as e:
            logger.error(f"토큰 생성 실패: {e}")
            raise
    
    def verify_token(self, token: str) -> Tuple[bool, Optional[Dict]]:
        """
        JWT 토큰 검증
        
        Args:
            token: JWT 토큰 문자열
            
        Returns:
            (검증 성공 여부, 페이로드 또는 None)
        """
        try:
            payload = jwt.decode(
                token, 
                self.jwt_secret, 
                algorithms=[self.JWT_ALGORITHM]
            )
            
            # 추가 검증
            required_fields = ["user_id", "role", "exp"]
            for field in required_fields:
                if field not in payload:
                    logger.warning(f"토큰 필드 누락: {field}")
                    return False, None
            
            # 역할 검증
            try:
                role = UserRole(payload["role"])
            except ValueError:
                logger.warning(f"잘못된 역할: {payload['role']}")
                return False, None
            
            payload["role"] = role
            return True, payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("토큰 만료")
            return False, None
        except jwt.InvalidTokenError as e:
            logger.warning(f"토큰 검증 실패: {e}")
            return False, None
        except Exception as e:
            logger.error(f"토큰 처리 오류: {e}")
            return False, None
    
    def can_connect(self, ip_address: str, user_id: str) -> Tuple[bool, Optional[str]]:
        """
        연결 가능 여부 확인
        
        Args:
            ip_address: 클라이언트 IP
            user_id: 사용자 ID
            
        Returns:
            (연결 가능 여부, 거부 사유)
        """
        # IP별 연결 수 확인
        ip_client_count = len(self.ip_connections.get(ip_address, set()))
        if ip_client_count >= self.MAX_CONNECTIONS_PER_IP:
            return False, f"IP당 최대 연결 수 초과 ({ip_client_count}/{self.MAX_CONNECTIONS_PER_IP})"
        
        # 사용자별 연결 수 확인
        user_client_count = len(self.user_connections.get(user_id, set()))
        if user_client_count >= self.MAX_CONNECTIONS_PER_USER:
            return False, f"사용자당 최대 연결 수 초과 ({user_client_count}/{self.MAX_CONNECTIONS_PER_USER})"
        
        return True, None
    
    def authenticate_client(self, client_id: str, token: str, 
                          ip_address: str) -> Tuple[bool, Optional[str], Optional[ClientInfo]]:
        """
        클라이언트 인증
        
        Args:
            client_id: 클라이언트 ID
            token: JWT 토큰
            ip_address: 클라이언트 IP
            
        Returns:
            (인증 성공 여부, 오류 메시지, ClientInfo)
        """
        try:
            # 토큰 검증
            is_valid, payload = self.verify_token(token)
            if not is_valid:
                return False, "토큰 검증 실패", None
            
            user_id = payload["user_id"]
            role = payload["role"]
            
            # 연결 제한 확인
            can_connect, reason = self.can_connect(ip_address, user_id)
            if not can_connect:
                return False, reason, None
            
            # 클라이언트 정보 생성
            now = datetime.now(timezone.utc)
            client_info = ClientInfo(
                client_id=client_id,
                user_id=user_id,
                role=role,
                ip_address=ip_address,
                connected_at=now,
                last_activity=now,
                subscription_channels=set(),
                is_authenticated=True
            )
            
            # 연결 정보 등록
            self.connected_clients[client_id] = client_info
            
            # IP별 연결 추적
            if ip_address not in self.ip_connections:
                self.ip_connections[ip_address] = set()
            self.ip_connections[ip_address].add(client_id)
            
            # 사용자별 연결 추적
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(client_id)
            
            logger.info(f"🔐 클라이언트 인증 성공: {client_id} (user={user_id}, role={role.value})")
            return True, None, client_info
            
        except Exception as e:
            logger.error(f"클라이언트 인증 오류: {e}")
            return False, f"인증 처리 오류: {str(e)}", None
    
    def has_channel_permission(self, client_id: str, channel: str) -> bool:
        """
        채널 구독 권한 확인
        
        Args:
            client_id: 클라이언트 ID
            channel: 채널명
            
        Returns:
            권한 보유 여부
        """
        client_info = self.connected_clients.get(client_id)
        if not client_info or not client_info.is_authenticated:
            return False
        
        # 채널 권한 요구사항 확인
        required_permission = self.CHANNEL_PERMISSIONS.get(channel, ChannelPermission.ADMIN)
        user_role = client_info.role
        
        # 권한 계층 확인
        permission_hierarchy = {
            ChannelPermission.PUBLIC: [UserRole.GUEST, UserRole.BASIC, UserRole.PREMIUM, UserRole.ADMIN],
            ChannelPermission.BASIC: [UserRole.BASIC, UserRole.PREMIUM, UserRole.ADMIN],
            ChannelPermission.PREMIUM: [UserRole.PREMIUM, UserRole.ADMIN],
            ChannelPermission.ADMIN: [UserRole.ADMIN]
        }
        
        allowed_roles = permission_hierarchy.get(required_permission, [])
        has_permission = user_role in allowed_roles
        
        if not has_permission:
            logger.warning(f"권한 부족: client={client_id}, channel={channel}, "
                         f"required={required_permission.value}, user_role={user_role.value}")
        
        return has_permission
    
    def subscribe_channel(self, client_id: str, channel: str) -> Tuple[bool, Optional[str]]:
        """
        채널 구독
        
        Args:
            client_id: 클라이언트 ID
            channel: 채널명
            
        Returns:
            (구독 성공 여부, 오류 메시지)
        """
        client_info = self.connected_clients.get(client_id)
        if not client_info:
            return False, "인증되지 않은 클라이언트"
        
        # 권한 확인
        if not self.has_channel_permission(client_id, channel):
            return False, f"채널 '{channel}' 구독 권한 없음"
        
        # 구독 추가
        client_info.subscription_channels.add(channel)
        client_info.last_activity = datetime.now(timezone.utc)
        
        logger.info(f"📺 채널 구독: client={client_id}, channel={channel}")
        return True, None
    
    def unsubscribe_channel(self, client_id: str, channel: str) -> bool:
        """채널 구독 해제"""
        client_info = self.connected_clients.get(client_id)
        if not client_info:
            return False
        
        client_info.subscription_channels.discard(channel)
        client_info.last_activity = datetime.now(timezone.utc)
        
        logger.info(f"📺 채널 구독 해제: client={client_id}, channel={channel}")
        return True
    
    def check_rate_limit(self, client_id: str) -> bool:
        """
        Rate Limit 확인
        
        Args:
            client_id: 클라이언트 ID
            
        Returns:
            Rate Limit 통과 여부
        """
        client_info = self.connected_clients.get(client_id)
        if not client_info:
            return False
        
        # 간단한 Rate Limit (분당 메시지 수)
        client_info.message_count += 1
        
        # 1분마다 카운터 리셋 (간단 구현)
        current_minute = int(time.time() / 60)
        if not hasattr(client_info, '_last_reset_minute'):
            client_info._last_reset_minute = current_minute
            client_info._minute_message_count = 1
        elif client_info._last_reset_minute != current_minute:
            client_info._last_reset_minute = current_minute
            client_info._minute_message_count = 1
        else:
            client_info._minute_message_count += 1
        
        if client_info._minute_message_count > self.MAX_MESSAGES_PER_MINUTE:
            logger.warning(f"Rate Limit 초과: client={client_id}, "
                         f"messages={client_info._minute_message_count}/{self.MAX_MESSAGES_PER_MINUTE}")
            return False
        
        client_info.last_activity = datetime.now(timezone.utc)
        return True
    
    def disconnect_client(self, client_id: str):
        """클라이언트 연결 해제"""
        client_info = self.connected_clients.pop(client_id, None)
        if not client_info:
            return
        
        # IP 연결 제거
        ip_clients = self.ip_connections.get(client_info.ip_address, set())
        ip_clients.discard(client_id)
        if not ip_clients:
            del self.ip_connections[client_info.ip_address]
        
        # 사용자 연결 제거
        user_clients = self.user_connections.get(client_info.user_id, set())
        user_clients.discard(client_id)
        if not user_clients:
            del self.user_connections[client_info.user_id]
        
        logger.info(f"🔌 클라이언트 연결 해제: {client_id}")
    
    def get_client_info(self, client_id: str) -> Optional[ClientInfo]:
        """클라이언트 정보 조회"""
        return self.connected_clients.get(client_id)
    
    def get_connection_stats(self) -> Dict:
        """연결 통계 조회"""
        total_connections = len(self.connected_clients)
        role_counts = {}
        channel_subscriptions = {}
        
        for client in self.connected_clients.values():
            # 역할별 통계
            role_name = client.role.value
            role_counts[role_name] = role_counts.get(role_name, 0) + 1
            
            # 채널별 구독 통계
            for channel in client.subscription_channels:
                channel_subscriptions[channel] = channel_subscriptions.get(channel, 0) + 1
        
        return {
            "total_connections": total_connections,
            "ip_connections": len(self.ip_connections),
            "user_connections": len(self.user_connections),
            "role_distribution": role_counts,
            "channel_subscriptions": channel_subscriptions,
            "max_connections_per_ip": self.MAX_CONNECTIONS_PER_IP,
            "max_connections_per_user": self.MAX_CONNECTIONS_PER_USER
        }
    
    def cleanup_inactive_clients(self, max_inactive_minutes: int = 30):
        """비활성 클라이언트 정리"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=max_inactive_minutes)
        inactive_clients = []
        
        for client_id, client_info in self.connected_clients.items():
            if client_info.last_activity < cutoff_time:
                inactive_clients.append(client_id)
        
        for client_id in inactive_clients:
            logger.info(f"🧹 비활성 클라이언트 정리: {client_id}")
            self.disconnect_client(client_id)
        
        if inactive_clients:
            logger.info(f"🧹 {len(inactive_clients)}개 비활성 클라이언트 정리 완료")

# 전역 인증 관리자 인스턴스
_global_auth_manager = None

def get_auth_manager(jwt_secret: Optional[str] = None) -> WebSocketAuthManager:
    """전역 인증 관리자 인스턴스 반환"""
    global _global_auth_manager
    if _global_auth_manager is None:
        _global_auth_manager = WebSocketAuthManager(jwt_secret)
    return _global_auth_manager

# 테스트 함수
def test_websocket_auth():
    """WebSocket 인증 시스템 테스트"""
    print("=== WebSocket 인증 및 권한 시스템 테스트 ===")
    
    auth_manager = WebSocketAuthManager()
    
    # 1. 토큰 생성 및 검증 테스트
    print("\n1. 토큰 생성 및 검증 테스트:")
    
    # 게스트 토큰
    guest_token = auth_manager.generate_token("guest_user", UserRole.GUEST)
    is_valid, payload = auth_manager.verify_token(guest_token)
    print(f"   게스트 토큰: {'✅ 유효' if is_valid else '❌ 무효'}")
    
    # 관리자 토큰
    admin_token = auth_manager.generate_token("admin_user", UserRole.ADMIN)
    is_valid, payload = auth_manager.verify_token(admin_token)
    print(f"   관리자 토큰: {'✅ 유효' if is_valid else '❌ 무효'}")
    
    # 2. 클라이언트 인증 테스트
    print("\n2. 클라이언트 인증 테스트:")
    
    # 게스트 인증
    success, error, client_info = auth_manager.authenticate_client(
        "client_1", guest_token, "192.168.1.100"
    )
    print(f"   게스트 인증: {'✅ 성공' if success else f'❌ 실패 - {error}'}")
    
    # 관리자 인증
    success, error, admin_info = auth_manager.authenticate_client(
        "client_2", admin_token, "192.168.1.101"
    )
    print(f"   관리자 인증: {'✅ 성공' if success else f'❌ 실패 - {error}'}")
    
    # 3. 권한 테스트
    print("\n3. 채널 권한 테스트:")
    
    channels = ["us_stocks", "us_news", "ai_signals"]
    for channel in channels:
        guest_permission = auth_manager.has_channel_permission("client_1", channel)
        admin_permission = auth_manager.has_channel_permission("client_2", channel)
        
        print(f"   {channel:12}: 게스트={'✅' if guest_permission else '❌'} | "
              f"관리자={'✅' if admin_permission else '❌'}")
    
    # 4. 구독 테스트
    print("\n4. 채널 구독 테스트:")
    
    # 게스트가 AI 시그널 구독 시도 (실패해야 함)
    success, error = auth_manager.subscribe_channel("client_1", "ai_signals")
    print(f"   게스트 -> AI 시그널: {'✅ 성공' if success else f'❌ 실패 - {error}'}")
    
    # 관리자가 AI 시그널 구독 (성공해야 함)
    success, error = auth_manager.subscribe_channel("client_2", "ai_signals")
    print(f"   관리자 -> AI 시그널: {'✅ 성공' if success else f'❌ 실패 - {error}'}")
    
    # 5. 연결 통계
    print("\n5. 연결 통계:")
    stats = auth_manager.get_connection_stats()
    print(f"   총 연결: {stats['total_connections']}개")
    print(f"   역할별: {stats['role_distribution']}")
    print(f"   구독별: {stats['channel_subscriptions']}")

if __name__ == "__main__":
    test_websocket_auth()