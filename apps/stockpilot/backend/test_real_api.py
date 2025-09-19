#!/usr/bin/env python3
"""
실제 데이터 API 엔드포인트 테스트
"""

import requests
import json
from datetime import datetime
import time

def test_real_api_endpoints():
    print('🔥 StockPilot 통합 API 서버 실데이터 엔드포인트 테스트')
    base_url = 'http://localhost:8000'

    # 테스트할 엔드포인트들
    test_endpoints = [
        ('/api/v1/stocks/real/AAPL', 'Apple 실제 주식 데이터'),
        ('/api/v1/stocks/trending/real?limit=3', '실제 인기 종목 (3개)'),
        ('/api/v1/stocks/chart/MSFT?period=1d', 'Microsoft 차트 데이터'),
        ('/api/v1/ai/analyze/TSLA', 'Tesla AI 분석'),
        ('/api/v1/ai/recommendations?limit=2', 'AI 추천 종목 (2개)'),
        ('/api/v1/market/summary/real', '실제 시장 현황'),
    ]

    print(f'\n📊 테스트 시작 시간: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

    success_count = 0
    total_count = len(test_endpoints)

    for endpoint, description in test_endpoints:
        try:
            print(f'\n🔍 {description} 테스트')
            print(f'   URL: {base_url}{endpoint}')
            
            response = requests.get(f'{base_url}{endpoint}', timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                print(f'   ✅ 성공 (응답 크기: {len(response.text)} bytes)')
                success_count += 1
                
                # 응답 구조 확인
                if 'success' in data and data['success']:
                    print(f'   📈 응답 성공 플래그: True')
                    if 'data' in data:
                        if isinstance(data['data'], list):
                            print(f'   📊 데이터 개수: {len(data["data"])}개')
                            if len(data['data']) > 0:
                                print(f'   📋 첫번째 항목 키: {list(data["data"][0].keys())[:5]}')
                        elif isinstance(data['data'], dict):
                            print(f'   📋 데이터 키: {list(data["data"].keys())[:5]}')
                            # 종목명과 가격 출력
                            if 'name' in data['data'] and 'price' in data['data']:
                                print(f'   💰 {data["data"]["name"]}: ${data["data"]["price"]:.2f}')
                else:
                    print(f'   ⚠️  응답 구조: {list(data.keys())[:3]}')
                    
            else:
                print(f'   ❌ HTTP {response.status_code}: {response.text[:100]}')
                
        except requests.exceptions.ConnectionError:
            print(f'   🔌 연결 실패 - 서버가 실행 중인지 확인하세요')
            break
        except Exception as e:
            print(f'   💥 오류: {str(e)[:100]}')

    print(f'\n🏁 테스트 완료: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'📈 성공률: {success_count}/{total_count} ({(success_count/total_count)*100:.1f}%)')

if __name__ == "__main__":
    # 3초 대기 후 테스트 시작
    time.sleep(3)
    test_real_api_endpoints()