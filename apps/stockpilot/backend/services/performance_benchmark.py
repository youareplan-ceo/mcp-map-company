#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StockPilot 성능 벤치마크 시스템
동시 사용자 1000명 부하 테스트 및 성능 최적화
"""

import asyncio
import websockets
import aiohttp
import time
import psutil
import json
import statistics
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/stockpilot/benchmark.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class BenchmarkResult:
    """벤치마크 결과 데이터 구조"""
    test_type: str
    start_time: datetime
    end_time: datetime
    duration: float
    concurrent_users: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    cpu_usage_avg: float
    memory_usage_avg: float
    errors: List[str]

class PerformanceBenchmark:
    """성능 벤치마크 관리자"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            'websocket_url': 'ws://localhost:8765',
            'api_base_url': 'http://localhost:8000',
            'max_concurrent_users': 1000,
            'test_duration': 300,  # 5분
            'ramp_up_time': 60,    # 1분
            'cpu_memory_interval': 1.0
        }
        self.results: List[BenchmarkResult] = []
        self.is_running = False
        
    async def run_websocket_load_test(self, concurrent_users: int = 1000) -> BenchmarkResult:
        """WebSocket 연결 부하 테스트"""
        logger.info(f"WebSocket 부하 테스트 시작 - 동시 사용자: {concurrent_users}")
        
        start_time = datetime.now()
        response_times = []
        successful_connections = 0
        failed_connections = 0
        errors = []
        
        # 시스템 리소스 모니터링 시작
        cpu_memory_task = asyncio.create_task(self._monitor_system_resources())
        
        async def connect_client(client_id: int):
            """개별 WebSocket 클라이언트 연결"""
            try:
                connect_start = time.time()
                
                async with websockets.connect(
                    self.config['websocket_url'],
                    timeout=10,
                    ping_interval=20,
                    ping_timeout=10
                ) as websocket:
                    connect_time = time.time() - connect_start
                    response_times.append(connect_time)
                    
                    # 테스트 메시지 전송
                    test_message = {
                        "type": "subscribe",
                        "symbols": ["AAPL", "GOOGL", "MSFT"],
                        "client_id": client_id
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    response = await websocket.recv()
                    
                    # 연결 유지 (테스트 지속 시간)
                    await asyncio.sleep(self.config['test_duration'] / concurrent_users)
                    
                    return True
                    
            except Exception as e:
                errors.append(f"Client {client_id}: {str(e)}")
                return False
        
        # 점진적 부하 증가 (Ramp-up)
        tasks = []
        ramp_interval = self.config['ramp_up_time'] / concurrent_users
        
        for i in range(concurrent_users):
            task = asyncio.create_task(connect_client(i))
            tasks.append(task)
            
            if i % 10 == 0:  # 10개씩 묶어서 지연
                await asyncio.sleep(ramp_interval * 10)
        
        # 모든 클라이언트 완료 대기
        results = await asyncio.gather(*tasks, return_exceptions=True)
        cpu_memory_task.cancel()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 결과 집계
        successful_connections = sum(1 for r in results if r is True)
        failed_connections = len(results) - successful_connections
        
        avg_cpu, avg_memory = await self._get_avg_system_usage()
        
        return BenchmarkResult(
            test_type="websocket_load_test",
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            concurrent_users=concurrent_users,
            total_requests=len(results),
            successful_requests=successful_connections,
            failed_requests=failed_connections,
            avg_response_time=statistics.mean(response_times) if response_times else 0,
            min_response_time=min(response_times) if response_times else 0,
            max_response_time=max(response_times) if response_times else 0,
            p95_response_time=np.percentile(response_times, 95) if response_times else 0,
            p99_response_time=np.percentile(response_times, 99) if response_times else 0,
            requests_per_second=successful_connections / duration if duration > 0 else 0,
            cpu_usage_avg=avg_cpu,
            memory_usage_avg=avg_memory,
            errors=errors[:50]  # 최대 50개 에러만 저장
        )
    
    async def run_api_load_test(self, concurrent_users: int = 500) -> BenchmarkResult:
        """REST API 부하 테스트"""
        logger.info(f"API 부하 테스트 시작 - 동시 사용자: {concurrent_users}")
        
        start_time = datetime.now()
        response_times = []
        successful_requests = 0
        failed_requests = 0
        errors = []
        
        # 시스템 리소스 모니터링 시작
        cpu_memory_task = asyncio.create_task(self._monitor_system_resources())
        
        async def make_api_request(session: aiohttp.ClientSession, request_id: int):
            """개별 API 요청"""
            try:
                request_start = time.time()
                
                # 다양한 엔드포인트 테스트
                endpoints = [
                    '/api/v1/stocks/AAPL/analysis',
                    '/api/v1/portfolio/optimize',
                    '/api/v1/signals/latest',
                    '/api/v1/market/summary'
                ]
                
                endpoint = endpoints[request_id % len(endpoints)]
                url = f"{self.config['api_base_url']}{endpoint}"
                
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    await response.text()
                    request_time = time.time() - request_start
                    response_times.append(request_time)
                    
                    if response.status == 200:
                        return True
                    else:
                        errors.append(f"Request {request_id}: HTTP {response.status}")
                        return False
                        
            except Exception as e:
                errors.append(f"Request {request_id}: {str(e)}")
                return False
        
        # 동시 요청 실행
        connector = aiohttp.TCPConnector(limit=concurrent_users, limit_per_host=concurrent_users)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = []
            
            for i in range(concurrent_users):
                task = asyncio.create_task(make_api_request(session, i))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        cpu_memory_task.cancel()
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 결과 집계
        successful_requests = sum(1 for r in results if r is True)
        failed_requests = len(results) - successful_requests
        
        avg_cpu, avg_memory = await self._get_avg_system_usage()
        
        return BenchmarkResult(
            test_type="api_load_test",
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            concurrent_users=concurrent_users,
            total_requests=len(results),
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=statistics.mean(response_times) if response_times else 0,
            min_response_time=min(response_times) if response_times else 0,
            max_response_time=max(response_times) if response_times else 0,
            p95_response_time=np.percentile(response_times, 95) if response_times else 0,
            p99_response_time=np.percentile(response_times, 99) if response_times else 0,
            requests_per_second=successful_requests / duration if duration > 0 else 0,
            cpu_usage_avg=avg_cpu,
            memory_usage_avg=avg_memory,
            errors=errors[:50]
        )
    
    async def run_openai_optimization_benchmark(self) -> BenchmarkResult:
        """OpenAI API 호출 최적화 벤치마크"""
        logger.info("OpenAI API 최적화 벤치마크 시작")
        
        start_time = datetime.now()
        response_times = []
        successful_requests = 0
        failed_requests = 0
        errors = []
        
        # 시스템 리소스 모니터링 시작
        cpu_memory_task = asyncio.create_task(self._monitor_system_resources())
        
        # OpenAI API 테스트 시나리오
        test_scenarios = [
            {
                "model": "gpt-3.5-turbo",
                "max_tokens": 150,
                "temperature": 0.3,
                "prompt": "Analyze AAPL stock performance"
            },
            {
                "model": "gpt-4",
                "max_tokens": 200,
                "temperature": 0.5,
                "prompt": "Generate investment recommendation"
            },
            {
                "model": "gpt-3.5-turbo",
                "max_tokens": 100,
                "temperature": 0.1,
                "prompt": "Summarize market news"
            }
        ]
        
        async def test_openai_call(scenario: Dict, call_id: int):
            """개별 OpenAI API 호출 테스트"""
            try:
                from services.ai_engine import AIEngine
                
                ai_engine = AIEngine()
                call_start = time.time()
                
                # 실제 OpenAI API 호출 시뮬레이션
                response = await ai_engine.generate_analysis(
                    symbol="AAPL",
                    prompt=scenario["prompt"],
                    model=scenario["model"],
                    max_tokens=scenario["max_tokens"],
                    temperature=scenario["temperature"]
                )
                
                call_time = time.time() - call_start
                response_times.append(call_time)
                
                if response and len(response) > 0:
                    return True
                else:
                    errors.append(f"OpenAI call {call_id}: Empty response")
                    return False
                    
            except Exception as e:
                errors.append(f"OpenAI call {call_id}: {str(e)}")
                return False
        
        # 다양한 시나리오로 테스트
        tasks = []
        for i in range(50):  # 50개의 테스트 호출
            scenario = test_scenarios[i % len(test_scenarios)]
            task = asyncio.create_task(test_openai_call(scenario, i))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        cpu_memory_task.cancel()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 결과 집계
        successful_requests = sum(1 for r in results if r is True)
        failed_requests = len(results) - successful_requests
        
        avg_cpu, avg_memory = await self._get_avg_system_usage()
        
        return BenchmarkResult(
            test_type="openai_optimization_benchmark",
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            concurrent_users=len(tasks),
            total_requests=len(results),
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=statistics.mean(response_times) if response_times else 0,
            min_response_time=min(response_times) if response_times else 0,
            max_response_time=max(response_times) if response_times else 0,
            p95_response_time=np.percentile(response_times, 95) if response_times else 0,
            p99_response_time=np.percentile(response_times, 99) if response_times else 0,
            requests_per_second=successful_requests / duration if duration > 0 else 0,
            cpu_usage_avg=avg_cpu,
            memory_usage_avg=avg_memory,
            errors=errors
        )
    
    async def _monitor_system_resources(self):
        """시스템 리소스 모니터링"""
        self.cpu_readings = []
        self.memory_readings = []
        
        try:
            while True:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_info = psutil.virtual_memory()
                
                self.cpu_readings.append(cpu_percent)
                self.memory_readings.append(memory_info.percent)
                
                await asyncio.sleep(self.config['cpu_memory_interval'])
        except asyncio.CancelledError:
            pass
    
    async def _get_avg_system_usage(self) -> Tuple[float, float]:
        """평균 시스템 사용량 계산"""
        avg_cpu = statistics.mean(self.cpu_readings) if self.cpu_readings else 0
        avg_memory = statistics.mean(self.memory_readings) if self.memory_readings else 0
        return avg_cpu, avg_memory
    
    def generate_performance_report(self, results: List[BenchmarkResult]) -> str:
        """성능 벤치마크 리포트 생성"""
        report = []
        report.append("=" * 80)
        report.append("StockPilot 성능 벤치마크 리포트")
        report.append("=" * 80)
        report.append(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        for result in results:
            report.append(f"테스트 유형: {result.test_type}")
            report.append(f"테스트 시간: {result.start_time.strftime('%Y-%m-%d %H:%M:%S')} - {result.end_time.strftime('%H:%M:%S')}")
            report.append(f"지속 시간: {result.duration:.2f}초")
            report.append(f"동시 사용자: {result.concurrent_users}")
            report.append(f"총 요청: {result.total_requests}")
            report.append(f"성공 요청: {result.successful_requests} ({result.successful_requests/result.total_requests*100:.1f}%)")
            report.append(f"실패 요청: {result.failed_requests} ({result.failed_requests/result.total_requests*100:.1f}%)")
            report.append(f"초당 요청: {result.requests_per_second:.2f} RPS")
            report.append("")
            report.append("응답 시간 통계:")
            report.append(f"  평균: {result.avg_response_time:.3f}초")
            report.append(f"  최소: {result.min_response_time:.3f}초")
            report.append(f"  최대: {result.max_response_time:.3f}초")
            report.append(f"  95th percentile: {result.p95_response_time:.3f}초")
            report.append(f"  99th percentile: {result.p99_response_time:.3f}초")
            report.append("")
            report.append("시스템 리소스:")
            report.append(f"  평균 CPU 사용률: {result.cpu_usage_avg:.1f}%")
            report.append(f"  평균 메모리 사용률: {result.memory_usage_avg:.1f}%")
            report.append("")
            
            if result.errors:
                report.append("주요 에러:")
                for error in result.errors[:10]:  # 상위 10개 에러만 표시
                    report.append(f"  - {error}")
                if len(result.errors) > 10:
                    report.append(f"  ... 및 {len(result.errors) - 10}개 추가 에러")
                report.append("")
            
            report.append("-" * 60)
            report.append("")
        
        return "\n".join(report)
    
    def save_results_to_json(self, results: List[BenchmarkResult], filename: str):
        """벤치마크 결과를 JSON 파일로 저장"""
        data = []
        for result in results:
            result_dict = asdict(result)
            # datetime 객체를 문자열로 변환
            result_dict['start_time'] = result.start_time.isoformat()
            result_dict['end_time'] = result.end_time.isoformat()
            data.append(result_dict)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"벤치마크 결과를 {filename}에 저장했습니다")
    
    def generate_performance_graphs(self, results: List[BenchmarkResult]):
        """성능 그래프 생성"""
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        test_types = [r.test_type for r in results]
        response_times = [r.avg_response_time for r in results]
        rps_values = [r.requests_per_second for r in results]
        cpu_usage = [r.cpu_usage_avg for r in results]
        memory_usage = [r.memory_usage_avg for r in results]
        
        # 응답 시간 차트
        axes[0, 0].bar(test_types, response_times, color='skyblue')
        axes[0, 0].set_title('평균 응답 시간', fontsize=12)
        axes[0, 0].set_ylabel('시간 (초)')
        axes[0, 0].tick_params(axis='x', rotation=45)
        
        # RPS 차트
        axes[0, 1].bar(test_types, rps_values, color='lightgreen')
        axes[0, 1].set_title('초당 요청 처리량 (RPS)', fontsize=12)
        axes[0, 1].set_ylabel('요청/초')
        axes[0, 1].tick_params(axis='x', rotation=45)
        
        # CPU 사용률 차트
        axes[1, 0].bar(test_types, cpu_usage, color='orange')
        axes[1, 0].set_title('평균 CPU 사용률', fontsize=12)
        axes[1, 0].set_ylabel('CPU %')
        axes[1, 0].tick_params(axis='x', rotation=45)
        
        # 메모리 사용률 차트
        axes[1, 1].bar(test_types, memory_usage, color='lightcoral')
        axes[1, 1].set_title('평균 메모리 사용률', fontsize=12)
        axes[1, 1].set_ylabel('메모리 %')
        axes[1, 1].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plt.savefig('/var/log/stockpilot/performance_benchmark.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info("성능 그래프를 /var/log/stockpilot/performance_benchmark.png에 저장했습니다")

async def main():
    """메인 벤치마크 실행 함수"""
    benchmark = PerformanceBenchmark()
    results = []
    
    try:
        logger.info("StockPilot 성능 벤치마크 시작")
        
        # 1. WebSocket 부하 테스트
        websocket_result = await benchmark.run_websocket_load_test(concurrent_users=1000)
        results.append(websocket_result)
        
        # 잠시 대기 (시스템 안정화)
        await asyncio.sleep(30)
        
        # 2. API 부하 테스트
        api_result = await benchmark.run_api_load_test(concurrent_users=500)
        results.append(api_result)
        
        # 잠시 대기
        await asyncio.sleep(30)
        
        # 3. OpenAI API 최적화 벤치마크
        openai_result = await benchmark.run_openai_optimization_benchmark()
        results.append(openai_result)
        
        # 결과 저장 및 리포트 생성
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON 결과 저장
        benchmark.save_results_to_json(
            results, 
            f'/var/log/stockpilot/benchmark_results_{timestamp}.json'
        )
        
        # 텍스트 리포트 생성
        report = benchmark.generate_performance_report(results)
        with open(f'/var/log/stockpilot/benchmark_report_{timestamp}.txt', 'w', encoding='utf-8') as f:
            f.write(report)
        
        # 그래프 생성
        benchmark.generate_performance_graphs(results)
        
        logger.info(f"벤치마크 완료. 결과는 /var/log/stockpilot/benchmark_*_{timestamp}.* 파일들에 저장되었습니다")
        print(report)
        
    except Exception as e:
        logger.error(f"벤치마크 실행 중 오류 발생: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())