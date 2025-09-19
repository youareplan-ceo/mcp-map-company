"""
한국어 텍스트 처리 유틸리티
한국 주식/금융 텍스트의 전처리, 정규화, 추출 기능
"""

import re
import logging
from typing import List, Dict, Tuple, Optional, Any, Set
from dataclasses import dataclass
import unicodedata
from datetime import datetime
import json

logger = logging.getLogger(__name__)

@dataclass
class ProcessedText:
    """처리된 텍스트 결과"""
    original: str
    processed: str
    removed_chars: List[str]
    normalized_numbers: Dict[str, str]
    extracted_entities: Dict[str, List[str]]
    confidence_score: float

class KoreanTextProcessor:
    """한국어 텍스트 처리기"""
    
    def __init__(self):
        # 한국 금융 관련 정규표현식 패턴들
        self.patterns = {
            # 숫자 및 금액 패턴
            "amount": r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*([조억만천원달러])',
            "percentage": r'(\d+(?:\.\d+)?)\s*%',
            "stock_code": r'\b(\d{6})\b',
            "price": r'(\d+(?:,\d{3})*)\s*원',
            
            # 날짜 패턴
            "date_kr": r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일',
            "date_slash": r'(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})',
            
            # 회사명 패턴
            "company_suffix": r'(주식회사|유한회사|\(주\)|\㈜)',
            "company_name": r'([가-힣A-Za-z0-9]+)(?:주식회사|유한회사|\(주\)|\㈜)',
            
            # 금융 용어 패턴
            "financial_metric": r'(매출액?|영업이익|당기순이익|부채비율|유동비율|ROE|ROA|PER|PBR|EPS)',
            "trading_term": r'(매수|매도|보유|상승|하락|급등|급락|돌파|지지|저항)',
            
            # 특수 문자 및 이모지
            "emoji": r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000026FF\U00002700-\U000027BF]',
            "special_chars": r'[^\w\s가-힣.,!?;:()\-\[\]{}"\'/]',
            
            # 뉴스 관련 패턴
            "news_source": r'\[(.*?)\]|\((.*?)\)$',
            "reporter": r'([가-힣]{2,4})\s*(기자|특파원|에디터)',
            "timestamp": r'(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})\s*(\d{1,2}):(\d{2})'
        }
        
        # 한국어 불용어 (금융 분석에서 제외할 단어들)
        self.stopwords = {
            "조사": ["은", "는", "이", "가", "을", "를", "에", "에서", "으로", "로", "의", "와", "과", "도", "만"],
            "어미": ["다", "라", "이다", "했다", "한다", "된다", "있다", "없다"],
            "기타": ["그", "이", "저", "것", "수", "때", "곳", "등", "및", "또", "또한", "하지만", "그러나", "따라서"]
        }
        
        # 한국 금융용어 사전
        self.financial_dictionary = self._load_financial_dictionary()
        
        # 숫자 단위 변환
        self.number_units = {
            "조": 1_000_000_000_000,
            "억": 100_000_000,
            "만": 10_000,
            "천": 1_000
        }
    
    def _load_financial_dictionary(self) -> Dict[str, Dict]:
        """한국 금융용어 사전 로드"""
        return {
            # 재무제표 관련
            "revenue_terms": ["매출", "매출액", "총매출", "순매출", "영업수익"],
            "profit_terms": ["영업이익", "당기순이익", "세전이익", "EBITDA", "순이익"],
            "debt_terms": ["부채", "차입금", "사채", "단기부채", "장기부채", "부채비율"],
            "asset_terms": ["자산", "총자산", "유동자산", "고정자산", "현금성자산"],
            
            # 주식 관련
            "stock_terms": ["주가", "시가", "고가", "저가", "종가", "거래량", "시가총액"],
            "valuation_terms": ["PER", "PBR", "PSR", "EV/EBITDA", "ROE", "ROA", "ROIC"],
            "trading_terms": ["매수", "매도", "보유", "손절", "익절", "물타기", "불타기"],
            
            # 시장 관련
            "market_terms": ["코스피", "코스닥", "코넥스", "장중", "개장", "마감", "동시호가"],
            "investor_terms": ["개인", "외국인", "기관", "연기금", "보험사", "은행", "증권사"],
            
            # 경제 지표
            "economic_terms": ["GDP", "물가", "금리", "환율", "무역수지", "경상수지", "실업률"],
            "policy_terms": ["금통위", "기준금리", "양적완화", "긴축", "부양책", "규제", "완화"]
        }
    
    def normalize_text(self, text: str) -> str:
        """텍스트 정규화 (기본 전처리)"""
        if not text:
            return ""
        
        # 유니코드 정규화
        text = unicodedata.normalize('NFC', text)
        
        # 연속된 공백을 하나로 통일 (줄바꿈 제외)
        text = re.sub(r'[^\S\n]+', ' ', text)
        
        # 연속된 줄바꿈을 하나로 통일
        text = re.sub(r'\n\s*\n', '\n', text)
        
        # 줄 시작 부분의 공백 제거
        text = re.sub(r'\n\s+', '\n', text)
        
        # 앞뒤 공백 제거
        text = text.strip()
        
        return text
    
    def clean_financial_text(self, text: str) -> ProcessedText:
        """금융 텍스트 정리 및 처리"""
        original = text
        processed = text
        removed_chars = []
        normalized_numbers = {}
        extracted_entities = {}
        
        try:
            # 1. 기본 정규화
            processed = self.normalize_text(processed)
            
            # 2. 특수문자 제거 (필요한 것만 보존)
            special_chars = re.findall(self.patterns["special_chars"], processed)
            removed_chars.extend(special_chars)
            processed = re.sub(self.patterns["special_chars"], ' ', processed)
            
            # 3. 이모지 제거
            emojis = re.findall(self.patterns["emoji"], processed)
            removed_chars.extend(emojis)
            processed = re.sub(self.patterns["emoji"], '', processed)
            
            # 4. 숫자 및 금액 정규화
            amounts = re.findall(self.patterns["amount"], processed)
            for amount, unit in amounts:
                original_str = f"{amount}{unit}"
                normalized_value = self._normalize_korean_number(amount, unit)
                normalized_numbers[original_str] = str(normalized_value)
            
            # 5. 엔티티 추출
            extracted_entities = self.extract_entities(processed)
            
            # 6. 연속 공백 재정리
            processed = re.sub(r'\s+', ' ', processed).strip()
            
            # 7. 신뢰도 점수 계산
            confidence_score = self._calculate_confidence(original, processed)
            
            return ProcessedText(
                original=original,
                processed=processed,
                removed_chars=removed_chars,
                normalized_numbers=normalized_numbers,
                extracted_entities=extracted_entities,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            logger.error(f"텍스트 처리 중 오류 발생: {e}")
            return ProcessedText(
                original=original,
                processed=original,
                removed_chars=[],
                normalized_numbers={},
                extracted_entities={},
                confidence_score=0.0
            )
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """금융 관련 엔티티 추출"""
        entities = {
            "stock_codes": [],
            "company_names": [],
            "amounts": [],
            "percentages": [],
            "dates": [],
            "financial_metrics": [],
            "trading_terms": [],
            "reporters": []
        }
        
        try:
            # 종목코드 추출
            stock_codes = re.findall(self.patterns["stock_code"], text)
            entities["stock_codes"] = list(set(stock_codes))
            
            # 회사명 추출
            company_matches = re.findall(self.patterns["company_name"], text)
            entities["company_names"] = list(set(company_matches))
            
            # 금액 추출
            amounts = re.findall(self.patterns["amount"], text)
            entities["amounts"] = [f"{amount}{unit}" for amount, unit in amounts]
            
            # 퍼센트 추출
            percentages = re.findall(self.patterns["percentage"], text)
            entities["percentages"] = [f"{p}%" for p in percentages]
            
            # 날짜 추출
            dates_kr = re.findall(self.patterns["date_kr"], text)
            dates_slash = re.findall(self.patterns["date_slash"], text)
            entities["dates"] = [f"{y}년{m}월{d}일" for y, m, d in dates_kr] + \
                              [f"{y}-{m}-{d}" for y, m, d in dates_slash]
            
            # 금융 메트릭 추출
            financial_metrics = re.findall(self.patterns["financial_metric"], text)
            entities["financial_metrics"] = list(set(financial_metrics))
            
            # 매매 용어 추출
            trading_terms = re.findall(self.patterns["trading_term"], text)
            entities["trading_terms"] = list(set(trading_terms))
            
            # 기자명 추출
            reporters = re.findall(self.patterns["reporter"], text)
            entities["reporters"] = [f"{name} {title}" for name, title in reporters]
            
        except Exception as e:
            logger.error(f"엔티티 추출 중 오류: {e}")
        
        return entities
    
    def _normalize_korean_number(self, number_str: str, unit: str) -> float:
        """한국어 숫자 단위 정규화"""
        try:
            # 쉼표 제거 후 숫자 변환
            number = float(number_str.replace(',', ''))
            
            # 단위 적용
            if unit in self.number_units:
                return number * self.number_units[unit]
            elif unit in ['원', '달러']:
                return number
            elif unit == '%':
                return number / 100
            else:
                return number
                
        except ValueError:
            return 0.0
    
    def _calculate_confidence(self, original: str, processed: str) -> float:
        """텍스트 처리 신뢰도 계산"""
        if not original:
            return 0.0
        
        # 길이 비율
        length_ratio = len(processed) / len(original)
        
        # 한글 문자 보존율
        korean_chars_orig = len(re.findall(r'[가-힣]', original))
        korean_chars_proc = len(re.findall(r'[가-힣]', processed))
        korean_preservation = korean_chars_proc / korean_chars_orig if korean_chars_orig > 0 else 1.0
        
        # 전체 신뢰도 (가중 평균)
        confidence = (length_ratio * 0.3 + korean_preservation * 0.7)
        
        return min(1.0, max(0.0, confidence))
    
    def extract_sentiment_keywords(self, text: str) -> Dict[str, List[str]]:
        """감정 분석용 키워드 추출"""
        from ..config.korean_market_config import korean_market_config
        
        sentiment_keywords = {
            "positive": [],
            "negative": [],
            "neutral": []
        }
        
        text_lower = text.lower()
        terms = korean_market_config.korean_financial_terms
        
        # 긍정 키워드
        for keyword in terms["positive"]:
            if keyword in text_lower:
                sentiment_keywords["positive"].append(keyword)
        
        # 부정 키워드
        for keyword in terms["negative"]:
            if keyword in text_lower:
                sentiment_keywords["negative"].append(keyword)
        
        # 중립 키워드
        for keyword in terms["neutral"]:
            if keyword in text_lower:
                sentiment_keywords["neutral"].append(keyword)
        
        return sentiment_keywords
    
    def tokenize_korean_text(self, text: str, remove_stopwords: bool = True) -> List[str]:
        """한국어 텍스트 토큰화 (간단한 구현)"""
        if not text:
            return []
        
        # 공백 기준 분리
        tokens = text.split()
        
        # 불용어 제거
        if remove_stopwords:
            all_stopwords = []
            for category in self.stopwords.values():
                all_stopwords.extend(category)
            
            tokens = [token for token in tokens if token not in all_stopwords]
        
        # 빈 토큰 제거
        tokens = [token.strip() for token in tokens if token.strip()]
        
        return tokens
    
    def analyze_text_complexity(self, text: str) -> Dict[str, Any]:
        """텍스트 복잡도 분석"""
        if not text:
            return {"complexity": "low", "score": 0.0}
        
        # 기본 통계
        char_count = len(text)
        word_count = len(text.split())
        sentence_count = len(re.split(r'[.!?]', text))
        
        # 한글 비율
        korean_chars = len(re.findall(r'[가-힣]', text))
        korean_ratio = korean_chars / char_count if char_count > 0 else 0
        
        # 전문용어 비율
        financial_terms_found = 0
        for category in self.financial_dictionary.values():
            for term in category:
                if term in text:
                    financial_terms_found += 1
        
        term_density = financial_terms_found / word_count if word_count > 0 else 0
        
        # 복잡도 점수 계산
        factors = {
            "length": min(1.0, char_count / 1000),  # 1000자 기준 정규화
            "avg_word_length": (char_count / word_count) / 10 if word_count > 0 else 0,
            "sentence_length": (word_count / sentence_count) / 20 if sentence_count > 0 else 0,
            "term_density": min(1.0, term_density * 10),
            "korean_ratio": korean_ratio
        }
        
        # 가중 평균으로 복잡도 계산
        weights = {"length": 0.2, "avg_word_length": 0.2, "sentence_length": 0.2, 
                  "term_density": 0.3, "korean_ratio": 0.1}
        
        complexity_score = sum(factors[k] * weights[k] for k in factors.keys())
        
        # 복잡도 분류
        if complexity_score < 0.3:
            complexity = "low"
        elif complexity_score < 0.6:
            complexity = "medium"
        else:
            complexity = "high"
        
        return {
            "complexity": complexity,
            "score": complexity_score,
            "factors": factors,
            "stats": {
                "char_count": char_count,
                "word_count": word_count,
                "sentence_count": sentence_count,
                "korean_ratio": korean_ratio,
                "term_density": term_density
            }
        }
    
    def preprocess_for_embedding(self, text: str) -> str:
        """임베딩을 위한 텍스트 전처리"""
        # 기본 정리
        processed_result = self.clean_financial_text(text)
        text = processed_result.processed
        
        # 추가 전처리
        # 1. 중복 공백 제거
        text = re.sub(r'\s+', ' ', text)
        
        # 2. 특수 구두점 정리
        text = re.sub(r'[.]{2,}', '.', text)  # 연속 마침표
        text = re.sub(r'[!]{2,}', '!', text)  # 연속 느낌표
        text = re.sub(r'[?]{2,}', '?', text)  # 연속 물음표
        
        # 3. 괄호 내용 정리 (필요에 따라)
        # text = re.sub(r'\([^)]*\)', '', text)  # 괄호 제거 (선택적)
        
        # 4. 최종 정리
        text = text.strip()
        
        return text
    
    def extract_key_phrases(self, text: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """핵심 구문 추출 (간단한 TF 기반)"""
        if not text:
            return []
        
        # 토큰화
        tokens = self.tokenize_korean_text(text, remove_stopwords=True)
        
        # 2-gram 및 3-gram 생성
        phrases = []
        phrases.extend(tokens)  # 1-gram
        
        # 2-gram
        for i in range(len(tokens) - 1):
            phrases.append(f"{tokens[i]} {tokens[i+1]}")
        
        # 3-gram
        for i in range(len(tokens) - 2):
            phrases.append(f"{tokens[i]} {tokens[i+1]} {tokens[i+2]}")
        
        # 빈도 계산
        phrase_counts = {}
        for phrase in phrases:
            phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
        
        # 점수 계산 (빈도 + 길이 보정)
        phrase_scores = []
        for phrase, count in phrase_counts.items():
            # 길이 보정 (긴 구문에 가중치)
            length_bonus = len(phrase.split()) * 0.1
            score = count + length_bonus
            phrase_scores.append((phrase, score))
        
        # 점수 순 정렬
        phrase_scores.sort(key=lambda x: x[1], reverse=True)
        
        return phrase_scores[:top_k]

# 글로벌 인스턴스
korean_text_processor = KoreanTextProcessor()

# 편의 함수들
def clean_korean_text(text: str) -> ProcessedText:
    """한국어 텍스트 정리"""
    return korean_text_processor.clean_financial_text(text)

def extract_financial_entities(text: str) -> Dict[str, List[str]]:
    """금융 엔티티 추출"""
    return korean_text_processor.extract_entities(text)

def preprocess_korean_for_ai(text: str) -> str:
    """AI 분석을 위한 한국어 전처리"""
    return korean_text_processor.preprocess_for_embedding(text)

def analyze_korean_complexity(text: str) -> Dict[str, Any]:
    """한국어 텍스트 복잡도 분석"""
    return korean_text_processor.analyze_text_complexity(text)

def extract_korean_keywords(text: str, top_k: int = 10) -> List[Tuple[str, float]]:
    """한국어 핵심 키워드 추출"""
    return korean_text_processor.extract_key_phrases(text, top_k)

# 사용 예시
if __name__ == "__main__":
    # 테스트 텍스트
    sample_text = """
    삼성전자(005930)가 2024년 1분기 실적을 발표했습니다. 
    매출액은 60조원으로 전년대비 15% 증가했으며, 영업이익은 8조5천억원을 기록했습니다.
    반도체 사업부문의 호조가 전체 실적을 견인했다고 분석됩니다. 📈
    김철수 기자 (서울=연합뉴스) 2024년 4월 30일 발표
    """
    
    print("=== 한국어 텍스트 처리 예시 ===")
    
    # 1. 텍스트 정리
    cleaned = clean_korean_text(sample_text)
    print(f"원본: {cleaned.original[:100]}...")
    print(f"정리됨: {cleaned.processed[:100]}...")
    print(f"신뢰도: {cleaned.confidence_score:.2f}")
    
    # 2. 엔티티 추출
    entities = extract_financial_entities(sample_text)
    print(f"\n추출된 엔티티:")
    for entity_type, values in entities.items():
        if values:
            print(f"  {entity_type}: {values}")
    
    # 3. 복잡도 분석
    complexity = analyze_korean_complexity(sample_text)
    print(f"\n복잡도: {complexity['complexity']} (점수: {complexity['score']:.2f})")
    
    # 4. 핵심 키워드
    keywords = extract_korean_keywords(sample_text, top_k=5)
    print(f"\n핵심 키워드:")
    for keyword, score in keywords:
        print(f"  {keyword}: {score:.2f}")
    
    # 5. AI 전처리
    ai_ready = preprocess_korean_for_ai(sample_text)
    print(f"\nAI 처리용: {ai_ready[:100]}...")