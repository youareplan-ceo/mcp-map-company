#!/usr/bin/env python3
"""
API 테스트 전후 비교 자동화
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from pathlib import Path

class APITestBeforeAfter:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.test_results = []
        
    async def test_api_endpoints(self):
        """API 엔드포인트 테스트 실행"""
        print("🔍 API 엔드포인트 테스트 실행 중...")
        
        test_endpoints = [
            {"name": "Backend Health Check", "url": "/health", "method": "GET"},
            {"name": "Stock Search API", "url": "/api/v1/stocks/search?q=삼성", "method": "GET"},
            {"name": "Portfolio API", "url": "/api/v1/portfolio/overview", "method": "GET"},
            {"name": "Alerts API", "url": "/api/v1/alerts/list", "method": "GET"},
            {"name": "Dashboard API", "url": "/api/v1/dashboard/widgets", "method": "GET"}
        ]
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                for endpoint in test_endpoints:
                    try:
                        url = f"{self.base_url}{endpoint['url']}"
                        start_time = datetime.now()
                        
                        async with session.get(url) as response:
                            end_time = datetime.now()
                            response_time = (end_time - start_time).total_seconds() * 1000
                            
                            status_code = response.status
                            success = status_code == 200
                            
                            try:
                                response_data = await response.json()
                            except:
                                response_data = {"error": "Invalid JSON response"}
                            
                            self.test_results.append({
                                "endpoint": endpoint["name"],
                                "url": endpoint["url"],
                                "method": endpoint["method"],
                                "status_code": status_code,
                                "success": success,
                                "response_time_ms": round(response_time, 2),
                                "response_size": len(str(response_data)),
                                "has_data": len(response_data) > 0,
                                "timestamp": datetime.now().isoformat()
                            })
                            
                    except Exception as e:
                        self.test_results.append({
                            "endpoint": endpoint["name"],
                            "url": endpoint["url"],
                            "method": endpoint["method"],
                            "status_code": 0,
                            "success": False,
                            "error": str(e),
                            "response_time_ms": 0,
                            "timestamp": datetime.now().isoformat()
                        })
                        
        except Exception as e:
            print(f"❌ 테스트 실행 오류: {str(e)}")
            
    def analyze_results(self):
        """테스트 결과 분석"""
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results if result.get('success', False))
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # 응답 시간 통계
        response_times = [r.get('response_time_ms', 0) for r in self.test_results if r.get('success', False)]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        
        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": total_tests - successful_tests,
            "success_rate": round(success_rate, 1),
            "performance": {
                "avg_response_time_ms": round(avg_response_time, 2),
                "max_response_time_ms": round(max_response_time, 2),
                "min_response_time_ms": round(min_response_time, 2)
            }
        }
        
    def generate_before_after_report(self):
        """전후 비교 리포트 생성"""
        print("📊 API 테스트 전후 비교 리포트 생성 중...")
        
        # 분석 결과
        analysis = self.analyze_results()
        
        # BEFORE (기존 상태) - 검증 리포트 기준
        before_data = {
            "total_tests": 5,
            "successful_tests": 3,
            "failed_tests": 2,
            "success_rate": 60.0,
            "failed_endpoints": [
                "Portfolio API (/api/v1/portfolio/overview)",
                "Alerts API (/api/v1/alerts/list)"
            ],
            "issues": [
                "404 Not Found errors on portfolio and alerts endpoints",
                "Missing route definitions",
                "Inconsistent URL patterns"
            ]
        }
        
        # AFTER (현재 상태)
        after_data = analysis.copy()
        after_data["improvements"] = []
        
        if after_data["success_rate"] > before_data["success_rate"]:
            after_data["improvements"].append("✅ API 성공률 향상")
        if after_data["failed_tests"] < before_data["failed_tests"]:
            after_data["improvements"].append("✅ 실패한 엔드포인트 수 감소")
        if after_data["success_rate"] >= 100:
            after_data["improvements"].append("✅ 100% API 성공률 달성")
            
        # 비교 리포트
        comparison_report = {
            "timestamp": datetime.now().isoformat(),
            "test_summary": {
                "before": before_data,
                "after": after_data
            },
            "improvements": {
                "success_rate_change": after_data["success_rate"] - before_data["success_rate"],
                "failed_tests_reduced": before_data["failed_tests"] - after_data["failed_tests"],
                "fixed_endpoints": []
            },
            "detailed_results": self.test_results,
            "recommendations": []
        }
        
        # 수정된 엔드포인트 식별
        for endpoint in before_data.get("failed_endpoints", []):
            endpoint_name = endpoint.split(" (")[0]
            current_result = next((r for r in self.test_results if endpoint_name in r.get("endpoint", "")), None)
            if current_result and current_result.get("success", False):
                comparison_report["improvements"]["fixed_endpoints"].append(endpoint_name)
        
        # 권장사항
        if after_data["success_rate"] < 100:
            comparison_report["recommendations"].append("🔧 남은 실패 엔드포인트 수정 필요")
        if after_data.get("performance", {}).get("avg_response_time_ms", 0) > 500:
            comparison_report["recommendations"].append("⚡ API 응답 시간 최적화 권장")
        if after_data["success_rate"] >= 100:
            comparison_report["recommendations"].append("✅ 모든 API 엔드포인트가 정상 작동합니다")
            
        return comparison_report
    
    async def run_test_and_generate_report(self):
        """테스트 실행 및 리포트 생성"""
        print("🚀 API 테스트 전후 비교 시작")
        print("="*60)
        
        # 1. API 테스트 실행
        await self.test_api_endpoints()
        
        # 2. 리포트 생성
        report = self.generate_before_after_report()
        
        # 3. 파일 저장
        with open("api_test_before_after_results.json", 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 4. 마크다운 리포트 생성
        await self.generate_markdown_report(report)
        
        print("="*60)
        print("✅ API 테스트 전후 비교 완료!")
        return report
        
    async def generate_markdown_report(self, report):
        """마크다운 리포트 생성"""
        before = report["test_summary"]["before"]
        after = report["test_summary"]["after"]
        
        markdown_content = f"""# API Test Before/After Comparison Report

Generated: {report["timestamp"]}

## 📊 Summary

### Before (Initial State)
- **Total Tests**: {before["total_tests"]}
- **Successful**: {before["successful_tests"]}
- **Failed**: {before["failed_tests"]}
- **Success Rate**: {before["success_rate"]}%

### After (Current State)  
- **Total Tests**: {after["total_tests"]}
- **Successful**: {after["successful_tests"]}
- **Failed**: {after["failed_tests"]}
- **Success Rate**: {after["success_rate"]}%

## 🔄 Improvements

- **Success Rate Change**: {report["improvements"]["success_rate_change"]:+.1f}%
- **Failed Tests Reduced**: {report["improvements"]["failed_tests_reduced"]}
- **Fixed Endpoints**: {len(report["improvements"]["fixed_endpoints"])}

## ✅ Fixed Endpoints

"""
        
        for endpoint in report["improvements"]["fixed_endpoints"]:
            markdown_content += f"- {endpoint}\n"
            
        markdown_content += f"""

## 📈 Performance Metrics

"""
        
        if "performance" in after:
            perf = after["performance"]
            markdown_content += f"""- **Average Response Time**: {perf["avg_response_time_ms"]:.2f}ms
- **Max Response Time**: {perf["max_response_time_ms"]:.2f}ms  
- **Min Response Time**: {perf["min_response_time_ms"]:.2f}ms
"""
        
        markdown_content += f"""

## 🔍 Detailed Test Results

| Endpoint | Status | Response Time | Success |
|----------|--------|---------------|---------|
"""
        
        for result in report["detailed_results"]:
            status_icon = "✅" if result.get("success", False) else "❌"
            response_time = result.get("response_time_ms", 0)
            markdown_content += f"| {result['endpoint']} | {result.get('status_code', 'N/A')} | {response_time:.2f}ms | {status_icon} |\n"
        
        markdown_content += f"""

## 💡 Recommendations

"""
        
        for rec in report.get("recommendations", []):
            markdown_content += f"- {rec}\n"
        
        # 파일 저장
        with open("API_TEST_BEFORE_AFTER.md", 'w', encoding='utf-8') as f:
            f.write(markdown_content)

async def main():
    tester = APITestBeforeAfter()
    report = await tester.run_test_and_generate_report()
    
    print(f"\n🎉 API 테스트 전후 비교 완료!")
    print(f"📊 성공률: {report['test_summary']['before']['success_rate']}% → {report['test_summary']['after']['success_rate']}%")
    print(f"🔧 수정된 엔드포인트: {len(report['improvements']['fixed_endpoints'])}개")
    print(f"📝 상세 리포트:")
    print(f"   - JSON: api_test_before_after_results.json")
    print(f"   - Markdown: API_TEST_BEFORE_AFTER.md")

if __name__ == "__main__":
    asyncio.run(main())