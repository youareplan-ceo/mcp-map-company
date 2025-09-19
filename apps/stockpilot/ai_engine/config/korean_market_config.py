"""
한국 주식시장 특화 설정
KRX (코스피/코스닥) 시장의 특성을 반영한 설정 및 유틸리티
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, time
import pytz

logger = logging.getLogger(__name__)

class KoreanMarket(Enum):
    """한국 주식시장 구분"""
    KOSPI = "KOSPI"      # 코스피 (대형주 중심)
    KOSDAQ = "KOSDAQ"    # 코스닥 (중소형주, IT 중심)
    KONEX = "KONEX"      # 코넥스 (신생기업)

class SectorKR(Enum):
    """한국 주식시장 섹터 분류 (GICS 기준 한국어)"""
    # 주요 11개 섹터
    IT = "정보기술"
    FINANCE = "금융"
    MATERIALS = "소재"
    INDUSTRIALS = "산업재"
    CONSUMER_DISC = "임의소비재"
    CONSUMER_STAPLES = "필수소비재"
    HEALTHCARE = "헬스케어"
    COMMUNICATION = "커뮤니케이션서비스"
    UTILITIES = "유틸리티"
    REAL_ESTATE = "부동산"
    ENERGY = "에너지"

@dataclass
class KoreanStockInfo:
    """한국 주식 정보"""
    symbol: str                    # 종목코드 (6자리)
    name_kr: str                  # 한글명
    name_en: Optional[str] = None # 영문명
    market: KoreanMarket = KoreanMarket.KOSPI
    sector: Optional[SectorKR] = None
    industry: Optional[str] = None
    market_cap: Optional[int] = None      # 시가총액 (백만원)
    listing_date: Optional[datetime] = None
    is_etf: bool = False
    is_reit: bool = False
    
    # yfinance용 심볼 변환
    @property
    def yf_symbol(self) -> str:
        """yfinance용 심볼 반환"""
        suffix = ".KS" if self.market == KoreanMarket.KOSPI else ".KQ"
        return f"{self.symbol}{suffix}"

class KoreanMarketConfig:
    """한국 주식시장 설정 및 유틸리티"""
    
    def __init__(self):
        # 한국 시장 시간대
        self.timezone = pytz.timezone('Asia/Seoul')
        
        # 거래 시간 설정
        self.trading_hours = {
            "regular": {
                "start": time(9, 0),   # 09:00
                "end": time(15, 30),   # 15:30
            },
            "pre_market": {
                "start": time(8, 30),  # 08:30 (동시호가)
                "end": time(9, 0),     # 09:00
            },
            "after_market": {
                "start": time(15, 30), # 15:30 (동시호가)
                "end": time(16, 0),    # 16:00
            }
        }
        
        # 주요 지수 정보
        self.major_indices = {
            "KOSPI": {
                "name": "코스피",
                "symbol": "^KS11",
                "description": "한국종합주가지수"
            },
            "KOSDAQ": {
                "name": "코스닥",
                "symbol": "^KQ11", 
                "description": "코스닥종합지수"
            },
            "KRX100": {
                "name": "KRX100",
                "symbol": "^KRX100",
                "description": "KRX 100지수"
            }
        }
        
        # 주요 대형주 정보 (예시)
        self.major_stocks = self._init_major_stocks()
        
        # 섹터별 대표주 매핑
        self.sector_representatives = self._init_sector_representatives()
        
        # 한국어 분석용 키워드
        self.korean_financial_terms = self._init_korean_terms()
        
        # 시가총액 기준 분류
        self.market_cap_thresholds = {
            "대형주": 2_000_000,    # 2조원 이상
            "중형주": 300_000,      # 3천억원 이상
            "소형주": 0             # 그 외
        }
    
    def _init_major_stocks(self) -> Dict[str, KoreanStockInfo]:
        """주요 종목 정보 초기화"""
        major_stocks = {
            # 삼성그룹
            "005930": KoreanStockInfo(
                symbol="005930", name_kr="삼성전자", name_en="Samsung Electronics",
                market=KoreanMarket.KOSPI, sector=SectorKR.IT
            ),
            "000660": KoreanStockInfo(
                symbol="000660", name_kr="SK하이닉스", name_en="SK Hynix",
                market=KoreanMarket.KOSPI, sector=SectorKR.IT
            ),
            
            # 금융
            "055550": KoreanStockInfo(
                symbol="055550", name_kr="신한지주", name_en="Shinhan Financial Group",
                market=KoreanMarket.KOSPI, sector=SectorKR.FINANCE
            ),
            "086790": KoreanStockInfo(
                symbol="086790", name_kr="하나금융지주", name_en="Hana Financial Group",
                market=KoreanMarket.KOSPI, sector=SectorKR.FINANCE
            ),
            
            # 바이오/제약
            "207940": KoreanStockInfo(
                symbol="207940", name_kr="삼성바이오로직스", name_en="Samsung Biologics",
                market=KoreanMarket.KOSPI, sector=SectorKR.HEALTHCARE
            ),
            
            # 화학/소재
            "051910": KoreanStockInfo(
                symbol="051910", name_kr="LG화학", name_en="LG Chem",
                market=KoreanMarket.KOSPI, sector=SectorKR.MATERIALS
            ),
            
            # 자동차
            "005380": KoreanStockInfo(
                symbol="005380", name_kr="현대차", name_en="Hyundai Motor",
                market=KoreanMarket.KOSPI, sector=SectorKR.CONSUMER_DISC
            ),
            
            # 게임 (코스닥)
            "036570": KoreanStockInfo(
                symbol="036570", name_kr="엔씨소프트", name_en="NCSOFT",
                market=KoreanMarket.KOSDAQ, sector=SectorKR.COMMUNICATION
            ),
        }
        
        return major_stocks
    
    def _init_sector_representatives(self) -> Dict[SectorKR, List[str]]:
        """섹터별 대표주 매핑"""
        return {
            SectorKR.IT: ["005930", "000660", "035420"],  # 삼성전자, SK하이닉스, NAVER
            SectorKR.FINANCE: ["055550", "086790", "316140"],  # 신한지주, 하나금융지주, 우리금융지주
            SectorKR.MATERIALS: ["051910", "096770", "034730"],  # LG화학, SK이노베이션, SK
            SectorKR.HEALTHCARE: ["207940", "068270", "326030"],  # 삼성바이오로직스, 셀트리온, SK바이오팜
            SectorKR.CONSUMER_DISC: ["005380", "012330", "051600"],  # 현대차, 현대모비스, 한진칼
            SectorKR.INDUSTRIALS: ["009540", "028260", "180640"],  # HD한국조선해양, 삼성물산, 한진
            SectorKR.COMMUNICATION: ["035420", "036570", "035900"],  # NAVER, 엔씨소프트, JYP Ent.
        }
    
    def _init_korean_terms(self) -> Dict[str, List[str]]:
        """한국 금융 용어 사전"""
        return {
            # 긍정적 키워드
            "positive": [
                "상승", "급등", "강세", "호재", "실적개선", "매수", "증가", "성장", 
                "확대", "투자", "개발", "출시", "수주", "계약", "협력", "제휴",
                "흑자", "이익", "수익", "매출", "호황", "부양", "활성화"
            ],
            
            # 부정적 키워드
            "negative": [
                "하락", "급락", "약세", "악재", "실적악화", "매도", "감소", "축소",
                "철수", "중단", "지연", "취소", "적자", "손실", "부진", "침체",
                "우려", "리스크", "위험", "불안", "경고", "제재", "규제"
            ],
            
            # 중립적/분석 키워드
            "neutral": [
                "전망", "예상", "계획", "목표", "전략", "정책", "발표", "공시",
                "실적", "재무", "매출", "영업이익", "당기순이익", "배당", "지배구조",
                "ESG", "지속가능", "디지털전환", "친환경"
            ],
            
            # 기술적 분석 용어
            "technical": [
                "지지선", "저항선", "돌파", "이탈", "반등", "조정", "추세", "패턴",
                "거래량", "이동평균", "RSI", "MACD", "볼린저밴드", "골든크로스", "데드크로스"
            ]
        }
    
    def validate_korean_stock_symbol(self, symbol: str) -> bool:
        """한국 주식 종목코드 검증"""
        if not symbol or not isinstance(symbol, str):
            return False
        
        # 6자리 숫자 형태 확인
        return bool(re.match(r'^\d{6}$', symbol))
    
    def convert_to_yfinance_symbol(self, symbol: str, market: Optional[KoreanMarket] = None) -> str:
        """yfinance용 심볼로 변환"""
        if not self.validate_korean_stock_symbol(symbol):
            raise ValueError(f"잘못된 종목코드 형식: {symbol}")
        
        # 시장 정보가 없으면 종목코드로 추정
        if market is None:
            market = self.guess_market_from_symbol(symbol)
        
        suffix = ".KS" if market == KoreanMarket.KOSPI else ".KQ"
        return f"{symbol}{suffix}"
    
    def guess_market_from_symbol(self, symbol: str) -> KoreanMarket:
        """종목코드로 시장 추정"""
        if not self.validate_korean_stock_symbol(symbol):
            return KoreanMarket.KOSPI  # 기본값
        
        # 알려진 종목이면 해당 시장 반환
        if symbol in self.major_stocks:
            return self.major_stocks[symbol].market
        
        # 코스닥 종목코드 패턴 (대략적)
        # 실제로는 정확한 매핑 테이블이 필요하지만, 여기서는 간단한 휴리스틱 사용
        first_digit = int(symbol[0])
        
        if first_digit >= 9:  # 90만번대 이상은 대부분 코스닥
            return KoreanMarket.KOSDAQ
        elif first_digit <= 1:  # 10만번대 이하는 대부분 코스피
            return KoreanMarket.KOSPI
        else:
            # 중간 범위는 추가 로직 필요 (여기서는 기본값 사용)
            return KoreanMarket.KOSPI
    
    def get_stock_info(self, symbol: str) -> Optional[KoreanStockInfo]:
        """종목 정보 조회"""
        return self.major_stocks.get(symbol)
    
    def is_trading_time(self, dt: Optional[datetime] = None) -> bool:
        """현재 거래시간 여부 확인"""
        if dt is None:
            dt = datetime.now(self.timezone)
        
        # 주말 제외
        if dt.weekday() >= 5:  # 토, 일
            return False
        
        current_time = dt.time()
        trading_start = self.trading_hours["regular"]["start"]
        trading_end = self.trading_hours["regular"]["end"]
        
        return trading_start <= current_time <= trading_end
    
    def get_market_status(self, dt: Optional[datetime] = None) -> str:
        """시장 상태 반환"""
        if dt is None:
            dt = datetime.now(self.timezone)
        
        if dt.weekday() >= 5:
            return "휴장"
        
        current_time = dt.time()
        
        if current_time < self.trading_hours["pre_market"]["start"]:
            return "장전"
        elif current_time < self.trading_hours["regular"]["start"]:
            return "동시호가(개장)"
        elif current_time <= self.trading_hours["regular"]["end"]:
            return "정규거래"
        elif current_time < self.trading_hours["after_market"]["end"]:
            return "동시호가(마감)"
        else:
            return "장후"
    
    def classify_by_market_cap(self, market_cap: int) -> str:
        """시가총액 기준 분류"""
        if market_cap >= self.market_cap_thresholds["대형주"]:
            return "대형주"
        elif market_cap >= self.market_cap_thresholds["중형주"]:
            return "중형주"
        else:
            return "소형주"
    
    def get_sector_stocks(self, sector: SectorKR) -> List[str]:
        """섹터별 대표 종목 반환"""
        return self.sector_representatives.get(sector, [])
    
    def analyze_korean_text_sentiment(self, text: str) -> Dict[str, Any]:
        """한국어 텍스트 감정 분석 (키워드 기반)"""
        if not text:
            return {"sentiment": "neutral", "score": 0.0, "keywords": []}
        
        text_lower = text.lower()
        
        positive_count = 0
        negative_count = 0
        found_keywords = []
        
        # 긍정적 키워드 검색
        for keyword in self.korean_financial_terms["positive"]:
            if keyword in text_lower:
                positive_count += text_lower.count(keyword)
                found_keywords.append(("positive", keyword))
        
        # 부정적 키워드 검색
        for keyword in self.korean_financial_terms["negative"]:
            if keyword in text_lower:
                negative_count += text_lower.count(keyword)
                found_keywords.append(("negative", keyword))
        
        # 감정 점수 계산
        total_count = positive_count + negative_count
        if total_count == 0:
            sentiment = "neutral"
            score = 0.0
        else:
            score = (positive_count - negative_count) / total_count
            if score > 0.1:
                sentiment = "positive"
            elif score < -0.1:
                sentiment = "negative"
            else:
                sentiment = "neutral"
        
        return {
            "sentiment": sentiment,
            "score": score,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "keywords": found_keywords
        }
    
    def extract_stock_mentions(self, text: str) -> List[Tuple[str, str]]:
        """텍스트에서 주식 종목명/코드 추출"""
        mentions = []
        
        # 종목코드 패턴 검색 (6자리 숫자)
        code_pattern = r'\b\d{6}\b'
        codes = re.findall(code_pattern, text)
        
        for code in codes:
            if self.validate_korean_stock_symbol(code):
                stock_info = self.get_stock_info(code)
                name = stock_info.name_kr if stock_info else "알 수 없음"
                mentions.append((code, name))
        
        # 주요 종목 한글명 검색
        for code, info in self.major_stocks.items():
            if info.name_kr in text:
                mentions.append((code, info.name_kr))
        
        return mentions
    
    def get_trading_calendar_info(self, dt: Optional[datetime] = None) -> Dict[str, Any]:
        """거래일정 정보 반환"""
        if dt is None:
            dt = datetime.now(self.timezone)
        
        return {
            "date": dt.date().isoformat(),
            "weekday": dt.strftime("%A"),
            "weekday_kr": ["월", "화", "수", "목", "금", "토", "일"][dt.weekday()],
            "is_trading_day": dt.weekday() < 5,
            "market_status": self.get_market_status(dt),
            "trading_hours": self.trading_hours
        }
    
    def format_korean_number(self, number: int) -> str:
        """한국식 숫자 표기법 (억, 조 단위)"""
        if number < 0:
            return f"-{self.format_korean_number(-number)}"
        
        if number >= 1_000_000_000_000:  # 조 단위
            jo = number // 1_000_000_000_000
            remaining = number % 1_000_000_000_000
            if remaining >= 100_000_000:  # 억 단위
                eok = remaining // 100_000_000
                return f"{jo}조 {eok}억"
            else:
                return f"{jo}조"
        elif number >= 100_000_000:  # 억 단위
            eok = number // 100_000_000
            remaining = number % 100_000_000
            if remaining >= 10_000:  # 만 단위
                man = remaining // 10_000
                return f"{eok}억 {man}만"
            else:
                return f"{eok}억"
        elif number >= 10_000:  # 만 단위
            man = number // 10_000
            remaining = number % 10_000
            if remaining > 0:
                return f"{man}만 {remaining:,}"
            else:
                return f"{man}만"
        else:
            return f"{number:,}"

# 글로벌 설정 인스턴스
korean_market_config = KoreanMarketConfig()

# 편의 함수들
def validate_stock_symbol(symbol: str) -> bool:
    """종목코드 검증"""
    return korean_market_config.validate_korean_stock_symbol(symbol)

def get_yfinance_symbol(symbol: str, market: Optional[KoreanMarket] = None) -> str:
    """yfinance 심볼 변환"""
    return korean_market_config.convert_to_yfinance_symbol(symbol, market)

def analyze_korean_sentiment(text: str) -> Dict[str, Any]:
    """한국어 감정 분석"""
    return korean_market_config.analyze_korean_text_sentiment(text)

def extract_stock_symbols(text: str) -> List[Tuple[str, str]]:
    """종목 추출"""
    return korean_market_config.extract_stock_mentions(text)

def is_market_open(dt: Optional[datetime] = None) -> bool:
    """장 개장 여부"""
    return korean_market_config.is_trading_time(dt)

def get_market_info() -> Dict[str, Any]:
    """시장 정보"""
    return {
        "major_indices": korean_market_config.major_indices,
        "trading_hours": korean_market_config.trading_hours,
        "timezone": str(korean_market_config.timezone),
        "market_status": korean_market_config.get_market_status()
    }

# 사용 예시
if __name__ == "__main__":
    # 종목코드 검증
    print(f"005930 검증: {validate_stock_symbol('005930')}")
    print(f"yfinance 심볼: {get_yfinance_symbol('005930')}")
    
    # 감정 분석
    text = "삼성전자가 실적 호조로 급등했습니다. 매출이 크게 증가했네요."
    sentiment = analyze_korean_sentiment(text)
    print(f"감정 분석: {sentiment}")
    
    # 종목 추출
    mentions = extract_stock_symbols("005930 삼성전자와 000660 SK하이닉스 분석")
    print(f"종목 추출: {mentions}")
    
    # 시장 정보
    print(f"현재 시장 상태: {korean_market_config.get_market_status()}")
    print(f"장 개장 여부: {is_market_open()}")