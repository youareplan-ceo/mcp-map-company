"""
미국 시장 AI 투자 시그널 생성기
주식 데이터 + 뉴스 감성분석 + 기술적분석을 종합하여 투자 시그널 생성
"""

import asyncio
import openai
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import json
from dataclasses import dataclass, asdict

from .us_stock_data import USStockDataService, USStockQuote
from .us_news_analyzer import USNewsAnalyzer, USNewsItem
from .currency_exchange import CurrencyExchangeService
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.openai_optimizer import get_openai_optimizer

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class InvestmentSignal:
    """투자 시그널 데이터 클래스"""
    id: str
    symbol: str
    company_name: str
    signal_type: str  # BUY, SELL, HOLD
    confidence: float  # 0.0 ~ 1.0
    strength: str  # HIGH, MEDIUM, LOW
    target_price: Optional[float]
    current_price: float
    expected_return: Optional[float]  # 예상 수익률 (%)
    risk_level: str  # HIGH, MEDIUM, LOW
    
    # 분석 근거
    technical_score: float  # 기술적 분석 점수 (-1.0 ~ 1.0)
    fundamental_score: float  # 펀더멘털 점수 (-1.0 ~ 1.0)
    sentiment_score: float  # 뉴스 감성 점수 (-1.0 ~ 1.0)
    
    reasoning: str  # AI 분석 근거
    news_summary: str  # 관련 뉴스 요약
    technical_indicators: Dict[str, Any]  # 기술적 지표들
    
    # 메타데이터
    created_at: str
    expires_at: str
    market_state: str
    currency: str = "USD"
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return asdict(self)

class USAISignalGenerator:
    """미국 시장 AI 시그널 생성기"""
    
    def __init__(self, openai_api_key: str):
        self.openai_client = openai.AsyncOpenAI(api_key=openai_api_key)
        self.stock_service = USStockDataService()
        self.currency_service = CurrencyExchangeService()
        # AI 시그널 생성용 최적화기 (15분 캐시 TTL)
        self.openai_optimizer = get_openai_optimizer(daily_budget=5.0)
        # AI 시그널용 캐시 TTL을 15분으로 설정
        self.openai_optimizer.cache_ttl = 900  # 15분 = 900초
        
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.news_analyzer = USNewsAnalyzer(self.openai_client.api_key)
        await self.news_analyzer.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if hasattr(self, 'news_analyzer'):
            await self.news_analyzer.__aexit__(exc_type, exc_val, exc_tb)

    def calculate_technical_score(self, stock: USStockQuote) -> tuple[float, Dict[str, Any]]:
        """기술적 분석 점수 계산"""
        try:
            indicators = {}
            
            # RSI 계산 (단순화 버전)
            price_change_pct = stock.change_percent
            if abs(price_change_pct) > 5:
                rsi = 70 if price_change_pct > 0 else 30
            else:
                rsi = 50 + (price_change_pct * 2)
            indicators["rsi"] = max(0, min(100, rsi))
            
            # 이동평균 추세 (단순 계산)
            price_position = (stock.current_price - stock.day_low) / (stock.day_high - stock.day_low) if stock.day_high > stock.day_low else 0.5
            indicators["price_position"] = price_position
            
            # 거래량 분석
            volume_ratio = stock.volume / stock.avg_volume if stock.avg_volume else 1.0
            indicators["volume_ratio"] = volume_ratio
            
            # 기술적 점수 계산 (-1.0 ~ 1.0)
            technical_score = 0.0
            
            # RSI 기반 점수
            if indicators["rsi"] < 30:  # 과매도
                technical_score += 0.3
            elif indicators["rsi"] > 70:  # 과매수
                technical_score -= 0.3
                
            # 가격 포지션 점수
            technical_score += (price_position - 0.5) * 0.4
            
            # 거래량 점수
            if volume_ratio > 1.5:  # 높은 거래량
                technical_score += 0.2 if price_change_pct > 0 else -0.2
            
            # 일간 변동성 점수
            daily_volatility = abs(price_change_pct) / 100
            if daily_volatility < 0.02:  # 안정적
                technical_score += 0.1
            elif daily_volatility > 0.05:  # 높은 변동성
                technical_score -= 0.1
                
            technical_score = max(-1.0, min(1.0, technical_score))
            
            return technical_score, indicators
            
        except Exception as e:
            logger.error(f"기술적 분석 오류: {e}")
            return 0.0, {}

    def calculate_fundamental_score(self, stock: USStockQuote) -> float:
        """펀더멘털 분석 점수 계산 (단순화)"""
        try:
            score = 0.0
            
            # P/E 비율 분석
            if stock.pe_ratio:
                if stock.pe_ratio < 15:  # 저평가
                    score += 0.3
                elif stock.pe_ratio > 30:  # 고평가
                    score -= 0.3
                    
            # 시가총액 분석 (대형주 선호)
            if stock.market_cap:
                if stock.market_cap > 100_000_000_000:  # 1000억 달러 이상 대형주
                    score += 0.2
                elif stock.market_cap < 10_000_000_000:  # 100억 달러 미만 소형주
                    score -= 0.1
                    
            # 배당수익률
            if stock.dividend_yield and stock.dividend_yield > 2:
                score += 0.2
                
            return max(-1.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"펀더멘털 분석 오류: {e}")
            return 0.0

    async def generate_ai_analysis(self, stock: USStockQuote, news_items: List[USNewsItem],
                                 technical_score: float, fundamental_score: float,
                                 sentiment_score: float) -> Dict[str, Any]:
        """GPT를 이용한 종합 투자 분석"""
        try:
            # 뉴스 요약
            news_summary = ""
            if news_items:
                news_titles = [news.title for news in news_items[:3]]
                news_summary = " | ".join(news_titles)
            
            prompt = f"""
            다음 미국 주식에 대한 종합 투자 분석을 수행해주세요:
            
            종목: {stock.symbol} ({stock.company_name})
            현재가: ${stock.current_price}
            일간변동: {stock.change_percent:+.2f}%
            거래량: {stock.volume:,}
            시가총액: ${stock.market_cap:,} (if available)
            P/E 비율: {stock.pe_ratio}
            시장상태: {stock.market_state}
            
            분석 점수:
            - 기술적 분석: {technical_score:.2f} (-1~1)
            - 펀더멘털: {fundamental_score:.2f} (-1~1)  
            - 뉴스 감성: {sentiment_score:.2f} (-1~1)
            
            최근 뉴스: {news_summary}
            
            다음 JSON 형식으로 투자 추천을 제공해주세요:
            {{
                "signal_type": "BUY/SELL/HOLD",
                "confidence": 0.0-1.0,
                "strength": "HIGH/MEDIUM/LOW",
                "target_price": 목표가격 (숫자),
                "expected_return": 예상수익률% (숫자),
                "risk_level": "HIGH/MEDIUM/LOW",
                "reasoning": "상세한 분석 근거 (한국어, 200자 이내)",
                "news_impact": "뉴스가 주가에 미치는 영향 분석 (한국어, 100자 이내)"
            }}
            
            미국 주식 시장 특성과 현재 경제 상황을 고려하여 분석해주세요.
            """
            
            # OpenAI 최적화기 사용 (캐시 + 백오프 + 비용 모니터링)
            response = await self.openai_optimizer.optimize_chat_completion(
                self.openai_client,
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # JSON 파싱 시도
            try:
                result = json.loads(result_text)
                return result
            except json.JSONDecodeError:
                logger.warning(f"GPT 응답 JSON 파싱 실패: {result_text}")
                return {
                    "signal_type": "HOLD",
                    "confidence": 0.5,
                    "strength": "MEDIUM", 
                    "target_price": stock.current_price,
                    "expected_return": 0.0,
                    "risk_level": "MEDIUM",
                    "reasoning": "분석 오류로 인한 기본 추천",
                    "news_impact": "분석 불가"
                }
                
        except Exception as e:
            logger.error(f"AI 분석 오류: {e}")
            return {
                "signal_type": "HOLD",
                "confidence": 0.3,
                "strength": "LOW",
                "target_price": stock.current_price,
                "expected_return": 0.0,
                "risk_level": "HIGH",
                "reasoning": f"분석 중 오류 발생: {str(e)}",
                "news_impact": "분석 불가"
            }

    async def generate_signal(self, symbol: str) -> Optional[InvestmentSignal]:
        """특정 종목에 대한 투자 시그널 생성"""
        try:
            logger.info(f"{symbol} 투자 시그널 생성 시작")
            
            # 1. 주식 데이터 조회
            stock = await self.stock_service.get_stock_info(symbol)
            if not stock:
                logger.error(f"{symbol} 주식 데이터 조회 실패")
                return None
            
            # 2. 관련 뉴스 조회
            news_items = await self.news_analyzer.get_symbol_news(symbol, limit=5)
            
            # 3. 기술적 분석
            technical_score, technical_indicators = self.calculate_technical_score(stock)
            
            # 4. 펀더멘털 분석
            fundamental_score = self.calculate_fundamental_score(stock)
            
            # 5. 뉴스 감성 분석
            sentiment_score = 0.0
            if news_items:
                sentiment_scores = [news.sentiment_score * news.impact_score for news in news_items]
                sentiment_score = sum(sentiment_scores) / len(sentiment_scores)
            
            # 6. AI 종합 분석
            ai_analysis = await self.generate_ai_analysis(
                stock, news_items, technical_score, fundamental_score, sentiment_score
            )
            
            # 7. 뉴스 요약
            news_summary = ""
            if news_items:
                top_news = sorted(news_items, key=lambda x: x.impact_score, reverse=True)[:2]
                summaries = [f"• {news.title[:50]}..." for news in top_news]
                news_summary = "\n".join(summaries)
            
            # 8. 시그널 ID 생성
            import hashlib
            signal_id = hashlib.md5(f"{symbol}{datetime.now().isoformat()}".encode()).hexdigest()
            
            # 9. 만료 시간 설정 (24시간 후)
            expires_at = (datetime.now() + timedelta(days=1)).isoformat()
            
            # 10. 투자 시그널 생성
            signal = InvestmentSignal(
                id=signal_id,
                symbol=symbol,
                company_name=stock.company_name,
                signal_type=ai_analysis["signal_type"],
                confidence=float(ai_analysis["confidence"]),
                strength=ai_analysis["strength"],
                target_price=float(ai_analysis["target_price"]) if ai_analysis["target_price"] else None,
                current_price=stock.current_price,
                expected_return=float(ai_analysis["expected_return"]) if ai_analysis["expected_return"] else None,
                risk_level=ai_analysis["risk_level"],
                technical_score=technical_score,
                fundamental_score=fundamental_score,
                sentiment_score=sentiment_score,
                reasoning=ai_analysis["reasoning"],
                news_summary=news_summary or "관련 뉴스 없음",
                technical_indicators=technical_indicators,
                created_at=datetime.now().isoformat(),
                expires_at=expires_at,
                market_state=stock.market_state
            )
            
            logger.info(f"{symbol} 시그널 생성 완료: {signal.signal_type} ({signal.confidence:.2f})")
            return signal
            
        except Exception as e:
            logger.error(f"{symbol} 시그널 생성 실패: {e}")
            return None

    async def generate_multiple_signals(self, symbols: List[str]) -> List[InvestmentSignal]:
        """여러 종목에 대한 시그널 동시 생성"""
        tasks = [self.generate_signal(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        signals = []
        for result in results:
            if isinstance(result, InvestmentSignal):
                signals.append(result)
            elif isinstance(result, Exception):
                logger.error(f"시그널 생성 오류: {result}")
        
        # 신뢰도 순으로 정렬
        signals.sort(key=lambda x: x.confidence, reverse=True)
        return signals

    async def get_top_signals(self, limit: int = 5) -> List[InvestmentSignal]:
        """주요 종목 TOP 시그널"""
        major_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "NFLX"]
        
        all_signals = await self.generate_multiple_signals(major_symbols)
        
        # 신뢰도와 강도 기준으로 필터링
        high_quality_signals = [
            signal for signal in all_signals 
            if signal.confidence >= 0.6 and signal.strength in ["HIGH", "MEDIUM"]
        ]
        
        return high_quality_signals[:limit]

# 테스트 함수
async def test_signal_generator():
    """AI 시그널 생성기 테스트"""
    import os
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("OPENAI_API_KEY 환경변수가 필요합니다.")
        return
    
    async with USAISignalGenerator(api_key) as generator:
        print("=== 미국 AI 투자 시그널 생성기 테스트 ===")
        
        # 1. AAPL 시그널 생성
        print("\n1. AAPL 투자 시그널:")
        aapl_signal = await generator.generate_signal("AAPL")
        if aapl_signal:
            print(json.dumps(aapl_signal.to_dict(), indent=2, ensure_ascii=False))
        
        # 2. TOP 시그널들
        print("\n2. TOP 투자 시그널들:")
        top_signals = await generator.get_top_signals(3)
        
        for i, signal in enumerate(top_signals, 1):
            print(f"\n[{i}] {signal.symbol} ({signal.company_name})")
            print(f"시그널: {signal.signal_type} | 신뢰도: {signal.confidence:.2f} | 강도: {signal.strength}")
            print(f"현재가: ${signal.current_price} | 목표가: ${signal.target_price}")
            print(f"예상수익: {signal.expected_return:+.1f}% | 위험도: {signal.risk_level}")
            print(f"분석: {signal.reasoning}")

if __name__ == "__main__":
    asyncio.run(test_signal_generator())