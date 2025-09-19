"""
한국어 분석 기능 테스트
한국 주식시장 특화 기능 검증
"""

import pytest
import os
from datetime import datetime, date
from unittest.mock import patch, MagicMock

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from ai_engine.config.korean_market_config import (
    KoreanMarketConfig, KoreanStockInfo, KoreanMarket, SectorKR,
    korean_market_config, validate_stock_symbol, get_yfinance_symbol,
    analyze_korean_sentiment, extract_stock_symbols, is_market_open
)

from ai_engine.config.prompt_templates_kr import (
    KoreanPromptTemplates, PromptType, korean_prompts,
    analyze_stock_kr, analyze_sentiment_kr, technical_analysis_kr
)

from ai_engine.utils.korean_text_processor import (
    KoreanTextProcessor, ProcessedText, korean_text_processor,
    clean_korean_text, extract_financial_entities, preprocess_korean_for_ai
)

from ai_engine.utils.ticker_converter import (
    TickerConverter, StockTicker, TickerFormat, ticker_converter,
    convert_ticker, to_yfinance, to_krx_code, validate_korean_ticker, get_stock_info
)

class TestKoreanMarketConfig:
    """한국 시장 설정 테스트"""
    
    def test_korean_stock_info_creation(self):
        """한국 주식 정보 생성 테스트"""
        stock = KoreanStockInfo(
            symbol="005930",
            name_kr="삼성전자",
            name_en="Samsung Electronics",
            market=KoreanMarket.KOSPI,
            sector=SectorKR.IT
        )
        
        assert stock.symbol == "005930"
        assert stock.name_kr == "삼성전자"
        assert stock.yf_symbol == "005930.KS"
        assert stock.market == KoreanMarket.KOSPI
    
    def test_stock_symbol_validation(self):
        """종목코드 유효성 검증 테스트"""
        config = KoreanMarketConfig()
        
        # 유효한 종목코드
        assert config.validate_korean_stock_symbol("005930")
        assert config.validate_korean_stock_symbol("000660")
        assert config.validate_korean_stock_symbol("123456")
        
        # 유효하지 않은 종목코드
        assert not config.validate_korean_stock_symbol("12345")   # 5자리
        assert not config.validate_korean_stock_symbol("1234567") # 7자리
        assert not config.validate_korean_stock_symbol("ABC123")  # 문자 포함
        assert not config.validate_korean_stock_symbol("")        # 빈 문자열
        assert not config.validate_korean_stock_symbol(None)      # None
    
    def test_yfinance_symbol_conversion(self):
        """yfinance 심볼 변환 테스트"""
        config = KoreanMarketConfig()
        
        # 코스피
        assert config.convert_to_yfinance_symbol("005930", KoreanMarket.KOSPI) == "005930.KS"
        
        # 코스닥
        assert config.convert_to_yfinance_symbol("036570", KoreanMarket.KOSDAQ) == "036570.KQ"
        
        # 잘못된 종목코드
        with pytest.raises(ValueError):
            config.convert_to_yfinance_symbol("12345")
    
    def test_market_guessing(self):
        """시장 추정 테스트"""
        config = KoreanMarketConfig()
        
        # 알려진 종목
        assert config.guess_market_from_symbol("005930") == KoreanMarket.KOSPI
        assert config.guess_market_from_symbol("036570") == KoreanMarket.KOSDAQ
        
        # 패턴 기반 추정
        assert config.guess_market_from_symbol("900000") == KoreanMarket.KOSDAQ  # 9로 시작
        assert config.guess_market_from_symbol("100000") == KoreanMarket.KOSPI   # 1로 시작
    
    def test_trading_time_check(self):
        """거래시간 확인 테스트"""
        config = KoreanMarketConfig()
        
        # 특정 시간으로 테스트 (가상의 거래시간)
        trading_time = datetime(2024, 1, 15, 10, 30)  # 월요일 10:30
        weekend = datetime(2024, 1, 13, 10, 30)       # 토요일 10:30
        
        assert config.is_trading_time(trading_time)
        assert not config.is_trading_time(weekend)
    
    def test_market_status(self):
        """시장 상태 확인 테스트"""
        config = KoreanMarketConfig()
        
        # 여러 시간대 테스트
        pre_market = datetime(2024, 1, 15, 8, 45)  # 08:45
        regular_hours = datetime(2024, 1, 15, 10, 30)  # 10:30
        after_market = datetime(2024, 1, 15, 16, 30)  # 16:30
        weekend = datetime(2024, 1, 13, 10, 30)  # 토요일
        
        assert config.get_market_status(pre_market) == "동시호가(개장)"
        assert config.get_market_status(regular_hours) == "정규거래"
        assert config.get_market_status(after_market) == "장후"
        assert config.get_market_status(weekend) == "휴장"
    
    def test_korean_sentiment_analysis(self):
        """한국어 감정 분석 테스트"""
        config = KoreanMarketConfig()
        
        # 긍정적 텍스트
        positive_text = "삼성전자 실적 호조로 급등했습니다. 매출이 크게 증가했네요."
        result = config.analyze_korean_text_sentiment(positive_text)
        
        assert result["sentiment"] == "positive"
        assert result["score"] > 0
        assert result["positive_count"] > 0
        assert len(result["keywords"]) > 0
        
        # 부정적 텍스트
        negative_text = "삼성전자가 실적 악화로 급락했습니다. 손실이 크네요."
        result = config.analyze_korean_text_sentiment(negative_text)
        
        assert result["sentiment"] == "negative"
        assert result["score"] < 0
        assert result["negative_count"] > 0
    
    def test_stock_mention_extraction(self):
        """종목 언급 추출 테스트"""
        config = KoreanMarketConfig()
        
        text = "삼성전자(005930)와 SK하이닉스(000660) 분석을 해보겠습니다."
        mentions = config.extract_stock_mentions(text)
        
        assert len(mentions) >= 2
        codes = [code for code, name in mentions]
        assert "005930" in codes
        assert "000660" in codes
    
    def test_korean_number_formatting(self):
        """한국식 숫자 표기법 테스트"""
        config = KoreanMarketConfig()
        
        assert config.format_korean_number(1000000000000) == "1조"
        assert config.format_korean_number(1500000000000) == "1조 5000억"
        assert config.format_korean_number(100000000) == "1억"
        assert config.format_korean_number(150000000) == "1억 5000만"
        assert config.format_korean_number(10000) == "1만"
        assert config.format_korean_number(12345) == "1만 2,345"

class TestKoreanPromptTemplates:
    """한국어 프롬프트 템플릿 테스트"""
    
    def test_template_initialization(self):
        """템플릿 초기화 테스트"""
        templates = KoreanPromptTemplates()
        
        assert PromptType.STOCK_ANALYSIS in templates.templates
        assert PromptType.SENTIMENT_ANALYSIS in templates.templates
        assert PromptType.TECHNICAL_ANALYSIS in templates.templates
        
        available_types = templates.get_available_types()
        assert len(available_types) > 0
        assert "stock_analysis" in available_types
    
    def test_stock_analysis_prompt(self):
        """종목 분석 프롬프트 테스트"""
        templates = KoreanPromptTemplates()
        
        prompt = templates.format_prompt(
            PromptType.STOCK_ANALYSIS,
            stock_name="삼성전자",
            stock_code="005930",
            market="코스피",
            sector="반도체",
            financial_data="매출 279조원...",
            recent_news="AI 반도체 수주 확대...",
            price_data="현재가 72,000원...",
            analysis_request="종합 투자 분석"
        )
        
        assert "system" in prompt
        assert "user" in prompt
        assert "삼성전자" in prompt["user"]
        assert "005930" in prompt["user"]
        assert "애널리스트" in prompt["system"]
    
    def test_sentiment_analysis_prompt(self):
        """감정 분석 프롬프트 테스트"""
        templates = KoreanPromptTemplates()
        
        prompt = templates.format_prompt(
            PromptType.SENTIMENT_ANALYSIS,
            news_articles="삼성전자, HBM3 양산 본격화로 실적 개선 기대",
            target_stocks="005930 삼성전자"
        )
        
        assert "system" in prompt
        assert "user" in prompt
        assert "HBM3" in prompt["user"]
        assert "감정" in prompt["system"]
    
    def test_required_fields_validation(self):
        """필수 필드 검증 테스트"""
        templates = KoreanPromptTemplates()
        
        # 필수 필드 누락
        missing_fields = templates.validate_required_fields(
            PromptType.STOCK_ANALYSIS,
            stock_name="삼성전자"
            # stock_code, market 등 누락
        )
        
        assert len(missing_fields) > 0
        assert "stock_code" in missing_fields
    
    def test_convenience_functions(self):
        """편의 함수 테스트"""
        # 종목 분석
        stock_prompt = analyze_stock_kr(
            stock_name="삼성전자",
            stock_code="005930",
            market="코스피",
            sector="반도체",
            financial_data="테스트 데이터",
            recent_news="테스트 뉴스",
            price_data="테스트 주가"
        )
        
        assert "system" in stock_prompt
        assert "user" in stock_prompt
        assert "삼성전자" in stock_prompt["user"]
        
        # 감정 분석
        sentiment_prompt = analyze_sentiment_kr(
            news_articles="긍정적인 뉴스입니다.",
            target_stocks="005930"
        )
        
        assert "system" in sentiment_prompt
        assert "긍정적인" in sentiment_prompt["user"]

class TestKoreanTextProcessor:
    """한국어 텍스트 처리기 테스트"""
    
    def test_text_normalization(self):
        """텍스트 정규화 테스트"""
        processor = KoreanTextProcessor()
        
        text = "  삼성전자가   좋습니다.\n\n  주가   상승  예상됩니다.  "
        normalized = processor.normalize_text(text)
        
        assert normalized == "삼성전자가 좋습니다.\n주가 상승 예상됩니다."
        assert not normalized.startswith(" ")
        assert not normalized.endswith(" ")
    
    def test_financial_text_cleaning(self):
        """금융 텍스트 정리 테스트"""
        processor = KoreanTextProcessor()
        
        text = "삼성전자(005930) 실적 호조!!! 📈 매출 60조원 달성 🎉"
        result = processor.clean_financial_text(text)
        
        assert isinstance(result, ProcessedText)
        assert result.original == text
        assert "📈" not in result.processed  # 이모지 제거
        assert "🎉" not in result.processed
        assert "삼성전자" in result.processed  # 핵심 내용 보존
        assert result.confidence_score > 0.5
    
    def test_entity_extraction(self):
        """엔티티 추출 테스트"""
        processor = KoreanTextProcessor()
        
        text = """
        삼성전자(005930)와 SK하이닉스(000660)의 실적을 비교해보겠습니다.
        매출액은 각각 60조원, 40조원이며, PER은 15배, 12배입니다.
        김철수 기자가 2024년 4월 30일에 보고했습니다.
        """
        
        entities = processor.extract_entities(text)
        
        assert "005930" in entities["stock_codes"]
        assert "000660" in entities["stock_codes"]
        assert len([a for a in entities["amounts"] if "조" in a]) >= 2
        assert any("PER" in metric for metric in entities["financial_metrics"])
        assert len(entities["reporters"]) >= 1
    
    def test_sentiment_keyword_extraction(self):
        """감정 키워드 추출 테스트"""
        processor = KoreanTextProcessor()
        
        text = "삼성전자 실적 호조로 급등했습니다. 매출 증가가 주요 요인입니다."
        keywords = processor.extract_sentiment_keywords(text)
        
        assert len(keywords["positive"]) > 0
        assert "호조" in keywords["positive"] or "급등" in keywords["positive"]
        assert "증가" in keywords["positive"]
    
    def test_text_complexity_analysis(self):
        """텍스트 복잡도 분석 테스트"""
        processor = KoreanTextProcessor()
        
        # 간단한 텍스트
        simple_text = "삼성전자 주가가 올랐다."
        simple_result = processor.analyze_text_complexity(simple_text)
        assert simple_result["complexity"] in ["low", "medium"]
        
        # 복잡한 텍스트
        complex_text = """
        삼성전자의 2024년 1분기 연결재무제표 기준 매출액은 전년동기대비 13.8% 증가한 
        60.01조원, 영업이익은 98.9% 증가한 6.61조원을 기록했다고 발표했습니다.
        메모리반도체 사업부문에서 DRAM과 NAND Flash 모두 수요 회복세를 보이며
        ASP(평균판매가격) 상승이 이어졌고, 시스템LSI와 파운드리 부문도 
        모바일 AP와 HPC(고성능컴퓨팅) 수요 증가로 실적 개선을 이뤘다고 설명했습니다.
        """
        complex_result = processor.analyze_text_complexity(complex_text)
        assert complex_result["complexity"] in ["medium", "high"]
        assert complex_result["score"] > simple_result["score"]
    
    def test_key_phrase_extraction(self):
        """핵심 구문 추출 테스트"""
        processor = KoreanTextProcessor()
        
        text = "삼성전자 실적 발표 결과 매출액 증가로 주가 상승 전망"
        phrases = processor.extract_key_phrases(text, top_k=5)
        
        assert len(phrases) <= 5
        assert all(isinstance(phrase, tuple) and len(phrase) == 2 for phrase in phrases)
        assert all(isinstance(score, (int, float)) for phrase, score in phrases)
    
    def test_preprocessing_for_embedding(self):
        """임베딩용 전처리 테스트"""
        processor = KoreanTextProcessor()
        
        text = "삼성전자!!! 실적 최고!!! 📈📈📈 주가 대박!!!"
        preprocessed = processor.preprocess_for_embedding(text)
        
        assert "📈" not in preprocessed
        assert "!!!" not in preprocessed
        assert "삼성전자" in preprocessed
        assert "실적" in preprocessed
        assert len(preprocessed) < len(text)

class TestTickerConverter:
    """티커 변환기 테스트"""
    
    def test_ticker_format_detection(self):
        """티커 형식 감지 테스트"""
        converter = TickerConverter()
        
        assert converter.detect_format("005930") == TickerFormat.KRX_CODE
        assert converter.detect_format("005930.KS") == TickerFormat.YFINANCE
        assert converter.detect_format("005930 KS Equity") == TickerFormat.BLOOMBERG
    
    def test_krx_code_extraction(self):
        """KRX 코드 추출 테스트"""
        converter = TickerConverter()
        
        assert converter.extract_krx_code("005930") == "005930"
        assert converter.extract_krx_code("005930.KS") == "005930"
        assert converter.extract_krx_code("005930.KQ") == "005930"
        assert converter.extract_krx_code("삼성전자(005930)") == "005930"
        assert converter.extract_krx_code("invalid") is None
    
    def test_format_conversion(self):
        """형식 변환 테스트"""
        converter = TickerConverter()
        
        # KRX 코드를 yfinance로
        yf_symbol = converter.convert_to_format("005930", TickerFormat.YFINANCE)
        assert yf_symbol in ["005930.KS", "005930.KQ"]  # 시장에 따라
        
        # yfinance를 KRX 코드로
        krx_code = converter.convert_to_format("005930.KS", TickerFormat.KRX_CODE)
        assert krx_code == "005930"
    
    def test_stock_info_retrieval(self):
        """종목 정보 조회 테스트"""
        converter = TickerConverter()
        
        # 코드로 조회
        stock_info = converter.get_stock_info("005930")
        if stock_info:  # 데이터베이스에 있는 경우만
            assert stock_info.krx_code == "005930"
            assert stock_info.name_kr == "삼성전자"
        
        # 이름으로 조회
        stock_info = converter.get_stock_info("삼성전자")
        if stock_info:
            assert stock_info.krx_code == "005930"
    
    def test_stock_search(self):
        """종목 검색 테스트"""
        converter = TickerConverter()
        
        results = converter.search_by_name("삼성", limit=5)
        assert len(results) <= 5
        
        if results:
            # 모든 결과에 "삼성"이 포함되어야 함
            for stock in results:
                assert "삼성" in stock.name_kr.lower()
    
    def test_batch_conversion(self):
        """일괄 변환 테스트"""
        converter = TickerConverter()
        
        tickers = ["005930", "000660", "invalid"]
        results = converter.batch_convert(tickers, TickerFormat.YFINANCE)
        
        assert len(results) == 3
        assert "005930" in results
        assert results["invalid"] is None  # 잘못된 티커
    
    def test_validation(self):
        """유효성 검증 테스트"""
        converter = TickerConverter()
        
        # 개별 검증
        assert converter.validate_krx_code("005930")
        assert not converter.validate_krx_code("12345")
        assert not converter.validate_krx_code("ABC123")
        
        # 일괄 검증
        tickers = ["005930", "000660", "invalid", "12345"]
        results = converter.validate_ticker_list(tickers)
        
        assert results["005930"]
        assert results["000660"] 
        assert not results["invalid"]
        assert not results["12345"]
    
    def test_convenience_functions(self):
        """편의 함수 테스트"""
        # KRX 코드 추출
        assert to_krx_code("005930.KS") == "005930"
        assert to_krx_code("invalid") is None
        
        # yfinance 변환
        yf_symbol = to_yfinance("005930")
        assert yf_symbol is not None
        assert yf_symbol.endswith((".KS", ".KQ"))
        
        # 검증
        assert validate_korean_ticker("005930")
        assert not validate_korean_ticker("invalid")

class TestIntegrationScenarios:
    """통합 시나리오 테스트"""
    
    def test_korean_stock_analysis_workflow(self):
        """한국 주식 분석 워크플로우 테스트"""
        # 1. 티커 변환
        yf_symbol = to_yfinance("005930")
        assert yf_symbol is not None
        
        # 2. 종목 정보 조회
        stock_info = get_stock_info("005930")
        if stock_info:
            assert stock_info["name_kr"] == "삼성전자"
        
        # 3. 뉴스 텍스트 처리
        news_text = "삼성전자(005930) 실적 호조로 급등 📈 매출 60조원 달성!"
        cleaned = clean_korean_text(news_text)
        assert cleaned.confidence_score > 0.5
        
        # 4. 감정 분석
        sentiment = analyze_korean_sentiment(news_text)
        assert sentiment["sentiment"] in ["positive", "negative", "neutral"]
        
        # 5. 프롬프트 생성
        prompt = analyze_stock_kr(
            stock_name="삼성전자",
            stock_code="005930",
            market="코스피",
            sector="반도체",
            financial_data="테스트 데이터",
            recent_news=cleaned.processed,
            price_data="현재가 72,000원"
        )
        assert "삼성전자" in prompt["user"]
    
    def test_multi_stock_analysis(self):
        """다종목 분석 테스트"""
        stocks = ["005930", "000660", "036570"]  # 삼성전자, SK하이닉스, 엔씨소프트
        
        for stock_code in stocks:
            # 유효성 검증
            assert validate_korean_ticker(stock_code)
            
            # yfinance 변환
            yf_symbol = to_yfinance(stock_code)
            assert yf_symbol is not None
            
            # 시장 정보
            info = get_stock_info(stock_code)
            if info:
                assert info["krx_code"] == stock_code
                assert info["market"] in ["KOSPI", "KOSDAQ"]

# pytest 설정
@pytest.fixture
def mock_datetime_now():
    """현재 시간 Mock (거래시간 테스트용)"""
    with patch('ai_engine.config.korean_market_config.datetime') as mock_dt:
        # 2024년 1월 15일 월요일 10시 30분 (거래시간)
        mock_dt.now.return_value = datetime(2024, 1, 15, 10, 30)
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        yield mock_dt

# 테스트 실행
if __name__ == "__main__":
    pytest.main([__file__, "-v"])