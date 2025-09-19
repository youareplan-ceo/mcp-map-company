"""
한국 주식 티커 변환 유틸리티
다양한 형식의 한국 주식 식별자 간 변환 및 검증
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass
from enum import Enum
import json
import csv
from pathlib import Path

logger = logging.getLogger(__name__)

class TickerFormat(Enum):
    """티커 형식 종류"""
    KRX_CODE = "krx_code"           # 6자리 종목코드 (005930)
    YFINANCE = "yfinance"           # yfinance 형식 (005930.KS)
    INVESTING = "investing"         # investing.com 형식
    TRADINGVIEW = "tradingview"     # TradingView 형식
    BLOOMBERG = "bloomberg"         # Bloomberg 형식
    REUTERS = "reuters"             # Reuters 형식

@dataclass
class StockTicker:
    """주식 티커 정보"""
    krx_code: str                   # 6자리 KRX 코드
    name_kr: str                    # 한글명
    name_en: Optional[str] = None   # 영문명
    market: str = "KOSPI"           # KOSPI/KOSDAQ/KONEX
    sector: Optional[str] = None    # 업종
    industry: Optional[str] = None  # 산업
    
    # 다양한 형식의 티커들
    yfinance_symbol: Optional[str] = None
    bloomberg_symbol: Optional[str] = None
    reuters_symbol: Optional[str] = None
    tradingview_symbol: Optional[str] = None
    
    # 추가 정보
    listing_date: Optional[str] = None
    market_cap: Optional[int] = None
    is_etf: bool = False
    is_reit: bool = False
    is_preferred: bool = False
    
    def __post_init__(self):
        """초기화 후 처리"""
        if not self.yfinance_symbol:
            self.yfinance_symbol = self._generate_yfinance_symbol()
    
    def _generate_yfinance_symbol(self) -> str:
        """yfinance 심볼 생성"""
        suffix = ".KS" if self.market == "KOSPI" else ".KQ"
        return f"{self.krx_code}{suffix}"

class TickerConverter:
    """한국 주식 티커 변환기"""
    
    def __init__(self):
        # 주요 종목 데이터베이스 (실제로는 외부 파일에서 로드)
        self.ticker_database = self._initialize_ticker_database()
        
        # 시장별 접미사 매핑
        self.market_suffixes = {
            "yfinance": {
                "KOSPI": ".KS",
                "KOSDAQ": ".KQ",
                "KONEX": ".KN"
            },
            "bloomberg": {
                "KOSPI": " KS Equity",
                "KOSDAQ": " KQ Equity",
                "KONEX": " KN Equity"
            },
            "reuters": {
                "KOSPI": ".KS",
                "KOSDAQ": ".KQ", 
                "KONEX": ".KN"
            },
            "tradingview": {
                "KOSPI": "",        # TradingView는 접미사 없이 사용
                "KOSDAQ": "",
                "KONEX": ""
            }
        }
        
        # 정규표현식 패턴들
        self.patterns = {
            "krx_code": r"^(\d{6})$",
            "yfinance": r"^(\d{6})\.(KS|KQ|KN)$",
            "bloomberg": r"^(\d{6})\s+(KS|KQ|KN)\s+Equity$",
            "reuters": r"^(\d{6})\.(KS|KQ|KN)$",
            "name_with_code": r"([가-힣A-Za-z0-9\s&]+)\s*\((\d{6})\)",
            "code_with_name": r"(\d{6})\s*([가-힣A-Za-z0-9\s&]+)"
        }
    
    def _initialize_ticker_database(self) -> Dict[str, StockTicker]:
        """티커 데이터베이스 초기화"""
        # 주요 종목들의 정보 (실제 환경에서는 외부 데이터 소스에서 로드)
        major_stocks = {
            # 삼성그룹
            "005930": StockTicker(
                krx_code="005930",
                name_kr="삼성전자",
                name_en="Samsung Electronics Co Ltd",
                market="KOSPI",
                sector="기술주",
                industry="반도체"
            ),
            
            # SK그룹
            "000660": StockTicker(
                krx_code="000660", 
                name_kr="SK하이닉스",
                name_en="SK Hynix Inc",
                market="KOSPI",
                sector="기술주",
                industry="반도체"
            ),
            
            # 금융
            "055550": StockTicker(
                krx_code="055550",
                name_kr="신한지주",
                name_en="Shinhan Financial Group Co Ltd",
                market="KOSPI",
                sector="금융",
                industry="은행"
            ),
            
            "086790": StockTicker(
                krx_code="086790",
                name_kr="하나금융지주", 
                name_en="Hana Financial Group Inc",
                market="KOSPI",
                sector="금융",
                industry="은행"
            ),
            
            # 바이오
            "207940": StockTicker(
                krx_code="207940",
                name_kr="삼성바이오로직스",
                name_en="Samsung Biologics Co Ltd",
                market="KOSPI",
                sector="헬스케어",
                industry="바이오"
            ),
            
            # 화학
            "051910": StockTicker(
                krx_code="051910",
                name_kr="LG화학",
                name_en="LG Chem Ltd",
                market="KOSPI",
                sector="소재",
                industry="화학"
            ),
            
            # 자동차
            "005380": StockTicker(
                krx_code="005380",
                name_kr="현대차",
                name_en="Hyundai Motor Company",
                market="KOSPI",
                sector="자동차",
                industry="완성차"
            ),
            
            # IT 서비스
            "035420": StockTicker(
                krx_code="035420",
                name_kr="NAVER",
                name_en="NAVER Corporation",
                market="KOSPI",
                sector="IT서비스",
                industry="인터넷"
            ),
            
            # 게임 (코스닥)
            "036570": StockTicker(
                krx_code="036570",
                name_kr="엔씨소프트",
                name_en="NCSOFT Corporation",
                market="KOSDAQ",
                sector="게임",
                industry="온라인게임"
            ),
            
            # 엔터테인먼트 (코스닥)  
            "035900": StockTicker(
                krx_code="035900",
                name_kr="JYP Ent.",
                name_en="JYP Entertainment Corp",
                market="KOSDAQ",
                sector="미디어",
                industry="엔터테인먼트"
            )
        }
        
        return major_stocks
    
    def detect_format(self, ticker_string: str) -> TickerFormat:
        """티커 형식 자동 감지"""
        if not ticker_string:
            raise ValueError("빈 티커 문자열입니다.")
        
        ticker_string = ticker_string.strip()
        
        # KRX 6자리 코드
        if re.match(self.patterns["krx_code"], ticker_string):
            return TickerFormat.KRX_CODE
        
        # yfinance 형식
        if re.match(self.patterns["yfinance"], ticker_string):
            return TickerFormat.YFINANCE
        
        # Bloomberg 형식
        if re.match(self.patterns["bloomberg"], ticker_string, re.IGNORECASE):
            return TickerFormat.BLOOMBERG
        
        # Reuters 형식 (yfinance와 동일하지만 구분을 위해)
        if re.match(self.patterns["reuters"], ticker_string):
            return TickerFormat.REUTERS
        
        # 종목명과 코드가 함께 있는 경우 (삼성전자(005930))
        if re.search(self.patterns["name_with_code"], ticker_string):
            return TickerFormat.KRX_CODE
        
        # 코드와 종목명이 함께 있는 경우 (005930 삼성전자)
        if re.search(self.patterns["code_with_name"], ticker_string):
            return TickerFormat.KRX_CODE
        
        # 기본값은 KRX 코드로 가정
        return TickerFormat.KRX_CODE
    
    def extract_krx_code(self, ticker_string: str) -> Optional[str]:
        """다양한 형식에서 KRX 6자리 코드 추출"""
        if not ticker_string:
            return None
        
        ticker_string = ticker_string.strip()
        ticker_format = self.detect_format(ticker_string)
        
        if ticker_format == TickerFormat.KRX_CODE:
            # 직접적인 KRX 코드인 경우
            if self.validate_krx_code(ticker_string):
                return ticker_string
            
            # 종목명과 함께 있는 경우를 먼저 확인
            name_code_match = re.search(self.patterns["name_with_code"], ticker_string)
            if name_code_match:
                return name_code_match.group(2)
            
            code_name_match = re.search(self.patterns["code_with_name"], ticker_string)
            if code_name_match:
                return code_name_match.group(1)
            
            return None
        
        elif ticker_format == TickerFormat.YFINANCE:
            match = re.match(self.patterns["yfinance"], ticker_string)
            return match.group(1) if match else None
        
        elif ticker_format == TickerFormat.BLOOMBERG:
            match = re.match(self.patterns["bloomberg"], ticker_string, re.IGNORECASE)
            return match.group(1) if match else None
        
        elif ticker_format == TickerFormat.REUTERS:
            match = re.match(self.patterns["reuters"], ticker_string)
            return match.group(1) if match else None
        
        # 종목명과 함께 있는 경우
        name_code_match = re.search(self.patterns["name_with_code"], ticker_string)
        if name_code_match:
            return name_code_match.group(2)
        
        code_name_match = re.search(self.patterns["code_with_name"], ticker_string)
        if code_name_match:
            return code_name_match.group(1)
        
        return None
    
    def validate_krx_code(self, code: str) -> bool:
        """KRX 종목코드 유효성 검증"""
        if not code or not isinstance(code, str):
            return False
        
        # 6자리 숫자인지 확인
        return bool(re.match(r"^\d{6}$", code))
    
    def convert_to_format(self, ticker_string: str, target_format: TickerFormat) -> Optional[str]:
        """다른 형식으로 변환"""
        krx_code = self.extract_krx_code(ticker_string)
        if not krx_code:
            return None
        
        # 데이터베이스에서 종목 정보 조회
        stock_info = self.get_stock_info(krx_code)
        if not stock_info:
            # 데이터베이스에 없는 경우 기본 변환 로직 사용
            stock_info = StockTicker(krx_code=krx_code, name_kr="Unknown", market="KOSPI")
        
        if target_format == TickerFormat.KRX_CODE:
            return krx_code
        
        elif target_format == TickerFormat.YFINANCE:
            suffix = self.market_suffixes["yfinance"][stock_info.market]
            return f"{krx_code}{suffix}"
        
        elif target_format == TickerFormat.BLOOMBERG:
            suffix = self.market_suffixes["bloomberg"][stock_info.market]
            return f"{krx_code}{suffix}"
        
        elif target_format == TickerFormat.REUTERS:
            suffix = self.market_suffixes["reuters"][stock_info.market]
            return f"{krx_code}{suffix}"
        
        elif target_format == TickerFormat.TRADINGVIEW:
            # TradingView는 KRX: 접두사 사용
            return f"KRX:{krx_code}"
        
        return None
    
    def get_stock_info(self, identifier: str) -> Optional[StockTicker]:
        """종목 정보 조회 (코드 또는 이름으로)"""
        # KRX 코드로 직접 조회
        krx_code = self.extract_krx_code(identifier)
        if krx_code and krx_code in self.ticker_database:
            return self.ticker_database[krx_code]
        
        # 종목명으로 검색
        identifier_lower = identifier.lower().strip()
        for stock in self.ticker_database.values():
            if (stock.name_kr.lower() == identifier_lower or 
                (stock.name_en and stock.name_en.lower() == identifier_lower)):
                return stock
        
        return None
    
    def search_by_name(self, query: str, limit: int = 10) -> List[StockTicker]:
        """종목명으로 검색 (부분 일치)"""
        if not query:
            return []
        
        query_lower = query.lower().strip()
        results = []
        
        for stock in self.ticker_database.values():
            # 한글명 검색
            if query_lower in stock.name_kr.lower():
                results.append(stock)
            # 영문명 검색
            elif stock.name_en and query_lower in stock.name_en.lower():
                results.append(stock)
        
        return results[:limit]
    
    def get_market_info(self, ticker: str) -> Dict[str, Any]:
        """시장 정보 반환"""
        krx_code = self.extract_krx_code(ticker)
        if not krx_code:
            return {}
        
        stock_info = self.get_stock_info(krx_code)
        if not stock_info:
            return {"krx_code": krx_code, "market": "UNKNOWN"}
        
        return {
            "krx_code": krx_code,
            "name_kr": stock_info.name_kr,
            "name_en": stock_info.name_en,
            "market": stock_info.market,
            "sector": stock_info.sector,
            "industry": stock_info.industry,
            "yfinance_symbol": stock_info.yfinance_symbol,
            "is_etf": stock_info.is_etf,
            "is_reit": stock_info.is_reit
        }
    
    def batch_convert(self, tickers: List[str], target_format: TickerFormat) -> Dict[str, Optional[str]]:
        """일괄 변환"""
        results = {}
        
        for ticker in tickers:
            try:
                converted = self.convert_to_format(ticker, target_format)
                results[ticker] = converted
            except Exception as e:
                logger.error(f"티커 변환 실패 {ticker}: {e}")
                results[ticker] = None
        
        return results
    
    def validate_ticker_list(self, tickers: List[str]) -> Dict[str, bool]:
        """티커 목록 유효성 검증"""
        results = {}
        
        for ticker in tickers:
            try:
                krx_code = self.extract_krx_code(ticker)
                results[ticker] = krx_code is not None and self.validate_krx_code(krx_code)
            except Exception:
                results[ticker] = False
        
        return results
    
    def suggest_similar_tickers(self, query: str, limit: int = 5) -> List[Tuple[str, float]]:
        """유사한 종목 추천 (간단한 문자열 유사도 기반)"""
        if not query:
            return []
        
        suggestions = []
        query_lower = query.lower().strip()
        
        for stock in self.ticker_database.values():
            # 한글명 유사도
            kr_similarity = self._calculate_similarity(query_lower, stock.name_kr.lower())
            if kr_similarity > 0.3:  # 임계값
                suggestions.append((f"{stock.name_kr}({stock.krx_code})", kr_similarity))
            
            # 영문명 유사도 (있는 경우)
            if stock.name_en:
                en_similarity = self._calculate_similarity(query_lower, stock.name_en.lower())
                if en_similarity > 0.3:
                    suggestions.append((f"{stock.name_en}({stock.krx_code})", en_similarity))
        
        # 유사도 순 정렬
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return suggestions[:limit]
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """간단한 문자열 유사도 계산 (Jaccard 유사도)"""
        if not str1 or not str2:
            return 0.0
        
        # 문자 단위 집합으로 변환
        set1 = set(str1)
        set2 = set(str2)
        
        # Jaccard 유사도: 교집합 / 합집합
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def export_ticker_mapping(self, format: str = "json") -> str:
        """티커 매핑 정보 내보내기"""
        data = []
        
        for stock in self.ticker_database.values():
            entry = {
                "krx_code": stock.krx_code,
                "name_kr": stock.name_kr,
                "name_en": stock.name_en,
                "market": stock.market,
                "sector": stock.sector,
                "industry": stock.industry,
                "yfinance": stock.yfinance_symbol,
                "bloomberg": f"{stock.krx_code} {stock.market[:2]} Equity",
                "tradingview": f"KRX:{stock.krx_code}"
            }
            data.append(entry)
        
        if format.lower() == "json":
            return json.dumps(data, ensure_ascii=False, indent=2)
        elif format.lower() == "csv":
            # CSV 형태로 변환 (간단 구현)
            lines = ["krx_code,name_kr,name_en,market,yfinance,bloomberg"]
            for entry in data:
                line = f"{entry['krx_code']},{entry['name_kr']},{entry.get('name_en', '')},{entry['market']},{entry['yfinance']},{entry['bloomberg']}"
                lines.append(line)
            return "\n".join(lines)
        
        return str(data)

# 글로벌 인스턴스
ticker_converter = TickerConverter()

# 편의 함수들
def convert_ticker(ticker: str, target_format: TickerFormat) -> Optional[str]:
    """티커 변환"""
    return ticker_converter.convert_to_format(ticker, target_format)

def to_yfinance(ticker: str) -> Optional[str]:
    """yfinance 형식으로 변환"""
    return convert_ticker(ticker, TickerFormat.YFINANCE)

def to_krx_code(ticker: str) -> Optional[str]:
    """KRX 코드로 변환"""
    return ticker_converter.extract_krx_code(ticker)

def validate_korean_ticker(ticker: str) -> bool:
    """한국 주식 티커 유효성 검증"""
    krx_code = to_krx_code(ticker)
    return krx_code is not None and ticker_converter.validate_krx_code(krx_code)

def get_stock_info(ticker: str) -> Optional[Dict[str, Any]]:
    """종목 정보 조회"""
    info = ticker_converter.get_market_info(ticker)
    return info if info else None

def search_stock(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """종목 검색"""
    stocks = ticker_converter.search_by_name(query, limit)
    return [
        {
            "code": stock.krx_code,
            "name_kr": stock.name_kr,
            "name_en": stock.name_en,
            "market": stock.market,
            "yfinance": stock.yfinance_symbol
        }
        for stock in stocks
    ]

# 사용 예시
if __name__ == "__main__":
    print("=== 한국 주식 티커 변환기 예시 ===")
    
    test_tickers = [
        "005930",           # KRX 코드
        "005930.KS",        # yfinance 형식
        "삼성전자",          # 종목명
        "NAVER",            # 영문명
        "036570.KQ"         # 코스닥 yfinance
    ]
    
    for ticker in test_tickers:
        print(f"\n입력: {ticker}")
        
        # 형식 감지
        try:
            format_detected = ticker_converter.detect_format(ticker)
            print(f"  감지된 형식: {format_detected.value}")
        except:
            format_detected = None
        
        # KRX 코드 추출
        krx_code = to_krx_code(ticker)
        print(f"  KRX 코드: {krx_code}")
        
        if krx_code:
            # 다양한 형식으로 변환
            yf_symbol = to_yfinance(ticker)
            print(f"  yfinance: {yf_symbol}")
            
            # 종목 정보
            stock_info = get_stock_info(ticker)
            if stock_info:
                print(f"  종목명: {stock_info['name_kr']}")
                print(f"  시장: {stock_info['market']}")
                print(f"  섹터: {stock_info.get('sector', 'N/A')}")
    
    # 종목 검색 예시
    print(f"\n=== '삼성' 검색 결과 ===")
    search_results = search_stock("삼성", limit=3)
    for result in search_results:
        print(f"  {result['name_kr']}({result['code']}) - {result['market']}")
    
    # 유사 종목 추천
    print(f"\n=== '삼성전' 유사 종목 ===")
    suggestions = ticker_converter.suggest_similar_tickers("삼성전", limit=3)
    for suggestion, similarity in suggestions:
        print(f"  {suggestion} (유사도: {similarity:.2f})")