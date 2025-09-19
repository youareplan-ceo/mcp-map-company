#!/usr/bin/env python3
"""
한국 금융 데이터 통합 서비스 테스트
금융감독원, 증권사 리포트, KOSPI/KOSDAQ 데이터 검증
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.kr_financial_data import create_kr_financial_service
from services.kr_news_analyzer import KRNewsAnalyzer

async def test_financial_data_service():
    """금융 데이터 서비스 테스트"""
    print("🔍 한국 금융 데이터 서비스 테스트 시작")
    print("=" * 60)
    
    try:
        # 금융 데이터 서비스 인스턴스 생성
        financial_service = await create_kr_financial_service()
        
        # 1. 금융감독원 전자공시 테스트
        print("\n1. 금융감독원 전자공시 데이터 테스트:")
        fss_data = await financial_service.fetch_fss_disclosures(5)
        print(f"   ✅ 수집된 공시: {len(fss_data)}건")
        
        if fss_data:
            sample = fss_data[0]
            print(f"   📄 샘플 공시: {sample.title}")
            print(f"   📊 영향도: {sample.impact_score:.2f}")
            print(f"   📈 감성: {sample.sentiment} ({sample.sentiment_score:.2f})")
        
        # 2. 증권사 리서치 리포트 테스트
        print("\n2. 증권사 리서치 리포트 데이터 테스트:")
        securities_data = await financial_service.fetch_securities_reports(5)
        print(f"   ✅ 수집된 리포트: {len(securities_data)}건")
        
        if securities_data:
            sample = securities_data[0]
            print(f"   📄 샘플 리포트: {sample.title}")
            print(f"   🏢 출처: {sample.source}")
            print(f"   📊 중요도: {sample.importance}")
        
        # 3. KOSPI/KOSDAQ 시장 데이터 테스트
        print("\n3. KOSPI/KOSDAQ 시장 데이터 테스트:")
        market_data = await financial_service.fetch_kospi_kosdaq_data()
        print(f"   ✅ 수집된 종목: {len(market_data)}개")
        
        kospi_count = len([stock for stock in market_data if stock.market == "KOSPI"])
        kosdaq_count = len([stock for stock in market_data if stock.market == "KOSDAQ"])
        print(f"   📈 KOSPI: {kospi_count}개, KOSDAQ: {kosdaq_count}개")
        
        if market_data:
            sample = market_data[0]
            print(f"   📊 샘플 종목: {sample.company_name} ({sample.symbol})")
            print(f"   💰 현재가: {sample.current_price:,.0f}원")
            print(f"   📊 변동률: {sample.change_percent:+.2f}%")
        
        # 4. 종합 데이터 테스트
        print("\n4. 종합 한국 금융 데이터 테스트:")
        comprehensive_data = await financial_service.get_comprehensive_kr_data()
        
        if comprehensive_data and not comprehensive_data.get('error'):
            print(f"   ✅ 뉴스: {len(comprehensive_data.get('news', []))}건")
            print(f"   ✅ 시장 데이터: {len(comprehensive_data.get('market_data', []))}종목")
            print(f"   📊 통계: {comprehensive_data.get('statistics', {})}")
        else:
            print(f"   ❌ 오류: {comprehensive_data.get('error', 'Unknown error')}")
        
        # 5. 시장 상태 확인
        print("\n5. 한국 시장 상태 확인:")
        is_open, market_state = financial_service.is_market_open()
        print(f"   📅 장 상태: {market_state}")
        print(f"   🔄 거래 중: {'예' if is_open else '아니오'}")
        
        # 6. 시장 캘린더 정보
        print("\n6. 시장 캘린더 정보:")
        calendar_info = financial_service.get_market_calendar_info()
        print(f"   📅 오늘: {calendar_info['today']}")
        print(f"   📈 거래일: {'예' if calendar_info['is_trading_day'] else '아니오'}")
        print(f"   📅 다음 거래일: {calendar_info['next_trading_day']}")
        print(f"   🏖️ 휴장일 수: {len(calendar_info['holidays_2024'])}일")
        
        # 서비스 정리
        await financial_service.__aexit__(None, None, None)
        
        print("\n✅ 한국 금융 데이터 서비스 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"\n❌ 금융 데이터 서비스 테스트 실패: {e}")
        return False

async def test_integrated_news_analyzer():
    """통합된 뉴스 분석기 테스트"""
    print("\n\n🔍 통합 뉴스 분석기 테스트 시작")
    print("=" * 60)
    
    try:
        # 뉴스 분석기 인스턴스 생성
        api_key = os.getenv('OPENAI_API_KEY', 'mock-key-for-testing')
        
        async with KRNewsAnalyzer(api_key) as analyzer:
            # 1. 종합 한국 데이터 수집 테스트
            print("\n1. 종합 한국 데이터 수집 테스트:")
            comprehensive_data = await analyzer.get_comprehensive_kr_data()
            
            if comprehensive_data.get('success'):
                stats = comprehensive_data.get('statistics', {})
                print(f"   ✅ 총 뉴스: {stats.get('total_news', 0)}건")
                print(f"   📰 전통 뉴스: {stats.get('traditional_news', 0)}건")
                print(f"   📄 금융 뉴스: {stats.get('financial_news', 0)}건")
                print(f"   📈 시장 데이터: {stats.get('market_stocks', 0)}종목")
                
                # 뉴스 샘플 출력
                news_list = comprehensive_data.get('news', [])
                if news_list:
                    print(f"\n   📰 최신 뉴스 샘플:")
                    for i, news in enumerate(news_list[:3]):
                        print(f"   {i+1}. {news.get('title', 'No title')[:50]}...")
                        print(f"      📊 감성: {news.get('sentiment', 'Unknown')} ({news.get('sentiment_score', 0):.2f})")
                        print(f"      🏢 출처: {news.get('source', 'Unknown')}")
                        print()
            else:
                print(f"   ❌ 데이터 수집 실패: {comprehensive_data.get('error', 'Unknown error')}")
            
            # 2. 한국 시장 데이터 품질 검증 테스트
            print("\n2. 시장 데이터 품질 검증 테스트:")
            validation_result = await analyzer.validate_kr_market_data()
            
            if validation_result.get('validation_status') != 'ERROR':
                quality_score = validation_result.get('quality_score', 0)
                status = validation_result.get('validation_status', 'Unknown')
                
                print(f"   📊 품질 점수: {quality_score:.2f}/100")
                print(f"   ✅ 검증 상태: {status}")
                print(f"   📈 총 종목: {validation_result.get('total_stocks', 0)}개")
                
                data_quality = validation_result.get('data_quality', {})
                print(f"   💰 유효한 가격: {data_quality.get('valid_prices', 0)}개")
                print(f"   📊 유효한 거래량: {data_quality.get('valid_volumes', 0)}개")
                print(f"   📈 완전한 데이터: {data_quality.get('complete_data', 0)}개")
                
                # 가격 범위 정보
                price_ranges = validation_result.get('price_ranges', {})
                print(f"   💰 KOSPI 평균가: {price_ranges.get('kospi_avg_price', 0):,.0f}원")
                print(f"   💰 KOSDAQ 평균가: {price_ranges.get('kosdaq_avg_price', 0):,.0f}원")
                
                # 검증 오류 출력
                errors = validation_result.get('validation_errors', [])
                if errors:
                    print(f"   ⚠️ 검증 오류: {len(errors)}개")
                    for error in errors[:3]:  # 최대 3개까지 출력
                        print(f"      - {error}")
            else:
                print(f"   ❌ 검증 실패: {validation_result.get('error', 'Unknown error')}")
            
            # 3. 시장 캘린더 테스트
            print("\n3. 시장 캘린더 테스트:")
            calendar_data = await analyzer.get_kr_market_calendar()
            
            if not calendar_data.get('error'):
                print(f"   📅 오늘: {calendar_data.get('today', 'Unknown')}")
                print(f"   📈 거래일: {'예' if calendar_data.get('is_trading_day', False) else '아니오'}")
                print(f"   🔄 시장 상태: {calendar_data.get('market_state', 'Unknown')}")
                print(f"   📅 다음 거래일: {calendar_data.get('next_trading_day', 'Unknown')}")
                
                market_hours = calendar_data.get('market_hours', {})
                regular_hours = market_hours.get('regular', {})
                print(f"   🕘 정규 시간: {regular_hours.get('open', '?')} - {regular_hours.get('close', '?')}")
            else:
                print(f"   ❌ 캘린더 조회 실패: {calendar_data.get('error', 'Unknown error')}")
        
        print("\n✅ 통합 뉴스 분석기 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"\n❌ 통합 뉴스 분석기 테스트 실패: {e}")
        return False

async def test_data_sources_integration():
    """데이터 소스 통합 테스트"""
    print("\n\n🔍 데이터 소스 통합 테스트 시작")
    print("=" * 60)
    
    try:
        api_key = os.getenv('OPENAI_API_KEY', 'mock-key-for-testing')
        
        async with KRNewsAnalyzer(api_key) as analyzer:
            # 종합 데이터 수집
            comprehensive_data = await analyzer.get_comprehensive_kr_data()
            
            if not comprehensive_data.get('success'):
                print("❌ 종합 데이터 수집 실패")
                return False
            
            # 데이터 소스 분석
            data_sources = comprehensive_data.get('data_sources', {})
            traditional_sources = data_sources.get('traditional', [])
            financial_sources = data_sources.get('financial', {})
            
            print(f"📰 전통 뉴스 소스: {len(traditional_sources)}개")
            for source in traditional_sources:
                print(f"   - {source}")
            
            print(f"\n🏦 금융 데이터 소스:")
            if isinstance(financial_sources, dict):
                fss_sources = financial_sources.get('fss', [])
                securities_sources = financial_sources.get('securities', [])
                
                print(f"   📄 금융감독원: {len(fss_sources)}개 소스")
                for source in fss_sources:
                    print(f"      - {source}")
                
                print(f"   🏢 증권사: {len(securities_sources)}개 소스")
                for source in securities_sources:
                    print(f"      - {source}")
            
            # 뉴스 품질 분석
            news_list = comprehensive_data.get('news', [])
            if news_list:
                print(f"\n📊 뉴스 품질 분석:")
                
                # 감성 분포
                sentiment_counts = {'POSITIVE': 0, 'NEGATIVE': 0, 'NEUTRAL': 0}
                source_types = {'traditional': 0, 'fss': 0, 'securities': 0}
                
                for news in news_list:
                    sentiment = news.get('sentiment', 'NEUTRAL')
                    if sentiment in sentiment_counts:
                        sentiment_counts[sentiment] += 1
                    
                    source_type = news.get('source_type', 'traditional')
                    if source_type in source_types:
                        source_types[source_type] += 1
                
                print(f"   😊 긍정적: {sentiment_counts['POSITIVE']}개")
                print(f"   😐 중립적: {sentiment_counts['NEUTRAL']}개") 
                print(f"   😞 부정적: {sentiment_counts['NEGATIVE']}개")
                
                print(f"\n📰 소스 타입별:")
                print(f"   📰 전통 뉴스: {source_types['traditional']}개")
                print(f"   📄 금융감독원: {source_types['fss']}개")
                print(f"   🏢 증권사: {source_types['securities']}개")
            
            # 시장 데이터 분석
            market_data = comprehensive_data.get('market_data', [])
            if market_data:
                print(f"\n📈 시장 데이터 분석:")
                
                kospi_stocks = [stock for stock in market_data if stock.get('market') == 'KOSPI']
                kosdaq_stocks = [stock for stock in market_data if stock.get('market') == 'KOSDAQ']
                
                print(f"   📈 KOSPI: {len(kospi_stocks)}종목")
                print(f"   📈 KOSDAQ: {len(kosdaq_stocks)}종목")
                
                # 상위 변동률 종목
                if market_data:
                    sorted_stocks = sorted(market_data, key=lambda x: abs(x.get('change_percent', 0)), reverse=True)
                    print(f"\n   🔥 상위 변동률 종목:")
                    for i, stock in enumerate(sorted_stocks[:3]):
                        change_percent = stock.get('change_percent', 0)
                        company_name = stock.get('company_name', 'Unknown')
                        symbol = stock.get('symbol', 'Unknown')
                        print(f"   {i+1}. {company_name} ({symbol}): {change_percent:+.2f}%")
            
        print("\n✅ 데이터 소스 통합 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"\n❌ 데이터 소스 통합 테스트 실패: {e}")
        return False

async def main():
    """메인 테스트 함수"""
    print("🚀 StockPilot 한국 금융 데이터 통합 테스트")
    print("=" * 80)
    print(f"⏰ 테스트 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 환경 변수 확인
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("⚠️ OPENAI_API_KEY 환경변수가 설정되지 않았습니다. Mock 데이터로 테스트합니다.")
    
    test_results = []
    
    # 테스트 실행
    test_results.append(await test_financial_data_service())
    test_results.append(await test_integrated_news_analyzer())
    test_results.append(await test_data_sources_integration())
    
    # 결과 요약
    print("\n\n📊 테스트 결과 요약")
    print("=" * 60)
    
    passed_tests = sum(test_results)
    total_tests = len(test_results)
    
    test_names = [
        "금융 데이터 서비스",
        "통합 뉴스 분석기", 
        "데이터 소스 통합"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, test_results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i+1}. {name}: {status}")
    
    print(f"\n📈 전체 성공률: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")
    
    if passed_tests == total_tests:
        print("🎉 모든 테스트가 성공적으로 완료되었습니다!")
        print("✅ KR 채널 안정화 및 확장 작업 완료")
    else:
        print("⚠️ 일부 테스트가 실패했습니다. 로그를 확인해주세요.")
    
    print(f"\n⏰ 테스트 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(main())