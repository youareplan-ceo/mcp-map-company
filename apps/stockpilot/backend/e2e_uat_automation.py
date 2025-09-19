#!/usr/bin/env python3
"""
StockPilot AI E2E UAT (User Acceptance Testing) 자동화
10가지 핵심 사용자 시나리오에 대한 End-to-End 테스트
"""

import asyncio
import aiohttp
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import tempfile
import websockets
import subprocess
import os

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('e2e_uat_automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class E2EUATAutomation:
    """StockPilot E2E UAT 자동화 테스트 클래스"""
    
    def __init__(self):
        self.frontend_url = 'http://localhost:3000'
        self.backend_url = 'http://localhost:8000'
        self.dashboard_url = 'http://localhost:8003'
        self.websocket_url = 'ws://localhost:8765'
        
        self.test_results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_scenarios': [],
            'performance_metrics': {},
            'timestamp': datetime.now().isoformat()
        }
        
        self.timeout = 30  # 30초 타임아웃
        
    async def run_e2e_uat_tests(self) -> Dict[str, Any]:
        """전체 E2E UAT 테스트 실행"""
        print("🚀 StockPilot AI E2E UAT 10건 자동화 테스트 시작")
        
        test_scenarios = [
            ("사용자 대시보드 로딩", self._test_dashboard_loading),
            ("실시간 주식 데이터 수신", self._test_realtime_stock_data),
            ("AI 시그널 알림 수신", self._test_ai_signal_notifications),
            ("포트폴리오 데이터 표시", self._test_portfolio_display),
            ("주식 검색 기능", self._test_stock_search),
            ("CSV 파일 업로드", self._test_csv_upload_flow),
            ("시장 상태 모니터링", self._test_market_status_monitoring),
            ("뉴스 분석 데이터 표시", self._test_news_analysis_display),
            ("시스템 상태 모니터링", self._test_system_monitoring),
            ("전체 워크플로우 통합", self._test_complete_workflow)
        ]
        
        for test_name, test_function in test_scenarios:
            await self._run_test_scenario(test_name, test_function)
            await asyncio.sleep(1)  # 테스트 간 간격
        
        # 성능 메트릭 수집
        self._collect_performance_metrics()
        
        # 결과 분석
        self._analyze_results()
        
        success_rate = (self.test_results['passed_tests'] / self.test_results['total_tests']) * 100
        print(f"✅ E2E UAT 테스트 완료: {self.test_results['passed_tests']}/{self.test_results['total_tests']} 통과 ({success_rate:.1f}%)")
        
        return self.test_results
    
    async def _run_test_scenario(self, test_name: str, test_function):
        """개별 테스트 시나리오 실행"""
        print(f"🔄 테스트 중: {test_name}")
        self.test_results['total_tests'] += 1
        
        start_time = time.time()
        
        try:
            result = await test_function()
            execution_time = time.time() - start_time
            
            scenario_result = {
                'name': test_name,
                'status': 'passed' if result['success'] else 'failed',
                'execution_time': round(execution_time, 3),
                'details': result,
                'timestamp': datetime.now().isoformat()
            }
            
            if result['success']:
                self.test_results['passed_tests'] += 1
                print(f"  ✅ {test_name}: 성공 ({execution_time:.2f}s)")
            else:
                self.test_results['failed_tests'] += 1
                print(f"  ❌ {test_name}: 실패 - {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            execution_time = time.time() - start_time
            scenario_result = {
                'name': test_name,
                'status': 'error',
                'execution_time': round(execution_time, 3),
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
            self.test_results['failed_tests'] += 1
            print(f"  💥 {test_name}: 오류 - {str(e)}")
        
        self.test_results['test_scenarios'].append(scenario_result)
    
    async def _test_dashboard_loading(self) -> Dict[str, Any]:
        """테스트 1: 사용자 대시보드 로딩"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                # 프론트엔드 헬스체크
                async with session.get(f"{self.frontend_url}") as response:
                    if response.status != 200:
                        return {'success': False, 'error': f'Frontend not accessible: {response.status}'}
                
                # 백엔드 API 헬스체크
                async with session.get(f"{self.backend_url}/health") as response:
                    backend_healthy = response.status == 200
                
                # 대시보드 API 헬스체크
                async with session.get(f"{self.dashboard_url}/health") as response:
                    dashboard_healthy = response.status == 200
                
                return {
                    'success': True,
                    'frontend_accessible': True,
                    'backend_healthy': backend_healthy,
                    'dashboard_healthy': dashboard_healthy
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _test_realtime_stock_data(self) -> Dict[str, Any]:
        """테스트 2: 실시간 주식 데이터 수신"""
        try:
            # WebSocket 연결 테스트
            async with websockets.connect(f"{self.websocket_url}/ws", timeout=10) as websocket:
                # 구독 메시지 전송
                subscribe_message = {
                    "type": "subscribe",
                    "events": ["us_stocks"],
                    "timestamp": datetime.now().isoformat()
                }
                
                await websocket.send(json.dumps(subscribe_message))
                
                # 응답 대기
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(response)
                
                # 주식 데이터 수신 대기
                stock_data = await asyncio.wait_for(websocket.recv(), timeout=15)
                stock_message = json.loads(stock_data)
                
                return {
                    'success': True,
                    'websocket_connected': True,
                    'subscription_confirmed': data.get('type') == 'subscribed',
                    'stock_data_received': stock_message.get('type') == 'us_stocks',
                    'data_sample': stock_message.get('payload', {}).get('stocks', [])[:2]
                }
                
        except asyncio.TimeoutError:
            return {'success': False, 'error': 'WebSocket timeout - no data received'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _test_ai_signal_notifications(self) -> Dict[str, Any]:
        """테스트 3: AI 시그널 알림 수신"""
        try:
            async with websockets.connect(f"{self.websocket_url}/ws", timeout=10) as websocket:
                # AI 시그널 구독
                subscribe_message = {
                    "type": "subscribe",
                    "events": ["ai_signals"],
                    "timestamp": datetime.now().isoformat()
                }
                
                await websocket.send(json.dumps(subscribe_message))
                
                # 구독 확인
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                
                # AI 시그널 대기
                signal_data = await asyncio.wait_for(websocket.recv(), timeout=15)
                signal_message = json.loads(signal_data)
                
                signals = signal_message.get('payload', {}).get('signals', [])
                
                return {
                    'success': True,
                    'ai_signals_received': len(signals) > 0,
                    'signals_count': len(signals),
                    'signal_types': list(set([s.get('signal_type') for s in signals[:3]])),
                    'confidence_scores': [s.get('confidence') for s in signals[:3]]
                }
                
        except asyncio.TimeoutError:
            return {'success': False, 'error': 'AI signals timeout'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _test_portfolio_display(self) -> Dict[str, Any]:
        """테스트 4: 포트폴리오 데이터 표시"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                # 포트폴리오 API 호출
                async with session.get(f"{self.dashboard_url}/api/portfolio/summary") as response:
                    if response.status != 200:
                        return {'success': False, 'error': f'Portfolio API error: {response.status}'}
                    
                    data = await response.json()
                    
                    return {
                        'success': True,
                        'portfolio_data_available': bool(data),
                        'has_holdings': 'holdings' in data,
                        'has_performance': 'performance' in data,
                        'data_structure_valid': isinstance(data, dict)
                    }
                    
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _test_stock_search(self) -> Dict[str, Any]:
        """테스트 5: 주식 검색 기능"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                # 주식 검색 테스트
                search_queries = ['AAPL', 'GOOGL', 'MSFT']
                search_results = []
                
                for query in search_queries:
                    async with session.get(f"{self.backend_url}/api/stocks/search", 
                                         params={'q': query}) as response:
                        if response.status == 200:
                            data = await response.json()
                            search_results.append({
                                'query': query,
                                'results_count': len(data.get('results', [])),
                                'has_results': len(data.get('results', [])) > 0
                            })
                        else:
                            search_results.append({
                                'query': query,
                                'error': response.status
                            })
                
                successful_searches = [r for r in search_results if 'error' not in r and r['has_results']]
                
                return {
                    'success': len(successful_searches) >= 2,
                    'total_searches': len(search_queries),
                    'successful_searches': len(successful_searches),
                    'search_results': search_results
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _test_csv_upload_flow(self) -> Dict[str, Any]:
        """테스트 6: CSV 파일 업로드"""
        try:
            # 테스트 CSV 파일 생성
            csv_content = "symbol,quantity,price,date\\nAAPL,100,150.25,2024-01-15\\nGOOGL,50,2800.50,2024-01-16"
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                # CSV 업로드 테스트
                data = aiohttp.FormData()
                data.add_field('file', csv_content.encode('utf-8'), 
                             filename='test.csv', 
                             content_type='text/csv')
                
                # 포트 8001로 수정 (API 서버가 실행되는 포트)
                async with session.post(f"http://localhost:8001/api/upload/csv", data=data) as response:
                    success = response.status in [200, 201]
                    
                    if success:
                        response_data = await response.json()
                        return {
                            'success': True,
                            'upload_successful': True,
                            'processed_rows': response_data.get('processed_rows', 0),
                            'filename': response_data.get('filename'),
                            'response_time': response_data.get('response_time', 0)
                        }
                    else:
                        error_text = await response.text()
                        return {'success': False, 'error': f'Upload failed: {response.status} - {error_text}'}
                        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _test_market_status_monitoring(self) -> Dict[str, Any]:
        """테스트 7: 시장 상태 모니터링"""
        try:
            async with websockets.connect(f"{self.websocket_url}/ws", timeout=10) as websocket:
                # 시장 상태 구독
                subscribe_message = {
                    "type": "subscribe",
                    "events": ["market_status"],
                    "timestamp": datetime.now().isoformat()
                }
                
                await websocket.send(json.dumps(subscribe_message))
                
                # 구독 확인
                await asyncio.wait_for(websocket.recv(), timeout=10)
                
                # 시장 상태 데이터 대기
                market_data = await asyncio.wait_for(websocket.recv(), timeout=15)
                market_message = json.loads(market_data)
                
                markets = market_message.get('payload', {}).get('markets', [])
                
                return {
                    'success': True,
                    'market_data_received': len(markets) > 0,
                    'markets_count': len(markets),
                    'market_info': [{'market_code': m.get('market_code'), 'status': m.get('status')} for m in markets[:2]]
                }
                
        except asyncio.TimeoutError:
            return {'success': False, 'error': 'Market status timeout'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _test_news_analysis_display(self) -> Dict[str, Any]:
        """테스트 8: 뉴스 분석 데이터 표시"""
        try:
            async with websockets.connect(f"{self.websocket_url}/ws", timeout=10) as websocket:
                # 뉴스 분석 구독
                subscribe_message = {
                    "type": "subscribe",
                    "events": ["us_news"],
                    "timestamp": datetime.now().isoformat()
                }
                
                await websocket.send(json.dumps(subscribe_message))
                
                # 구독 확인
                await asyncio.wait_for(websocket.recv(), timeout=10)
                
                # 뉴스 데이터 대기
                news_data = await asyncio.wait_for(websocket.recv(), timeout=15)
                news_message = json.loads(news_data)
                
                news_items = news_message.get('payload', {}).get('news', [])
                
                return {
                    'success': True,
                    'news_data_received': len(news_items) > 0,
                    'news_count': len(news_items),
                    'sentiment_analysis': len([n for n in news_items if 'sentiment' in n]) > 0,
                    'news_sample': news_items[:2] if news_items else []
                }
                
        except asyncio.TimeoutError:
            return {'success': False, 'error': 'News analysis timeout'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _test_system_monitoring(self) -> Dict[str, Any]:
        """테스트 9: 시스템 상태 모니터링"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                # 시스템 메트릭 확인
                async with session.get(f"{self.dashboard_url}/api/system/metrics") as response:
                    system_healthy = response.status == 200
                    
                    if system_healthy:
                        metrics_data = await response.json()
                    else:
                        metrics_data = {}
                
                # 서비스 상태 확인
                services_status = {}
                services = [
                    ('frontend', self.frontend_url),
                    ('backend', f"{self.backend_url}/health"),
                    ('dashboard', f"{self.dashboard_url}/health")
                ]
                
                for service_name, service_url in services:
                    try:
                        async with session.get(service_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                            services_status[service_name] = response.status == 200
                    except:
                        services_status[service_name] = False
                
                healthy_services = sum(services_status.values())
                
                return {
                    'success': healthy_services >= 2,  # 최소 2개 서비스가 정상이어야 함
                    'system_metrics_available': system_healthy,
                    'services_status': services_status,
                    'healthy_services_count': healthy_services,
                    'total_services': len(services),
                    'metrics_data': bool(metrics_data)
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _test_complete_workflow(self) -> Dict[str, Any]:
        """테스트 10: 전체 워크플로우 통합"""
        try:
            workflow_steps = []
            
            # 1단계: 대시보드 접근
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(f"{self.frontend_url}") as response:
                    workflow_steps.append({
                        'step': '대시보드 접근',
                        'success': response.status == 200
                    })
            
            # 2단계: WebSocket 연결 및 데이터 수신
            try:
                async with websockets.connect(f"{self.websocket_url}/ws", timeout=10) as websocket:
                    # 모든 이벤트 구독
                    subscribe_message = {
                        "type": "subscribe",
                        "events": ["us_stocks", "ai_signals", "market_status"],
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    await websocket.send(json.dumps(subscribe_message))
                    
                    # 구독 확인 및 첫 데이터 수신
                    await asyncio.wait_for(websocket.recv(), timeout=10)
                    data_received = await asyncio.wait_for(websocket.recv(), timeout=15)
                    
                    workflow_steps.append({
                        'step': '실시간 데이터 수신',
                        'success': bool(data_received)
                    })
                    
            except asyncio.TimeoutError:
                workflow_steps.append({
                    'step': '실시간 데이터 수신',
                    'success': False,
                    'error': 'Timeout'
                })
            
            # 3단계: API 상호작용
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(f"{self.backend_url}/api/stocks/search", 
                                     params={'q': 'AAPL'}) as response:
                    workflow_steps.append({
                        'step': 'API 상호작용',
                        'success': response.status == 200
                    })
            
            # 전체 성공 여부 판단
            successful_steps = len([s for s in workflow_steps if s['success']])
            total_steps = len(workflow_steps)
            
            return {
                'success': successful_steps >= total_steps * 0.7,  # 70% 이상 성공
                'workflow_steps': workflow_steps,
                'successful_steps': successful_steps,
                'total_steps': total_steps,
                'completion_rate': round((successful_steps / total_steps) * 100, 1) if total_steps > 0 else 0
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _collect_performance_metrics(self):
        """성능 메트릭 수집"""
        # 테스트 실행 시간 통계
        execution_times = [scenario.get('execution_time', 0) 
                          for scenario in self.test_results['test_scenarios'] 
                          if 'execution_time' in scenario]
        
        if execution_times:
            self.test_results['performance_metrics'] = {
                'average_execution_time': round(sum(execution_times) / len(execution_times), 3),
                'max_execution_time': max(execution_times),
                'min_execution_time': min(execution_times),
                'total_execution_time': round(sum(execution_times), 3)
            }
    
    def _analyze_results(self):
        """결과 분석 및 추천사항 생성"""
        total_tests = self.test_results['total_tests']
        passed_tests = self.test_results['passed_tests']
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        self.test_results['analysis'] = {
            'success_rate': round(success_rate, 2),
            'quality_grade': self._get_quality_grade(success_rate),
            'critical_failures': [
                scenario['name'] for scenario in self.test_results['test_scenarios']
                if scenario['status'] in ['failed', 'error'] and 
                scenario['name'] in ['사용자 대시보드 로딩', '실시간 주식 데이터 수신', '전체 워크플로우 통합']
            ],
            'recommendations': self._generate_recommendations(success_rate)
        }
    
    def _get_quality_grade(self, success_rate: float) -> str:
        """품질 등급 결정"""
        if success_rate >= 90:
            return 'A (우수)'
        elif success_rate >= 80:
            return 'B (양호)'
        elif success_rate >= 70:
            return 'C (보통)'
        elif success_rate >= 60:
            return 'D (개선필요)'
        else:
            return 'F (불량)'
    
    def _generate_recommendations(self, success_rate: float) -> List[str]:
        """추천사항 생성"""
        recommendations = []
        
        if success_rate < 70:
            recommendations.append("🚨 긴급: 핵심 기능 안정성 개선 필요")
            recommendations.append("🔧 서비스 연결성 및 에러 처리 강화 권장")
        elif success_rate < 90:
            recommendations.append("⚠️ 일부 기능 최적화 및 안정성 개선 권장")
            recommendations.append("📈 성능 튜닝 및 모니터링 강화")
        else:
            recommendations.append("✨ 우수한 품질 상태 유지")
            recommendations.append("🔄 정기적인 품질 검증 지속")
        
        recommendations.extend([
            "📊 성능 메트릭 모니터링 대시보드 구축",
            "🛡️ 자동화된 품질 게이트 적용",
            "📝 테스트 커버리지 확대 검토"
        ])
        
        return recommendations


async def main():
    """메인 실행 함수"""
    logger.info("🚀 StockPilot AI E2E UAT 자동화 테스트 시작")
    
    try:
        automation = E2EUATAutomation()
        results = await automation.run_e2e_uat_tests()
        
        # 결과를 JSON 파일로 저장
        with open('e2e_uat_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # 요약 보고서 출력
        print("\\n" + "="*80)
        print("📊 StockPilot AI E2E UAT 자동화 테스트 결과")
        print("="*80)
        print(f"테스트 수행 시간: {results['timestamp']}")
        print(f"전체 테스트: {results['total_tests']}개")
        print(f"통과 테스트: {results['passed_tests']}개")
        print(f"실패 테스트: {results['failed_tests']}개")
        print(f"성공률: {results['analysis']['success_rate']}%")
        print(f"품질 등급: {results['analysis']['quality_grade']}")
        
        # 성능 메트릭
        if 'performance_metrics' in results:
            metrics = results['performance_metrics']
            print(f"\\n⚡ 성능 메트릭:")
            print(f"  평균 실행시간: {metrics.get('average_execution_time', 0)}초")
            print(f"  최대 실행시간: {metrics.get('max_execution_time', 0)}초")
            print(f"  전체 실행시간: {metrics.get('total_execution_time', 0)}초")
        
        # 실패한 테스트
        failed_scenarios = [s for s in results['test_scenarios'] if s['status'] != 'passed']
        if failed_scenarios:
            print(f"\\n❌ 실패한 테스트:")
            for scenario in failed_scenarios:
                print(f"  - {scenario['name']}: {scenario.get('error', scenario.get('details', {}).get('error', 'Unknown'))}")
        
        # 추천사항
        if 'recommendations' in results['analysis']:
            print(f"\\n💡 추천사항:")
            for rec in results['analysis']['recommendations']:
                print(f"  {rec}")
        
        print("\\n💾 상세 결과: e2e_uat_results.json")
        print("="*80)
        print("🎉 E2E UAT 자동화 테스트 완료!")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ E2E UAT 테스트 실행 실패: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())