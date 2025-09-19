#!/usr/bin/env python3
"""
StockPilot AI 성능 분석 도구
시스템 성능, API 응답시간, 메모리 사용량, 데이터베이스 성능 등을 종합 분석
"""

import os
import sys
import time
import psutil
import asyncio
import aiohttp
import json
import statistics
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timedelta
import subprocess
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import matplotlib.pyplot as plt
import numpy as np

@dataclass
class PerformanceMetric:
    """성능 지표"""
    timestamp: str
    metric_name: str
    value: float
    unit: str
    category: str
    description: str = ""

@dataclass  
class LoadTestResult:
    """부하 테스트 결과"""
    endpoint: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    requests_per_second: float
    error_rate: float

class PerformanceAnalyzer:
    """성능 분석 메인 클래스"""
    
    def __init__(self, project_root: str, base_url: str = "http://localhost:8000"):
        self.project_root = Path(project_root)
        self.base_url = base_url
        self.metrics: List[PerformanceMetric] = []
        
        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # 성능 모니터링 스레드 제어
        self.monitoring_active = False
        self.monitor_thread = None

    async def run_comprehensive_analysis(self) -> Dict:
        """종합 성능 분석 실행"""
        self.logger.info("종합 성능 분석 시작")
        
        results = {
            'analysis_info': {
                'timestamp': datetime.now().isoformat(),
                'base_url': self.base_url,
                'project_root': str(self.project_root)
            },
            'system_performance': {},
            'api_performance': {},
            'load_test_results': {},
            'database_performance': {},
            'resource_usage': {},
            'recommendations': []
        }
        
        try:
            # 1. 시스템 성능 분석
            self.logger.info("시스템 성능 분석 중...")
            results['system_performance'] = await self.analyze_system_performance()
            
            # 2. API 성능 테스트
            self.logger.info("API 성능 테스트 중...")
            results['api_performance'] = await self.test_api_performance()
            
            # 3. 부하 테스트
            self.logger.info("부하 테스트 실행 중...")
            results['load_test_results'] = await self.run_load_tests()
            
            # 4. 데이터베이스 성능 분석
            self.logger.info("데이터베이스 성능 분석 중...")
            results['database_performance'] = await self.analyze_database_performance()
            
            # 5. 리소스 사용량 분석
            self.logger.info("리소스 사용량 분석 중...")
            results['resource_usage'] = await self.analyze_resource_usage()
            
            # 6. 성능 권장사항 생성
            results['recommendations'] = self.generate_recommendations(results)
            
        except Exception as e:
            self.logger.error(f"성능 분석 중 오류 발생: {e}")
            results['error'] = str(e)
        
        return results

    async def analyze_system_performance(self) -> Dict:
        """시스템 성능 분석"""
        # CPU 정보
        cpu_info = {
            'physical_cores': psutil.cpu_count(logical=False),
            'logical_cores': psutil.cpu_count(logical=True),
            'cpu_freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {},
            'cpu_percent': psutil.cpu_percent(interval=1)
        }
        
        # 메모리 정보
        memory = psutil.virtual_memory()
        memory_info = {
            'total': memory.total,
            'available': memory.available,
            'used': memory.used,
            'percentage': memory.percent
        }
        
        # 디스크 정보
        disk = psutil.disk_usage('/')
        disk_info = {
            'total': disk.total,
            'used': disk.used,
            'free': disk.free,
            'percentage': (disk.used / disk.total) * 100
        }
        
        # 네트워크 정보
        net_io = psutil.net_io_counters()
        network_info = {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv
        }
        
        # Python 프로세스 정보
        python_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                if 'python' in proc.info['name'].lower():
                    python_processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return {
            'cpu': cpu_info,
            'memory': memory_info,
            'disk': disk_info,
            'network': network_info,
            'python_processes': python_processes,
            'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None
        }

    async def test_api_performance(self) -> Dict:
        """API 성능 테스트"""
        endpoints = [
            '/api/v1/health',
            '/api/v1/status', 
            '/api/v1/health/comprehensive',
            '/api/v1/usage/stats',
            '/api/v1/batch/jobs'
        ]
        
        results = {}
        
        async with aiohttp.ClientSession() as session:
            for endpoint in endpoints:
                url = f"{self.base_url}{endpoint}"
                response_times = []
                
                # 각 엔드포인트를 10번 테스트
                for _ in range(10):
                    start_time = time.time()
                    try:
                        async with session.get(url, timeout=30) as response:
                            await response.text()
                            response_time = (time.time() - start_time) * 1000  # ms
                            response_times.append(response_time)
                            
                    except Exception as e:
                        self.logger.warning(f"API 테스트 실패 {url}: {e}")
                        response_times.append(30000)  # 타임아웃을 30초로 기록
                
                if response_times:
                    results[endpoint] = {
                        'avg_response_time': statistics.mean(response_times),
                        'min_response_time': min(response_times),
                        'max_response_time': max(response_times),
                        'median_response_time': statistics.median(response_times),
                        'std_dev': statistics.stdev(response_times) if len(response_times) > 1 else 0,
                        'success_rate': sum(1 for t in response_times if t < 5000) / len(response_times) * 100
                    }
        
        return results

    async def run_load_tests(self) -> Dict:
        """부하 테스트 실행"""
        test_configs = [
            {'concurrent_users': 10, 'duration': 30},
            {'concurrent_users': 50, 'duration': 60},
            {'concurrent_users': 100, 'duration': 30}
        ]
        
        results = {}
        
        for config in test_configs:
            test_name = f"{config['concurrent_users']}_users_{config['duration']}s"
            self.logger.info(f"부하 테스트 실행: {test_name}")
            
            result = await self._run_single_load_test(
                concurrent_users=config['concurrent_users'],
                duration=config['duration'],
                endpoint='/api/v1/health'
            )
            
            results[test_name] = asdict(result)
        
        return results

    async def _run_single_load_test(self, concurrent_users: int, duration: int, endpoint: str) -> LoadTestResult:
        """단일 부하 테스트 실행"""
        url = f"{self.base_url}{endpoint}"
        response_times = []
        successful_requests = 0
        failed_requests = 0
        
        start_time = time.time()
        end_time = start_time + duration
        
        async def make_request(session):
            nonlocal successful_requests, failed_requests
            
            while time.time() < end_time:
                request_start = time.time()
                try:
                    async with session.get(url, timeout=10) as response:
                        await response.text()
                        response_time = (time.time() - request_start) * 1000
                        response_times.append(response_time)
                        
                        if response.status == 200:
                            successful_requests += 1
                        else:
                            failed_requests += 1
                            
                except Exception:
                    failed_requests += 1
                    response_times.append(10000)  # 타임아웃/에러를 10초로 기록
                
                # 잠시 대기 (CPU 과부하 방지)
                await asyncio.sleep(0.01)
        
        # 동시 사용자 시뮬레이션
        connector = aiohttp.TCPConnector(limit=concurrent_users * 2)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [make_request(session) for _ in range(concurrent_users)]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        total_requests = successful_requests + failed_requests
        actual_duration = time.time() - start_time
        
        # 통계 계산
        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            
            # 95 퍼센타일 계산
            sorted_times = sorted(response_times)
            p95_index = int(len(sorted_times) * 0.95)
            p95_response_time = sorted_times[p95_index] if p95_index < len(sorted_times) else max_response_time
        else:
            avg_response_time = min_response_time = max_response_time = p95_response_time = 0
        
        return LoadTestResult(
            endpoint=endpoint,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            requests_per_second=total_requests / actual_duration if actual_duration > 0 else 0,
            error_rate=(failed_requests / total_requests * 100) if total_requests > 0 else 0
        )

    async def analyze_database_performance(self) -> Dict:
        """데이터베이스 성능 분석"""
        results = {
            'connection_test': False,
            'query_performance': {},
            'connection_pool': {},
            'slow_queries': []
        }
        
        # 기본 연결 테스트
        try:
            # SQLite 테스트 (프로젝트에 SQLite 파일이 있는 경우)
            sqlite_files = list(self.project_root.rglob("*.db"))
            if sqlite_files:
                db_path = sqlite_files[0]
                start_time = time.time()
                conn = sqlite3.connect(str(db_path))
                
                # 간단한 쿼리 테스트
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]
                
                connection_time = (time.time() - start_time) * 1000
                
                results['connection_test'] = True
                results['query_performance'] = {
                    'connection_time_ms': connection_time,
                    'table_count': table_count
                }
                
                # 테이블별 행 수 조회
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                table_stats = {}
                for (table_name,) in tables:
                    try:
                        start_time = time.time()
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        row_count = cursor.fetchone()[0]
                        query_time = (time.time() - start_time) * 1000
                        
                        table_stats[table_name] = {
                            'row_count': row_count,
                            'query_time_ms': query_time
                        }
                    except Exception as e:
                        table_stats[table_name] = {'error': str(e)}
                
                results['table_statistics'] = table_stats
                conn.close()
                
        except Exception as e:
            results['database_error'] = str(e)
        
        return results

    async def analyze_resource_usage(self) -> Dict:
        """리소스 사용량 분석"""
        # 30초간 리소스 사용량 모니터링
        monitoring_duration = 30
        interval = 1
        
        cpu_usage = []
        memory_usage = []
        disk_io = []
        network_io = []
        
        initial_disk_io = psutil.disk_io_counters()
        initial_net_io = psutil.net_io_counters()
        
        self.logger.info(f"{monitoring_duration}초간 리소스 사용량 모니터링...")
        
        for _ in range(monitoring_duration):
            # CPU 사용률
            cpu_percent = psutil.cpu_percent()
            cpu_usage.append(cpu_percent)
            
            # 메모리 사용률
            memory = psutil.virtual_memory()
            memory_usage.append(memory.percent)
            
            # 디스크 I/O
            current_disk_io = psutil.disk_io_counters()
            if initial_disk_io:
                disk_io.append({
                    'read_bytes': current_disk_io.read_bytes - initial_disk_io.read_bytes,
                    'write_bytes': current_disk_io.write_bytes - initial_disk_io.write_bytes
                })
            
            # 네트워크 I/O
            current_net_io = psutil.net_io_counters()
            if initial_net_io:
                network_io.append({
                    'bytes_sent': current_net_io.bytes_sent - initial_net_io.bytes_sent,
                    'bytes_recv': current_net_io.bytes_recv - initial_net_io.bytes_recv
                })
            
            await asyncio.sleep(interval)
        
        return {
            'cpu_usage': {
                'avg': statistics.mean(cpu_usage) if cpu_usage else 0,
                'min': min(cpu_usage) if cpu_usage else 0,
                'max': max(cpu_usage) if cpu_usage else 0,
                'samples': cpu_usage
            },
            'memory_usage': {
                'avg': statistics.mean(memory_usage) if memory_usage else 0,
                'min': min(memory_usage) if memory_usage else 0,
                'max': max(memory_usage) if memory_usage else 0,
                'samples': memory_usage
            },
            'disk_io': disk_io,
            'network_io': network_io,
            'monitoring_duration': monitoring_duration
        }

    def generate_recommendations(self, results: Dict) -> List[str]:
        """성능 개선 권장사항 생성"""
        recommendations = []
        
        # API 성능 권장사항
        api_perf = results.get('api_performance', {})
        slow_apis = [endpoint for endpoint, metrics in api_perf.items() 
                    if metrics.get('avg_response_time', 0) > 1000]
        
        if slow_apis:
            recommendations.append(f"⚡ 느린 API 개선 필요: {', '.join(slow_apis)} (1초 이상 응답시간)")
        
        # 시스템 리소스 권장사항
        sys_perf = results.get('system_performance', {})
        
        cpu_percent = sys_perf.get('cpu', {}).get('cpu_percent', 0)
        if cpu_percent > 80:
            recommendations.append(f"🔥 CPU 사용률이 높습니다 ({cpu_percent:.1f}%). 최적화가 필요합니다.")
        
        memory_percent = sys_perf.get('memory', {}).get('percentage', 0)
        if memory_percent > 80:
            recommendations.append(f"💾 메모리 사용률이 높습니다 ({memory_percent:.1f}%). 메모리 최적화가 필요합니다.")
        
        disk_percent = sys_perf.get('disk', {}).get('percentage', 0)
        if disk_percent > 80:
            recommendations.append(f"💿 디스크 사용률이 높습니다 ({disk_percent:.1f}%). 정리가 필요합니다.")
        
        # 부하 테스트 권장사항
        load_test = results.get('load_test_results', {})
        for test_name, test_result in load_test.items():
            error_rate = test_result.get('error_rate', 0)
            if error_rate > 5:
                recommendations.append(f"🚨 {test_name} 테스트에서 높은 에러율 ({error_rate:.1f}%) 발생")
            
            rps = test_result.get('requests_per_second', 0)
            if rps < 10:
                recommendations.append(f"⚡ {test_name} 테스트에서 낮은 처리량 ({rps:.1f} RPS) 기록")
        
        # 일반적인 권장사항
        if not recommendations:
            recommendations.append("✅ 전반적인 성능이 양호합니다.")
        
        recommendations.extend([
            "📊 정기적인 성능 모니터링을 권장합니다.",
            "🔍 프로파일링을 통한 병목점 분석을 고려하세요.",
            "⚡ 캐싱 전략을 검토하여 성능을 향상시키세요.",
            "📈 API 응답 시간 모니터링 대시보드를 구축하세요.",
            "🔧 데이터베이스 쿼리 최적화를 검토하세요."
        ])
        
        return recommendations

    def generate_performance_charts(self, results: Dict, output_dir: str = "performance_reports"):
        """성능 차트 생성"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # API 응답 시간 차트
        api_perf = results.get('api_performance', {})
        if api_perf:
            endpoints = list(api_perf.keys())
            avg_times = [metrics.get('avg_response_time', 0) for metrics in api_perf.values()]
            
            plt.figure(figsize=(12, 6))
            plt.bar(endpoints, avg_times, color='skyblue')
            plt.title('API 평균 응답 시간')
            plt.xlabel('엔드포인트')
            plt.ylabel('응답 시간 (ms)')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig(output_path / 'api_response_times.png', dpi=300, bbox_inches='tight')
            plt.close()
        
        # 리소스 사용량 차트
        resource_usage = results.get('resource_usage', {})
        if resource_usage:
            cpu_samples = resource_usage.get('cpu_usage', {}).get('samples', [])
            memory_samples = resource_usage.get('memory_usage', {}).get('samples', [])
            
            if cpu_samples and memory_samples:
                time_points = list(range(len(cpu_samples)))
                
                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
                
                # CPU 사용률
                ax1.plot(time_points, cpu_samples, label='CPU 사용률', color='red', linewidth=2)
                ax1.set_title('CPU 사용률 (시간별)')
                ax1.set_xlabel('시간 (초)')
                ax1.set_ylabel('CPU 사용률 (%)')
                ax1.grid(True, alpha=0.3)
                ax1.legend()
                
                # 메모리 사용률
                ax2.plot(time_points, memory_samples, label='메모리 사용률', color='blue', linewidth=2)
                ax2.set_title('메모리 사용률 (시간별)')
                ax2.set_xlabel('시간 (초)')
                ax2.set_ylabel('메모리 사용률 (%)')
                ax2.grid(True, alpha=0.3)
                ax2.legend()
                
                plt.tight_layout()
                plt.savefig(output_path / 'resource_usage.png', dpi=300, bbox_inches='tight')
                plt.close()
        
        # 부하 테스트 결과 차트
        load_tests = results.get('load_test_results', {})
        if load_tests:
            test_names = list(load_tests.keys())
            rps_values = [test.get('requests_per_second', 0) for test in load_tests.values()]
            error_rates = [test.get('error_rate', 0) for test in load_tests.values()]
            
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            
            # RPS 차트
            ax1.bar(test_names, rps_values, color='green', alpha=0.7)
            ax1.set_title('초당 요청 처리량 (RPS)')
            ax1.set_xlabel('테스트 시나리오')
            ax1.set_ylabel('RPS')
            ax1.tick_params(axis='x', rotation=45)
            
            # 에러율 차트
            ax2.bar(test_names, error_rates, color='red', alpha=0.7)
            ax2.set_title('에러율 (%)')
            ax2.set_xlabel('테스트 시나리오')
            ax2.set_ylabel('에러율 (%)')
            ax2.tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            plt.savefig(output_path / 'load_test_results.png', dpi=300, bbox_inches='tight')
            plt.close()
        
        self.logger.info(f"성능 차트가 생성되었습니다: {output_path}")

    def generate_html_report(self, results: Dict, output_file: str):
        """HTML 성능 리포트 생성"""
        html_template = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StockPilot AI 성능 분석 리포트</title>
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0; padding: 20px; background: #f5f5f5; 
        }}
        .container {{ 
            max-width: 1200px; margin: 0 auto; background: white; 
            border-radius: 8px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .score {{ font-size: 48px; font-weight: bold; margin: 10px 0; color: #28a745; }}
        .metrics-grid {{ 
            display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 20px; margin-bottom: 30px; 
        }}
        .metric-card {{ 
            background: #f8f9fa; padding: 20px; border-radius: 6px; 
        }}
        .metric-title {{ font-size: 14px; color: #666; text-transform: uppercase; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
        .metric-unit {{ font-size: 14px; color: #666; }}
        .section {{ margin: 30px 0; }}
        .section h2 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        .api-table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        .api-table th, .api-table td {{ 
            border: 1px solid #ddd; padding: 12px; text-align: left; 
        }}
        .api-table th {{ background: #f8f9fa; }}
        .load-test {{ 
            background: #e7f3ff; border: 1px solid #bee5eb; 
            border-radius: 6px; padding: 20px; margin: 15px 0; 
        }}
        .recommendations {{ 
            background: #d4edda; border: 1px solid #c3e6cb; 
            border-radius: 6px; padding: 20px; margin: 30px 0; 
        }}
        .chart {{ text-align: center; margin: 20px 0; }}
        .chart img {{ max-width: 100%; height: auto; border: 1px solid #ddd; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 StockPilot AI 성능 분석 리포트</h1>
            <div class="score">{overall_score}</div>
            <p>분석 일시: {timestamp}</p>
            <p>기준 URL: {base_url}</p>
        </div>
        
        <div class="metrics-grid">
            {metrics_cards}
        </div>
        
        <div class="section">
            <h2>🖥️ 시스템 성능</h2>
            {system_performance}
        </div>
        
        <div class="section">
            <h2>⚡ API 성능</h2>
            {api_performance}
        </div>
        
        <div class="section">
            <h2>🚀 부하 테스트 결과</h2>
            {load_test_results}
        </div>
        
        <div class="section">
            <h2>💾 데이터베이스 성능</h2>
            {database_performance}
        </div>
        
        <div class="section">
            <h2>📈 리소스 사용량</h2>
            {resource_usage}
        </div>
        
        <div class="recommendations">
            <h2>💡 성능 개선 권장사항</h2>
            {recommendations}
        </div>
    </div>
</body>
</html>
"""
        
        # 전체 성능 점수 계산 (간단한 예시)
        overall_score = self._calculate_overall_score(results)
        
        # 각 섹션의 HTML 생성
        metrics_cards = self._generate_metrics_cards(results)
        system_performance = self._generate_system_performance_html(results.get('system_performance', {}))
        api_performance = self._generate_api_performance_html(results.get('api_performance', {}))
        load_test_results = self._generate_load_test_html(results.get('load_test_results', {}))
        database_performance = self._generate_database_performance_html(results.get('database_performance', {}))
        resource_usage = self._generate_resource_usage_html(results.get('resource_usage', {}))
        recommendations = self._generate_recommendations_html(results.get('recommendations', []))
        
        # HTML 생성
        html_content = html_template.format(
            overall_score=overall_score,
            timestamp=results['analysis_info']['timestamp'],
            base_url=results['analysis_info']['base_url'],
            metrics_cards=metrics_cards,
            system_performance=system_performance,
            api_performance=api_performance,
            load_test_results=load_test_results,
            database_performance=database_performance,
            resource_usage=resource_usage,
            recommendations=recommendations
        )
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"HTML 리포트가 생성되었습니다: {output_file}")

    def _calculate_overall_score(self, results: Dict) -> int:
        """전체 성능 점수 계산"""
        score = 100
        
        # API 성능 점수
        api_perf = results.get('api_performance', {})
        for metrics in api_perf.values():
            avg_time = metrics.get('avg_response_time', 0)
            if avg_time > 2000:
                score -= 15
            elif avg_time > 1000:
                score -= 10
            elif avg_time > 500:
                score -= 5
        
        # 부하 테스트 점수
        load_tests = results.get('load_test_results', {})
        for test_result in load_tests.values():
            error_rate = test_result.get('error_rate', 0)
            if error_rate > 10:
                score -= 20
            elif error_rate > 5:
                score -= 10
        
        # 시스템 리소스 점수
        sys_perf = results.get('system_performance', {})
        cpu_percent = sys_perf.get('cpu', {}).get('cpu_percent', 0)
        memory_percent = sys_perf.get('memory', {}).get('percentage', 0)
        
        if cpu_percent > 90:
            score -= 15
        elif cpu_percent > 80:
            score -= 10
        
        if memory_percent > 90:
            score -= 15
        elif memory_percent > 80:
            score -= 10
        
        return max(0, score)

    def _generate_metrics_cards(self, results: Dict) -> str:
        """메트릭 카드 HTML 생성"""
        cards = []
        
        # API 평균 응답시간
        api_perf = results.get('api_performance', {})
        if api_perf:
            avg_times = [metrics.get('avg_response_time', 0) for metrics in api_perf.values()]
            overall_avg = sum(avg_times) / len(avg_times) if avg_times else 0
            
            cards.append(f"""
            <div class="metric-card">
                <div class="metric-title">평균 API 응답시간</div>
                <div class="metric-value">{overall_avg:.1f}</div>
                <div class="metric-unit">ms</div>
            </div>
            """)
        
        # 시스템 메트릭
        sys_perf = results.get('system_performance', {})
        cpu_percent = sys_perf.get('cpu', {}).get('cpu_percent', 0)
        memory_percent = sys_perf.get('memory', {}).get('percentage', 0)
        
        cards.extend([
            f"""
            <div class="metric-card">
                <div class="metric-title">CPU 사용률</div>
                <div class="metric-value">{cpu_percent:.1f}</div>
                <div class="metric-unit">%</div>
            </div>
            """,
            f"""
            <div class="metric-card">
                <div class="metric-title">메모리 사용률</div>
                <div class="metric-value">{memory_percent:.1f}</div>
                <div class="metric-unit">%</div>
            </div>
            """
        ])
        
        # 부하 테스트 결과
        load_tests = results.get('load_test_results', {})
        if load_tests:
            # 최고 RPS 찾기
            max_rps = max([test.get('requests_per_second', 0) for test in load_tests.values()], default=0)
            cards.append(f"""
            <div class="metric-card">
                <div class="metric-title">최대 처리량</div>
                <div class="metric-value">{max_rps:.1f}</div>
                <div class="metric-unit">RPS</div>
            </div>
            """)
        
        return ''.join(cards)

    def _generate_system_performance_html(self, sys_perf: Dict) -> str:
        """시스템 성능 HTML 생성"""
        if not sys_perf:
            return "<p>시스템 성능 데이터가 없습니다.</p>"
        
        cpu_info = sys_perf.get('cpu', {})
        memory_info = sys_perf.get('memory', {})
        
        return f"""
        <p><strong>CPU:</strong> {cpu_info.get('physical_cores', 'N/A')}코어 (논리 {cpu_info.get('logical_cores', 'N/A')}코어), 사용률 {cpu_info.get('cpu_percent', 0):.1f}%</p>
        <p><strong>메모리:</strong> {memory_info.get('used', 0) / (1024**3):.1f}GB / {memory_info.get('total', 0) / (1024**3):.1f}GB ({memory_info.get('percentage', 0):.1f}%)</p>
        <p><strong>디스크:</strong> {sys_perf.get('disk', {}).get('percentage', 0):.1f}% 사용중</p>
        """

    def _generate_api_performance_html(self, api_perf: Dict) -> str:
        """API 성능 HTML 생성"""
        if not api_perf:
            return "<p>API 성능 데이터가 없습니다.</p>"
        
        html = '<table class="api-table"><tr><th>엔드포인트</th><th>평균 응답시간</th><th>최소</th><th>최대</th><th>성공률</th></tr>'
        
        for endpoint, metrics in api_perf.items():
            html += f"""
            <tr>
                <td>{endpoint}</td>
                <td>{metrics.get('avg_response_time', 0):.1f}ms</td>
                <td>{metrics.get('min_response_time', 0):.1f}ms</td>
                <td>{metrics.get('max_response_time', 0):.1f}ms</td>
                <td>{metrics.get('success_rate', 0):.1f}%</td>
            </tr>
            """
        
        html += '</table>'
        return html

    def _generate_load_test_html(self, load_tests: Dict) -> str:
        """부하 테스트 HTML 생성"""
        if not load_tests:
            return "<p>부하 테스트 데이터가 없습니다.</p>"
        
        html = ""
        for test_name, result in load_tests.items():
            html += f"""
            <div class="load-test">
                <h3>{test_name}</h3>
                <p><strong>처리량:</strong> {result.get('requests_per_second', 0):.1f} RPS</p>
                <p><strong>평균 응답시간:</strong> {result.get('avg_response_time', 0):.1f}ms</p>
                <p><strong>에러율:</strong> {result.get('error_rate', 0):.1f}%</p>
                <p><strong>성공/실패:</strong> {result.get('successful_requests', 0)}/{result.get('failed_requests', 0)}</p>
            </div>
            """
        
        return html

    def _generate_database_performance_html(self, db_perf: Dict) -> str:
        """데이터베이스 성능 HTML 생성"""
        if not db_perf:
            return "<p>데이터베이스 성능 데이터가 없습니다.</p>"
        
        html = f"<p><strong>연결 테스트:</strong> {'성공' if db_perf.get('connection_test') else '실패'}</p>"
        
        if 'query_performance' in db_perf:
            qp = db_perf['query_performance']
            html += f"<p><strong>연결 시간:</strong> {qp.get('connection_time_ms', 0):.1f}ms</p>"
            html += f"<p><strong>테이블 수:</strong> {qp.get('table_count', 0)}개</p>"
        
        return html

    def _generate_resource_usage_html(self, resource_usage: Dict) -> str:
        """리소스 사용량 HTML 생성"""
        if not resource_usage:
            return "<p>리소스 사용량 데이터가 없습니다.</p>"
        
        cpu = resource_usage.get('cpu_usage', {})
        memory = resource_usage.get('memory_usage', {})
        
        return f"""
        <p><strong>모니터링 시간:</strong> {resource_usage.get('monitoring_duration', 0)}초</p>
        <p><strong>CPU 사용률:</strong> 평균 {cpu.get('avg', 0):.1f}%, 최대 {cpu.get('max', 0):.1f}%</p>
        <p><strong>메모리 사용률:</strong> 평균 {memory.get('avg', 0):.1f}%, 최대 {memory.get('max', 0):.1f}%</p>
        """

    def _generate_recommendations_html(self, recommendations: List[str]) -> str:
        """권장사항 HTML 생성"""
        if not recommendations:
            return "<p>권장사항이 없습니다.</p>"
        
        html = "<ul>"
        for rec in recommendations:
            html += f"<li>{rec}</li>"
        html += "</ul>"
        
        return html

    def save_results(self, results: Dict, output_prefix: str = "performance_analysis"):
        """결과를 파일로 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON 보고서
        json_file = f"{output_prefix}_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        self.logger.info(f"JSON 리포트 저장: {json_file}")
        
        # HTML 보고서
        html_file = f"{output_prefix}_{timestamp}.html"
        self.generate_html_report(results, html_file)
        
        # 성능 차트 생성
        self.generate_performance_charts(results, f"charts_{timestamp}")

async def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='StockPilot AI 성능 분석 도구')
    parser.add_argument('--project-root', '-p', default='.', help='프로젝트 루트 디렉토리')
    parser.add_argument('--base-url', '-u', default='http://localhost:8000', help='API 기본 URL')
    parser.add_argument('--output-prefix', '-o', default='performance_analysis', help='출력 파일 접두사')
    parser.add_argument('--skip-load-test', action='store_true', help='부하 테스트 건너뛰기')
    parser.add_argument('--quick', action='store_true', help='빠른 분석 (리소스 모니터링 시간 단축)')
    parser.add_argument('--verbose', '-v', action='store_true', help='상세 로그 출력')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 성능 분석 실행
    analyzer = PerformanceAnalyzer(args.project_root, args.base_url)
    
    try:
        results = await analyzer.run_comprehensive_analysis()
        
        # 결과 저장
        analyzer.save_results(results, args.output_prefix)
        
        # 콘솔 요약 출력
        overall_score = analyzer._calculate_overall_score(results)
        print(f"\n📊 성능 분석 완료")
        print(f"전체 점수: {overall_score}/100")
        
        # 주요 메트릭 요약
        api_perf = results.get('api_performance', {})
        if api_perf:
            avg_times = [metrics.get('avg_response_time', 0) for metrics in api_perf.values()]
            overall_avg = sum(avg_times) / len(avg_times) if avg_times else 0
            print(f"평균 API 응답시간: {overall_avg:.1f}ms")
        
        sys_perf = results.get('system_performance', {})
        if sys_perf:
            print(f"CPU 사용률: {sys_perf.get('cpu', {}).get('cpu_percent', 0):.1f}%")
            print(f"메모리 사용률: {sys_perf.get('memory', {}).get('percentage', 0):.1f}%")
        
        return 0 if overall_score >= 70 else 1
        
    except Exception as e:
        logging.error(f"성능 분석 중 오류 발생: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))