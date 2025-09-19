#!/usr/bin/env python3
"""
End-to-End 플로우 테스트
AAPL → 데이터 수집 → AI 분석 → 투자 시그널 생성
"""

import asyncio
import os
import json
from datetime import datetime

# 로컬 서비스들 import
from services.us_stock_data import USStockDataService
from services.currency_exchange import CurrencyExchangeService
from services.us_news_analyzer import USNewsAnalyzer
from services.us_ai_signal_generator import USAISignalGenerator

async def test_complete_pipeline():
    """완전한 파이프라인 테스트"""
    print("=" * 60)
    print("🚀 StockPilot AI - End-to-End 플로우 테스트")
    print("=" * 60)
    
    # OpenAI API 키 확인
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY 환경변수가 필요합니다.")
        return
    
    test_symbol = "AAPL"
    start_time = datetime.now()
    
    print(f"\n🎯 타겟 종목: {test_symbol}")
    print(f"⏰ 시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1단계: 주식 데이터 수집
        print(f"\n📊 1단계: {test_symbol} 주식 데이터 수집 중...")
        stock_service = USStockDataService()
        stock_data = await stock_service.get_stock_info(test_symbol)
        
        if not stock_data:
            print(f"❌ {test_symbol} 주식 데이터 수집 실패")
            return
            
        print(f"✅ 주식 데이터 수집 완료:")
        print(f"   회사명: {stock_data.company_name}")
        print(f"   현재가: ${stock_data.current_price}")
        print(f"   변동률: {stock_data.change_percent:+.2f}%")
        print(f"   거래량: {stock_data.volume:,}")
        print(f"   시장상태: {stock_data.market_state}")
        
        # 2단계: 환율 정보
        print(f"\n💱 2단계: USD/KRW 환율 정보 조회 중...")
        currency_service = CurrencyExchangeService()
        exchange_rate = await currency_service.get_exchange_rate("USD", "KRW")
        
        if exchange_rate:
            print(f"✅ 환율 정보:")
            print(f"   USD/KRW: {exchange_rate.rate:,.2f}원 ({exchange_rate.change_percent:+.2f}%)")
            
            # 원화 환산
            krw_price = stock_data.current_price * exchange_rate.rate
            print(f"   {test_symbol} 원화 가격: ₩{krw_price:,.0f}")
        
        # 3단계: 뉴스 분석 (간단 버전)
        print(f"\n📰 3단계: {test_symbol} 관련 뉴스 분석 중...")
        async with USNewsAnalyzer(api_key) as news_analyzer:
            # 일반 뉴스 먼저 수집
            general_news = await news_analyzer.get_latest_us_news(5)
            print(f"✅ 전체 뉴스 {len(general_news)}건 수집")
            
            # 특정 종목 뉴스
            symbol_news = await news_analyzer.get_symbol_news(test_symbol, 3)
            print(f"✅ {test_symbol} 관련 뉴스 {len(symbol_news)}건 발견")
            
            if symbol_news:
                for i, news in enumerate(symbol_news, 1):
                    print(f"   [{i}] {news.title[:50]}...")
                    print(f"       감성: {news.sentiment} ({news.sentiment_score:+.2f})")
                    print(f"       영향도: {news.impact_score:.2f}")
        
        # 4단계: AI 투자 시그널 생성
        print(f"\n🤖 4단계: AI 투자 시그널 생성 중...")
        async with USAISignalGenerator(api_key) as signal_generator:
            investment_signal = await signal_generator.generate_signal(test_symbol)
            
            if not investment_signal:
                print(f"❌ {test_symbol} 투자 시그널 생성 실패")
                return
                
            print(f"✅ 투자 시그널 생성 완료:")
            print(f"   시그널: {investment_signal.signal_type}")
            print(f"   신뢰도: {investment_signal.confidence:.2f}")
            print(f"   강도: {investment_signal.strength}")
            print(f"   현재가: ${investment_signal.current_price}")
            print(f"   목표가: ${investment_signal.target_price}")
            print(f"   예상수익률: {investment_signal.expected_return:+.1f}%")
            print(f"   위험도: {investment_signal.risk_level}")
            
            print(f"\n📋 AI 분석 근거:")
            print(f"   {investment_signal.reasoning}")
            
            print(f"\n📈 기술적 분석:")
            print(f"   기술적 점수: {investment_signal.technical_score:+.2f}")
            print(f"   펀더멘털 점수: {investment_signal.fundamental_score:+.2f}")
            print(f"   뉴스 감성 점수: {investment_signal.sentiment_score:+.2f}")
            
        # 5단계: TOP 시그널들
        print(f"\n🏆 5단계: TOP 투자 시그널들 생성 중...")
        async with USAISignalGenerator(api_key) as signal_generator:
            top_signals = await signal_generator.get_top_signals(3)
            
            print(f"✅ TOP {len(top_signals)}개 시그널:")
            for i, signal in enumerate(top_signals, 1):
                print(f"   [{i}] {signal.symbol}: {signal.signal_type} "
                      f"(신뢰도: {signal.confidence:.2f}, {signal.strength})")
                print(f"       현재가: ${signal.current_price} → 목표가: ${signal.target_price} "
                      f"(예상수익: {signal.expected_return:+.1f}%)")
        
        # 완료 시간
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n✅ End-to-End 테스트 완료!")
        print(f"⏱️  총 소요시간: {duration:.1f}초")
        print(f"🎯 타겟 달성: 실시간 데이터 → AI 분석 → 투자 시그널")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_individual_services():
    """개별 서비스 단위 테스트"""
    print("\n" + "=" * 60)
    print("🧪 개별 서비스 단위 테스트")
    print("=" * 60)
    
    # 1. 주식 데이터 서비스
    print("\n📊 주식 데이터 서비스 테스트...")
    try:
        stock_service = USStockDataService()
        
        # 개별 종목
        aapl = await stock_service.get_stock_info("AAPL")
        print(f"✅ AAPL: ${aapl.current_price} ({aapl.change_percent:+.2f}%)")
        
        # 다중 종목
        stocks = await stock_service.get_multiple_stocks(["MSFT", "GOOGL"])
        print(f"✅ 다중 종목: {len(stocks)}개 조회 성공")
        
        # 인기 종목
        trending = stock_service.get_trending_stocks(3)
        print(f"✅ 인기 종목: {len(trending)}개 조회")
        
    except Exception as e:
        print(f"❌ 주식 데이터 서비스 오류: {e}")
    
    # 2. 환율 서비스
    print("\n💱 환율 서비스 테스트...")
    try:
        currency_service = CurrencyExchangeService()
        
        usd_krw = await currency_service.get_exchange_rate("USD", "KRW")
        print(f"✅ USD/KRW: {usd_krw.rate:,.2f}원")
        
        conversion = await currency_service.convert_amount_async(100, "USD", "KRW")
        print(f"✅ $100 = ₩{conversion['converted_amount']:,.0f}")
        
    except Exception as e:
        print(f"❌ 환율 서비스 오류: {e}")
    
    # 3. 뉴스 분석 서비스 (간단 테스트)
    print("\n📰 뉴스 분석 서비스 테스트...")
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        async with USNewsAnalyzer(api_key) as news_analyzer:
            # RSS 뉴스만 수집 (AI 분석 제외)
            news_data = await news_analyzer.fetch_rss_news("yahoo_finance", 2)
            print(f"✅ Yahoo Finance RSS: {len(news_data)}건 뉴스 수집")
            
    except Exception as e:
        print(f"❌ 뉴스 분석 서비스 오류: {e}")
    
    print("\n✅ 개별 서비스 테스트 완료")

async def main():
    """메인 테스트 함수"""
    print("🚀 StockPilot AI - 미국 시장 실시간 데이터 파이프라인 테스트")
    
    # 환경 확인
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("   .env 파일에 OpenAI API 키를 설정해주세요.")
        return
    
    # 1. 개별 서비스 테스트
    await test_individual_services()
    
    # 2. 전체 파이프라인 테스트
    success = await test_complete_pipeline()
    
    if success:
        print("\n🎉 모든 테스트 성공! 미국 시장 AI 투자 코파일럿이 정상 작동합니다.")
    else:
        print("\n⚠️  일부 테스트가 실패했습니다.")

if __name__ == "__main__":
    asyncio.run(main())