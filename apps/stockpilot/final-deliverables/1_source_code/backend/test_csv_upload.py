#!/usr/bin/env python3
"""
StockPilot CSV 업로드 기능 검증 스크립트
작성자: StockPilot Team
용도: CSV/Excel 파일 업로드 스트레스 테스트, 대용량 파일 처리 검증
"""

import asyncio
import aiohttp
import pandas as pd
import io
import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import tempfile
import random
import string
from pathlib import Path
import numpy as np

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('csv_upload_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CSVUploadTester:
    """CSV 업로드 기능 테스터 클래스"""
    
    def __init__(self):
        self.base_url = 'http://localhost:8001'
        self.test_results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'upload_tests': [],
            'performance_stats': {},
            'errors': []
        }
    
    async def run_csv_tests(self) -> Dict[str, Any]:
        """모든 CSV 업로드 테스트 실행"""
        logger.info("📊 CSV 업로드 테스트 시작")
        
        # 1. 기본 CSV 파일 테스트
        await self._test_basic_csv_upload()
        
        # 2. Excel 파일 테스트
        await self._test_excel_upload()
        
        # 3. 대용량 파일 테스트
        await self._test_large_file_upload()
        
        # 4. 잘못된 형식 파일 테스트
        await self._test_invalid_file_upload()
        
        # 5. 동시 업로드 테스트
        await self._test_concurrent_uploads()
        
        # 6. 파일 크기 제한 테스트
        await self._test_file_size_limits()
        
        # 7. 데이터 유효성 검증 테스트
        await self._test_data_validation()
        
        # 8. 성능 스트레스 테스트
        await self._test_performance_stress()
        
        # 결과 리포트 생성
        report = self._generate_report()
        
        logger.info(f"✅ CSV 테스트 완료: {self.test_results['passed_tests']}/{self.test_results['total_tests']} 통과")
        
        return report
    
    async def _test_basic_csv_upload(self):
        """기본 CSV 파일 업로드 테스트"""
        logger.info("📁 기본 CSV 업로드 테스트")
        
        try:
            # 테스트용 CSV 데이터 생성
            test_data = [
                {'symbol': 'AAPL', 'quantity': 100, 'price': 150.25, 'date': '2024-01-15'},
                {'symbol': 'GOOGL', 'quantity': 50, 'price': 2800.50, 'date': '2024-01-16'},
                {'symbol': 'MSFT', 'quantity': 75, 'price': 400.75, 'date': '2024-01-17'},
                {'symbol': 'TSLA', 'quantity': 25, 'price': 200.00, 'date': '2024-01-18'},
                {'symbol': 'AMZN', 'quantity': 30, 'price': 3200.25, 'date': '2024-01-19'}
            ]
            
            # CSV 파일 생성
            csv_content = self._create_csv_content(test_data)
            
            # 업로드 테스트
            result = await self._upload_file(
                content=csv_content.encode('utf-8'),
                filename='test_basic.csv',
                content_type='text/csv'
            )
            
            self._record_test_result(
                test_name='기본 CSV 업로드',
                success=result['success'],
                response_time=result['response_time'],
                file_size=len(csv_content),
                error=result.get('error')
            )
            
            if result['success']:
                logger.info("✅ 기본 CSV 업로드 성공")
            else:
                logger.error(f"❌ 기본 CSV 업로드 실패: {result.get('error')}")
                
        except Exception as e:
            self._record_test_result(
                test_name='기본 CSV 업로드',
                success=False,
                error=str(e)
            )
            logger.error(f"❌ 기본 CSV 테스트 실패: {e}")
    
    async def _test_excel_upload(self):
        """Excel 파일 업로드 테스트"""
        logger.info("📊 Excel 업로드 테스트")
        
        try:
            # 테스트용 Excel 데이터 생성
            test_data = pd.DataFrame({
                'symbol': ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN'],
                'quantity': [100, 50, 75, 25, 30],
                'price': [150.25, 2800.50, 400.75, 200.00, 3200.25],
                'date': ['2024-01-15', '2024-01-16', '2024-01-17', '2024-01-18', '2024-01-19']
            })
            
            # Excel 파일로 변환
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
                test_data.to_excel(tmp_file.name, index=False)
                
                with open(tmp_file.name, 'rb') as f:
                    excel_content = f.read()
                
                os.unlink(tmp_file.name)
            
            # 업로드 테스트
            result = await self._upload_file(
                content=excel_content,
                filename='test_basic.xlsx',
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
            self._record_test_result(
                test_name='Excel 업로드',
                success=result['success'],
                response_time=result['response_time'],
                file_size=len(excel_content),
                error=result.get('error')
            )
            
            if result['success']:
                logger.info("✅ Excel 업로드 성공")
            else:
                logger.error(f"❌ Excel 업로드 실패: {result.get('error')}")
                
        except Exception as e:
            self._record_test_result(
                test_name='Excel 업로드',
                success=False,
                error=str(e)
            )
            logger.error(f"❌ Excel 테스트 실패: {e}")
    
    async def _test_large_file_upload(self):
        """대용량 파일 업로드 테스트"""
        logger.info("🏋️ 대용량 파일 업로드 테스트")
        
        try:
            # 10,000 행의 대용량 CSV 데이터 생성
            large_data = []
            symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'META', 'NFLX', 'NVDA', 'AMD', 'INTC']
            
            for i in range(10000):
                large_data.append({
                    'symbol': random.choice(symbols),
                    'quantity': random.randint(1, 1000),
                    'price': round(random.uniform(10.0, 5000.0), 2),
                    'date': (datetime.now() - timedelta(days=random.randint(0, 365))).strftime('%Y-%m-%d'),
                    'order_type': random.choice(['BUY', 'SELL']),
                    'portfolio_id': f'portfolio_{random.randint(1, 100)}'
                })
            
            csv_content = self._create_csv_content(large_data)
            
            # 업로드 테스트
            start_time = time.time()
            result = await self._upload_file(
                content=csv_content.encode('utf-8'),
                filename='test_large.csv',
                content_type='text/csv'
            )
            
            self._record_test_result(
                test_name='대용량 파일 업로드',
                success=result['success'],
                response_time=result['response_time'],
                file_size=len(csv_content),
                rows_count=len(large_data),
                error=result.get('error')
            )
            
            if result['success']:
                logger.info(f"✅ 대용량 파일 업로드 성공 ({len(large_data):,}행, {len(csv_content):,}바이트)")
            else:
                logger.error(f"❌ 대용량 파일 업로드 실패: {result.get('error')}")
                
        except Exception as e:
            self._record_test_result(
                test_name='대용량 파일 업로드',
                success=False,
                error=str(e)
            )
            logger.error(f"❌ 대용량 파일 테스트 실패: {e}")
    
    async def _test_invalid_file_upload(self):
        """잘못된 형식 파일 업로드 테스트"""
        logger.info("❌ 잘못된 형식 파일 테스트")
        
        test_cases = [
            {
                'name': '텍스트 파일',
                'content': 'This is not a CSV file',
                'filename': 'test.txt',
                'content_type': 'text/plain'
            },
            {
                'name': '빈 파일',
                'content': '',
                'filename': 'empty.csv',
                'content_type': 'text/csv'
            },
            {
                'name': '잘못된 CSV 헤더',
                'content': 'invalid,header,format\\ndata1,data2,data3',
                'filename': 'invalid_header.csv',
                'content_type': 'text/csv'
            },
            {
                'name': '이미지 파일',
                'content': b'\\x89PNG\\r\\n\\x1a\\n\\x00\\x00\\x00\\rIHDR\\x00\\x00',
                'filename': 'test.png',
                'content_type': 'image/png'
            }
        ]
        
        for case in test_cases:
            try:
                content = case['content'] if isinstance(case['content'], bytes) else case['content'].encode('utf-8')
                
                result = await self._upload_file(
                    content=content,
                    filename=case['filename'],
                    content_type=case['content_type']
                )
                
                # 잘못된 파일은 실패해야 함
                expected_failure = True
                actual_success = result['success']
                
                test_success = not actual_success if expected_failure else actual_success
                
                self._record_test_result(
                    test_name=f'잘못된 형식: {case["name"]}',
                    success=test_success,
                    response_time=result['response_time'],
                    file_size=len(content),
                    error=result.get('error') if not test_success else None
                )
                
                if test_success:
                    logger.info(f"✅ {case['name']} 검증 성공 (올바르게 거부됨)")
                else:
                    logger.warning(f"⚠️ {case['name']} 검증 실패 (잘못 허용됨)")
                    
            except Exception as e:
                self._record_test_result(
                    test_name=f'잘못된 형식: {case["name"]}',
                    success=False,
                    error=str(e)
                )
                logger.error(f"❌ {case['name']} 테스트 실패: {e}")
    
    async def _test_concurrent_uploads(self):
        """동시 업로드 테스트"""
        logger.info("⚡ 동시 업로드 테스트")
        
        try:
            concurrent_count = 5
            tasks = []
            
            for i in range(concurrent_count):
                # 각각 다른 테스트 데이터 생성
                test_data = [
                    {'symbol': f'TEST{i}_{j}', 'quantity': random.randint(1, 100), 'price': random.uniform(10, 1000), 'date': '2024-01-15'}
                    for j in range(100)
                ]
                
                csv_content = self._create_csv_content(test_data)
                
                task = self._upload_file(
                    content=csv_content.encode('utf-8'),
                    filename=f'concurrent_test_{i}.csv',
                    content_type='text/csv'
                )
                tasks.append(task)
            
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            successful_uploads = sum(1 for r in results if not isinstance(r, Exception) and r.get('success', False))
            
            self.test_results['performance_stats']['concurrent_uploads'] = {
                'total_uploads': concurrent_count,
                'successful_uploads': successful_uploads,
                'total_time': total_time,
                'uploads_per_second': concurrent_count / total_time if total_time > 0 else 0
            }
            
            self._record_test_result(
                test_name='동시 업로드',
                success=successful_uploads >= concurrent_count * 0.8,  # 80% 이상 성공
                response_time=total_time * 1000,
                concurrent_count=concurrent_count,
                successful_count=successful_uploads
            )
            
            logger.info(f"✅ 동시 업로드 테스트: {successful_uploads}/{concurrent_count} 성공")
            
        except Exception as e:
            self._record_test_result(
                test_name='동시 업로드',
                success=False,
                error=str(e)
            )
            logger.error(f"❌ 동시 업로드 테스트 실패: {e}")
    
    async def _test_file_size_limits(self):
        """파일 크기 제한 테스트"""
        logger.info("📏 파일 크기 제한 테스트")
        
        # 다양한 크기의 파일 테스트
        size_tests = [
            {'name': '1KB 파일', 'rows': 10},
            {'name': '100KB 파일', 'rows': 1000},
            {'name': '1MB 파일', 'rows': 10000},
            {'name': '5MB 파일', 'rows': 50000},
        ]
        
        for test in size_tests:
            try:
                # 지정된 행 수만큼 데이터 생성
                test_data = []
                for i in range(test['rows']):
                    test_data.append({
                        'symbol': f'STOCK{i % 100}',
                        'quantity': random.randint(1, 1000),
                        'price': round(random.uniform(1.0, 1000.0), 2),
                        'date': '2024-01-15',
                        'extra_field': ''.join(random.choices(string.ascii_letters, k=50))  # 파일 크기 증가용
                    })
                
                csv_content = self._create_csv_content(test_data)
                file_size_mb = len(csv_content) / (1024 * 1024)
                
                result = await self._upload_file(
                    content=csv_content.encode('utf-8'),
                    filename=f'size_test_{test["rows"]}.csv',
                    content_type='text/csv'
                )
                
                self._record_test_result(
                    test_name=f'크기 테스트: {test["name"]}',
                    success=result['success'],
                    response_time=result['response_time'],
                    file_size=len(csv_content),
                    file_size_mb=round(file_size_mb, 2),
                    rows_count=test['rows'],
                    error=result.get('error')
                )
                
                if result['success']:
                    logger.info(f"✅ {test['name']} 성공 ({file_size_mb:.2f}MB)")
                else:
                    logger.warning(f"⚠️ {test['name']} 실패: {result.get('error')}")
                    
            except Exception as e:
                self._record_test_result(
                    test_name=f'크기 테스트: {test["name"]}',
                    success=False,
                    error=str(e)
                )
                logger.error(f"❌ {test['name']} 테스트 실패: {e}")
    
    async def _test_data_validation(self):
        """데이터 유효성 검증 테스트"""
        logger.info("🔍 데이터 유효성 검증 테스트")
        
        validation_tests = [
            {
                'name': '올바른 데이터',
                'data': [
                    {'symbol': 'AAPL', 'quantity': 100, 'price': 150.25, 'date': '2024-01-15'},
                    {'symbol': 'GOOGL', 'quantity': 50, 'price': 2800.50, 'date': '2024-01-16'}
                ],
                'should_pass': True
            },
            {
                'name': '빈 심볼',
                'data': [
                    {'symbol': '', 'quantity': 100, 'price': 150.25, 'date': '2024-01-15'},
                ],
                'should_pass': False
            },
            {
                'name': '음수 수량',
                'data': [
                    {'symbol': 'AAPL', 'quantity': -100, 'price': 150.25, 'date': '2024-01-15'},
                ],
                'should_pass': False
            },
            {
                'name': '잘못된 날짜 형식',
                'data': [
                    {'symbol': 'AAPL', 'quantity': 100, 'price': 150.25, 'date': '15-01-2024'},
                ],
                'should_pass': False
            },
            {
                'name': '문자열 가격',
                'data': [
                    {'symbol': 'AAPL', 'quantity': 100, 'price': 'expensive', 'date': '2024-01-15'},
                ],
                'should_pass': False
            }
        ]
        
        for test in validation_tests:
            try:
                csv_content = self._create_csv_content(test['data'])
                
                result = await self._upload_file(
                    content=csv_content.encode('utf-8'),
                    filename=f'validation_{test["name"].replace(" ", "_").lower()}.csv',
                    content_type='text/csv'
                )
                
                # 예상 결과와 실제 결과 비교
                expected_success = test['should_pass']
                actual_success = result['success']
                test_success = (expected_success == actual_success)
                
                self._record_test_result(
                    test_name=f'유효성 검증: {test["name"]}',
                    success=test_success,
                    response_time=result['response_time'],
                    expected_result=expected_success,
                    actual_result=actual_success,
                    error=result.get('error') if not test_success else None
                )
                
                if test_success:
                    logger.info(f"✅ {test['name']} 검증 성공")
                else:
                    logger.warning(f"⚠️ {test['name']} 검증 실패 (예상: {expected_success}, 실제: {actual_success})")
                    
            except Exception as e:
                self._record_test_result(
                    test_name=f'유효성 검증: {test["name"]}',
                    success=False,
                    error=str(e)
                )
                logger.error(f"❌ {test['name']} 검증 테스트 실패: {e}")
    
    async def _test_performance_stress(self):
        """성능 스트레스 테스트"""
        logger.info("🔥 성능 스트레스 테스트")
        
        try:
            # 연속적으로 여러 파일 업로드
            stress_count = 10
            results = []
            
            for i in range(stress_count):
                # 중간 크기 파일 생성 (1000행)
                test_data = [
                    {
                        'symbol': f'STRESS{j % 50}',
                        'quantity': random.randint(1, 1000),
                        'price': round(random.uniform(10.0, 1000.0), 2),
                        'date': '2024-01-15'
                    }
                    for j in range(1000)
                ]
                
                csv_content = self._create_csv_content(test_data)
                
                start_time = time.time()
                result = await self._upload_file(
                    content=csv_content.encode('utf-8'),
                    filename=f'stress_test_{i}.csv',
                    content_type='text/csv'
                )
                
                result['upload_index'] = i
                result['timestamp'] = time.time()
                results.append(result)
                
                logger.info(f"스트레스 테스트 {i+1}/{stress_count}: {'성공' if result['success'] else '실패'}")
                
                # 짧은 대기 시간
                await asyncio.sleep(0.1)
            
            # 통계 계산
            successful_uploads = sum(1 for r in results if r['success'])
            total_time = results[-1]['timestamp'] - time.time() + results[-1]['response_time'] / 1000
            avg_response_time = sum(r['response_time'] for r in results if r['success']) / max(successful_uploads, 1)
            
            self.test_results['performance_stats']['stress_test'] = {
                'total_uploads': stress_count,
                'successful_uploads': successful_uploads,
                'success_rate': (successful_uploads / stress_count) * 100,
                'total_time': total_time,
                'average_response_time': avg_response_time,
                'uploads_per_second': stress_count / total_time if total_time > 0 else 0
            }
            
            self._record_test_result(
                test_name='성능 스트레스 테스트',
                success=successful_uploads >= stress_count * 0.9,  # 90% 이상 성공
                response_time=avg_response_time,
                total_uploads=stress_count,
                successful_uploads=successful_uploads,
                success_rate=round((successful_uploads / stress_count) * 100, 2)
            )
            
            logger.info(f"✅ 스트레스 테스트 완료: {successful_uploads}/{stress_count} 성공 ({(successful_uploads/stress_count)*100:.1f}%)")
            
        except Exception as e:
            self._record_test_result(
                test_name='성능 스트레스 테스트',
                success=False,
                error=str(e)
            )
            logger.error(f"❌ 스트레스 테스트 실패: {e}")
    
    async def _upload_file(self, content: bytes, filename: str, content_type: str) -> Dict[str, Any]:
        """파일 업로드 실행"""
        try:
            start_time = time.time()
            
            # Multipart form data 생성
            data = aiohttp.FormData()
            data.add_field('file', 
                          content, 
                          filename=filename,
                          content_type=content_type)
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/upload/csv"
                
                async with session.post(url, data=data, timeout=aiohttp.ClientTimeout(total=60)) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    try:
                        response_data = await response.json()
                    except:
                        response_data = await response.text()
                    
                    return {
                        'success': response.status in [200, 201],
                        'response_time': response_time,
                        'status_code': response.status,
                        'response_data': response_data,
                        'error': None if response.status in [200, 201] else f"HTTP {response.status}: {response_data}"
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'response_time': (time.time() - start_time) * 1000 if 'start_time' in locals() else 0,
                'error': str(e)
            }
    
    def _create_csv_content(self, data: List[Dict[str, Any]]) -> str:
        """CSV 콘텐츠 생성"""
        if not data:
            return ""
        
        # 헤더 생성
        headers = list(data[0].keys())
        csv_lines = [','.join(headers)]
        
        # 데이터 행 생성
        for row in data:
            csv_line = ','.join(str(row.get(header, '')) for header in headers)
            csv_lines.append(csv_line)
        
        return '\\n'.join(csv_lines)
    
    def _record_test_result(self, test_name: str, success: bool, response_time: float = 0, **kwargs):
        """테스트 결과 기록"""
        self.test_results['total_tests'] += 1
        
        if success:
            self.test_results['passed_tests'] += 1
        else:
            self.test_results['failed_tests'] += 1
            if kwargs.get('error'):
                self.test_results['errors'].append({
                    'test': test_name,
                    'error': kwargs['error'],
                    'timestamp': datetime.now().isoformat()
                })
        
        test_result = {
            'test_name': test_name,
            'success': success,
            'response_time': response_time,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        
        self.test_results['upload_tests'].append(test_result)
    
    def _generate_report(self) -> Dict[str, Any]:
        """최종 리포트 생성"""
        success_rate = (self.test_results['passed_tests'] / self.test_results['total_tests'] * 100) if self.test_results['total_tests'] > 0 else 0
        
        # 응답 시간 통계
        response_times = [t['response_time'] for t in self.test_results['upload_tests'] if t['success']]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        
        # 파일 크기 통계
        file_sizes = [t.get('file_size', 0) for t in self.test_results['upload_tests'] if t['success']]
        avg_file_size = sum(file_sizes) / len(file_sizes) if file_sizes else 0
        max_file_size = max(file_sizes) if file_sizes else 0
        
        report = {
            'summary': {
                'total_tests': self.test_results['total_tests'],
                'passed_tests': self.test_results['passed_tests'],
                'failed_tests': self.test_results['failed_tests'],
                'success_rate': round(success_rate, 2),
                'average_response_time': round(avg_response_time, 2),
                'max_response_time': round(max_response_time, 2),
                'average_file_size': round(avg_file_size / 1024, 2),  # KB
                'max_file_size': round(max_file_size / (1024*1024), 2),  # MB
                'timestamp': datetime.now().isoformat()
            },
            'performance_stats': self.test_results['performance_stats'],
            'detailed_results': self.test_results['upload_tests'],
            'errors': self.test_results['errors']
        }
        
        return report

async def main():
    """메인 실행 함수"""
    logger.info("🚀 StockPilot CSV 업로드 테스트 시작")
    
    try:
        tester = CSVUploadTester()
        report = await tester.run_csv_tests()
        
        # 리포트를 JSON 파일로 저장
        with open('csv_upload_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # 콘솔에 요약 출력
        print("\\n" + "="*80)
        print("📊 CSV 업로드 테스트 리포트")
        print("="*80)
        print(f"총 테스트: {report['summary']['total_tests']}")
        print(f"성공: {report['summary']['passed_tests']}")
        print(f"실패: {report['summary']['failed_tests']}")
        print(f"성공률: {report['summary']['success_rate']}%")
        print(f"평균 응답시간: {report['summary']['average_response_time']:.2f}ms")
        print(f"최대 응답시간: {report['summary']['max_response_time']:.2f}ms")
        print(f"평균 파일크기: {report['summary']['average_file_size']:.2f}KB")
        print(f"최대 파일크기: {report['summary']['max_file_size']:.2f}MB")
        print("="*80)
        
        # 성능 통계 출력
        if report['performance_stats']:
            print("\\n⚡ 성능 통계:")
            for test_name, stats in report['performance_stats'].items():
                print(f"  {test_name}:")
                for key, value in stats.items():
                    if isinstance(value, float):
                        print(f"    {key}: {value:.2f}")
                    else:
                        print(f"    {key}: {value}")
        
        # 에러 요약 출력
        if report['errors']:
            print(f"\\n❌ 에러 ({len(report['errors'])}개):")
            for error in report['errors'][:5]:  # 최근 5개만 표시
                print(f"  - {error['test']}: {error['error']}")
        
        print(f"\\n📄 상세 리포트: csv_upload_report.json")
        
        return report
        
    except Exception as e:
        logger.error(f"❌ CSV 업로드 테스트 실행 실패: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())