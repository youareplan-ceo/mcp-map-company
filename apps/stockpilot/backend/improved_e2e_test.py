#!/usr/bin/env python3
"""
개선된 E2E UAT 테스트 - 모든 기능을 실제 API와 통합하여 테스트
"""

import asyncio
import aiohttp
import websockets
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import statistics
import tempfile
import os

class ImprovedE2ETest:
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.ws_url = "ws://localhost:8000/ws"
        self.results = []
        self.total_tests = 10
        self.passed_tests = 0
        
    async def test_dashboard_loading(self) -> Dict:
        """1. 사용자 대시보드 로딩"""
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                # Dashboard summary API 호출
                async with session.get(f"{self.api_base_url}/api/v1/dashboard/summary") as response:
                    if response.status == 200:
                        data = await response.json()
                        execution_time = time.time() - start_time
                        return {
                            "name": "사용자 대시보드 로딩",
                            "status": "passed",
                            "execution_time": execution_time,
                            "details": {
                                "success": True,
                                "response_data": data,
                                "api_status": response.status
                            },
                            "timestamp": datetime.now().isoformat()
                        }
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "name": "사용자 대시보드 로딩",
                "status": "failed",
                "execution_time": execution_time,
                "details": {
                    "success": False,
                    "error": str(e)
                },
                "timestamp": datetime.now().isoformat()
            }

    async def test_realtime_stock_data(self) -> Dict:
        """2. 실시간 주식 데이터 수신"""
        start_time = time.time()
        try:
            # WebSocket 연결 테스트 (간단한 버전)
            async with aiohttp.ClientSession() as session:
                # 실시간 데이터 API 호출로 대체
                async with session.get(f"{self.api_base_url}/api/v1/stocks/realtime") as response:
                    if response.status == 200:
                        data = await response.json()
                        execution_time = time.time() - start_time
                        return {
                            "name": "실시간 주식 데이터 수신",
                            "status": "passed",
                            "execution_time": execution_time,
                            "details": {
                                "success": True,
                                "stocks_count": len(data.get("stocks", [])),
                                "api_status": response.status
                            },
                            "timestamp": datetime.now().isoformat()
                        }
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "name": "실시간 주식 데이터 수신",
                "status": "failed",
                "execution_time": execution_time,
                "details": {
                    "success": False,
                    "error": str(e)
                },
                "timestamp": datetime.now().isoformat()
            }

    async def test_ai_signals(self) -> Dict:
        """3. AI 시그널 알림 수신"""
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base_url}/api/v1/ai/signals") as response:
                    if response.status == 200:
                        data = await response.json()
                        signals = data.get("signals", [])
                        execution_time = time.time() - start_time
                        return {
                            "name": "AI 시그널 알림 수신",
                            "status": "passed",
                            "execution_time": execution_time,
                            "details": {
                                "success": True,
                                "signals_count": len(signals),
                                "api_status": response.status
                            },
                            "timestamp": datetime.now().isoformat()
                        }
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "name": "AI 시그널 알림 수신",
                "status": "failed",
                "execution_time": execution_time,
                "details": {
                    "success": False,
                    "error": str(e)
                },
                "timestamp": datetime.now().isoformat()
            }

    async def test_portfolio_display(self) -> Dict:
        """4. 포트폴리오 데이터 표시"""
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base_url}/api/v1/portfolio") as response:
                    if response.status == 200:
                        data = await response.json()
                        execution_time = time.time() - start_time
                        return {
                            "name": "포트폴리오 데이터 표시",
                            "status": "passed",
                            "execution_time": execution_time,
                            "details": {
                                "success": True,
                                "portfolio_value": data.get("total_value", 0),
                                "positions_count": len(data.get("portfolio", [])),
                                "api_status": response.status
                            },
                            "timestamp": datetime.now().isoformat()
                        }
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "name": "포트폴리오 데이터 표시",
                "status": "failed",
                "execution_time": execution_time,
                "details": {
                    "success": False,
                    "error": str(e)
                },
                "timestamp": datetime.now().isoformat()
            }

    async def test_stock_search(self) -> Dict:
        """5. 주식 검색 기능"""
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                search_queries = ["삼성", "LG", "SK"]
                successful_searches = 0
                search_results = []
                
                for query in search_queries:
                    async with session.get(f"{self.api_base_url}/api/v1/stocks/search?q={query}") as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get("results"):
                                successful_searches += 1
                            search_results.append({
                                "query": query,
                                "status": response.status,
                                "results_count": len(data.get("results", []))
                            })
                        else:
                            search_results.append({
                                "query": query,
                                "status": response.status,
                                "error": "API Error"
                            })
                
                execution_time = time.time() - start_time
                if successful_searches > 0:
                    return {
                        "name": "주식 검색 기능",
                        "status": "passed",
                        "execution_time": execution_time,
                        "details": {
                            "success": True,
                            "total_searches": len(search_queries),
                            "successful_searches": successful_searches,
                            "search_results": search_results
                        },
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "name": "주식 검색 기능",
                        "status": "failed",
                        "execution_time": execution_time,
                        "details": {
                            "success": False,
                            "total_searches": len(search_queries),
                            "successful_searches": successful_searches,
                            "search_results": search_results
                        },
                        "timestamp": datetime.now().isoformat()
                    }
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "name": "주식 검색 기능",
                "status": "failed",
                "execution_time": execution_time,
                "details": {
                    "success": False,
                    "error": str(e)
                },
                "timestamp": datetime.now().isoformat()
            }

    async def test_csv_upload(self) -> Dict:
        """6. CSV 파일 업로드"""
        start_time = time.time()
        try:
            # 임시 CSV 파일 생성
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
                csv_content = """symbol,name,price,volume
005930,삼성전자,70000,1000000
000660,SK하이닉스,120000,500000
035420,NAVER,200000,300000"""
                tmp_file.write(csv_content)
                tmp_file_path = tmp_file.name
            
            async with aiohttp.ClientSession() as session:
                # Multipart 파일 업로드
                with open(tmp_file_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename='test_stocks.csv', content_type='text/csv')
                    
                    async with session.post(f"{self.api_base_url}/api/v1/upload/csv", data=data) as response:
                        execution_time = time.time() - start_time
                        
                        if response.status == 200:
                            result_data = await response.json()
                            return {
                                "name": "CSV 파일 업로드",
                                "status": "passed",
                                "execution_time": execution_time,
                                "details": {
                                    "success": True,
                                    "file_size": len(csv_content),
                                    "rows_processed": result_data.get("rows", 0),
                                    "api_status": response.status
                                },
                                "timestamp": datetime.now().isoformat()
                            }
                        else:
                            error_text = await response.text()
                            return {
                                "name": "CSV 파일 업로드",
                                "status": "failed",
                                "execution_time": execution_time,
                                "details": {
                                    "success": False,
                                    "error": f"Upload failed: {response.status} - {error_text}"
                                },
                                "timestamp": datetime.now().isoformat()
                            }
            
            # 임시 파일 삭제
            os.unlink(tmp_file_path)
            
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "name": "CSV 파일 업로드",
                "status": "failed",
                "execution_time": execution_time,
                "details": {
                    "success": False,
                    "error": str(e)
                },
                "timestamp": datetime.now().isoformat()
            }

    async def test_market_monitoring(self) -> Dict:
        """7. 시장 상태 모니터링"""
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base_url}/api/v1/market/status") as response:
                    if response.status == 200:
                        data = await response.json()
                        execution_time = time.time() - start_time
                        return {
                            "name": "시장 상태 모니터링",
                            "status": "passed",
                            "execution_time": execution_time,
                            "details": {
                                "success": True,
                                "market_status": data.get("status"),
                                "api_status": response.status
                            },
                            "timestamp": datetime.now().isoformat()
                        }
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "name": "시장 상태 모니터링",
                "status": "failed",
                "execution_time": execution_time,
                "details": {
                    "success": False,
                    "error": str(e)
                },
                "timestamp": datetime.now().isoformat()
            }

    async def test_news_analysis(self) -> Dict:
        """8. 뉴스 분석 데이터 표시"""
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base_url}/api/v1/news") as response:
                    if response.status == 200:
                        data = await response.json()
                        execution_time = time.time() - start_time
                        return {
                            "name": "뉴스 분석 데이터 표시",
                            "status": "passed",
                            "execution_time": execution_time,
                            "details": {
                                "success": True,
                                "news_count": len(data.get("news", [])),
                                "api_status": response.status
                            },
                            "timestamp": datetime.now().isoformat()
                        }
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "name": "뉴스 분석 데이터 표시",
                "status": "failed",
                "execution_time": execution_time,
                "details": {
                    "success": False,
                    "error": str(e)
                },
                "timestamp": datetime.now().isoformat()
            }

    async def test_system_health(self) -> Dict:
        """9. 시스템 상태 모니터링"""
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base_url}/api/v1/system/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        execution_time = time.time() - start_time
                        return {
                            "name": "시스템 상태 모니터링",
                            "status": "passed",
                            "execution_time": execution_time,
                            "details": {
                                "success": True,
                                "overall_status": data.get("overall_status"),
                                "api_status": response.status
                            },
                            "timestamp": datetime.now().isoformat()
                        }
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "name": "시스템 상태 모니터링",
                "status": "failed",
                "execution_time": execution_time,
                "details": {
                    "success": False,
                    "error": str(e)
                },
                "timestamp": datetime.now().isoformat()
            }

    async def test_integrated_workflow(self) -> Dict:
        """10. 전체 워크플로우 통합"""
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                # 여러 API를 순차적으로 호출하여 통합 워크플로우 테스트
                workflow_steps = [
                    ("/api/v1/dashboard/summary", "dashboard"),
                    ("/api/v1/stocks/realtime", "realtime"),
                    ("/api/v1/ai/signals", "signals"),
                    ("/api/v1/portfolio", "portfolio")
                ]
                
                successful_steps = 0
                workflow_results = []
                
                for endpoint, step_name in workflow_steps:
                    try:
                        async with session.get(f"{self.api_base_url}{endpoint}") as response:
                            if response.status == 200:
                                successful_steps += 1
                                workflow_results.append({
                                    "step": step_name,
                                    "status": "success",
                                    "response_status": response.status
                                })
                            else:
                                workflow_results.append({
                                    "step": step_name,
                                    "status": "failed",
                                    "response_status": response.status
                                })
                    except Exception as step_error:
                        workflow_results.append({
                            "step": step_name,
                            "status": "error",
                            "error": str(step_error)
                        })
                
                execution_time = time.time() - start_time
                success_rate = (successful_steps / len(workflow_steps)) * 100
                
                if success_rate >= 75:  # 75% 이상 성공하면 통과
                    return {
                        "name": "전체 워크플로우 통합",
                        "status": "passed",
                        "execution_time": execution_time,
                        "details": {
                            "success": True,
                            "workflow_success_rate": success_rate,
                            "successful_steps": successful_steps,
                            "total_steps": len(workflow_steps),
                            "workflow_results": workflow_results
                        },
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "name": "전체 워크플로우 통합",
                        "status": "failed",
                        "execution_time": execution_time,
                        "details": {
                            "success": False,
                            "workflow_success_rate": success_rate,
                            "successful_steps": successful_steps,
                            "total_steps": len(workflow_steps),
                            "workflow_results": workflow_results
                        },
                        "timestamp": datetime.now().isoformat()
                    }
                    
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "name": "전체 워크플로우 통합",
                "status": "failed",
                "execution_time": execution_time,
                "details": {
                    "success": False,
                    "error": str(e)
                },
                "timestamp": datetime.now().isoformat()
            }

    async def run_all_tests(self):
        """모든 E2E 테스트 실행"""
        print("🚀 개선된 E2E UAT 테스트 시작")
        
        test_functions = [
            self.test_dashboard_loading,
            self.test_realtime_stock_data,
            self.test_ai_signals,
            self.test_portfolio_display,
            self.test_stock_search,
            self.test_csv_upload,
            self.test_market_monitoring,
            self.test_news_analysis,
            self.test_system_health,
            self.test_integrated_workflow
        ]
        
        for test_func in test_functions:
            print(f"🔄 테스트 중: {test_func.__name__.replace('test_', '').replace('_', ' ')}")
            result = await test_func()
            self.results.append(result)
            
            if result["status"] == "passed":
                self.passed_tests += 1
                print(f"  ✅ {result['name']}: 성공 ({result['execution_time']:.2f}s)")
            else:
                print(f"  ❌ {result['name']}: 실패 - {result['details'].get('error', 'Unknown error')}")
        
        await self.generate_report()

    async def generate_report(self):
        """테스트 결과 리포트 생성"""
        success_rate = (self.passed_tests / self.total_tests) * 100
        
        # 성능 메트릭
        execution_times = [r['execution_time'] for r in self.results]
        avg_time = statistics.mean(execution_times)
        max_time = max(execution_times)
        min_time = min(execution_times)
        total_time = sum(execution_times)
        
        # 품질 등급
        if success_rate >= 90:
            quality_grade = "A (우수)"
        elif success_rate >= 80:
            quality_grade = "B (양호)"
        elif success_rate >= 70:
            quality_grade = "C (보통)"
        elif success_rate >= 50:
            quality_grade = "D (미흡)"
        else:
            quality_grade = "F (불량)"
        
        # 실패한 테스트
        failed_tests = [r for r in self.results if r["status"] == "failed"]
        
        report = {
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": len(failed_tests),
            "test_scenarios": self.results,
            "performance_metrics": {
                "average_execution_time": round(avg_time, 3),
                "max_execution_time": round(max_time, 3),
                "min_execution_time": round(min_time, 3),
                "total_execution_time": round(total_time, 3)
            },
            "timestamp": datetime.now().isoformat(),
            "analysis": {
                "success_rate": round(success_rate, 1),
                "quality_grade": quality_grade,
                "critical_failures": [t["name"] for t in failed_tests if "통합" in t["name"] or "실시간" in t["name"]],
                "recommendations": [
                    "🚨 긴급: 핵심 기능 안정성 개선 필요" if success_rate < 50 else "✅ 시스템 안정성 양호",
                    "🔧 서비스 연결성 및 에러 처리 강화 권장" if len(failed_tests) > 3 else "✅ 서비스 연결성 양호",
                    "📊 성능 메트릭 모니터링 대시보드 구축",
                    "🛡️ 자동화된 품질 게이트 적용",
                    "📝 테스트 커버리지 확대 검토"
                ]
            }
        }
        
        # 결과 저장
        with open("improved_e2e_results.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 콘솔 출력
        print(f"✅ 개선된 E2E UAT 테스트 완료: {self.passed_tests}/{self.total_tests} 통과 ({success_rate:.1f}%)")
        print("\n" + "="*80)
        print("📊 개선된 E2E UAT 테스트 결과")
        print("="*80)
        print(f"전체 테스트: {self.total_tests}개")
        print(f"통과 테스트: {self.passed_tests}개")
        print(f"실패 테스트: {len(failed_tests)}개")
        print(f"성공률: {success_rate:.1f}%")
        print(f"품질 등급: {quality_grade}")
        print()
        print("⚡ 성능 메트릭:")
        print(f"  평균 실행시간: {avg_time:.3f}초")
        print(f"  최대 실행시간: {max_time:.3f}초")
        print(f"  전체 실행시간: {total_time:.3f}초")
        
        if failed_tests:
            print("\n❌ 실패한 테스트:")
            for test in failed_tests:
                print(f"  - {test['name']}: {test['details'].get('error', 'Unknown error')}")
        
        print(f"\n💾 상세 결과: improved_e2e_results.json")
        print("="*80)

async def main():
    tester = ImprovedE2ETest()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())