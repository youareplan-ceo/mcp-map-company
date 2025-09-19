#!/usr/bin/env python3
"""
오프라인 프리뷰 모드 테스트 스크립트
"""

import asyncio
import aiohttp
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OfflineModeTest:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        self.start_time = None
        
    async def test_endpoint(self, session: aiohttp.ClientSession, endpoint: str, description: str) -> Dict[str, Any]:
        """개별 엔드포인트 테스트"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            async with session.get(url) as response:
                response_time = (time.time() - start_time) * 1000
                data = await response.json()
                
                # 오프라인 모드 표시자 확인
                has_watermark = "watermark" in data or "OFFLINE" in str(data)
                offline_mock_logs = "OFFLINE-MOCK" in str(data)
                
                result = {
                    "endpoint": endpoint,
                    "description": description,
                    "status_code": response.status,
                    "response_time_ms": round(response_time, 2),
                    "success": response.status == 200,
                    "has_watermark": has_watermark,
                    "has_mock_data": bool(data.get("stocks") or data.get("signals") or data.get("portfolio") or data.get("news")),
                    "data_count": len(data.get("stocks", data.get("signals", data.get("portfolio", data.get("news_articles", data.get("results", [])))))),
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.info(f"✅ {endpoint}: {response.status} ({response_time:.1f}ms) - Watermark: {has_watermark}")
                return result
                
        except Exception as e:
            result = {
                "endpoint": endpoint,
                "description": description,
                "status_code": None,
                "response_time_ms": None,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"❌ {endpoint}: {str(e)}")
            return result

    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """포괄적인 오프라인 모드 테스트 실행"""
        self.start_time = time.time()
        logger.info("🔴 오프라인 프리뷰 모드 테스트 시작")
        
        # 테스트 대상 엔드포인트들
        test_endpoints = [
            ("/", "메인 서비스 정보"),
            ("/health", "헬스 체크"),
            ("/api/v1/stocks/realtime", "실시간 주식 데이터"),
            ("/api/v1/ai/signals", "AI 시그널"),
            ("/api/v1/portfolio", "포트폴리오 데이터"),
            ("/api/v1/news", "뉴스 및 감성 분석"),
            ("/api/v1/dashboard/widgets", "대시보드 위젯"),
            ("/api/v1/stocks/search?q=삼성", "주식 검색"),
            ("/api/v1/dashboard/summary", "대시보드 요약"),
            ("/api/v1/market/status", "시장 상태")
        ]
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for endpoint, description in test_endpoints:
                task = self.test_endpoint(session, endpoint, description)
                tasks.append(task)
            
            # 모든 테스트 병렬 실행
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 예외 처리
            self.test_results = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"테스트 실행 오류: {result}")
                    continue
                self.test_results.append(result)
        
        # 결과 분석
        total_time = time.time() - self.start_time
        analysis = self.analyze_results(total_time)
        
        return analysis

    def analyze_results(self, total_time: float) -> Dict[str, Any]:
        """테스트 결과 분석"""
        if not self.test_results:
            return {"error": "테스트 결과 없음"}
        
        successful_tests = [r for r in self.test_results if r.get("success", False)]
        failed_tests = [r for r in self.test_results if not r.get("success", True)]
        
        watermarked_tests = [r for r in successful_tests if r.get("has_watermark", False)]
        mock_data_tests = [r for r in successful_tests if r.get("has_mock_data", False)]
        
        response_times = [r["response_time_ms"] for r in successful_tests if r.get("response_time_ms")]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        analysis = {
            "test_summary": {
                "total_tests": len(self.test_results),
                "successful_tests": len(successful_tests),
                "failed_tests": len(failed_tests),
                "success_rate": (len(successful_tests) / len(self.test_results)) * 100,
                "total_execution_time_seconds": round(total_time, 2)
            },
            "offline_mode_verification": {
                "watermarked_responses": len(watermarked_tests),
                "mock_data_responses": len(mock_data_tests),
                "offline_mode_coverage": (len(watermarked_tests) / len(successful_tests)) * 100 if successful_tests else 0
            },
            "performance_metrics": {
                "average_response_time_ms": round(avg_response_time, 2),
                "fastest_response_ms": min(response_times) if response_times else 0,
                "slowest_response_ms": max(response_times) if response_times else 0
            },
            "detailed_results": self.test_results,
            "failed_tests": failed_tests,
            "timestamp": datetime.now().isoformat(),
            "test_passed": len(failed_tests) == 0 and len(watermarked_tests) >= 5  # 최소 5개 엔드포인트에서 워터마크 확인
        }
        
        return analysis

    def print_summary(self, analysis: Dict[str, Any]):
        """테스트 결과 요약 출력"""
        print("\n" + "="*60)
        print("🔴 오프라인 프리뷰 모드 테스트 결과")
        print("="*60)
        
        summary = analysis["test_summary"]
        offline = analysis["offline_mode_verification"]
        performance = analysis["performance_metrics"]
        
        print(f"📊 테스트 요약:")
        print(f"   • 총 테스트: {summary['total_tests']}")
        print(f"   • 성공: {summary['successful_tests']}")
        print(f"   • 실패: {summary['failed_tests']}")
        print(f"   • 성공률: {summary['success_rate']:.1f}%")
        print(f"   • 실행시간: {summary['total_execution_time_seconds']}초")
        
        print(f"\n🔴 오프라인 모드 검증:")
        print(f"   • 워터마크 응답: {offline['watermarked_responses']}")
        print(f"   • 모의 데이터 응답: {offline['mock_data_responses']}")
        print(f"   • 오프라인 모드 커버리지: {offline['offline_mode_coverage']:.1f}%")
        
        print(f"\n⚡ 성능 지표:")
        print(f"   • 평균 응답시간: {performance['average_response_time_ms']}ms")
        print(f"   • 최고 속도: {performance['fastest_response_ms']}ms")
        print(f"   • 최저 속도: {performance['slowest_response_ms']}ms")
        
        # 실패한 테스트 상세
        if analysis["failed_tests"]:
            print(f"\n❌ 실패한 테스트:")
            for test in analysis["failed_tests"]:
                print(f"   • {test['endpoint']}: {test.get('error', 'Unknown error')}")
        
        # 최종 판정
        if analysis["test_passed"]:
            print(f"\n✅ 오프라인 프리뷰 모드 테스트 통과!")
        else:
            print(f"\n❌ 오프라인 프리뷰 모드 테스트 실패")
        
        print("="*60)

async def main():
    """메인 테스트 실행"""
    tester = OfflineModeTest()
    analysis = await tester.run_comprehensive_test()
    tester.print_summary(analysis)
    
    # 결과를 파일로 저장
    with open("offline_mode_test_results.json", "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    
    logger.info("테스트 결과가 offline_mode_test_results.json에 저장되었습니다.")

if __name__ == "__main__":
    asyncio.run(main())