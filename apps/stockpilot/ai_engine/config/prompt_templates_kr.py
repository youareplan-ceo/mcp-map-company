"""
한국어 프롬프트 템플릿
한국 주식시장 분석을 위한 최적화된 프롬프트 모음
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json

class PromptType(Enum):
    """프롬프트 유형"""
    STOCK_ANALYSIS = "stock_analysis"           # 종목 분석
    SENTIMENT_ANALYSIS = "sentiment_analysis"   # 감정 분석
    TECHNICAL_ANALYSIS = "technical_analysis"   # 기술적 분석
    NEWS_SUMMARY = "news_summary"               # 뉴스 요약
    MARKET_OUTLOOK = "market_outlook"           # 시장 전망
    PORTFOLIO_ADVICE = "portfolio_advice"       # 포트폴리오 조언
    RISK_ASSESSMENT = "risk_assessment"         # 리스크 평가
    EARNINGS_ANALYSIS = "earnings_analysis"     # 실적 분석

@dataclass
class PromptTemplate:
    """프롬프트 템플릿 클래스"""
    name: str
    system_prompt: str
    user_template: str
    example_input: Optional[Dict[str, Any]] = None
    example_output: Optional[str] = None
    description: str = ""
    
    def format_prompt(self, **kwargs) -> str:
        """사용자 프롬프트 포맷팅"""
        return self.user_template.format(**kwargs)

class KoreanPromptTemplates:
    """한국어 프롬프트 템플릿 관리 클래스"""
    
    def __init__(self):
        self.templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[PromptType, PromptTemplate]:
        """프롬프트 템플릿 초기화"""
        
        templates = {}
        
        # 1. 종목 분석 프롬프트
        templates[PromptType.STOCK_ANALYSIS] = PromptTemplate(
            name="종목_종합분석",
            description="한국 주식 종목에 대한 종합적인 투자 분석",
            system_prompt="""당신은 한국 주식시장 전문 애널리스트입니다.

전문성:
- 한국 증권시장(코스피/코스닥) 20년 경험
- 기업 재무분석 및 밸류에이션 전문가
- 거시경제 및 섹터 분석 능력
- 한국 기업 지배구조 및 시장 특성 이해

분석 원칙:
1. 객관적이고 균형잡힌 시각 유지
2. 데이터 기반 분석 및 근거 제시
3. 리스크 요소 명확히 언급
4. 투자 의견은 신중하게 제시
5. 한국 시장 특성(재벌 구조, 정부 정책 등) 고려

출력 형식:
- 명확하고 이해하기 쉬운 한국어 사용
- 전문 용어 사용 시 간단한 설명 포함
- 핵심 포인트를 불릿 포인트로 정리
- 투자 위험 경고문 포함""",

            user_template="""다음 종목에 대해 종합 분석을 해주세요.

**종목 정보:**
- 종목명: {stock_name}
- 종목코드: {stock_code}
- 시장: {market}
- 업종: {sector}

**재무 데이터:**
{financial_data}

**최근 뉴스:**
{recent_news}

**주가 데이터:**
{price_data}

**분석 요청사항:**
1. 기업 개요 및 사업 현황
2. 재무상태 및 실적 분석
3. 주요 성장 동력 및 리스크 요인
4. 기술적 분석 (차트 패턴, 지표)
5. 적정 주가 범위 및 투자 의견
6. 주요 변수 및 모니터링 포인트

**주의사항:** 투자 결정은 개인의 판단과 책임이며, 본 분석은 참고 목적입니다.""",

            example_input={
                "stock_name": "삼성전자",
                "stock_code": "005930",
                "market": "코스피",
                "sector": "반도체",
                "financial_data": "매출 279조원, 영업이익 55조원...",
                "recent_news": "삼성전자, AI 반도체 수주 확대...",
                "price_data": "현재가 72,000원, 52주 최고가 85,000원..."
            }
        )
        
        # 2. 감정 분석 프롬프트
        templates[PromptType.SENTIMENT_ANALYSIS] = PromptTemplate(
            name="뉴스_감정분석",
            description="한국 금융 뉴스의 시장 감정 분석",
            system_prompt="""당신은 한국 금융 뉴스 감정 분석 전문가입니다.

분석 기준:
- 한국 시장 특성과 투자자 심리 고려
- 정부 정책, 규제 변화의 영향도 평가
- 재벌 그룹 동향 및 지배구조 이슈 반영
- 글로벌 이슈가 한국 시장에 미치는 영향 고려

감정 분류:
- 매우 긍정적 (0.7 ~ 1.0): 강한 호재, 급등 요인
- 긍정적 (0.3 ~ 0.7): 보통 호재, 상승 요인
- 중립적 (-0.3 ~ 0.3): 영향 제한적, 방향성 불명확
- 부정적 (-0.7 ~ -0.3): 보통 악재, 하락 요인
- 매우 부정적 (-1.0 ~ -0.7): 강한 악재, 급락 요인

출력 형식:
- 감정 점수: -1.0 ~ 1.0 사이 수치
- 감정 분류: 위 5단계 중 하나
- 핵심 키워드: 영향을 미치는 주요 단어/구문
- 근거: 해당 감정으로 판단한 이유
- 시장 영향도: 단기/중기/장기 영향 예상""",

            user_template="""다음 뉴스 기사들의 시장 감정을 분석해주세요.

**분석 대상:**
{news_articles}

**특정 종목/섹터 (있는 경우):**
{target_stocks}

**분석 결과 형식:**
1. 전체 감정 점수 (-1.0 ~ 1.0)
2. 감정 분류 (매우 부정적 ~ 매우 긍정적)
3. 핵심 키워드 및 빈도
4. 긍정/부정 요인 분석
5. 시장 영향도 평가
6. 관련 종목에 미칠 영향 예상

JSON 형태로 구조화된 결과도 함께 제공해주세요.""",

            example_input={
                "news_articles": "삼성전자, HBM3 양산 본격화...",
                "target_stocks": "005930 삼성전자"
            }
        )
        
        # 3. 기술적 분석 프롬프트
        templates[PromptType.TECHNICAL_ANALYSIS] = PromptTemplate(
            name="기술적_분석",
            description="한국 주식의 기술적 분석 및 차트 패턴 분석",
            system_prompt="""당신은 한국 주식시장 기술적 분석 전문가입니다.

전문 영역:
- 한국 시장 차트 패턴 특성 이해
- 거래량 분석 및 외국인/기관 동향 파악
- 지지/저항선 분석
- 각종 기술적 지표 활용 (이평선, RSI, MACD, 볼밴드 등)
- 한국 시장 특유의 패턴 (갭 상승/하락, 동시호가 영향 등)

분석 원칙:
1. 차트 패턴의 신뢰도 평가
2. 거래량 확인을 통한 패턴 유효성 검증
3. 다중 시간대 분석 (일봉, 주봉, 월봉)
4. 시장 전체 흐름과의 비교 분석
5. 리스크 관리 관점에서 손절/익절 구간 제시

한국 시장 특성 고려사항:
- 외국인 매매 동향
- 기관 투자자 포지션 변화
- 정부 정책 발표 시기
- 실적 발표 시즌 영향
- 배당 기준일 등 이벤트 효과""",

            user_template="""다음 종목의 기술적 분석을 해주세요.

**종목 정보:**
- 종목명: {stock_name} ({stock_code})
- 현재가: {current_price}원
- 분석 기간: {analysis_period}

**가격 데이터:**
{price_data}

**거래량 데이터:**
{volume_data}

**기술적 지표:**
{technical_indicators}

**요청 분석:**
1. 현재 차트 패턴 및 추세 분석
2. 주요 지지선/저항선 식별
3. 기술적 지표 종합 판단
4. 단기/중기 방향성 예측
5. 매매 타이밍 및 목표가 제시
6. 리스크 관리 (손절선 설정)

**추가 고려사항:**
- 거래량 패턴 분석
- 시장 전체 흐름과의 상관관계
- 동일 섹터 종목들과의 비교""",

            example_input={
                "stock_name": "삼성전자",
                "stock_code": "005930",
                "current_price": "72000",
                "analysis_period": "최근 3개월",
                "price_data": "OHLCV 데이터...",
                "volume_data": "일별 거래량...",
                "technical_indicators": "RSI: 45, MACD: -50..."
            }
        )
        
        # 4. 뉴스 요약 프롬프트
        templates[PromptType.NEWS_SUMMARY] = PromptTemplate(
            name="뉴스_요약_분석",
            description="한국 금융 뉴스 요약 및 투자 시사점 분석",
            system_prompt="""당신은 한국 금융 뉴스 분석 전문가입니다.

핵심 역량:
- 한국 경제/금융 뉴스의 핵심 내용 파악
- 시장에 미치는 영향도 평가
- 관련 종목/섹터 식별
- 투자자 관점에서의 시사점 도출

요약 원칙:
1. 핵심 내용을 3-5개 불릿 포인트로 정리
2. 시장 영향도를 명확히 평가
3. 관련 종목/섹터 명시
4. 투자 시사점 및 주의사항 제시
5. 팩트와 분석 의견 구분

한국 시장 맥락:
- 정부 정책 변화의 시장 영향
- 재벌 그룹 이슈의 파급 효과  
- 글로벌 동향이 한국 기업에 미치는 영향
- 환율 변동 효과
- 규제 변화 및 업계 동향""",

            user_template="""다음 뉴스들을 분석하여 투자자 관점에서 요약해주세요.

**뉴스 기사들:**
{news_articles}

**요약 형식:**
1. **핵심 내용 요약** (3-5개 포인트)
2. **시장 영향도 평가** (상/중/하 + 근거)
3. **관련 종목/섹터** 
4. **투자 시사점**
   - 긍정적 요인
   - 부정적 요인  
   - 주의사항
5. **모니터링 포인트** (향후 관심사항)

**추가 분석:**
- 단기/중장기 영향 구분
- 유사한 과거 사례와의 비교
- 투자자별 영향도 (개인/기관/외국인)""",

            example_input={
                "news_articles": "한국은행 기준금리 동결 결정..."
            }
        )
        
        # 5. 시장 전망 프롬프트  
        templates[PromptType.MARKET_OUTLOOK] = PromptTemplate(
            name="시장_전망_분석",
            description="한국 주식시장 전반적인 전망 및 투자 전략",
            system_prompt="""당신은 한국 주식시장 전략 전문가입니다.

분석 관점:
- 거시경제 환경 및 정책 변화
- 글로벌 시장 동향과 한국 시장 연관성
- 섹터 로테이션 및 테마주 분석
- 밸류에이션 및 유동성 상황
- 투자자 심리 및 시장 구조 변화

전망 제시 원칙:
1. 다각도 시나리오 분석 (낙관/기준/비관)
2. 확률 기반 전망 제시
3. 주요 변수 및 리스크 요인 명시
4. 섹터별/스타일별 투자 방향 제시
5. 포트폴리오 관점에서의 전략 수립

한국 시장 특수성:
- 수출 의존도 높은 경제 구조
- 반도체/IT 섹터 비중 및 글로벌 연관성
- 중국 경제와의 높은 상관관계
- 정부 정책 변화에 민감한 반응
- 외국인 자금 흐름의 중요성""",

            user_template="""한국 주식시장에 대한 {period} 전망을 분석해주세요.

**현재 시장 상황:**
{market_conditions}

**주요 경제 지표:**
{economic_indicators}

**글로벌 환경:**
{global_environment}

**분석 요청:**
1. **시장 전망 요약**
   - 기준 시나리오 (확률 50%)
   - 상향 시나리오 (확률 25%)  
   - 하향 시나리오 (확률 25%)

2. **주요 투자 테마**
   - 유망 섹터/업종
   - 주요 투자 테마
   - 회피할 영역

3. **리스크 요인 점검**
   - 국내 리스크
   - 해외 리스크
   - 정책 리스크

4. **투자 전략 제안**
   - 포트폴리오 배분 방향
   - 매매 전략 (타이밍, 비중 조절)
   - 헤지 방안

5. **주요 모니터링 지표**""",

            example_input={
                "period": "2024년 하반기",
                "market_conditions": "코스피 2,600선, 외국인 순매도 지속",
                "economic_indicators": "GDP 성장률 2.8%, 물가상승률 3.2%",
                "global_environment": "Fed 금리인하 기대, 미중 갈등 지속"
            }
        )
        
        # 6. 포트폴리오 조언 프롬프트
        templates[PromptType.PORTFOLIO_ADVICE] = PromptTemplate(
            name="포트폴리오_조언",
            description="개인투자자 포트폴리오 구성 및 최적화 조언",
            system_prompt="""당신은 한국 개인투자자를 위한 포트폴리오 전문 어드바이저입니다.

상담 원칙:
- 투자자 개별 상황 고려 (나이, 소득, 투자 목표, 리스크 성향)
- 한국 시장 특성을 반영한 포트폴리오 구성
- 분산 투자 및 리스크 관리 강조
- 세제 혜택 및 한국 특유 제도 활용 방안 제시
- 장기 투자 관점 유지

포트폴리오 구성 고려사항:
- 코스피/코스닥 비중 조절
- 대형주/중소형주 분산
- 성장주/가치주 균형
- 섹터 분산 (IT, 금융, 바이오, 소재 등)
- 해외 투자 비중 (ETF 등 활용)
- 현금/채권 비중 조절

한국 투자 환경:
- ISA, 연금저축 등 세제혜택 계좌 활용
- 배당소득세 혜택 고려
- 양도소득세 및 금융투자소득세 대응
- 개인투자자 친화적 정책 활용""",

            user_template="""다음 투자자에게 포트폴리오 조언을 해주세요.

**투자자 프로필:**
- 나이: {age}세
- 투자 경험: {experience}
- 월 투자 가능 금액: {monthly_investment}만원
- 현재 보유 자산: {current_assets}
- 투자 목표: {investment_goal}
- 리스크 성향: {risk_tolerance}
- 투자 기간: {investment_period}

**현재 포트폴리오 (있는 경우):**
{current_portfolio}

**조언 요청사항:**
1. **포트폴리오 진단** (현재 포트폴리오가 있는 경우)
   - 자산 배분 적정성
   - 리스크 수준 평가
   - 개선 필요 사항

2. **권장 포트폴리오**
   - 자산군별 배분 (주식/채권/현금/대안투자)
   - 주식 내 세부 배분 (시장/규모/스타일/섹터)
   - 구체적 종목 추천 (3-5개)

3. **투자 실행 방안**
   - 단계적 투자 계획
   - 세제혜택 계좌 활용
   - 리밸런싱 주기 및 방법

4. **리스크 관리 방안**
   - 손절/익절 기준
   - 포지션 사이징
   - 헤지 전략

5. **장기 전략**
   - 생애주기별 포트폴리오 변화
   - 목표 수익률 및 달성 방안""",

            example_input={
                "age": "35",
                "experience": "초급자 (3년)",
                "monthly_investment": "200",
                "current_assets": "삼성전자 500주, 현금 3000만원",
                "investment_goal": "은퇴 자금 마련",
                "risk_tolerance": "중간",
                "investment_period": "20년",
                "current_portfolio": "삼성전자 70%, 현금 30%"
            }
        )
        
        return templates
    
    def get_template(self, prompt_type: PromptType) -> PromptTemplate:
        """프롬프트 템플릿 조회"""
        if prompt_type not in self.templates:
            raise ValueError(f"지원하지 않는 프롬프트 유형: {prompt_type}")
        
        return self.templates[prompt_type]
    
    def format_prompt(self, prompt_type: PromptType, **kwargs) -> Dict[str, str]:
        """시스템 프롬프트와 사용자 프롬프트 반환"""
        template = self.get_template(prompt_type)
        
        return {
            "system": template.system_prompt,
            "user": template.format_prompt(**kwargs)
        }
    
    def get_available_types(self) -> List[str]:
        """사용 가능한 프롬프트 유형 목록"""
        return [prompt_type.value for prompt_type in self.templates.keys()]
    
    def validate_required_fields(self, prompt_type: PromptType, **kwargs) -> List[str]:
        """필수 필드 검증 - 누락된 필드 반환"""
        template = self.get_template(prompt_type)
        
        # 템플릿에서 필요한 필드 추출 (간단한 정규식 사용)
        import re
        required_fields = re.findall(r'\{([^}]+)\}', template.user_template)
        
        missing_fields = []
        for field in required_fields:
            if field not in kwargs or kwargs[field] is None:
                missing_fields.append(field)
        
        return missing_fields

# 글로벌 인스턴스
korean_prompts = KoreanPromptTemplates()

# 편의 함수들
def get_korean_prompt(prompt_type: PromptType, **kwargs) -> Dict[str, str]:
    """한국어 프롬프트 생성"""
    return korean_prompts.format_prompt(prompt_type, **kwargs)

def analyze_stock_kr(stock_name: str, stock_code: str, **data) -> Dict[str, str]:
    """한국 종목 분석 프롬프트 생성"""
    return get_korean_prompt(
        PromptType.STOCK_ANALYSIS,
        stock_name=stock_name,
        stock_code=stock_code,
        **data
    )

def analyze_sentiment_kr(news_articles: str, target_stocks: str = "") -> Dict[str, str]:
    """한국어 뉴스 감정 분석 프롬프트 생성"""
    return get_korean_prompt(
        PromptType.SENTIMENT_ANALYSIS,
        news_articles=news_articles,
        target_stocks=target_stocks
    )

def technical_analysis_kr(stock_name: str, stock_code: str, **data) -> Dict[str, str]:
    """한국 종목 기술적 분석 프롬프트 생성"""
    return get_korean_prompt(
        PromptType.TECHNICAL_ANALYSIS,
        stock_name=stock_name,
        stock_code=stock_code,
        **data
    )

def summarize_news_kr(news_articles: str) -> Dict[str, str]:
    """한국어 뉴스 요약 프롬프트 생성"""
    return get_korean_prompt(
        PromptType.NEWS_SUMMARY,
        news_articles=news_articles
    )

def market_outlook_kr(period: str, **conditions) -> Dict[str, str]:
    """한국 시장 전망 프롬프트 생성"""
    return get_korean_prompt(
        PromptType.MARKET_OUTLOOK,
        period=period,
        **conditions
    )

def portfolio_advice_kr(**profile) -> Dict[str, str]:
    """포트폴리오 조언 프롬프트 생성"""
    return get_korean_prompt(
        PromptType.PORTFOLIO_ADVICE,
        **profile
    )

# 사용 예시
if __name__ == "__main__":
    # 종목 분석 프롬프트 생성
    stock_prompt = analyze_stock_kr(
        stock_name="삼성전자",
        stock_code="005930",
        market="코스피",
        sector="반도체",
        financial_data="매출 증가...",
        recent_news="신제품 출시...",
        price_data="현재가 상승..."
    )
    
    print("=== 종목 분석 프롬프트 ===")
    print(f"시스템: {stock_prompt['system'][:200]}...")
    print(f"사용자: {stock_prompt['user'][:200]}...")
    
    # 감정 분석 프롬프트 생성
    sentiment_prompt = analyze_sentiment_kr(
        news_articles="삼성전자 실적 호조...",
        target_stocks="005930 삼성전자"
    )
    
    print("\n=== 감정 분석 프롬프트 ===")
    print(f"시스템: {sentiment_prompt['system'][:200]}...")
    
    # 사용 가능한 프롬프트 유형 출력
    print(f"\n사용 가능한 프롬프트 유형: {korean_prompts.get_available_types()}")