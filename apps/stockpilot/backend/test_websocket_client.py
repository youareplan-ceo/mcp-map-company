#!/usr/bin/env python3
"""
WebSocket 클라이언트 테스트
미국 시장 실시간 데이터 수신 테스트
"""

import asyncio
import websockets
import json
from datetime import datetime

class StockPilotWebSocketClient:
    """StockPilot WebSocket 클라이언트 테스터"""
    
    def __init__(self, uri="ws://localhost:8765/ws"):
        self.uri = uri
        self.websocket = None
        self.connected = False

    async def connect(self):
        """WebSocket 서버에 연결"""
        try:
            print(f"🔌 WebSocket 서버 연결 중: {self.uri}")
            self.websocket = await websockets.connect(
                self.uri,
                subprotocols=["stockpilot-v1"],
                ping_interval=20,
                ping_timeout=10
            )
            self.connected = True
            print("✅ WebSocket 서버 연결 성공!")
            return True
        except Exception as e:
            print(f"❌ WebSocket 연결 실패: {e}")
            return False

    async def send_message(self, message):
        """메시지 전송"""
        if self.connected and self.websocket:
            try:
                await self.websocket.send(json.dumps(message, ensure_ascii=False))
                print(f"📤 메시지 전송: {message['type']}")
            except Exception as e:
                print(f"❌ 메시지 전송 실패: {e}")

    async def listen_messages(self):
        """메시지 수신 대기"""
        if not self.connected or not self.websocket:
            return

        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(data)
                except json.JSONDecodeError as e:
                    print(f"❌ JSON 파싱 실패: {e}")
                except Exception as e:
                    print(f"❌ 메시지 처리 실패: {e}")
        except websockets.exceptions.ConnectionClosed:
            print("🔌 WebSocket 연결이 종료되었습니다.")
            self.connected = False
        except Exception as e:
            print(f"❌ 메시지 수신 오류: {e}")
            self.connected = False

    async def handle_message(self, data):
        """수신된 메시지 처리"""
        message_type = data.get('type')
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if message_type == 'connection':
            print(f"[{timestamp}] 🎉 연결 성공: {data.get('client_id')}")
            print(f"   사용 가능한 서비스: {data.get('services')}")
            print(f"   채널: {data.get('available_channels')}")
            
            # 미국 주식 구독
            await self.subscribe_to_channels(['us_stocks', 'exchange_rates'])
            
        elif message_type == 'subscribed':
            print(f"[{timestamp}] 📋 구독 완료: {data.get('channel')}")
            
        elif message_type == 'us_stocks':
            payload = data.get('payload', {})
            stocks = payload.get('stocks', [])
            print(f"[{timestamp}] 📊 미국 주식 업데이트: {len(stocks)}개")
            
            for stock in stocks[:3]:  # 처음 3개만 출력
                symbol = stock.get('symbol')
                price = stock.get('current_price')
                change_pct = stock.get('change_percent')
                state = stock.get('market_state')
                
                print(f"   {symbol}: ${price:.2f} ({change_pct:+.2f}%) [{state}]")
                
        elif message_type == 'exchange_rates':
            payload = data.get('payload', {})
            rates = payload.get('rates', [])
            print(f"[{timestamp}] 💱 환율 업데이트:")
            
            for rate in rates:
                pair = rate.get('pair')
                rate_value = rate.get('rate')
                change_pct = rate.get('change_percent')
                
                print(f"   {pair}: {rate_value:,.2f} ({change_pct:+.2f}%)")
                
        elif message_type == 'us_news':
            payload = data.get('payload', {})
            news_items = payload.get('news', [])
            print(f"[{timestamp}] 📰 미국 뉴스 업데이트: {len(news_items)}개")
            
            for news in news_items[:2]:  # 처음 2개만 출력
                title = news.get('title', '')[:50]
                sentiment = news.get('sentiment')
                impact = news.get('impact_score')
                
                print(f"   • {title}... [{sentiment}, 영향도: {impact:.2f}]")
                
        elif message_type == 'ai_signals':
            payload = data.get('payload', {})
            signals = payload.get('signals', [])
            print(f"[{timestamp}] 🤖 AI 시그널 업데이트: {len(signals)}개")
            
            for signal in signals:
                symbol = signal.get('symbol')
                signal_type = signal.get('signal_type')
                confidence = signal.get('confidence')
                target = signal.get('target_price')
                
                print(f"   {symbol}: {signal_type} (신뢰도: {confidence:.2f}, 목표: ${target})")
                
        elif message_type == 'market_status':
            payload = data.get('payload', {})
            markets = payload.get('markets', [])
            print(f"[{timestamp}] 🏢 시장 상태 업데이트:")
            
            for market in markets:
                name = market.get('market_name')
                status = market.get('status')
                
                print(f"   {name}: {status}")
                
        elif message_type == 'pong':
            # Pong은 조용히 처리
            pass
            
        else:
            print(f"[{timestamp}] ❓ 알 수 없는 메시지: {message_type}")

    async def subscribe_to_channels(self, channels):
        """채널 구독"""
        message = {
            "type": "subscribe",
            "events": channels
        }
        await self.send_message(message)

    async def send_ping(self):
        """주기적으로 Ping 전송"""
        while self.connected:
            await asyncio.sleep(30)
            if self.connected:
                await self.send_message({"type": "ping"})

    async def close(self):
        """연결 종료"""
        if self.websocket:
            await self.websocket.close()
        self.connected = False
        print("🔌 WebSocket 연결 종료")

async def main():
    """메인 테스트 함수"""
    print("🚀 StockPilot WebSocket 클라이언트 테스트 시작")
    print("=" * 60)
    
    client = StockPilotWebSocketClient()
    
    try:
        # 연결
        if await client.connect():
            # 병렬 작업: 메시지 수신 + Ping 전송
            tasks = [
                asyncio.create_task(client.listen_messages()),
                asyncio.create_task(client.send_ping())
            ]
            
            print("📡 실시간 데이터 수신 중... (Ctrl+C로 종료)")
            print("=" * 60)
            
            # 작업 실행 (사용자가 중단할 때까지)
            await asyncio.gather(*tasks, return_exceptions=True)
            
    except KeyboardInterrupt:
        print("\n⏹️  사용자가 테스트를 중단했습니다.")
    except Exception as e:
        print(f"❌ 테스트 오류: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())