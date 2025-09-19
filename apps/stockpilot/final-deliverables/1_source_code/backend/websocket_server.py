#!/usr/bin/env python3
"""
StockPilot AI - 미국 시장 실시간 WebSocket 서버
Yahoo Finance API + OpenAI 통합 스트리밍
"""

import asyncio
import json
import time
import os
from datetime import datetime, timezone
from typing import Dict, Set, Any, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import logging
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 새로운 유틸리티 임포트
from utils.market_time_calculator import get_current_market_status
from utils.simple_schema_validator import validate_simple_message
from utils.websocket_auth import get_auth_manager, UserRole
from utils.rate_limiter import get_rate_limiter, rate_limit, connection_rate_limit, message_rate_limit

# 미국 시장 서비스 모듈들
from services.us_stock_data import USStockDataService
from services.currency_exchange import CurrencyExchangeService
from services.us_news_analyzer import USNewsAnalyzer
from services.us_ai_signal_generator import USAISignalGenerator
from ai_mock_signals import generate_mock_ai_signals

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="StockPilot WebSocket Server",
    version="1.0.0",
    description="실시간 데이터 스트리밍 서버"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class USMarketConnectionManager:
    """미국 시장 전용 WebSocket 연결 관리자 (인증 통합)"""
    
    def __init__(self):
        # 활성 연결 관리
        self.active_connections: Dict[str, WebSocket] = {}
        
        # 구독 관리 (연결ID -> 구독 이벤트 목록)
        self.subscriptions: Dict[str, Set[str]] = {}
        
        # Ping/Pong 관리
        self.last_pong: Dict[str, float] = {}
        
        # 통계
        self.connection_count = 0
        self.message_count = 0
        
        # 미국 시장 서비스 초기화
        self.stock_service = USStockDataService()
        self.currency_service = CurrencyExchangeService()
        
        # OpenAI 서비스 (있는 경우에만)
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.news_analyzer = None
        self.signal_generator = None
        
        # 실시간 데이터 캐시
        self.data_cache = {
            'us_stocks': {},
            'us_indices': {},
            'exchange_rates': {},
            'us_news': [],
            'ai_signals': []
        }
        
        # 스트리밍 간격 설정 (OpenAI Rate Limit 고려)
        self.streaming_intervals = {
            'us_stocks': 3,      # 3초마다 미국 주식
            'us_indices': 10,    # 10초마다 미국 지수
            'exchange_rates': 30, # 30초마다 환율
            'us_news': 300,      # 5분마다 미국 뉴스
            'ai_signals': 30     # 30초마다 AI 시그널 (Rate Limit 고려)
        }
        
        # AI 시그널 상태 관리
        self.ai_signal_retry_count = 0
        self.ai_signal_max_retries = 3
        self.ai_signal_last_success = None
        self.ai_signal_buffer = []
        self.ai_signal_fallback_enabled = True  # Rate limit 시 Mock 시그널 사용
        self.ai_signal_mock_counter = 0
        
        # 인증 및 권한 관리자 초기화
        jwt_secret = os.getenv('JWT_SECRET_KEY', 'stockpilot-dev-secret-2024')
        self.auth_manager = get_auth_manager(jwt_secret)
        
        # 레이트 리미터 초기화
        self.rate_limiter = get_rate_limiter()
        
        logger.info("🔐 WebSocket 인증 시스템 통합 완료")
        logger.info("⚡ 레이트 리미팅 시스템 통합 완료")

    async def connect(self, websocket: WebSocket, client_id: str, token: str = None, ip_address: str = "unknown"):
        """새 연결 등록 (인증 + 레이트 리미팅)"""
        # 연결 레이트 리미트 검사
        allowed, reason = await self.rate_limiter.check_rate_limit(client_id, "connection", "connect")
        if not allowed:
            await websocket.close(code=1008, reason=f"연결 레이트 리미트 초과: {reason}")
            logger.warning(f"연결 차단: {client_id} - {reason}")
            return
            
        await websocket.accept(subprotocol="stockpilot-v1")
        
        # 기본 연결 설정 (기존 역호호환성)
        self.active_connections[client_id] = websocket
        self.subscriptions[client_id] = set()
        self.last_pong[client_id] = time.time()
        self.connection_count += 1
        
        # 인증 시도 (토큰이 있을 경우)
        user_role = UserRole.ADMIN  # 기본 권한 (기존 동작 유지)
        is_authenticated = False
        
        if token:
            try:
                success, error, client_info = self.auth_manager.authenticate_client(
                    client_id, token, ip_address
                )
                if success and client_info:
                    user_role = client_info.role
                    is_authenticated = True
                    logger.info(f"🔐 클라이언트 인증 성공: {client_id} (role={user_role.value})")
                else:
                    logger.warning(f"⚠️ 토큰 인증 실패: {client_id} - {error}")
                    # 인증 실패시 게스트로 처리
                    user_role = UserRole.GUEST
            except Exception as e:
                logger.error(f"인증 처리 오류: {e}")
                user_role = UserRole.GUEST
        
        logger.info(f"✅ 클라이언트 연결: {client_id} (총 {len(self.active_connections)}개, role={user_role.value})")
        
        # OpenAI 서비스 초기화 (처음 연결시에만)
        if self.openai_api_key and not self.news_analyzer:
            try:
                self.news_analyzer = USNewsAnalyzer(self.openai_api_key)
                await self.news_analyzer.__aenter__()
                
                self.signal_generator = USAISignalGenerator(self.openai_api_key)
                await self.signal_generator.__aenter__()
                
                logger.info("✅ OpenAI 서비스 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ OpenAI 서비스 초기화 실패: {e}")
        
        # 연결 성공 메시지 전송 (권한 정보 포함)
        available_channels = self._get_available_channels_for_role(user_role)
        
        connection_payload = {
            "client_id": client_id,
            "server_version": "2.0.0",
            "services": {
                "stock_data": True,
                "currency_exchange": user_role in [UserRole.BASIC, UserRole.PREMIUM, UserRole.ADMIN],
                "news_analysis": self.news_analyzer is not None and user_role in [UserRole.PREMIUM, UserRole.ADMIN],
                "ai_signals": self.signal_generator is not None and user_role == UserRole.ADMIN
            },
            "available_channels": available_channels,
            "user_role": user_role.value,
            "is_authenticated": is_authenticated
        }
        
        await self.send_to_client(client_id, {
            "type": "connection",
            "payload": connection_payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "schema_version": "1.0"
        })
    
    def _get_available_channels_for_role(self, role: UserRole) -> List[str]:
        """역할에 따른 이용 가능 채널 리스트 반환"""
        channels = []
        
        # 모든 역할이 접근 가능한 채널
        channels.extend(["us_stocks", "market_status"])
        
        # BASIC 이상 배경
        if role in [UserRole.BASIC, UserRole.PREMIUM, UserRole.ADMIN]:
            channels.extend(["us_indices", "exchange_rates"])
        
        # PREMIUM 이상 배경
        if role in [UserRole.PREMIUM, UserRole.ADMIN]:
            channels.append("us_news")
        
        # ADMIN만 접근 가능
        if role == UserRole.ADMIN:
            channels.append("ai_signals")
        
        return channels
    
    def _check_subscription_permission(self, client_id: str, channel: str) -> bool:
        """채널 구독 권한 확인"""
        # 기존 호환성을 위해 auth_manager에 클라이언트가 등록되어 있는지 확인
        client_info = self.auth_manager.get_client_info(client_id)
        if client_info:
            # 인증된 클라이언트는 auth_manager를 통해 권한 확인
            return self.auth_manager.has_channel_permission(client_id, channel)
        else:
            # 비인증 클라이언트는 기본적으로 ADMIN 배경 (기존 동작 유지)
            admin_channels = self._get_available_channels_for_role(UserRole.ADMIN)
            return channel in admin_channels

    def disconnect(self, client_id: str):
        """연결 해제 (인증 상태 정리 포함)"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            
        if client_id in self.subscriptions:
            del self.subscriptions[client_id]
            
        if client_id in self.last_pong:
            del self.last_pong[client_id]
        
        # 인증 관리자에서도 연결 정리
        self.auth_manager.disconnect_client(client_id)
            
        logger.info(f"🔌 클라이언트 연결 해제: {client_id} (총 {len(self.active_connections)}개)")

    async def send_to_client(self, client_id: str, data: Dict[str, Any]):
        """특정 클라이언트에게 메시지 전송"""
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_text(json.dumps(data, ensure_ascii=False))
                self.message_count += 1
                return True
            except Exception as e:
                logger.error(f"❌ 메시지 전송 실패 ({client_id}): {e}")
                self.disconnect(client_id)
                return False
        return False

    async def broadcast(self, event_type: str, data: Dict[str, Any]):
        """구독자들에게 브로드캐스트 (스키마 검증 포함)"""
        message = {
            "type": event_type,
            "payload": data,
            "timestamp": datetime.now().isoformat(),
            "schema_version": "1.0"
        }
        
        # 메시지 스키마 검증
        is_valid, error_msg = validate_simple_message(message)
        if not is_valid:
            logger.warning(f"⚠️ 브로드캐스트 메시지 스키마 검증 실패 ({event_type}): {error_msg}")
            # 검증 실패해도 계속 진행 (프로덕션 환경에서 서비스 중단 방지)
        
        # 해당 이벤트를 구독한 클라이언트들에게만 전송
        subscribers = [
            client_id for client_id, events in self.subscriptions.items()
            if event_type in events
        ]
        
        if subscribers:
            logger.info(f"📡 브로드캐스트: {event_type} -> {len(subscribers)}명 (스키마 검증: {'✅' if is_valid else '⚠️'})")
            
            for client_id in subscribers:
                # 클라이언트별 채널 레이트 리미트 검사
                channel_type = event_type.split(':')[0] if ':' in event_type else event_type
                allowed, reason = await self.rate_limiter.check_rate_limit(client_id, channel_type, "broadcast_receive")
                
                if allowed:
                    await self.send_to_client(client_id, message)
                else:
                    logger.debug(f"클라이언트 {client_id} 브로드캐스트 차단 ({channel_type}): {reason}")

    async def handle_ping(self, client_id: str):
        """Ping 메시지 처리"""
        await self.send_to_client(client_id, {
            "type": "pong",
            "timestamp": time.time()
        })

    async def handle_pong(self, client_id: str):
        """Pong 메시지 처리"""
        self.last_pong[client_id] = time.time()

    async def handle_subscribe(self, client_id: str, events: List[str]):
        """이벤트 구독 처리 (권한 검사 + 레이트 리미팅)"""
        # 구독 요청 레이트 리미트 검사
        allowed, reason = await self.rate_limiter.check_rate_limit(client_id, "connection", "subscribe")
        if not allowed:
            await self.send_error(client_id, "RATE_LIMIT_EXCEEDED", f"구독 요청 제한: {reason}")
            return
            
        if client_id not in self.subscriptions:
            self.subscriptions[client_id] = set()
        
        # 권한 검사 및 필터링
        allowed_events = []
        denied_events = []
        
        for event in events:
            if self._check_subscription_permission(client_id, event):
                self.subscriptions[client_id].add(event)
                allowed_events.append(event)
            else:
                denied_events.append(event)
        
        # 구독 결과 로그
        if allowed_events:
            logger.info(f"📵 구독 성공: {client_id} -> {allowed_events}")
        if denied_events:
            logger.warning(f"⚠️ 구독 거부: {client_id} -> {denied_events} (권한 부족)")
            
        # AI 시그널 구독 시 즉시 Mock 시그널 생성 (E2E 테스트 지원)
        if "ai_signals" in allowed_events and self.ai_signal_fallback_enabled:
            logger.info("🚀 AI 시그널 구독 감지 - 즉시 Mock 시그널 전송")
            
            # Mock 시그널 생성 및 대상 인간 클라이언트에게 전송
            try:
                mock_signals = self._generate_mock_ai_signals()
                
                if mock_signals:
                    signal_payload = {
                        "signals": mock_signals,
                        "market": "US",
                        "count": len(mock_signals),
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "is_mock": True,
                        "reason": "Immediate AI Signals for E2E Testing",
                        "schema_version": "1.0"
                    }
                    
                    # 스키마 검증 후 전송
                    if self._validate_ai_signals_schema(signal_payload):
                        await self.send_to_client(client_id, {
                            "type": "ai_signals",
                            "payload": signal_payload
                        })
                        logger.info(f"✅ 즉시 AI 시그널 전송 완료: {len(mock_signals)}개 시그널 -> {client_id}")
                    else:
                        logger.error(f"❌ 즉시 AI 시그널 스키마 검증 실패")
            except Exception as e:
                logger.error(f"❌ 즉시 AI 시그널 생성 오류: {e}")
        
        # Market Status 구독 시 즉시 시장 상태 전송 (E2E 테스트 지원)
        if "market_status" in events:
            logger.info("🏢 Market Status 구독 감지 - 즉시 시장 상태 전송")
            
            try:
                market_status_data = self._generate_current_market_status()
                await self.send_to_client(client_id, {
                    "type": "market_status",
                    "payload": market_status_data
                })
                logger.info(f"✅ 즉시 시장 상태 전송 완료: {market_status_data['markets'][0]['status']} -> {client_id}")
            except Exception as e:
                logger.error(f"❌ 즉시 시장 상태 생성 오류: {e}")
        
        # 구독 상태 메시지 전송
        subscription_payload = {
            "status": "subscribed" if allowed_events else "failed",
            "events": allowed_events
        }
        
        if denied_events:
            subscription_payload["denied_events"] = denied_events
            subscription_payload["reason"] = "권한 부족"
        
        await self.send_to_client(client_id, {
            "type": "subscription",
            "payload": subscription_payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "schema_version": "1.0"
        })

    async def handle_unsubscribe(self, client_id: str, events: List[str]):
        """이벤트 구독 해제"""
        if client_id in self.subscriptions:
            for event in events:
                self.subscriptions[client_id].discard(event)
                
        logger.info(f"📋 구독 해제: {client_id} -> {events}")
        
        await self.send_to_client(client_id, {
            "type": "subscription",
            "status": "unsubscribed", 
            "events": events
        })

    def get_stats(self):
        """연결 통계 반환"""
        return {
            "active_connections": len(self.active_connections),
            "total_connections": self.connection_count,
            "total_messages": self.message_count,
            "subscriptions": {
                client_id: list(events) 
                for client_id, events in self.subscriptions.items()
            }
        }

    async def start_us_market_streaming(self):
        """미국 시장 실시간 스트리밍 시작"""
        logger.info("🚀 미국 시장 실시간 스트리밍 시작")
        
        # 병렬 스트리밍 작업들
        tasks = [
            asyncio.create_task(self.stream_us_stocks()),
            asyncio.create_task(self.stream_exchange_rates()),
            asyncio.create_task(self.stream_us_market_status())
        ]
        
        # OpenAI 서비스가 가능한 경우 추가 작업
        if self.openai_api_key:
            tasks.extend([
                asyncio.create_task(self.stream_us_news()),
                asyncio.create_task(self.stream_ai_signals())
            ])
            logger.info("📡 AI 시그널 스트리밍 작업 스케줄링됨")
        
        # 모든 스트리밍 작업 시작
        await asyncio.gather(*tasks, return_exceptions=True)

    async def stream_us_stocks(self):
        """미국 주식 실시간 스트리밍"""
        major_us_stocks = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "NFLX"]
        
        while True:
            try:
                stock_updates = []
                
                for symbol in major_us_stocks:
                    stock_data = await self.stock_service.get_stock_info(symbol)
                    if stock_data:
                        stock_dict = {
                            'symbol': stock_data.symbol,
                            'company_name': stock_data.company_name,
                            'current_price': stock_data.current_price,
                            'change': stock_data.change,
                            'change_percent': stock_data.change_percent,
                            'volume': stock_data.volume,
                            'market_cap': stock_data.market_cap,
                            'market_state': stock_data.market_state,
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }
                        stock_updates.append(stock_dict)
                        self.data_cache['us_stocks'][symbol] = stock_dict
                
                # 구독자들에게 브로드캐스트
                if stock_updates:
                    await self.broadcast("us_stocks", {
                        "stocks": stock_updates,
                        "market": "US",
                        "count": len(stock_updates)
                    })
                
                logger.info(f"📊 미국 주식 데이터 업데이트: {len(stock_updates)}개")
                    
            except Exception as e:
                logger.error(f"미국 주식 스트리밍 오류: {e}")
            
            await asyncio.sleep(self.streaming_intervals['us_stocks'])

    async def stream_exchange_rates(self):
        """환율 실시간 스트리밍"""
        while True:
            try:
                usd_krw = await self.currency_service.get_exchange_rate("USD", "KRW")
                
                if usd_krw:
                    exchange_data = {
                        'pair': 'USD/KRW',
                        'rate': usd_krw.rate,
                        'change_percent': usd_krw.change_percent,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    
                    self.data_cache['exchange_rates']['USD/KRW'] = exchange_data
                    
                    await self.broadcast("exchange_rates", {
                        "rates": [exchange_data],
                        "base_currency": "USD"
                    })
                    
                    logger.info(f"💱 환율 업데이트: USD/KRW = {usd_krw.rate}")
                
            except Exception as e:
                logger.error(f"환율 스트리밍 오류: {e}")
            
            await asyncio.sleep(self.streaming_intervals['exchange_rates'])

    async def stream_us_news(self):
        """미국 뉴스 실시간 스트리밍"""
        if not self.news_analyzer:
            return
            
        while True:
            try:
                news_items = await self.news_analyzer.get_latest_us_news(5)
                
                if news_items:
                    news_data = []
                    for news in news_items:
                        news_dict = {
                            'id': news.id,
                            'title': news.title,
                            'summary': news.summary[:200] + "..." if len(news.summary) > 200 else news.summary,
                            'sentiment': news.sentiment,
                            'sentiment_score': news.sentiment_score,
                            'impact_score': news.impact_score,
                            'source': news.source,
                            'published_at': news.published_at.isoformat() if news.published_at else None,
                            'url': news.url
                        }
                        news_data.append(news_dict)
                    
                    self.data_cache['us_news'] = news_data
                    
                    await self.broadcast("us_news", {
                        "news": news_data,
                        "market": "US",
                        "count": len(news_data)
                    })
                    
                    logger.info(f"📰 미국 뉴스 업데이트: {len(news_data)}개")
                
            except Exception as e:
                logger.error(f"미국 뉴스 스트리밍 오류: {e}")
            
            await asyncio.sleep(self.streaming_intervals['us_news'])

    async def stream_ai_signals(self):
        """AI 투자 시그널 실시간 스트리밍 (강화된 다시 시도 및 버퍼링)"""
        if not self.signal_generator:
            logger.warning("⚠️ AI 시그널 생성기가 초기화되지 않음")
            return
            
        logger.info("🤖 AI 시그널 스트리밍 시작 (30초 간격, Rate Limit 고려 + Mock 시그널 지원)")
        
        while True:
            try:
                # AI 시그널 생성 시도
                logger.info("📊 AI 시그널 생성 시작...")
                start_time = time.time()
                
                top_signals = await self.signal_generator.get_top_signals(3)
                
                generation_time = time.time() - start_time
                logger.info(f"⏱️ AI 시그널 생성 소요시간: {generation_time:.2f}초")
                
                if top_signals:
                    # 시그널 데이터 직렬화 및 스키마 검증
                    signals_data = []
                    for signal in top_signals:
                        signal_dict = self._validate_and_serialize_signal(signal)
                        if signal_dict:
                            signals_data.append(signal_dict)
                    
                    if signals_data:
                        # 버퍼에 저장 및 캐시 업데이트
                        self.ai_signal_buffer = signals_data
                        self.data_cache['ai_signals'] = signals_data
                        self.ai_signal_last_success = time.time()
                        
                        # 방송 내용 생성
                        broadcast_payload = {
                            "signals": signals_data,
                            "market": "US",
                            "count": len(signals_data),
                            "generated_at": datetime.now(timezone.utc).isoformat(),
                            "schema_version": "1.0"
                        }
                        
                        # 방송 전 스키마 검증
                        if self._validate_ai_signals_schema(broadcast_payload):
                            await self.broadcast("ai_signals", broadcast_payload)
                            logger.info(f"✅ AI 시그널 성공 다시춤캠스트: {len(signals_data)}개 시그널")
                            self.ai_signal_retry_count = 0  # 성공 시 재시도 수 초기화
                        else:
                            logger.error("❌ AI 시그널 스키마 검증 실패")
                            await self._handle_ai_signal_failure()
                    else:
                        logger.warning("⚠️ 유효한 AI 시그널이 생성되지 않음")
                        await self._handle_ai_signal_failure()
                else:
                    logger.warning("⚠️ AI 시그널 생성 실패 - 빈 결과")
                    await self._handle_ai_signal_failure()
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ AI 시그널 스트리밍 오류: {error_msg}")
                
                # Rate Limit 오류를 제대로 처리
                if "rate limit" in error_msg.lower() or "429" in error_msg:
                    logger.warning("⚠️ OpenAI Rate Limit 감지 - Mock 시그널 사용")
                    mock_signals = self._generate_mock_ai_signals()
                    
                    if mock_signals:
                        broadcast_payload = {
                            "signals": mock_signals,
                            "market": "US",
                            "count": len(mock_signals),
                            "generated_at": datetime.now(timezone.utc).isoformat(),
                            "is_mock": True,
                            "reason": "OpenAI Rate Limit Exceeded"
                        }
                        
                        if self._validate_ai_signals_schema(broadcast_payload):
                            await self.broadcast("ai_signals", broadcast_payload)
                            logger.info(f"✅ Mock AI 시그널 성공 브로드캐스트: {len(mock_signals)}개")
                            continue  # Rate Limit이면 재시도하지 않고 다음 사이클 대기
                
                await self._handle_ai_signal_failure()
            
            # 다음 시그널 생성까지 대기
            await asyncio.sleep(self.streaming_intervals['ai_signals'])
    
    def _validate_and_serialize_signal(self, signal) -> dict:
        """AI 시그널 데이터 검증 및 직렬화"""
        try:
            signal_dict = {
                'id': str(signal.id),
                'symbol': str(signal.symbol),
                'company_name': str(signal.company_name),
                'signal_type': str(signal.signal_type),
                'confidence': float(signal.confidence),
                'strength': str(signal.strength),
                'current_price': float(signal.current_price),
                'target_price': float(signal.target_price) if signal.target_price else None,
                'expected_return': float(signal.expected_return) if signal.expected_return else None,
                'risk_level': str(signal.risk_level),
                'reasoning': str(signal.reasoning),
                'technical_score': float(signal.technical_score),
                'fundamental_score': float(signal.fundamental_score),
                'sentiment_score': float(signal.sentiment_score),
                'created_at': str(signal.created_at),
                'market_state': str(signal.market_state)
            }
            
            # 기본 검증
            if not all([
                signal_dict['id'], 
                signal_dict['symbol'], 
                signal_dict['signal_type'] in ['BUY', 'SELL', 'HOLD'],
                0.0 <= signal_dict['confidence'] <= 1.0,
                signal_dict['current_price'] > 0
            ]):
                logger.warning(f"⚠️ 시그널 기본 검증 실패: {signal_dict['symbol']}")
                return None
                
            return signal_dict
            
        except Exception as e:
            logger.error(f"❌ 시그널 직렬화 오류: {e}")
            return None
    
    def _validate_ai_signals_schema(self, payload: dict) -> bool:
        """AI 시그널 메시지 스키마 검증"""
        try:
            required_fields = ['signals', 'market', 'count', 'generated_at']
            if not all(field in payload for field in required_fields):
                return False
                
            if not isinstance(payload['signals'], list):
                return False
                
            if payload['count'] != len(payload['signals']):
                return False
                
            # 각 시그널의 필수 필드 검증
            for signal in payload['signals']:
                required_signal_fields = ['id', 'symbol', 'signal_type', 'confidence', 'current_price']
                if not all(field in signal for field in required_signal_fields):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 스키마 검증 오류: {e}")
            return False
    
    async def _handle_ai_signal_failure(self):
        """AI 시그널 실패 처리 및 재시도 로직"""
        self.ai_signal_retry_count += 1
        
        if self.ai_signal_retry_count <= self.ai_signal_max_retries:
            logger.warning(f"🔄 AI 시그널 재시도 {self.ai_signal_retry_count}/{self.ai_signal_max_retries}")
            
            # 버퍼에 이전 데이터가 있으면 재사용
            if self.ai_signal_buffer:
                logger.info("💼 버퍼에서 이전 AI 시그널 재발행")
                await self.broadcast("ai_signals", {
                    "signals": self.ai_signal_buffer,
                    "market": "US",
                    "count": len(self.ai_signal_buffer),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "is_retry": True,
                    "retry_count": self.ai_signal_retry_count
                })
        else:
            logger.error(f"❌ AI 시그널 에러 - 최대 재시도 초과 ({self.ai_signal_max_retries}\ucc28례)")
            # 대체 데이터 발송 (에러 상태 알림)
            await self.broadcast("ai_signals", {
                "signals": [],
                "market": "US",
                "count": 0,
                "error": "AI 시그널 생성 서비스 일시적 장애",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "retry_exceeded": True
            })

    def _generate_mock_ai_signals(self) -> list:
        """Rate Limit 시 사용할 Mock AI 시그널 생성"""
        self.ai_signal_mock_counter += 1
        
        # 외부 Mock 시그널 생성기 사용
        signals = generate_mock_ai_signals(self.ai_signal_mock_counter)
        
        logger.info(f"🤖 Mock AI 시그널 {len(signals)}개 생성 완료")
        return signals

    def _generate_current_market_status(self) -> Dict[str, Any]:
        """현재 시장 상태 생성 (정확한 시간 계산기 사용)"""
        try:
            # 정확한 시장 시간 계산기 사용
            market_status_data = get_current_market_status()
            
            # WebSocket 형식으로 변환
            return {"markets": [market_status_data]}
            
        except Exception as e:
            logger.error(f"시장 상태 계산 오류: {e}")
            
            # 폴백: 기본 시장 상태
            current_time = datetime.now(timezone.utc)
            fallback_data = {
                "market_code": "US",
                "market_name": "미국 시장 (폴백)",
                "status": "CLOSED",
                "timezone": "America/New_York",
                "timezone_name": "EST",
                "utc_offset": "-05:00",
                "is_dst": False,
                "local_time": current_time.isoformat(),
                "timestamp": current_time.isoformat(),
                "description": "시장 시간 계산 오류 - 기본값 사용"
            }
            
            return {"markets": [fallback_data]}

    async def stream_us_market_status(self):
        """미국 시장 상태 스트리밍"""
        while True:
            try:
                current_time = datetime.now(timezone.utc)
                
                # 간단한 시장 상태 계산 (동부 표준시 기준)
                # 현재는 UTC이므로 EST(-5)와 EDT(-4) 고려하여 대략적으로 계산
                est_hour = (current_time.hour - 5) % 24
                
                if 9 <= est_hour < 16:
                    market_status = "OPEN"
                elif 4 <= est_hour < 9:
                    market_status = "PRE_MARKET"
                elif 16 <= est_hour < 20:
                    market_status = "AFTER_HOURS"
                else:
                    market_status = "CLOSED"
                
                market_data = {
                    "market_code": "US",
                    "market_name": "미국 시장",
                    "status": market_status,
                    "timezone": "US/Eastern",
                    "open_time": "09:30",
                    "close_time": "16:00",
                    "current_time": current_time.isoformat(),
                    "timestamp": current_time.isoformat()
                }
                
                await self.broadcast("market_status", {
                    "markets": [market_data]
                })
                
                logger.info(f"🏢 미국 시장 상태: {market_status} (EST: {est_hour}시)")
                
            except Exception as e:
                logger.error(f"시장 상태 스트리밍 오류: {e}")
            
            await asyncio.sleep(600)  # 10분마다

# 전역 연결 관리자
manager = USMarketConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 엔드포인트"""
    
    # 클라이언트 ID 생성
    client_id = f"client_{int(time.time() * 1000)}_{id(websocket)}"
    
    try:
        # 연결 설정
        await manager.connect(websocket, client_id)
        
        while True:
            # 메시지 수신 대기
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "ping":
                    await manager.handle_ping(client_id)
                    
                elif message_type == "pong":
                    await manager.handle_pong(client_id)
                    
                elif message_type == "subscribe":
                    events = message.get("events", [])
                    await manager.handle_subscribe(client_id, events)
                    
                elif message_type == "unsubscribe":
                    events = message.get("events", [])
                    await manager.handle_unsubscribe(client_id, events)
                    
                else:
                    logger.warning(f"⚠️ 알 수 없는 메시지 타입: {message_type}")
                    
            except json.JSONDecodeError:
                logger.error(f"❌ JSON 파싱 실패: {data}")
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"❌ WebSocket 에러 ({client_id}): {e}")
        manager.disconnect(client_id)

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "StockPilot WebSocket Server",
        "version": "1.0.0",
        "status": "running",
        "stats": manager.get_stats()
    }

@app.get("/ws/stats")
async def websocket_stats():
    """WebSocket 통계"""
    return manager.get_stats()

@app.get("/ws/rate-limit-stats")
async def rate_limit_stats():
    """레이트 리미팅 통계"""
    return manager.rate_limiter.get_global_stats()

@app.post("/ws/rate-limit/block-client")
async def block_client(client_id: str, duration_seconds: int = 600, reason: str = "관리자 차단"):
    """클라이언트 수동 차단"""
    manager.rate_limiter.manually_block_client(client_id, duration_seconds, reason)
    return {"status": "blocked", "client_id": client_id, "duration": duration_seconds}

@app.post("/ws/rate-limit/unblock-client")
async def unblock_client(client_id: str, reason: str = "관리자 차단 해제"):
    """클라이언트 차단 해제"""
    manager.rate_limiter.manually_unblock_client(client_id, reason)
    return {"status": "unblocked", "client_id": client_id}

@app.get("/ws/rate-limit/client-status/{client_id}")
async def client_rate_limit_status(client_id: str):
    """특정 클라이언트 레이트 리미트 상태"""
    return manager.rate_limiter.get_client_status(client_id)

# 백그라운드 태스크들
async def broadcast_system_status():
    """시스템 상태 브로드캐스트 (30초마다)"""
    while True:
        await asyncio.sleep(30)
        
        status_data = {
            "overall_status": "operational",
            "services": {
                "api": "online",
                "database": "online", 
                "ai_engine": "online",
                "websocket": "online",
                "batch_system": "online"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        await manager.broadcast("system:status", status_data)

async def broadcast_usage_stats():
    """사용량 통계 브로드캐스트 (1분마다)"""
    while True:
        await asyncio.sleep(60)
        
        usage_data = {
            "daily_cost": 2.45,
            "requests_count": 127,
            "usage_percent": 24.5,
            "timestamp": datetime.now().isoformat()
        }
        
        await manager.broadcast("system:usage", usage_data)

async def broadcast_price_updates():
    """주가 업데이트 브로드캐스트 (5초마다)"""
    import random
    
    symbols = ["005930", "000660", "035420", "005380", "051910"]
    
    while True:
        await asyncio.sleep(5)
        
        # 랜덤 주식 선택
        symbol = random.choice(symbols)
        base_price = 75000 if symbol == "005930" else random.randint(10000, 100000)
        
        price_data = {
            "symbol": symbol,
            "price": base_price + random.randint(-1000, 1000),
            "change": random.randint(-500, 500),
            "change_percent": round(random.uniform(-2.0, 2.0), 2),
            "volume": random.randint(100000, 1000000),
            "timestamp": datetime.now().isoformat()
        }
        
        await manager.broadcast("price:update", price_data)

async def broadcast_signal_updates():
    """투자 시그널 브로드캐스트 (2분마다)"""
    import random
    
    while True:
        await asyncio.sleep(120)
        
        signal_data = {
            "id": f"signal_{int(time.time())}",
            "symbol": "005930",
            "signal": random.choice(["BUY", "SELL", "HOLD"]),
            "strength": random.choice(["HIGH", "MEDIUM", "LOW"]),
            "confidence": round(random.uniform(0.6, 0.95), 2),
            "timestamp": datetime.now().isoformat()
        }
        
        await manager.broadcast("signal:update", signal_data)

async def broadcast_market_status():
    """시장 상태 브로드캐스트 (10분마다)"""
    while True:
        await asyncio.sleep(600)
        
        current_hour = datetime.now().hour
        
        # 시장 상태 결정
        if 9 <= current_hour < 15:
            status = "OPEN"
        elif 8 <= current_hour < 9:
            status = "PRE_MARKET"
        elif 15 <= current_hour < 18:
            status = "AFTER_HOURS"
        else:
            status = "CLOSED"
        
        market_data = {
            "market": "KOSPI",
            "status": status,
            "next_open": "09:00:00",
            "next_close": "15:30:00", 
            "timestamp": datetime.now().isoformat()
        }
        
        await manager.broadcast("market:status", market_data)

# 애플리케이션 시작시 미국 시장 스트리밍 실행
@app.on_event("startup")
async def startup_event():
    """앱 시작시 미국 시장 스트리밍 시작"""
    logger.info("🚀 StockPilot AI - 미국 시장 WebSocket 서버 시작")
    
    # 미국 시장 스트리밍 시작
    asyncio.create_task(manager.start_us_market_streaming())
    
    # 레이트 리미터 백그라운드 작업 시작
    asyncio.create_task(manager.rate_limiter.start_cleanup_task())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)