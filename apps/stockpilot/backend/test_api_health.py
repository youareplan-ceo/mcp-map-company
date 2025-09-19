#!/usr/bin/env python3
"""
StockPilot API 체크리스트 실행 검증 스크립트
작성자: StockPilot Team
용도: 모든 API 엔드포인트 헬스체크, 응답시간, 에러 로깅
"""

import asyncio
import aiohttp
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import ssl
import certifi

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api_health_check.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class APIHealthChecker:
    """API 헬스체크 및 성능 검증 클래스"""
    
    def __init__(self):
        self.base_urls = {
            'backend': 'http://localhost:8000',
            'websocket': 'ws://localhost:8765',
            'auth': 'http://localhost:8002',
            'dashboard': 'http://localhost:8003'
        }
        
        self.test_results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'endpoints': [],
            'performance_stats': {},
            'errors': []
        }
        
        # SSL 컨텍스트 생성
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
    
    async def run_health_checks(self) -> Dict[str, Any]:
        """모든 헬스체크 실행"""
        logger.info("🩺 API 헬스체크 시작")
        
        # 1. 기본 백엔드 API 체크
        await self._check_backend_apis()
        
        # 2. 인증 API 체크
        await self._check_auth_apis()
        
        # 3. 대시보드 API 체크
        await self._check_dashboard_apis()
        
        # 4. WebSocket 연결 체크
        await self._check_websocket_connection()
        
        # 5. 데이터베이스 연결 체크
        await self._check_database_connection()
        
        # 6. 외부 API 연결 체크
        await self._check_external_apis()
        
        # 7. 성능 테스트
        await self._run_performance_tests()
        
        # 결과 리포트 생성
        report = self._generate_report()
        
        logger.info(f"✅ 헬스체크 완료: {self.test_results['passed_tests']}/{self.test_results['total_tests']} 통과")
        
        return report
    
    async def _check_backend_apis(self):
        """백엔드 API 엔드포인트 체크"""
        logger.info("🔍 백엔드 API 체크 시작")
        
        endpoints = [
            {'method': 'GET', 'path': '/health', 'name': '헬스체크'},
            {'method': 'GET', 'path': '/api/status', 'name': '시스템 상태'},
            {'method': 'GET', 'path': '/api/version', 'name': '버전 정보'},
            {'method': 'GET', 'path': '/docs', 'name': 'API 문서'},
            {'method': 'GET', 'path': '/openapi.json', 'name': 'OpenAPI 스펙'},
            {'method': 'POST', 'path': '/api/stocks/analyze', 'name': '주식 분석', 
             'data': {'symbol': 'AAPL', 'analysis_type': 'quick'}},
            {'method': 'GET', 'path': '/api/stocks/search', 'name': '종목 검색',
             'params': {'q': 'Samsung'}},
            {'method': 'POST', 'path': '/api/portfolio/validate', 'name': '포트폴리오 검증',
             'data': {'stocks': [{'symbol': 'AAPL', 'quantity': 10}]}},
        ]
        
        for endpoint in endpoints:
            await self._test_endpoint('backend', endpoint)
    
    async def _check_auth_apis(self):
        """인증 API 체크"""
        logger.info("🔐 인증 API 체크 시작")
        
        endpoints = [
            {'method': 'GET', 'path': '/health', 'name': '인증서버 헬스체크'},
            {'method': 'POST', 'path': '/auth/login', 'name': '로그인 테스트',
             'data': {'username': 'test@example.com', 'password': 'testpass123'}},
            {'method': 'POST', 'path': '/auth/register', 'name': '회원가입 테스트',
             'data': {'email': 'test@example.com', 'password': 'testpass123', 'name': 'Test User'}},
            {'method': 'GET', 'path': '/auth/verify', 'name': '토큰 검증'},
        ]
        
        for endpoint in endpoints:
            await self._test_endpoint('auth', endpoint)
    
    async def _check_dashboard_apis(self):
        """대시보드 API 체크"""
        logger.info("📊 대시보드 API 체크 시작")
        
        endpoints = [
            {'method': 'GET', 'path': '/health', 'name': '대시보드 헬스체크'},
            {'method': 'GET', 'path': '/dashboard/stats', 'name': '통계 조회'},
            {'method': 'GET', 'path': '/dashboard/portfolio', 'name': '포트폴리오 조회'},
            {'method': 'GET', 'path': '/dashboard/alerts', 'name': '알림 조회'},
        ]
        
        for endpoint in endpoints:
            await self._test_endpoint('dashboard', endpoint)
    
    async def _check_websocket_connection(self):
        """WebSocket 연결 테스트"""
        logger.info("🔌 WebSocket 연결 체크")
        
        try:
            import websockets
            
            start_time = time.time()
            uri = "ws://localhost:8765/health"
            
            async with websockets.connect(uri) as websocket:
                # 연결 테스트 메시지 발송
                test_message = json.dumps({
                    'type': 'health_check',
                    'timestamp': datetime.now().isoformat()
                })
                
                await websocket.send(test_message)
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                
                response_time = (time.time() - start_time) * 1000
                
                self._record_test_result(
                    service='websocket',
                    endpoint={'name': 'WebSocket 연결 테스트', 'path': '/health'},
                    success=True,
                    response_time=response_time,
                    response=response
                )
                
                logger.info(f"✅ WebSocket 연결 성공 (응답시간: {response_time:.2f}ms)")
                
        except Exception as e:
            self._record_test_result(
                service='websocket',
                endpoint={'name': 'WebSocket 연결 테스트', 'path': '/health'},
                success=False,
                error=str(e)
            )
            logger.error(f"❌ WebSocket 연결 실패: {e}")
    
    async def _check_database_connection(self):
        """데이터베이스 연결 테스트"""
        logger.info("🗄️ 데이터베이스 연결 체크")
        
        try:
            # Redis 연결 테스트
            await self._test_redis_connection()
            
            # PostgreSQL 연결 테스트 (실제 환경에서는 asyncpg 사용)
            await self._test_postgres_connection()
            
        except Exception as e:
            logger.error(f"❌ 데이터베이스 연결 실패: {e}")
    
    async def _test_redis_connection(self):
        """Redis 연결 테스트"""
        try:
            import aioredis
            
            start_time = time.time()
            redis = await aioredis.from_url("redis://localhost:6379")
            
            # 연결 테스트
            await redis.ping()
            
            # 읽기/쓰기 테스트
            test_key = f"health_check_{datetime.now().timestamp()}"
            await redis.set(test_key, "test_value", ex=10)
            value = await redis.get(test_key)
            await redis.delete(test_key)
            
            response_time = (time.time() - start_time) * 1000
            
            self._record_test_result(
                service='redis',
                endpoint={'name': 'Redis 연결 테스트', 'path': 'redis://localhost:6379'},
                success=True,
                response_time=response_time
            )
            
            logger.info(f"✅ Redis 연결 성공 (응답시간: {response_time:.2f}ms)")
            
            await redis.close()
            
        except Exception as e:
            self._record_test_result(
                service='redis',
                endpoint={'name': 'Redis 연결 테스트', 'path': 'redis://localhost:6379'},
                success=False,
                error=str(e)
            )
            logger.error(f"❌ Redis 연결 실패: {e}")
    
    async def _test_postgres_connection(self):
        """PostgreSQL 연결 테스트"""
        try:
            # 실제 환경에서는 asyncpg나 SQLAlchemy async 사용
            # 여기서는 간단한 HTTP API 호출로 대체
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                
                url = f"{self.base_urls['backend']}/api/db/health"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        self._record_test_result(
                            service='postgres',
                            endpoint={'name': 'PostgreSQL 연결 테스트', 'path': '/api/db/health'},
                            success=True,
                            response_time=response_time
                        )
                        logger.info(f"✅ PostgreSQL 연결 성공 (응답시간: {response_time:.2f}ms)")
                    else:
                        raise Exception(f"HTTP {response.status}")
                        
        except Exception as e:
            self._record_test_result(
                service='postgres',
                endpoint={'name': 'PostgreSQL 연결 테스트', 'path': '/api/db/health'},
                success=False,
                error=str(e)
            )
            logger.error(f"❌ PostgreSQL 연결 실패: {e}")
    
    async def _check_external_apis(self):
        """외부 API 연결 테스트"""
        logger.info("🌐 외부 API 연결 체크")
        
        external_apis = [
            {
                'name': 'OpenAI API',
                'url': 'https://api.openai.com/v1/models',
                'headers': {'Authorization': 'Bearer test-key'}
            },
            {
                'name': 'Alpha Vantage API',
                'url': 'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=1min&apikey=demo'
            },
            {
                'name': 'Yahoo Finance',
                'url': 'https://query1.finance.yahoo.com/v8/finance/chart/AAPL'
            }
        ]
        
        for api in external_apis:
            await self._test_external_api(api)
    
    async def _test_external_api(self, api_config: Dict[str, Any]):
        """외부 API 테스트"""
        try:
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                headers = api_config.get('headers', {})
                
                async with session.get(
                    api_config['url'], 
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                    ssl=self.ssl_context
                ) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    # 일부 외부 API는 인증키 없으면 401/403을 반환하지만 연결은 정상
                    success = response.status in [200, 401, 403]
                    
                    self._record_test_result(
                        service='external',
                        endpoint={'name': api_config['name'], 'path': api_config['url']},
                        success=success,
                        response_time=response_time,
                        status_code=response.status
                    )
                    
                    if success:
                        logger.info(f"✅ {api_config['name']} 연결 성공 (응답시간: {response_time:.2f}ms)")
                    else:
                        logger.warning(f"⚠️ {api_config['name']} 연결 이슈: HTTP {response.status}")
                        
        except Exception as e:
            self._record_test_result(
                service='external',
                endpoint={'name': api_config['name'], 'path': api_config['url']},
                success=False,
                error=str(e)
            )
            logger.error(f"❌ {api_config['name']} 연결 실패: {e}")
    
    async def _run_performance_tests(self):
        """성능 테스트 실행"""
        logger.info("⚡ 성능 테스트 시작")
        
        # 동시 요청 테스트
        await self._run_concurrent_requests_test()
        
        # 응답 시간 테스트
        await self._run_response_time_test()
        
        # 부하 테스트
        await self._run_load_test()
    
    async def _run_concurrent_requests_test(self):
        """동시 요청 처리 테스트"""
        logger.info("📊 동시 요청 처리 테스트")
        
        try:
            concurrent_requests = 10
            url = f"{self.base_urls['backend']}/health"
            
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                tasks = []
                for i in range(concurrent_requests):
                    task = self._make_request(session, 'GET', url)
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
            
            total_time = time.time() - start_time
            successful_requests = sum(1 for r in results if not isinstance(r, Exception))
            
            self.test_results['performance_stats']['concurrent_requests'] = {
                'total_requests': concurrent_requests,
                'successful_requests': successful_requests,
                'total_time': total_time,
                'requests_per_second': concurrent_requests / total_time if total_time > 0 else 0
            }
            
            logger.info(f"✅ 동시 요청 테스트 완료: {successful_requests}/{concurrent_requests} 성공")
            
        except Exception as e:
            logger.error(f"❌ 동시 요청 테스트 실패: {e}")
    
    async def _run_response_time_test(self):
        """응답 시간 테스트"""
        logger.info("⏱️ 응답 시간 테스트")
        
        try:
            url = f"{self.base_urls['backend']}/health"
            response_times = []
            
            async with aiohttp.ClientSession() as session:
                for i in range(5):
                    start_time = time.time()
                    async with session.get(url) as response:
                        response_time = (time.time() - start_time) * 1000
                        response_times.append(response_time)
                        await asyncio.sleep(0.1)
            
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)
            
            self.test_results['performance_stats']['response_times'] = {
                'average': avg_response_time,
                'maximum': max_response_time,
                'minimum': min_response_time,
                'samples': response_times
            }
            
            logger.info(f"✅ 평균 응답 시간: {avg_response_time:.2f}ms")
            
        except Exception as e:
            logger.error(f"❌ 응답 시간 테스트 실패: {e}")
    
    async def _run_load_test(self):
        """간단한 부하 테스트"""
        logger.info("🏋️ 부하 테스트")
        
        try:
            requests_per_batch = 5
            batches = 3
            url = f"{self.base_urls['backend']}/health"
            
            total_requests = 0
            successful_requests = 0
            total_time = 0
            
            async with aiohttp.ClientSession() as session:
                for batch in range(batches):
                    start_time = time.time()
                    
                    tasks = []
                    for i in range(requests_per_batch):
                        task = self._make_request(session, 'GET', url)
                        tasks.append(task)
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    batch_time = time.time() - start_time
                    batch_successful = sum(1 for r in results if not isinstance(r, Exception))
                    
                    total_requests += requests_per_batch
                    successful_requests += batch_successful
                    total_time += batch_time
                    
                    logger.info(f"배치 {batch + 1}: {batch_successful}/{requests_per_batch} 성공 ({batch_time:.2f}s)")
                    
                    await asyncio.sleep(0.5)  # 배치 간 대기
            
            self.test_results['performance_stats']['load_test'] = {
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'success_rate': (successful_requests / total_requests) * 100 if total_requests > 0 else 0,
                'total_time': total_time,
                'requests_per_second': total_requests / total_time if total_time > 0 else 0
            }
            
            logger.info(f"✅ 부하 테스트 완료: {successful_requests}/{total_requests} 성공")
            
        except Exception as e:
            logger.error(f"❌ 부하 테스트 실패: {e}")
    
    async def _test_endpoint(self, service: str, endpoint: Dict[str, Any]):
        """개별 엔드포인트 테스트"""
        try:
            base_url = self.base_urls.get(service)
            if not base_url:
                raise ValueError(f"Unknown service: {service}")
            
            url = base_url + endpoint['path']
            method = endpoint.get('method', 'GET')
            data = endpoint.get('data')
            params = endpoint.get('params')
            
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                
                response = await self._make_request(
                    session, method, url, data=data, params=params
                )
                
                response_time = (time.time() - start_time) * 1000
                
                if isinstance(response, Exception):
                    raise response
                
                self._record_test_result(
                    service=service,
                    endpoint=endpoint,
                    success=True,
                    response_time=response_time,
                    status_code=response['status'],
                    response=response.get('data')
                )
                
                logger.info(f"✅ {endpoint['name']} 성공 (응답시간: {response_time:.2f}ms)")
                
        except Exception as e:
            self._record_test_result(
                service=service,
                endpoint=endpoint,
                success=False,
                error=str(e)
            )
            logger.error(f"❌ {endpoint['name']} 실패: {e}")
    
    async def _make_request(self, session: aiohttp.ClientSession, method: str, url: str, 
                           data: Any = None, params: Any = None):
        """HTTP 요청 실행"""
        try:
            kwargs = {
                'timeout': aiohttp.ClientTimeout(total=10),
                'ssl': self.ssl_context
            }
            
            if data:
                kwargs['json'] = data
            
            if params:
                kwargs['params'] = params
            
            async with session.request(method, url, **kwargs) as response:
                try:
                    response_data = await response.json()
                except:
                    response_data = await response.text()
                
                return {
                    'status': response.status,
                    'data': response_data,
                    'headers': dict(response.headers)
                }
                
        except Exception as e:
            return e
    
    def _record_test_result(self, service: str, endpoint: Dict[str, Any], success: bool, 
                           response_time: float = 0, status_code: int = None, 
                           response: Any = None, error: str = None):
        """테스트 결과 기록"""
        self.test_results['total_tests'] += 1
        
        if success:
            self.test_results['passed_tests'] += 1
        else:
            self.test_results['failed_tests'] += 1
            self.test_results['errors'].append({
                'service': service,
                'endpoint': endpoint['name'],
                'error': error,
                'timestamp': datetime.now().isoformat()
            })
        
        endpoint_result = {
            'service': service,
            'name': endpoint['name'],
            'path': endpoint.get('path', ''),
            'success': success,
            'response_time': response_time,
            'status_code': status_code,
            'timestamp': datetime.now().isoformat()
        }
        
        if error:
            endpoint_result['error'] = error
        
        self.test_results['endpoints'].append(endpoint_result)
    
    def _generate_report(self) -> Dict[str, Any]:
        """최종 리포트 생성"""
        success_rate = (self.test_results['passed_tests'] / self.test_results['total_tests'] * 100) if self.test_results['total_tests'] > 0 else 0
        
        # 서비스별 통계
        service_stats = {}
        for endpoint in self.test_results['endpoints']:
            service = endpoint['service']
            if service not in service_stats:
                service_stats[service] = {'total': 0, 'passed': 0, 'failed': 0}
            
            service_stats[service]['total'] += 1
            if endpoint['success']:
                service_stats[service]['passed'] += 1
            else:
                service_stats[service]['failed'] += 1
        
        # 응답 시간 통계
        response_times = [ep['response_time'] for ep in self.test_results['endpoints'] if ep['success']]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        report = {
            'summary': {
                'total_tests': self.test_results['total_tests'],
                'passed_tests': self.test_results['passed_tests'],
                'failed_tests': self.test_results['failed_tests'],
                'success_rate': round(success_rate, 2),
                'average_response_time': round(avg_response_time, 2),
                'timestamp': datetime.now().isoformat()
            },
            'service_stats': service_stats,
            'performance_stats': self.test_results['performance_stats'],
            'detailed_results': self.test_results['endpoints'],
            'errors': self.test_results['errors']
        }
        
        return report

async def main():
    """메인 실행 함수"""
    logger.info("🚀 StockPilot API 헬스체크 시작")
    
    try:
        checker = APIHealthChecker()
        report = await checker.run_health_checks()
        
        # 리포트를 JSON 파일로 저장
        with open('api_health_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # 콘솔에 요약 출력
        print("\n" + "="*80)
        print("📊 API 헬스체크 리포트")
        print("="*80)
        print(f"총 테스트: {report['summary']['total_tests']}")
        print(f"성공: {report['summary']['passed_tests']}")
        print(f"실패: {report['summary']['failed_tests']}")
        print(f"성공률: {report['summary']['success_rate']}%")
        print(f"평균 응답시간: {report['summary']['average_response_time']}ms")
        print("="*80)
        
        # 서비스별 통계 출력
        print("\n📈 서비스별 통계:")
        for service, stats in report['service_stats'].items():
            success_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"  {service}: {stats['passed']}/{stats['total']} 성공 ({success_rate:.1f}%)")
        
        # 성능 통계 출력
        if report['performance_stats']:
            print("\n⚡ 성능 통계:")
            for test_name, stats in report['performance_stats'].items():
                print(f"  {test_name}: {stats}")
        
        # 에러 요약 출력
        if report['errors']:
            print(f"\n❌ 에러 ({len(report['errors'])}개):")
            for error in report['errors'][:5]:  # 최근 5개만 표시
                print(f"  - {error['service']}/{error['endpoint']}: {error['error']}")
        
        print(f"\n📄 상세 리포트: api_health_report.json")
        
        return report
        
    except Exception as e:
        logger.error(f"❌ 헬스체크 실행 실패: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())