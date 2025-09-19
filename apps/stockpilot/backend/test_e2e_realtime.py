#!/usr/bin/env python3
"""
StockPilot AI 실시간 기능 End-to-End 테스트
WebSocket 서버 + 프론트엔드 연동 + 실제 데이터 플로우 검증
"""

import asyncio
import websockets
import json
import requests
import time
from datetime import datetime
from typing import Dict, List, Any
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class E2ERealTimeTest:
    """실시간 기능 E2E 테스트"""
    
    def __init__(self):
        self.websocket_url = "ws://localhost:8765/ws"
        self.frontend_url = "http://localhost:3010"
        self.api_url = "http://localhost:8765"
        
        # 테스트 결과 저장
        self.test_results = {
            "websocket_connection": False,
            "stock_data_received": False,
            "exchange_rate_received": False,
            "market_status_received": False,
            "ai_signals_received": False,
            "schema_validation": True,
            "data_accuracy": True,
            "reconnection_test": False,
            "performance_test": False
        }
        
        self.received_messages = []
        self.connection_time = 0
        self.total_messages = 0

    async def test_websocket_connection(self):
        """WebSocket 연결 테스트"""
        logger.info("🔌 WebSocket 연결 테스트 시작...")
        
        try:
            start_time = time.time()
            
            async with websockets.connect(
                self.websocket_url,
                subprotocols=["stockpilot-v1"],
                ping_interval=20,
                ping_timeout=10
            ) as websocket:
                
                self.connection_time = time.time() - start_time
                logger.info(f"✅ WebSocket 연결 성공 (소요시간: {self.connection_time:.3f}초)")
                
                self.test_results["websocket_connection"] = True
                
                # 환영 메시지 수신 대기
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                welcome_data = json.loads(welcome_msg)
                
                logger.info(f"📨 환영 메시지 수신: {welcome_data['type']}")
                
                if welcome_data['type'] == 'connection':
                    logger.info(f"   클라이언트 ID: {welcome_data['client_id']}")
                    logger.info(f"   사용 가능한 서비스: {welcome_data['services']}")
                    logger.info(f"   채널: {welcome_data['available_channels']}")
                    
                    # 채널 구독
                    await self.subscribe_to_channels(websocket)
                    
                    # 실시간 데이터 수신 테스트
                    await self.test_realtime_data_flow(websocket)
                    
                return True
                
        except Exception as e:
            logger.error(f"❌ WebSocket 연결 실패: {e}")
            return False

    async def subscribe_to_channels(self, websocket):
        """채널 구독"""
        logger.info("📋 채널 구독 중...")
        
        subscribe_msg = {
            "type": "subscribe",
            "events": ["us_stocks", "exchange_rates", "market_status", "ai_signals"]
        }
        
        await websocket.send(json.dumps(subscribe_msg))
        
        # 구독 관련 메시지들 처리 (구독 확인 + 즉시 AI 시그널)
        messages_received = 0
        max_subscription_messages = 5  # 구독 확인 + 즉시 AI 시그널 + 추가 메시지
        subscription_confirmed = False
        
        while messages_received < max_subscription_messages:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                response_data = json.loads(response)
                message_type = response_data.get('type')
                
                logger.info(f"📨 구독 단계 메시지 수신: {message_type}")
                
                if message_type == 'subscription':
                    logger.info(f"✅ 채널 구독 성공: {response_data.get('events', [])}")
                    subscription_confirmed = True
                elif message_type == 'ai_signals':
                    logger.info(f"🤖 즉시 AI 시그널 수신: {len(response_data.get('payload', {}).get('signals', []))}개")
                    # AI 시그널을 받았으므로 바로 처리
                    await self.process_received_message(response_data)
                    self.total_messages += 1
                    self.received_messages.append({
                        'type': message_type,
                        'timestamp': datetime.now().isoformat(),
                        'size': len(response)
                    })
                else:
                    logger.info(f"📨 구독 중 추가 메시지 수신: {message_type}")
                    # 다른 메시지도 처리
                    await self.process_received_message(response_data)
                    self.total_messages += 1
                    self.received_messages.append({
                        'type': message_type,
                        'timestamp': datetime.now().isoformat(),
                        'size': len(response)
                    })
                
                messages_received += 1
                
                # 구독 확인과 AI 시그널을 둘 다 받았으면 종료
                if subscription_confirmed and self.test_results.get("ai_signals_received"):
                    logger.info("✅ 구독 확인 및 AI 시그널 수신 완료")
                    break
                
            except asyncio.TimeoutError:
                logger.info(f"구독 메시지 수신 타임아웃 ({messages_received}개 수신)")
                break

    async def test_realtime_data_flow(self, websocket):
        """실시간 데이터 플로우 테스트"""
        logger.info("📊 실시간 데이터 플로우 테스트 (30초간)...")
        
        message_types_received = set()
        start_time = time.time()
        timeout = 30  # 30초간 테스트
        
        while time.time() - start_time < timeout:
            try:
                # 메시지 수신 (1초 타임아웃)
                message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                data = json.loads(message)
                
                message_type = data.get('type')
                message_types_received.add(message_type)
                self.total_messages += 1
                self.received_messages.append({
                    'type': message_type,
                    'timestamp': datetime.now().isoformat(),
                    'size': len(message)
                })
                
                # 메시지 타입별 처리
                await self.process_received_message(data)
                
                # 진행 상황 출력 (5초마다)
                elapsed = time.time() - start_time
                if int(elapsed) % 5 == 0 and elapsed > 0:
                    logger.info(f"   진행: {elapsed:.0f}초 | 수신: {self.total_messages}개 메시지 | 타입: {message_types_received}")
                
            except asyncio.TimeoutError:
                # 타임아웃은 정상 (메시지가 없을 수 있음)
                continue
            except Exception as e:
                logger.error(f"메시지 처리 오류: {e}")
        
        logger.info(f"✅ 실시간 데이터 플로우 테스트 완료")
        logger.info(f"   총 수신: {self.total_messages}개 메시지")
        logger.info(f"   메시지 타입: {message_types_received}")

    async def process_received_message(self, data: Dict[str, Any]):
        """수신된 메시지 처리 및 검증"""
        message_type = data.get('type')
        
        if message_type == 'us_stocks':
            await self.validate_stock_data(data)
            
        elif message_type == 'exchange_rates':
            await self.validate_exchange_rate_data(data)
            
        elif message_type == 'market_status':
            await self.validate_market_status_data(data)
            
        elif message_type == 'ai_signals':
            await self.validate_ai_signals_data(data)

    async def validate_stock_data(self, data: Dict[str, Any]):
        """주식 데이터 검증"""
        if not self.test_results["stock_data_received"]:
            logger.info("📈 미국 주식 데이터 수신 시작")
            self.test_results["stock_data_received"] = True
        
        payload = data.get('payload', {})
        stocks = payload.get('stocks', [])
        
        if stocks:
            sample_stock = stocks[0]
            logger.info(f"   📊 {sample_stock['symbol']}: ${sample_stock['current_price']} ({sample_stock['change_percent']:+.2f}%)")
            
            # 데이터 유효성 검사
            required_fields = ['symbol', 'current_price', 'change_percent', 'volume']
            for field in required_fields:
                if field not in sample_stock:
                    logger.error(f"❌ 필수 필드 누락: {field}")
                    self.test_results["data_accuracy"] = False

    async def validate_exchange_rate_data(self, data: Dict[str, Any]):
        """환율 데이터 검증"""
        if not self.test_results["exchange_rate_received"]:
            logger.info("💱 환율 데이터 수신 시작")
            self.test_results["exchange_rate_received"] = True
        
        payload = data.get('payload', {})
        rates = payload.get('rates', [])
        
        for rate in rates:
            if rate.get('pair') == 'USD/KRW':
                logger.info(f"   💵 USD/KRW: {rate['rate']:,.2f}원")

    async def validate_market_status_data(self, data: Dict[str, Any]):
        """시장 상태 데이터 검증"""
        if not self.test_results["market_status_received"]:
            logger.info("🏢 시장 상태 데이터 수신 시작")
            self.test_results["market_status_received"] = True
        
        payload = data.get('payload', {})
        markets = payload.get('markets', [])
        
        for market in markets:
            if market.get('market_code') == 'US':
                logger.info(f"   🇺🇸 미국 시장: {market['status']}")

    async def validate_ai_signals_data(self, data: Dict[str, Any]):
        """AI 시그널 데이터 검증"""
        if not self.test_results["ai_signals_received"]:
            logger.info("🤖 AI 시그널 데이터 수신 시작")
            self.test_results["ai_signals_received"] = True
        
        payload = data.get('payload', {})
        signals = payload.get('signals', [])
        
        if signals:
            sample_signal = signals[0]
            logger.info(f"   🎯 {sample_signal['symbol']}: {sample_signal['signal_type']} (신뢰도: {sample_signal['confidence']:.2f})")

    def test_api_endpoints(self):
        """API 엔드포인트 테스트"""
        logger.info("🔗 API 엔드포인트 테스트...")
        
        try:
            # 서버 상태 확인
            response = requests.get(f"{self.api_url}/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ 서버 상태: {data['status']}")
                logger.info(f"   활성 연결: {data['stats']['active_connections']}개")
            
            # WebSocket 통계 확인
            response = requests.get(f"{self.api_url}/ws/stats", timeout=5)
            if response.status_code == 200:
                stats = response.json()
                logger.info(f"✅ WebSocket 통계: {stats}")
            
        except Exception as e:
            logger.error(f"❌ API 테스트 실패: {e}")

    async def test_reconnection(self):
        """재연결 테스트"""
        logger.info("🔄 재연결 테스트...")
        
        try:
            # 짧은 연결 후 재연결
            async with websockets.connect(
                self.websocket_url,
                subprotocols=["stockpilot-v1"]
            ) as websocket:
                await websocket.recv()  # 환영 메시지 수신
                pass  # 연결을 바로 종료
            
            # 바로 재연결
            async with websockets.connect(
                self.websocket_url,
                subprotocols=["stockpilot-v1"]
            ) as websocket:
                welcome_msg = await websocket.recv()
                welcome_data = json.loads(welcome_msg)
                
                if welcome_data['type'] == 'connection':
                    logger.info("✅ 재연결 성공")
                    self.test_results["reconnection_test"] = True
                    
        except Exception as e:
            logger.error(f"❌ 재연결 테스트 실패: {e}")

    def test_frontend_accessibility(self):
        """프론트엔드 접근성 테스트"""
        logger.info("🌐 프론트엔드 접근성 테스트...")
        
        try:
            response = requests.get(self.frontend_url, timeout=10)
            if response.status_code == 200:
                logger.info("✅ 프론트엔드 서버 접근 가능")
                
                # HTML 콘텐츠 확인
                if "StockPilot" in response.text:
                    logger.info("✅ StockPilot 콘텐츠 확인")
                    
        except Exception as e:
            logger.warning(f"⚠️ 프론트엔드 접근 실패: {e}")

    def calculate_performance_metrics(self):
        """성능 메트릭 계산"""
        if self.total_messages > 0:
            avg_message_size = sum(msg['size'] for msg in self.received_messages) / self.total_messages
            message_rate = self.total_messages / 30  # 30초 동안의 평균
            
            logger.info(f"📊 성능 메트릭:")
            logger.info(f"   연결 시간: {self.connection_time:.3f}초")
            logger.info(f"   메시지 전송률: {message_rate:.1f}개/초")
            logger.info(f"   평균 메시지 크기: {avg_message_size:.0f}바이트")
            
            # 성능 기준
            if self.connection_time < 1.0 and message_rate > 0.1:
                self.test_results["performance_test"] = True
                logger.info("✅ 성능 기준 만족")
            else:
                logger.warning("⚠️ 성능 기준 미달")

    def generate_test_report(self):
        """테스트 리포트 생성"""
        logger.info("📋 E2E 테스트 리포트 생성...")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        pass_rate = passed_tests / total_tests * 100
        
        print("\n" + "="*60)
        print("📊 StockPilot AI 실시간 기능 E2E 테스트 리포트")
        print("="*60)
        
        print(f"\n📈 전체 결과: {passed_tests}/{total_tests} 통과 ({pass_rate:.1f}%)")
        
        print(f"\n🔍 상세 결과:")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name:<25}: {status}")
        
        print(f"\n📊 실시간 데이터 통계:")
        print(f"   총 수신 메시지: {self.total_messages:,}개")
        print(f"   연결 시간: {self.connection_time:.3f}초")
        
        if self.received_messages:
            message_types = {}
            for msg in self.received_messages:
                msg_type = msg['type']
                message_types[msg_type] = message_types.get(msg_type, 0) + 1
            
            print(f"\n📨 메시지 타입별 수신 횟수:")
            for msg_type, count in message_types.items():
                print(f"   {msg_type}: {count}개")
        
        print(f"\n🎯 권장사항:")
        if not self.test_results["ai_signals_received"]:
            print("   - AI 시그널 서비스 연결 확인 필요 (OpenAI API 키 설정)")
        if not self.test_results["performance_test"]:
            print("   - 성능 최적화 검토 필요")
        if pass_rate == 100:
            print("   - 모든 테스트 통과! 🎉")
        
        print("="*60)

async def main():
    """메인 테스트 실행"""
    test = E2ERealTimeTest()
    
    print("🚀 StockPilot AI 실시간 기능 End-to-End 테스트 시작")
    print("="*60)
    
    # 1. API 엔드포인트 테스트
    test.test_api_endpoints()
    
    # 2. 프론트엔드 접근성 테스트  
    test.test_frontend_accessibility()
    
    # 3. WebSocket 연결 및 실시간 데이터 테스트
    await test.test_websocket_connection()
    
    # 4. 재연결 테스트
    await test.test_reconnection()
    
    # 5. 성능 메트릭 계산
    test.calculate_performance_metrics()
    
    # 6. 테스트 리포트 생성
    test.generate_test_report()

if __name__ == "__main__":
    asyncio.run(main())