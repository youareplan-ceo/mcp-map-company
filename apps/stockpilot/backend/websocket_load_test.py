"""
WebSocket 서버 부하 테스트 도구
1000+ 동시 연결 시뮬레이션 및 성능 검증
"""

import asyncio
import websockets
import json
import time
import psutil
import threading
from datetime import datetime
from typing import List, Dict, Any
import logging
from concurrent.futures import ThreadPoolExecutor
import gc

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WebSocketLoadTester:
    """WebSocket 부하 테스트 클래스"""
    
    def __init__(self, ws_url: str = "ws://localhost:8001/ws"):
        self.ws_url = ws_url
        self.connections: List[websockets.WebSocketServerProtocol] = []
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'failed_connections': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'total_bytes_sent': 0,
            'total_bytes_received': 0,
            'connection_errors': 0,
            'start_time': None,
            'end_time': None,
            'memory_usage': [],
            'cpu_usage': [],
        }
        self.is_running = False
        
    async def create_connection(self, connection_id: int) -> Dict[str, Any]:
        """개별 WebSocket 연결 생성"""
        connection_stats = {
            'id': connection_id,
            'connected': False,
            'messages_sent': 0,
            'messages_received': 0,
            'connection_time': None,
            'last_ping_time': None,
            'errors': []
        }
        
        try:
            start_time = time.time()
            
            # WebSocket 연결 시도
            websocket = await websockets.connect(
                self.ws_url,
                subprotocols=["stockpilot-v1"],
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10,
                max_size=10**6,  # 1MB
                max_queue=32
            )
            
            connection_time = time.time() - start_time
            connection_stats['connected'] = True
            connection_stats['connection_time'] = connection_time
            
            self.connections.append(websocket)
            self.stats['active_connections'] += 1
            
            logger.info(f"✅ 연결 {connection_id} 성공 ({connection_time:.3f}s)")
            
            # 구독 메시지 전송
            subscribe_message = {
                "type": "subscribe",
                "events": ["price:update", "signal:update", "system:status"]
            }
            
            await websocket.send(json.dumps(subscribe_message))
            connection_stats['messages_sent'] += 1
            self.stats['messages_sent'] += 1
            
            # 메시지 수신 대기 (비동기)
            asyncio.create_task(self.listen_messages(websocket, connection_stats))
            
            # 주기적으로 ping 전송
            asyncio.create_task(self.send_periodic_ping(websocket, connection_stats))
            
            return connection_stats
            
        except Exception as e:
            self.stats['failed_connections'] += 1
            self.stats['connection_errors'] += 1
            connection_stats['errors'].append(str(e))
            logger.error(f"❌ 연결 {connection_id} 실패: {e}")
            return connection_stats
    
    async def listen_messages(self, websocket, connection_stats: Dict[str, Any]):
        """메시지 수신 처리"""
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    connection_stats['messages_received'] += 1
                    self.stats['messages_received'] += 1
                    self.stats['total_bytes_received'] += len(message.encode('utf-8'))
                    
                    # Pong 응답 처리
                    if data.get('type') == 'pong':
                        connection_stats['last_ping_time'] = time.time()
                        
                except json.JSONDecodeError:
                    logger.warning(f"JSON 파싱 실패: {message[:100]}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"연결 {connection_stats['id']} 종료됨")
            self.stats['active_connections'] -= 1
        except Exception as e:
            logger.error(f"메시지 수신 에러 (연결 {connection_stats['id']}): {e}")
            connection_stats['errors'].append(str(e))
    
    async def send_periodic_ping(self, websocket, connection_stats: Dict[str, Any]):
        """주기적 ping 전송"""
        while not websocket.closed:
            try:
                await asyncio.sleep(30)  # 30초마다 ping
                
                ping_message = {
                    "type": "ping",
                    "timestamp": time.time()
                }
                
                await websocket.send(json.dumps(ping_message))
                connection_stats['messages_sent'] += 1
                self.stats['messages_sent'] += 1
                self.stats['total_bytes_sent'] += len(json.dumps(ping_message).encode('utf-8'))
                
            except websockets.exceptions.ConnectionClosed:
                break
            except Exception as e:
                logger.error(f"Ping 전송 실패 (연결 {connection_stats['id']}): {e}")
                connection_stats['errors'].append(str(e))
    
    def monitor_system_resources(self):
        """시스템 리소스 모니터링"""
        while self.is_running:
            try:
                # 메모리 사용량
                memory_info = psutil.virtual_memory()
                memory_usage = {
                    'percent': memory_info.percent,
                    'used_mb': memory_info.used / 1024 / 1024,
                    'available_mb': memory_info.available / 1024 / 1024,
                    'timestamp': time.time()
                }
                
                # CPU 사용량
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_usage = {
                    'percent': cpu_percent,
                    'timestamp': time.time()
                }
                
                self.stats['memory_usage'].append(memory_usage)
                self.stats['cpu_usage'].append(cpu_usage)
                
                # 경고 체크
                if memory_usage['percent'] > 90:
                    logger.warning(f"⚠️ 높은 메모리 사용률: {memory_usage['percent']:.1f}%")
                
                if cpu_percent > 80:
                    logger.warning(f"⚠️ 높은 CPU 사용률: {cpu_percent:.1f}%")
                
                time.sleep(5)  # 5초마다 체크
                
            except Exception as e:
                logger.error(f"시스템 모니터링 에러: {e}")
    
    async def run_load_test(self, total_connections: int = 1000, batch_size: int = 50, batch_delay: float = 0.1):
        """부하 테스트 실행"""
        logger.info(f"🚀 WebSocket 부하 테스트 시작")
        logger.info(f"총 연결 수: {total_connections}, 배치 크기: {batch_size}, 배치 지연: {batch_delay}s")
        
        self.is_running = True
        self.stats['start_time'] = time.time()
        
        # 시스템 리소스 모니터링 시작
        monitor_thread = threading.Thread(target=self.monitor_system_resources)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        connection_results = []
        
        try:
            # 배치별로 연결 생성
            for batch_start in range(0, total_connections, batch_size):
                batch_end = min(batch_start + batch_size, total_connections)
                batch_connections = batch_end - batch_start
                
                logger.info(f"📦 배치 {batch_start//batch_size + 1}: {batch_connections}개 연결 생성 중...")
                
                # 배치 내 연결들을 동시에 생성
                tasks = []
                for i in range(batch_start, batch_end):
                    task = asyncio.create_task(self.create_connection(i))
                    tasks.append(task)
                
                # 배치 완료 대기
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                connection_results.extend(batch_results)
                
                self.stats['total_connections'] = batch_end
                
                logger.info(f"✅ 배치 완료. 총 연결: {self.stats['total_connections']}, "
                           f"활성: {self.stats['active_connections']}, "
                           f"실패: {self.stats['failed_connections']}")
                
                # 배치 간 지연
                if batch_end < total_connections:
                    await asyncio.sleep(batch_delay)
                
                # 가비지 컬렉션
                gc.collect()
            
            # 테스트 지속 시간 (30초)
            logger.info("🔄 연결 안정성 테스트 중... (30초)")
            await asyncio.sleep(30)
            
            # 일부 연결 종료 테스트
            logger.info("🔌 연결 종료 테스트 중...")
            close_count = min(100, len(self.connections) // 10)  # 10% 연결 종료
            
            for i in range(close_count):
                if i < len(self.connections):
                    try:
                        await self.connections[i].close()
                        self.stats['active_connections'] -= 1
                    except Exception as e:
                        logger.error(f"연결 종료 실패: {e}")
            
            await asyncio.sleep(5)  # 정리 시간
            
        except Exception as e:
            logger.error(f"부하 테스트 중 에러: {e}")
        
        finally:
            self.is_running = False
            self.stats['end_time'] = time.time()
            
            # 남은 연결들 정리
            logger.info("🧹 연결 정리 중...")
            for ws in self.connections:
                try:
                    if not ws.closed:
                        await ws.close()
                except Exception:
                    pass
            
            # 결과 분석
            self.analyze_results(connection_results)
    
    def analyze_results(self, connection_results: List[Dict[str, Any]]):
        """테스트 결과 분석"""
        test_duration = self.stats['end_time'] - self.stats['start_time']
        
        # 연결 시간 통계
        connection_times = [r['connection_time'] for r in connection_results 
                          if isinstance(r, dict) and r.get('connected') and r.get('connection_time')]
        
        avg_connection_time = sum(connection_times) / len(connection_times) if connection_times else 0
        max_connection_time = max(connection_times) if connection_times else 0
        min_connection_time = min(connection_times) if connection_times else 0
        
        # 메모리 사용량 통계
        memory_stats = self.stats['memory_usage']
        if memory_stats:
            avg_memory = sum(m['percent'] for m in memory_stats) / len(memory_stats)
            max_memory = max(m['percent'] for m in memory_stats)
            peak_memory_mb = max(m['used_mb'] for m in memory_stats)
        else:
            avg_memory = max_memory = peak_memory_mb = 0
        
        # CPU 사용량 통계
        cpu_stats = self.stats['cpu_usage']
        if cpu_stats:
            avg_cpu = sum(c['percent'] for c in cpu_stats) / len(cpu_stats)
            max_cpu = max(c['percent'] for c in cpu_stats)
        else:
            avg_cpu = max_cpu = 0
        
        # 메시지 처리량
        total_messages = self.stats['messages_sent'] + self.stats['messages_received']
        message_rate = total_messages / test_duration if test_duration > 0 else 0
        
        # 결과 출력
        print("\n" + "="*60)
        print("🚀 WEBSOCKET 부하 테스트 결과")
        print("="*60)
        
        print(f"\n📊 연결 통계:")
        print(f"  • 총 연결 시도: {self.stats['total_connections']}")
        print(f"  • 성공한 연결: {self.stats['total_connections'] - self.stats['failed_connections']}")
        print(f"  • 실패한 연결: {self.stats['failed_connections']}")
        print(f"  • 성공률: {((self.stats['total_connections'] - self.stats['failed_connections']) / self.stats['total_connections'] * 100):.1f}%")
        
        print(f"\n⏱️ 성능 지표:")
        print(f"  • 테스트 지속 시간: {test_duration:.1f}초")
        print(f"  • 평균 연결 시간: {avg_connection_time:.3f}초")
        print(f"  • 최대 연결 시간: {max_connection_time:.3f}초")
        print(f"  • 최소 연결 시간: {min_connection_time:.3f}초")
        
        print(f"\n📨 메시지 통계:")
        print(f"  • 전송된 메시지: {self.stats['messages_sent']:,}")
        print(f"  • 수신된 메시지: {self.stats['messages_received']:,}")
        print(f"  • 총 메시지: {total_messages:,}")
        print(f"  • 메시지 처리율: {message_rate:.1f} msg/sec")
        
        print(f"\n💾 리소스 사용량:")
        print(f"  • 평균 메모리 사용률: {avg_memory:.1f}%")
        print(f"  • 최대 메모리 사용률: {max_memory:.1f}%")
        print(f"  • 피크 메모리 사용량: {peak_memory_mb:.1f}MB")
        print(f"  • 평균 CPU 사용률: {avg_cpu:.1f}%")
        print(f"  • 최대 CPU 사용률: {max_cpu:.1f}%")
        
        print(f"\n🔢 데이터 전송:")
        print(f"  • 전송된 데이터: {self.stats['total_bytes_sent'] / 1024:.1f}KB")
        print(f"  • 수신된 데이터: {self.stats['total_bytes_received'] / 1024:.1f}KB")
        
        print(f"\n❌ 에러 통계:")
        print(f"  • 연결 에러: {self.stats['connection_errors']}")
        
        # 성능 등급 평가
        print(f"\n🏆 성능 등급:")
        success_rate = (self.stats['total_connections'] - self.stats['failed_connections']) / self.stats['total_connections'] * 100
        
        if success_rate >= 99 and avg_connection_time < 0.1 and max_memory < 80:
            grade = "🥇 EXCELLENT"
        elif success_rate >= 95 and avg_connection_time < 0.2 and max_memory < 90:
            grade = "🥈 GOOD"
        elif success_rate >= 90 and avg_connection_time < 0.5:
            grade = "🥉 FAIR"
        else:
            grade = "❌ NEEDS IMPROVEMENT"
        
        print(f"  {grade}")
        
        print("\n" + "="*60)

async def main():
    """메인 테스트 실행"""
    tester = WebSocketLoadTester()
    
    # 테스트 파라미터
    TOTAL_CONNECTIONS = 500  # 1000개 연결 (메모리 고려하여 500으로 조정)
    BATCH_SIZE = 25          # 배치 크기
    BATCH_DELAY = 0.05       # 배치 간 지연
    
    try:
        await tester.run_load_test(
            total_connections=TOTAL_CONNECTIONS,
            batch_size=BATCH_SIZE,
            batch_delay=BATCH_DELAY
        )
    except KeyboardInterrupt:
        print("\n사용자에 의해 테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n테스트 실행 중 에러: {e}")

if __name__ == "__main__":
    print("🚀 StockPilot WebSocket 부하 테스트 도구")
    print("=" * 50)
    asyncio.run(main())