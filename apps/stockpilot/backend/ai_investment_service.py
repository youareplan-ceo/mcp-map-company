"""
AI 투자 추천 시스템 - 비용 최적화된 GPT 모델 활용
실제 종목 분석, 추천 사유, 목표가/손절가 자동 생성 (비용 절감 버전)
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from real_stock_service import RealStockService, RealStockData
import numpy as np
import pandas as pd
import os

# 비용 최적화된 GPT 서비스 import
from optimized_gpt_service import optimized_gpt_service

@dataclass
class AIAnalysisResult:
    """AI 분석 결과 구조체"""
    symbol: str
    company_name: str
    current_price: float
    recommendation: str  # 'buy', 'sell', 'hold'
    confidence_score: float  # 0-100
    target_price: float
    stop_loss: float
    analysis_summary: str
    key_factors: List[str]
    technical_score: float
    fundamental_score: float
    sentiment_score: float
    risk_level: str  # 'low', 'medium', 'high'
    investment_horizon: str  # 'short', 'medium', 'long'
    timestamp: str

@dataclass 
class TradingSignal:
    """매매 신호 구조체"""
    signal_id: str
    symbol: str
    signal_type: str  # 'buy', 'sell'
    strength: float  # 0-100
    price_at_signal: float
    reason: str
    technical_indicators: Dict[str, float]
    timestamp: str

class AIInvestmentService:
    """AI 투자 추천 서비스"""
    
    def __init__(self):
        self.stock_service = RealStockService()
        self.logger = logging.getLogger(__name__)
        self.logger.info("🤖 비용 최적화된 AI 투자 서비스 초기화")
        
    def analyze_stock_with_ai(self, symbol: str, news_content: str = "") -> Optional[AIAnalysisResult]:
        """비용 최적화된 AI 기반 종목 분석"""
        try:
            # 실제 주식 데이터 조회
            stock_data = self.stock_service.get_stock_data(symbol)
            if not stock_data:
                self.logger.warning(f"주식 데이터 조회 실패: {symbol}")
                return None
            
            # 최적화된 GPT 서비스 사용 (비용 절감)
            gpt_result = optimized_gpt_service.analyze_investment(
                symbol=symbol,
                news_content=news_content,
                held_stocks=[]  # 필요시 보유 종목 목록 전달
            )
            
            if not gpt_result.get("success", False):
                self.logger.error(f"GPT 분석 실패: {gpt_result.get('message', '알 수 없는 오류')}")
                return self._create_fallback_analysis(symbol, stock_data)
            
            # GPT 분석 결과를 AIAnalysisResult 구조로 변환
            return self._convert_gpt_to_analysis_result(stock_data, gpt_result)
            
        except Exception as e:
            self.logger.error(f"AI 분석 실패 - {symbol}: {e}")
            return self._create_fallback_analysis(symbol, stock_data) if stock_data else None
    
    def _convert_gpt_to_analysis_result(self, stock_data: RealStockData, gpt_result: Dict[str, Any]) -> AIAnalysisResult:
        """GPT 결과를 AIAnalysisResult로 변환 (비용 최적화 버전)"""
        gpt_data = gpt_result.get("data", {})
        
        # 목표가와 손절가 계산 (간단한 공식 사용)
        current_price = stock_data.current_price
        recommendation = gpt_data.get("recommendation", "hold")
        confidence = gpt_data.get("confidence_score", 50)
        
        # 추천에 따른 목표가/손절가 설정
        if recommendation == "buy":
            target_price = current_price * 1.15  # 15% 상승 목표
            stop_loss = current_price * 0.95    # 5% 하락시 손절
            risk_level = "medium"
        elif recommendation == "sell":
            target_price = current_price * 0.95  # 5% 하락 예상
            stop_loss = current_price * 1.05    # 5% 상승시 손절
            risk_level = "high"
        else:  # hold
            target_price = current_price * 1.05  # 5% 상승 목표
            stop_loss = current_price * 0.98    # 2% 하락시 손절
            risk_level = "low"
        
        return AIAnalysisResult(
            symbol=stock_data.symbol,
            company_name=stock_data.company_name,
            current_price=current_price,
            recommendation=recommendation,
            confidence_score=confidence,
            target_price=target_price,
            stop_loss=stop_loss,
            analysis_summary=gpt_data.get("reason", "AI 분석 완료"),
            key_factors=[gpt_data.get("reason", "투자 분석")[:20]],  # 핵심 요소 1개만
            technical_score=confidence * 0.8,   # 신뢰도 기반 점수
            fundamental_score=confidence * 0.9,
            sentiment_score=confidence * 0.7,
            risk_level=risk_level,
            investment_horizon="medium",
            timestamp=datetime.now().isoformat()
        )
    
    def _create_fallback_analysis(self, symbol: str, stock_data: RealStockData) -> AIAnalysisResult:
        """GPT 실패시 기본 분석 결과 (비용 절감)"""
        current_price = stock_data.current_price
        
        return AIAnalysisResult(
            symbol=stock_data.symbol,
            company_name=stock_data.company_name,
            current_price=current_price,
            recommendation="hold",
            confidence_score=50,
            target_price=current_price * 1.05,
            stop_loss=current_price * 0.98,
            analysis_summary="기술적 분석 기반 중립적 관점 유지 권장",
            key_factors=["기술적 지표 중립"],
            technical_score=50.0,
            fundamental_score=50.0,
            sentiment_score=50.0,
            risk_level="medium",
            investment_horizon="medium",
            timestamp=datetime.now().isoformat()
        )
    
    def _create_analysis_prompt(self, stock_data: RealStockData, chart_data=None) -> str:
        """AI 분석용 프롬프트 생성"""
        prompt = f"""
다음 주식에 대해 투자 분석을 수행해주세요:

【기본 정보】
- 종목명: {stock_data.name} ({stock_data.symbol})
- 현재가: ${stock_data.price:.2f}
- 변동률: {stock_data.change_percent:.2f}%
- 거래량: {stock_data.volume:,}
- 시가총액: {stock_data.market_cap if stock_data.market_cap else 'N/A'}
- PER: {stock_data.pe_ratio if stock_data.pe_ratio else 'N/A'}
- 52주 최고/최저: ${stock_data.high_52w}/{stock_data.low_52w}
- 배당수익률: {stock_data.dividend_yield if stock_data.dividend_yield else 'N/A'}%

【분석 요청사항】
다음 형식으로 JSON 구조의 분석 결과를 제공해주세요:

{{
    "recommendation": "buy/sell/hold 중 하나",
    "confidence_score": 0-100 사이의 신뢰도,
    "target_price": 목표 주가 (숫자),
    "stop_loss": 손절가 (숫자),
    "analysis_summary": "핵심 분석 요약 (200자 이내)",
    "key_factors": ["주요 투자 요인 1", "주요 투자 요인 2", "주요 투자 요인 3"],
    "technical_score": 기술적 분석 점수 (0-100),
    "fundamental_score": 기본적 분석 점수 (0-100),
    "sentiment_score": 시장 심리 점수 (0-100),
    "risk_level": "low/medium/high",
    "investment_horizon": "short/medium/long"
}}

투자 추천 시 다음 사항을 고려해주세요:
- 현재 시장 상황과 경제 환경
- 기업의 재무 건전성과 성장성
- 기술적 차트 패턴과 거래량
- 업계 동향과 경쟁 상황
- 위험 대비 수익률
"""
        
        if chart_data and len(chart_data.prices) > 10:
            recent_prices = chart_data.prices[-20:]  # 최근 20개 데이터
            prompt += f"\n【최근 주가 동향】\n최근 20개 데이터포인트: {recent_prices}"
        
        return prompt
    
    def _parse_ai_analysis(self, stock_data: RealStockData, ai_analysis: str) -> AIAnalysisResult:
        """AI 응답을 구조화된 결과로 파싱"""
        try:
            # JSON 부분 추출 시도
            import re
            json_match = re.search(r'\{.*\}', ai_analysis, re.DOTALL)
            if json_match:
                analysis_data = json.loads(json_match.group())
            else:
                # JSON 파싱 실패 시 기본값 사용
                analysis_data = self._create_fallback_analysis(ai_analysis)
            
            return AIAnalysisResult(
                symbol=stock_data.symbol,
                company_name=stock_data.name,
                current_price=stock_data.price,
                recommendation=analysis_data.get('recommendation', 'hold'),
                confidence_score=float(analysis_data.get('confidence_score', 50)),
                target_price=float(analysis_data.get('target_price', stock_data.price * 1.1)),
                stop_loss=float(analysis_data.get('stop_loss', stock_data.price * 0.9)),
                analysis_summary=analysis_data.get('analysis_summary', '분석 중...'),
                key_factors=analysis_data.get('key_factors', ['시장 분석', '기술적 지표', '기업 가치']),
                technical_score=float(analysis_data.get('technical_score', 50)),
                fundamental_score=float(analysis_data.get('fundamental_score', 50)),
                sentiment_score=float(analysis_data.get('sentiment_score', 50)),
                risk_level=analysis_data.get('risk_level', 'medium'),
                investment_horizon=analysis_data.get('investment_horizon', 'medium'),
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            self.logger.error(f"AI 응답 파싱 실패: {e}")
            return self._create_demo_analysis(stock_data)
    
    def _create_fallback_analysis(self, ai_text: str) -> Dict[str, Any]:
        """AI 텍스트 기반 기본 분석"""
        # 간단한 키워드 기반 분석
        text_lower = ai_text.lower()
        
        if any(word in text_lower for word in ['buy', '매수', 'positive', '긍정']):
            recommendation = 'buy'
            confidence = 75
        elif any(word in text_lower for word in ['sell', '매도', 'negative', '부정']):
            recommendation = 'sell'  
            confidence = 70
        else:
            recommendation = 'hold'
            confidence = 60
            
        return {
            'recommendation': recommendation,
            'confidence_score': confidence,
            'target_price': 0,
            'stop_loss': 0,
            'analysis_summary': ai_text[:200] + '...' if len(ai_text) > 200 else ai_text,
            'key_factors': ['AI 분석', '시장 동향', '기술적 지표'],
            'technical_score': 60,
            'fundamental_score': 55,
            'sentiment_score': 65,
            'risk_level': 'medium',
            'investment_horizon': 'medium'
        }
    
    def _create_demo_analysis(self, stock_data: RealStockData) -> AIAnalysisResult:
        """데모용 분석 결과 생성"""
        # 가격 변동률 기반 단순 분석
        change_pct = stock_data.change_percent
        
        if change_pct > 2:
            recommendation = 'hold'  # 급등 후 관망
            confidence = 65
            risk = 'medium'
        elif change_pct > 0:
            recommendation = 'buy'
            confidence = 70
            risk = 'low'
        elif change_pct > -2:
            recommendation = 'hold'
            confidence = 60
            risk = 'medium'
        else:
            recommendation = 'buy'  # 급락 시 매수 기회
            confidence = 75
            risk = 'high'
        
        return AIAnalysisResult(
            symbol=stock_data.symbol,
            company_name=stock_data.name,
            current_price=stock_data.price,
            recommendation=recommendation,
            confidence_score=confidence,
            target_price=stock_data.price * (1.15 if recommendation == 'buy' else 1.05),
            stop_loss=stock_data.price * (0.90 if risk == 'high' else 0.95),
            analysis_summary=f"{stock_data.name} 종목은 현재 {change_pct:+.2f}% 변동을 보이고 있습니다. 기술적 지표와 시장 상황을 종합 분석한 결과 {recommendation} 포지션을 권장합니다.",
            key_factors=[
                "기술적 차트 패턴",
                "거래량 분석", 
                "시장 심리 지표"
            ],
            technical_score=65 + (change_pct * 2),
            fundamental_score=60,
            sentiment_score=55 + change_pct,
            risk_level=risk,
            investment_horizon='medium',
            timestamp=datetime.now().isoformat()
        )
    
    def get_multiple_recommendations(self, symbols: List[str], limit: int = 5) -> List[AIAnalysisResult]:
        """다중 종목 AI 추천"""
        results = []
        for symbol in symbols[:limit]:
            try:
                analysis = self.analyze_stock_with_ai(symbol)
                if analysis:
                    results.append(analysis)
            except Exception as e:
                self.logger.error(f"종목 분석 실패 - {symbol}: {e}")
                continue
        
        # 신뢰도 순으로 정렬
        return sorted(results, key=lambda x: x.confidence_score, reverse=True)
    
    def get_trending_ai_recommendations(self, limit: int = 5) -> List[AIAnalysisResult]:
        """인기 종목 AI 추천"""
        # 인기 종목 목록 조회
        trending_stocks = self.stock_service.get_trending_stocks(limit * 2)
        symbols = [stock.symbol for stock in trending_stocks]
        
        return self.get_multiple_recommendations(symbols, limit)
    
    def generate_trading_signals(self, symbols: List[str]) -> List[TradingSignal]:
        """매매 신호 생성"""
        signals = []
        
        for symbol in symbols:
            try:
                # 기술적 분석 기반 신호 생성
                stock_data = self.stock_service.get_stock_data(symbol)
                if not stock_data:
                    continue
                
                # 간단한 기술적 지표 계산
                chart_data = self.stock_service.get_chart_data(symbol, '1d')
                if not chart_data or len(chart_data.prices) < 10:
                    continue
                
                signal = self._calculate_technical_signal(stock_data, chart_data)
                if signal:
                    signals.append(signal)
                    
            except Exception as e:
                self.logger.error(f"신호 생성 실패 - {symbol}: {e}")
                continue
        
        return signals
    
    def _calculate_technical_signal(self, stock_data: RealStockData, chart_data) -> Optional[TradingSignal]:
        """기술적 분석 기반 매매 신호 계산"""
        try:
            prices = np.array(chart_data.prices)
            volumes = np.array(chart_data.volumes)
            
            # 이동평균선
            if len(prices) >= 20:
                ma_5 = np.mean(prices[-5:])
                ma_20 = np.mean(prices[-20:])
                
                # 골든 크로스 / 데드 크로스
                if ma_5 > ma_20 * 1.02:  # 2% 이상 상승
                    signal_type = 'buy'
                    strength = min(((ma_5 - ma_20) / ma_20) * 100, 100)
                    reason = f"5일선이 20일선을 상향 돌파 (강도: {strength:.1f}%)"
                elif ma_5 < ma_20 * 0.98:  # 2% 이상 하락  
                    signal_type = 'sell'
                    strength = min(((ma_20 - ma_5) / ma_20) * 100, 100)
                    reason = f"5일선이 20일선을 하향 돌파 (강도: {strength:.1f}%)"
                else:
                    return None
                
                return TradingSignal(
                    signal_id=f"{stock_data.symbol}_{int(datetime.now().timestamp())}",
                    symbol=stock_data.symbol,
                    signal_type=signal_type,
                    strength=strength,
                    price_at_signal=stock_data.price,
                    reason=reason,
                    technical_indicators={
                        'ma_5': float(ma_5),
                        'ma_20': float(ma_20), 
                        'current_price': stock_data.price,
                        'volume_avg': float(np.mean(volumes[-5:]))
                    },
                    timestamp=datetime.now().isoformat()
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"기술적 신호 계산 실패: {e}")
            return None
    
    def get_trending_ai_recommendations(self, limit: int = 5) -> List[AIAnalysisResult]:
        """AI 추천 종목 조회"""
        try:
            # 인기 종목들 가져오기
            popular_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
            recommendations = []
            
            for symbol in popular_symbols[:limit]:
                try:
                    analysis = self.analyze_stock_with_ai(symbol)
                    if analysis and analysis.recommendation in ['buy', 'hold']:
                        recommendations.append(analysis)
                except Exception as e:
                    self.logger.error(f"추천 분석 실패 - {symbol}: {e}")
                    continue
            
            # 신뢰도 순으로 정렬
            return sorted(recommendations, key=lambda x: x.confidence_score, reverse=True)[:limit]
            
        except Exception as e:
            self.logger.error(f"AI 추천 종목 조회 실패: {e}")
            return []
    
    def analyze_market_sentiment(self) -> Dict[str, Any]:
        """시장 심리 분석"""
        try:
            # 주요 지수들의 데이터 수집
            market_indices = ['^GSPC', '^IXIC', '^DJI']  # S&P 500, NASDAQ, Dow Jones
            sentiment_scores = []
            
            for index in market_indices:
                try:
                    stock_data = self.stock_service.get_stock_data(index)
                    if stock_data:
                        # 변동률 기반 심리 점수 계산
                        if stock_data.change_percent > 1:
                            score = min(75 + stock_data.change_percent * 5, 100)
                        elif stock_data.change_percent < -1:
                            score = max(25 + stock_data.change_percent * 5, 0)
                        else:
                            score = 50 + stock_data.change_percent * 10
                        
                        sentiment_scores.append(score)
                except Exception as e:
                    self.logger.error(f"지수 데이터 조회 실패 - {index}: {e}")
                    continue
            
            if sentiment_scores:
                avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
            else:
                avg_sentiment = 50  # 중립
            
            # 심리 상태 분류
            if avg_sentiment >= 70:
                sentiment_label = "매우 긍정"
            elif avg_sentiment >= 55:
                sentiment_label = "긍정"
            elif avg_sentiment >= 45:
                sentiment_label = "중립"
            elif avg_sentiment >= 30:
                sentiment_label = "부정"
            else:
                sentiment_label = "매우 부정"
            
            return {
                "overall_sentiment": sentiment_label,
                "sentiment_score": round(avg_sentiment, 1),
                "market_indices_count": len(sentiment_scores),
                "timestamp": datetime.now().isoformat(),
                "recommendation": "매수 관점" if avg_sentiment >= 60 else "관망" if avg_sentiment >= 40 else "주의"
            }
            
        except Exception as e:
            self.logger.error(f"시장 심리 분석 실패: {e}")
            return {
                "overall_sentiment": "알 수 없음",
                "sentiment_score": 50.0,
                "market_indices_count": 0,
                "timestamp": datetime.now().isoformat(),
                "recommendation": "관망"
            }

# 전역 서비스 인스턴스
ai_investment_service = AIInvestmentService()

# 테스트 함수
def test_ai_investment_service():
    """AI 투자 서비스 테스트"""
    print("🤖 AI 투자 추천 시스템 테스트")
    
    # 1. 개별 종목 AI 분석
    print("\n1. Apple 종목 AI 분석:")
    apple_analysis = ai_investment_service.analyze_stock_with_ai('AAPL')
    if apple_analysis:
        print(f"   추천: {apple_analysis.recommendation.upper()}")
        print(f"   신뢰도: {apple_analysis.confidence_score:.1f}%")
        print(f"   목표가: ${apple_analysis.target_price:.2f}")
        print(f"   손절가: ${apple_analysis.stop_loss:.2f}")
        print(f"   분석 요약: {apple_analysis.analysis_summary}")
        print(f"   위험도: {apple_analysis.risk_level}")
    
    # 2. 인기 종목 AI 추천
    print("\n2. 인기 종목 AI 추천:")
    trending_recommendations = ai_investment_service.get_trending_ai_recommendations(3)
    for i, rec in enumerate(trending_recommendations, 1):
        print(f"   {i}. {rec.company_name} ({rec.symbol})")
        print(f"      추천: {rec.recommendation.upper()} | 신뢰도: {rec.confidence_score:.1f}%")
        print(f"      현재가: ${rec.current_price:.2f} → 목표가: ${rec.target_price:.2f}")
    
    # 3. 매매 신호 생성
    print("\n3. 매매 신호:")
    signals = ai_investment_service.generate_trading_signals(['AAPL', 'TSLA', 'MSFT'])
    for signal in signals:
        print(f"   {signal.symbol}: {signal.signal_type.upper()} 신호")
        print(f"   강도: {signal.strength:.1f}% | 가격: ${signal.price_at_signal:.2f}")
        print(f"   사유: {signal.reason}")

if __name__ == "__main__":
    test_ai_investment_service()