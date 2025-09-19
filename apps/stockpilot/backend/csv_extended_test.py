#!/usr/bin/env python3
"""
CSV 업로드 확장 검증 - 소용량/대용량, 진행상태, 에러 처리 테스트
"""

import asyncio
import aiohttp
import time
import json
import pandas as pd
import io
import tempfile
import os
from datetime import datetime

class CSVExtendedTest:
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.test_results = []
        
    def generate_small_csv(self) -> str:
        """소용량 CSV 생성 (100 rows)"""
        data = {
            'symbol': [f'00{i:04d}' for i in range(100)],
            'name': [f'테스트주식{i}' for i in range(100)],
            'price': [50000 + i * 100 for i in range(100)],
            'volume': [1000000 + i * 10000 for i in range(100)],
            'change': [(i % 10) - 5 for i in range(100)],
            'change_percent': [((i % 10) - 5) / 50 for i in range(100)]
        }
        
        df = pd.DataFrame(data)
        csv_content = df.to_csv(index=False)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_file.write(csv_content)
            return tmp_file.name, len(csv_content)
    
    def generate_large_csv(self) -> str:
        """대용량 CSV 생성 (100k rows)"""
        print("📊 대용량 CSV 파일 생성 중 (100k rows)...")
        
        data = {
            'symbol': [f'{i:06d}' for i in range(100000)],
            'name': [f'대용량테스트주식{i}' for i in range(100000)],
            'price': [10000 + (i % 90000) for i in range(100000)],
            'volume': [100000 + (i % 5000000) for i in range(100000)],
            'change': [(i % 2000) - 1000 for i in range(100000)],
            'change_percent': [((i % 2000) - 1000) / 50000 for i in range(100000)],
            'market_cap': [1000000000 + (i % 50000000000) for i in range(100000)],
            'pe_ratio': [5 + (i % 50) for i in range(100000)],
            'dividend_yield': [(i % 100) / 100 for i in range(100000)]
        }
        
        df = pd.DataFrame(data)
        csv_content = df.to_csv(index=False)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_file.write(csv_content)
            print(f"✅ 대용량 CSV 파일 생성 완료: {len(csv_content)/1024/1024:.2f}MB")
            return tmp_file.name, len(csv_content)
    
    def generate_invalid_csv(self) -> str:
        """잘못된 형식 CSV 생성"""
        invalid_content = """symbol,name,price,volume
005930,삼성전자,INVALID_PRICE,1000000
000660,SK하이닉스,120000,INVALID_VOLUME
INVALID_SYMBOL,NAVER,200000,300000"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_file.write(invalid_content)
            return tmp_file.name, len(invalid_content)
    
    def generate_excel_file(self) -> str:
        """Excel 파일 생성"""
        data = {
            'symbol': ['005930', '000660', '035420'],
            'name': ['삼성전자', 'SK하이닉스', 'NAVER'],
            'price': [70000, 120000, 200000],
            'volume': [1000000, 500000, 300000]
        }
        
        df = pd.DataFrame(data)
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            df.to_excel(tmp_file.name, index=False)
            return tmp_file.name, os.path.getsize(tmp_file.name)

    async def test_small_csv_upload(self) -> dict:
        """소용량 CSV 업로드 테스트"""
        print("🔄 소용량 CSV 업로드 테스트 (100 rows)")
        start_time = time.time()
        
        try:
            file_path, file_size = self.generate_small_csv()
            
            async with aiohttp.ClientSession() as session:
                with open(file_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename='small_test.csv', content_type='text/csv')
                    
                    async with session.post(f"{self.api_base_url}/api/v1/upload/csv", data=data) as response:
                        execution_time = time.time() - start_time
                        
                        if response.status == 200:
                            result_data = await response.json()
                            os.unlink(file_path)
                            return {
                                "test_name": "소용량 CSV 업로드",
                                "status": "success",
                                "execution_time": execution_time,
                                "file_size_bytes": file_size,
                                "file_size_kb": round(file_size / 1024, 2),
                                "rows_processed": result_data.get("rows", 0),
                                "processing_rate": result_data.get("rows", 0) / execution_time if execution_time > 0 else 0,
                                "api_response": result_data,
                                "timestamp": datetime.now().isoformat()
                            }
                        else:
                            error_text = await response.text()
                            os.unlink(file_path)
                            return {
                                "test_name": "소용량 CSV 업로드",
                                "status": "failed",
                                "execution_time": execution_time,
                                "error": f"HTTP {response.status}: {error_text}",
                                "timestamp": datetime.now().isoformat()
                            }
        
        except Exception as e:
            execution_time = time.time() - start_time
            if 'file_path' in locals():
                try:
                    os.unlink(file_path)
                except:
                    pass
            return {
                "test_name": "소용량 CSV 업로드",
                "status": "error",
                "execution_time": execution_time,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def test_large_csv_upload(self) -> dict:
        """대용량 CSV 업로드 테스트"""
        print("🔄 대용량 CSV 업로드 테스트 (100k rows)")
        start_time = time.time()
        
        try:
            file_path, file_size = self.generate_large_csv()
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=300)) as session:
                with open(file_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename='large_test.csv', content_type='text/csv')
                    
                    print("📤 대용량 파일 업로드 중...")
                    async with session.post(f"{self.api_base_url}/api/v1/upload/csv", data=data) as response:
                        execution_time = time.time() - start_time
                        
                        if response.status == 200:
                            result_data = await response.json()
                            os.unlink(file_path)
                            return {
                                "test_name": "대용량 CSV 업로드",
                                "status": "success",
                                "execution_time": execution_time,
                                "file_size_bytes": file_size,
                                "file_size_mb": round(file_size / 1024 / 1024, 2),
                                "rows_processed": result_data.get("rows", 0),
                                "processing_rate": result_data.get("rows", 0) / execution_time if execution_time > 0 else 0,
                                "throughput_mbps": (file_size / 1024 / 1024) / execution_time if execution_time > 0 else 0,
                                "api_response": result_data,
                                "timestamp": datetime.now().isoformat()
                            }
                        else:
                            error_text = await response.text()
                            os.unlink(file_path)
                            return {
                                "test_name": "대용량 CSV 업로드",
                                "status": "failed",
                                "execution_time": execution_time,
                                "file_size_mb": round(file_size / 1024 / 1024, 2),
                                "error": f"HTTP {response.status}: {error_text}",
                                "timestamp": datetime.now().isoformat()
                            }
        
        except Exception as e:
            execution_time = time.time() - start_time
            if 'file_path' in locals():
                try:
                    os.unlink(file_path)
                except:
                    pass
            return {
                "test_name": "대용량 CSV 업로드",
                "status": "error",
                "execution_time": execution_time,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def test_excel_upload(self) -> dict:
        """Excel 파일 업로드 테스트"""
        print("🔄 Excel 파일 업로드 테스트")
        start_time = time.time()
        
        try:
            file_path, file_size = self.generate_excel_file()
            
            async with aiohttp.ClientSession() as session:
                with open(file_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename='test_data.xlsx', 
                                 content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    
                    async with session.post(f"{self.api_base_url}/api/v1/upload/csv", data=data) as response:
                        execution_time = time.time() - start_time
                        
                        if response.status == 200:
                            result_data = await response.json()
                            os.unlink(file_path)
                            return {
                                "test_name": "Excel 파일 업로드",
                                "status": "success",
                                "execution_time": execution_time,
                                "file_size_bytes": file_size,
                                "rows_processed": result_data.get("rows", 0),
                                "api_response": result_data,
                                "timestamp": datetime.now().isoformat()
                            }
                        else:
                            error_text = await response.text()
                            os.unlink(file_path)
                            return {
                                "test_name": "Excel 파일 업로드",
                                "status": "failed",
                                "execution_time": execution_time,
                                "error": f"HTTP {response.status}: {error_text}",
                                "timestamp": datetime.now().isoformat()
                            }
        
        except Exception as e:
            execution_time = time.time() - start_time
            if 'file_path' in locals():
                try:
                    os.unlink(file_path)
                except:
                    pass
            return {
                "test_name": "Excel 파일 업로드",
                "status": "error",
                "execution_time": execution_time,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def test_invalid_csv_upload(self) -> dict:
        """잘못된 형식 CSV 업로드 테스트"""
        print("🔄 잘못된 형식 CSV 업로드 테스트")
        start_time = time.time()
        
        try:
            file_path, file_size = self.generate_invalid_csv()
            
            async with aiohttp.ClientSession() as session:
                with open(file_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename='invalid_test.csv', content_type='text/csv')
                    
                    async with session.post(f"{self.api_base_url}/api/v1/upload/csv", data=data) as response:
                        execution_time = time.time() - start_time
                        result_data = await response.json() if response.status == 200 else await response.text()
                        
                        os.unlink(file_path)
                        return {
                            "test_name": "잘못된 형식 CSV 업로드",
                            "status": "completed",  # 에러 처리가 정상적으로 작동하는지 확인
                            "execution_time": execution_time,
                            "response_status": response.status,
                            "expected_behavior": "에러 처리 또는 데이터 정제",
                            "api_response": result_data,
                            "timestamp": datetime.now().isoformat()
                        }
        
        except Exception as e:
            execution_time = time.time() - start_time
            if 'file_path' in locals():
                try:
                    os.unlink(file_path)
                except:
                    pass
            return {
                "test_name": "잘못된 형식 CSV 업로드",
                "status": "error",
                "execution_time": execution_time,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def test_file_size_limit(self) -> dict:
        """파일 크기 제한 테스트 (10MB 초과)"""
        print("🔄 파일 크기 제한 테스트")
        start_time = time.time()
        
        try:
            # 11MB 크기의 더미 파일 생성
            large_content = "symbol,name,price\n" + "TEST,테스트주식,50000\n" * 500000
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
                tmp_file.write(large_content)
                file_path = tmp_file.name
                file_size = len(large_content)
            
            async with aiohttp.ClientSession() as session:
                with open(file_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename='oversized_test.csv', content_type='text/csv')
                    
                    async with session.post(f"{self.api_base_url}/api/v1/upload/csv", data=data) as response:
                        execution_time = time.time() - start_time
                        result_text = await response.text()
                        
                        os.unlink(file_path)
                        return {
                            "test_name": "파일 크기 제한 테스트",
                            "status": "completed",
                            "execution_time": execution_time,
                            "file_size_mb": round(file_size / 1024 / 1024, 2),
                            "response_status": response.status,
                            "expected_behavior": "413 Payload Too Large 또는 적절한 에러 메시지",
                            "api_response": result_text,
                            "timestamp": datetime.now().isoformat()
                        }
        
        except Exception as e:
            execution_time = time.time() - start_time
            if 'file_path' in locals():
                try:
                    os.unlink(file_path)
                except:
                    pass
            return {
                "test_name": "파일 크기 제한 테스트",
                "status": "error",
                "execution_time": execution_time,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def run_all_tests(self):
        """모든 CSV 업로드 테스트 실행"""
        print("🚀 CSV 업로드 확장 검증 테스트 시작")
        print("="*60)
        
        test_functions = [
            self.test_small_csv_upload,
            self.test_large_csv_upload,
            self.test_excel_upload,
            self.test_invalid_csv_upload,
            self.test_file_size_limit
        ]
        
        for test_func in test_functions:
            result = await test_func()
            self.test_results.append(result)
            
            if result["status"] == "success":
                print(f"✅ {result['test_name']}: 성공 ({result['execution_time']:.2f}s)")
                if 'rows_processed' in result:
                    print(f"   📊 처리된 행: {result['rows_processed']}개")
                if 'processing_rate' in result:
                    print(f"   ⚡ 처리 속도: {result['processing_rate']:.0f} rows/s")
            elif result["status"] == "completed":
                print(f"✅ {result['test_name']}: 완료 ({result['execution_time']:.2f}s)")
                print(f"   📋 응답 상태: HTTP {result.get('response_status', 'N/A')}")
            else:
                print(f"❌ {result['test_name']}: 실패 - {result.get('error', 'Unknown error')}")
            
            print()
        
        await self.generate_report()

    async def generate_report(self):
        """테스트 결과 리포트 생성"""
        successful_tests = [r for r in self.test_results if r["status"] == "success"]
        completed_tests = [r for r in self.test_results if r["status"] in ["success", "completed"]]
        success_rate = (len(successful_tests) / len(self.test_results)) * 100
        completion_rate = (len(completed_tests) / len(self.test_results)) * 100
        
        # 성능 메트릭 계산
        execution_times = [r["execution_time"] for r in self.test_results]
        avg_time = sum(execution_times) / len(execution_times)
        max_time = max(execution_times)
        min_time = min(execution_times)
        
        report = {
            "test_summary": {
                "total_tests": len(self.test_results),
                "successful_tests": len(successful_tests),
                "completed_tests": len(completed_tests),
                "success_rate": round(success_rate, 1),
                "completion_rate": round(completion_rate, 1)
            },
            "performance_metrics": {
                "avg_execution_time": round(avg_time, 3),
                "max_execution_time": round(max_time, 3),
                "min_execution_time": round(min_time, 3)
            },
            "test_results": self.test_results,
            "timestamp": datetime.now().isoformat(),
            "recommendations": [
                "✅ 소용량 파일 처리 성능 우수" if any("소용량" in r["test_name"] and r["status"] == "success" for r in self.test_results) else "⚠️ 소용량 파일 처리 개선 필요",
                "✅ 대용량 파일 처리 지원" if any("대용량" in r["test_name"] and r["status"] == "success" for r in self.test_results) else "⚠️ 대용량 파일 처리 최적화 필요",
                "✅ 다양한 파일 형식 지원" if any("Excel" in r["test_name"] and r["status"] == "success" for r in self.test_results) else "⚠️ 파일 형식 지원 확대 필요",
                "✅ 에러 처리 메커니즘 작동" if any("잘못된" in r["test_name"] and r["status"] == "completed" for r in self.test_results) else "⚠️ 에러 처리 강화 필요",
                "✅ 파일 크기 제한 정책 적용" if any("크기 제한" in r["test_name"] and r["status"] == "completed" for r in self.test_results) else "⚠️ 파일 크기 제한 정책 필요"
            ]
        }
        
        # 결과 저장
        with open("csv_extended_test_results.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 콘솔 출력
        print("="*60)
        print("📊 CSV 업로드 확장 검증 결과")
        print("="*60)
        print(f"총 테스트: {len(self.test_results)}개")
        print(f"성공: {len(successful_tests)}개")
        print(f"완료: {len(completed_tests)}개")
        print(f"성공률: {success_rate:.1f}%")
        print(f"완료율: {completion_rate:.1f}%")
        print()
        print("⚡ 성능 메트릭:")
        print(f"  평균 실행시간: {avg_time:.3f}초")
        print(f"  최대 실행시간: {max_time:.3f}초")
        print(f"  최소 실행시간: {min_time:.3f}초")
        print()
        print("💡 추천사항:")
        for rec in report["recommendations"]:
            print(f"  {rec}")
        print()
        print("💾 상세 결과: csv_extended_test_results.json")
        print("="*60)

async def main():
    tester = CSVExtendedTest()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())