"""
AI 분석 모듈
다양한 AI 모델을 활용한 주식 데이터 분석
감성 분석, 기술적 분석, 펀더멘털 분석, 시장 예측 등의 기능 포함
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
import numpy as np
from openai import AsyncOpenAI

from ..config.model_policy import ModelTier, TaskComplexity, ContentType, model_policy
from ..rag.context_builder import ContextBuilder
from ..rag.retriever import SearchQuery, DocumentRetriever
from ..routing.model_router import ModelRouter

logger = logging.getLogger(__name__)


class AnalysisType(Enum):
    """분석 유형"""
    SENTIMENT = "sentiment"                    # 감성 분석
    TECHNICAL = "technical"                    # 기술적 분석
    FUNDAMENTAL = "fundamental"                # 펀더멘털 분석
    MARKET_PREDICTION = "market_prediction"    # 시장 예측
    RISK_ASSESSMENT = "risk_assessment"        # 리스크 평가
    STRATEGY_GENERATION = "strategy_generation" # 투자 전략 생성
    NEWS_IMPACT = "news_impact"               # 뉴스 영향도 분석
    CORRELATION = "correlation"                # 상관관계 분석


@dataclass
class AnalysisRequest:
    """분석 요청"""
    request_id: str
    analysis_type: AnalysisType
    symbol: str
    timeframe: str = "1d"                     # 1m, 5m, 1h, 1d, 1w, 1M
    lookback_period: int = 30                 # 일 단위
    custom_params: Dict[str, Any] = None
    priority: int = 3                         # 1(높음) ~ 5(낮음)
    user_context: Optional[str] = None        # 사용자 맥락 정보


@dataclass
class AnalysisResult:
    """분석 결과"""
    request_id: str
    analysis_type: AnalysisType
    symbol: str
    confidence: float                         # 신뢰도 (0.0 ~ 1.0)
    recommendation: str                       # BUY, SELL, HOLD
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    analysis_summary: str = ""
    detailed_analysis: Dict[str, Any] = None
    risk_factors: List[str] = None
    supporting_data: List[Dict[str, Any]] = None
    model_info: Dict[str, str] = None
    created_at: datetime = None
    expires_at: Optional[datetime] = None


class SentimentAnalyzer:
    """감성 분석기"""
    
    def __init__(self, model_router: ModelRouter):
        self.model_router = model_router
        
    async def analyze_sentiment(
        self, 
        symbol: str, 
        news_data: List[Dict[str, Any]],
        social_media_data: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        뉴스 및 소셜미디어 데이터 감성 분석
        
        Args:
            symbol: 주식 심볼
            news_data: 뉴스 데이터
            social_media_data: 소셜미디어 데이터
            
        Returns:
            Dict: 감성 분석 결과
        """
        try:
            logger.info(f"감성 분석 시작: {symbol}")
            
            # 데이터 통합
            all_texts = []
            for news in news_data:
                text = f"{news.get('title', '')} {news.get('content', '')}"
                all_texts.append({
                    'text': text,
                    'source': 'news',
                    'published_at': news.get('published_at'),
                    'weight': 1.0
                })
            
            if social_media_data:
                for social in social_media_data:
                    all_texts.append({
                        'text': social.get('content', ''),
                        'source': 'social_media',
                        'published_at': social.get('created_at'),
                        'weight': 0.3  # 소셜미디어는 낮은 가중치
                    })
            
            if not all_texts:
                return self._create_neutral_sentiment_result(symbol)
            
            # AI 모델을 통한 감성 분석
            sentiment_prompt = f"""
다음은 {symbol} 주식과 관련된 뉴스 및 소셜미디어 데이터입니다.
각 텍스트의 감성을 분석하고 전체적인 시장 심리를 평가해주세요.

분석할 텍스트들:
{json.dumps([{'text': t['text'][:500], 'source': t['source']} for t in all_texts[:10]], ensure_ascii=False, indent=2)}

다음 JSON 형식으로 응답해주세요:
{{
    "overall_sentiment": "positive/negative/neutral",
    "sentiment_score": -1.0 ~ 1.0 사이의 수치,
    "confidence": 0.0 ~ 1.0 사이의 신뢰도,
    "key_themes": ["주요 테마들"],
    "sentiment_breakdown": {{
        "positive_count": 긍정적 텍스트 수,
        "negative_count": 부정적 텍스트 수,
        "neutral_count": 중립적 텍스트 수
    }},
    "market_impact": "high/medium/low",
    "reasoning": "분석 근거"
}}
"""
            
            # 모델 선택 및 분석 실행
            model_tier = model_policy.get_model_for_task(
                "sentiment_analysis",
                TaskComplexity.MODERATE,
                ContentType.NEWS_ANALYSIS
            )
            
            response = await self.model_router.route_request(
                prompt=sentiment_prompt,
                model_tier=model_tier,
                temperature=0.3,
                max_tokens=1000
            )
            
            # 응답 파싱
            try:
                sentiment_result = json.loads(response.content)
            except json.JSONDecodeError:
                logger.warning("JSON 파싱 실패, 텍스트 분석으로 폴백")
                sentiment_result = self._parse_text_sentiment_response(response.content)
            
            # 시간별 감성 트렌드 분석
            time_trend = self._analyze_sentiment_trend(all_texts)
            sentiment_result['time_trend'] = time_trend
            
            # 신뢰도 조정
            sentiment_result['confidence'] *= (min(len(all_texts) / 10.0, 1.0))  # 데이터 양에 따른 신뢰도 조정
            
            return sentiment_result
            
        except Exception as e:
            logger.error(f"감성 분석 실패: {str(e)}")
            return self._create_error_sentiment_result(symbol, str(e))
    
    def _create_neutral_sentiment_result(self, symbol: str) -> Dict[str, Any]:
        """중립적 감성 분석 결과 생성"""
        return {
            "overall_sentiment": "neutral",
            "sentiment_score": 0.0,
            "confidence": 0.1,
            "key_themes": [],
            "sentiment_breakdown": {
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0
            },
            "market_impact": "low",
            "reasoning": "분석할 데이터가 부족합니다"
        }
    
    def _create_error_sentiment_result(self, symbol: str, error: str) -> Dict[str, Any]:
        """오류시 감성 분석 결과 생성"""
        return {
            "overall_sentiment": "neutral",
            "sentiment_score": 0.0,
            "confidence": 0.0,
            "key_themes": [],
            "sentiment_breakdown": {
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0
            },
            "market_impact": "unknown",
            "reasoning": f"분석 중 오류 발생: {error}"
        }
    
    def _parse_text_sentiment_response(self, response_text: str) -> Dict[str, Any]:
        """텍스트 응답에서 감성 정보 추출"""
        try:
            # 간단한 텍스트 파싱 로직
            sentiment = "neutral"
            score = 0.0
            
            response_lower = response_text.lower()
            
            if any(word in response_lower for word in ['긍정', 'positive', '상승', '좋은']):
                sentiment = "positive"
                score = 0.5
            elif any(word in response_lower for word in ['부정', 'negative', '하락', '나쁜']):
                sentiment = "negative"
                score = -0.5
            
            return {
                "overall_sentiment": sentiment,
                "sentiment_score": score,
                "confidence": 0.3,
                "key_themes": [],
                "sentiment_breakdown": {
                    "positive_count": 1 if sentiment == "positive" else 0,
                    "negative_count": 1 if sentiment == "negative" else 0,
                    "neutral_count": 1 if sentiment == "neutral" else 0
                },
                "market_impact": "medium",
                "reasoning": "텍스트 분석 기반 추정"
            }
            
        except Exception as e:
            logger.error(f"텍스트 감성 파싱 실패: {str(e)}")
            return self._create_neutral_sentiment_result("")
    
    def _analyze_sentiment_trend(self, texts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """시간별 감성 트렌드 분석"""
        try:
            if not texts:
                return {"trend": "stable", "recent_shift": "none"}
            
            # 시간순 정렬
            sorted_texts = sorted(
                [t for t in texts if t.get('published_at')], 
                key=lambda x: x['published_at']
            )
            
            if len(sorted_texts) < 2:
                return {"trend": "stable", "recent_shift": "none"}
            
            # 최근 24시간과 그 이전 비교
            now = datetime.utcnow()
            recent_cutoff = now - timedelta(hours=24)
            
            recent_texts = [t for t in sorted_texts if t['published_at'] > recent_cutoff]
            older_texts = [t for t in sorted_texts if t['published_at'] <= recent_cutoff]
            
            # 간단한 키워드 기반 감성 점수 계산
            def calculate_simple_sentiment(text_list):
                if not text_list:
                    return 0.0
                
                total_score = 0.0
                for text_data in text_list:
                    text = text_data['text'].lower()
                    score = 0.0
                    
                    positive_words = ['상승', '긍정', '성장', '호재', '매수']
                    negative_words = ['하락', '부정', '악재', '위험', '매도']
                    
                    for word in positive_words:
                        score += text.count(word) * 0.1
                    for word in negative_words:
                        score -= text.count(word) * 0.1
                    
                    total_score += score * text_data.get('weight', 1.0)
                
                return total_score / len(text_list)
            
            recent_sentiment = calculate_simple_sentiment(recent_texts)
            older_sentiment = calculate_simple_sentiment(older_texts)
            
            # 트렌드 결정
            sentiment_diff = recent_sentiment - older_sentiment
            
            if abs(sentiment_diff) < 0.1:
                trend = "stable"
                shift = "none"
            elif sentiment_diff > 0.2:
                trend = "improving"
                shift = "positive"
            elif sentiment_diff < -0.2:
                trend = "deteriorating"
                shift = "negative"
            else:
                trend = "stable"
                shift = "slight_positive" if sentiment_diff > 0 else "slight_negative"
            
            return {
                "trend": trend,
                "recent_shift": shift,
                "recent_sentiment_score": recent_sentiment,
                "older_sentiment_score": older_sentiment,
                "sentiment_change": sentiment_diff
            }
            
        except Exception as e:
            logger.error(f"감성 트렌드 분석 실패: {str(e)}")
            return {"trend": "unknown", "recent_shift": "unknown"}


class TechnicalAnalyzer:
    """기술적 분석기"""
    
    def __init__(self, model_router: ModelRouter):
        self.model_router = model_router
    
    async def analyze_technical(
        self, 
        symbol: str, 
        price_data: List[Dict[str, Any]],
        indicators: List[str] = None
    ) -> Dict[str, Any]:
        """
        기술적 분석 수행
        
        Args:
            symbol: 주식 심볼
            price_data: 가격 데이터 (OHLCV)
            indicators: 분석할 기술적 지표 리스트
            
        Returns:
            Dict: 기술적 분석 결과
        """
        try:
            logger.info(f"기술적 분석 시작: {symbol}")
            
            if not price_data:
                return self._create_error_technical_result(symbol, "가격 데이터 없음")
            
            # 기본 지표 목록
            if not indicators:
                indicators = ['SMA', 'RSI', 'MACD', 'Bollinger Bands', 'Volume']
            
            # 가격 데이터 정리
            sorted_data = sorted(price_data, key=lambda x: x['date'])
            
            # 지표 계산
            calculated_indicators = self._calculate_indicators(sorted_data, indicators)
            
            # 패턴 분석
            patterns = self._detect_patterns(sorted_data)
            
            # AI 분석 프롬프트 구성
            analysis_prompt = f"""
{symbol} 주식의 기술적 분석을 수행해주세요.

가격 데이터 (최근 10일):
{json.dumps(sorted_data[-10:], indent=2, default=str)}

계산된 기술적 지표:
{json.dumps(calculated_indicators, indent=2)}

감지된 패턴:
{json.dumps(patterns, indent=2)}

다음 JSON 형식으로 분석 결과를 제공해주세요:
{{
    "overall_signal": "BUY/SELL/HOLD",
    "signal_strength": 0.0 ~ 1.0 사이의 신호 강도,
    "confidence": 0.0 ~ 1.0 사이의 신뢰도,
    "key_indicators": ["주요 지표들과 신호"],
    "support_levels": [지지선 가격들],
    "resistance_levels": [저항선 가격들],
    "target_price": 목표가,
    "stop_loss": 손절가,
    "timeframe_outlook": {{
        "short_term": "1-5일 전망",
        "medium_term": "1-4주 전망",
        "long_term": "1-3개월 전망"
    }},
    "risk_assessment": "HIGH/MEDIUM/LOW",
    "reasoning": "분석 근거"
}}
"""
            
            # AI 분석 실행
            model_tier = model_policy.get_model_for_task(
                "technical_analysis",
                TaskComplexity.COMPLEX,
                ContentType.TECHNICAL_ANALYSIS
            )
            
            response = await self.model_router.route_request(
                prompt=analysis_prompt,
                model_tier=model_tier,
                temperature=0.2,
                max_tokens=1500
            )
            
            # 결과 파싱
            try:
                technical_result = json.loads(response.content)
            except json.JSONDecodeError:
                logger.warning("JSON 파싱 실패, 텍스트 분석으로 폴백")
                technical_result = self._parse_text_technical_response(response.content)
            
            # 추가 정보 첨부
            technical_result.update({
                'indicators': calculated_indicators,
                'patterns': patterns,
                'data_points': len(sorted_data),
                'analysis_date': datetime.utcnow().isoformat()
            })
            
            return technical_result
            
        except Exception as e:
            logger.error(f"기술적 분석 실패: {str(e)}")
            return self._create_error_technical_result(symbol, str(e))
    
    def _calculate_indicators(
        self, 
        price_data: List[Dict[str, Any]], 
        indicators: List[str]
    ) -> Dict[str, Any]:
        """기술적 지표 계산"""
        try:
            result = {}
            
            if len(price_data) < 2:
                return result
            
            # 가격 배열 준비
            closes = [float(d['close']) for d in price_data]
            highs = [float(d['high']) for d in price_data]
            lows = [float(d['low']) for d in price_data]
            volumes = [float(d.get('volume', 0)) for d in price_data]
            
            # SMA (Simple Moving Average)
            if 'SMA' in indicators and len(closes) >= 20:
                sma_5 = sum(closes[-5:]) / 5
                sma_20 = sum(closes[-20:]) / 20
                result['SMA'] = {
                    'SMA_5': sma_5,
                    'SMA_20': sma_20,
                    'signal': 'BUY' if sma_5 > sma_20 else 'SELL'
                }
            
            # RSI (Relative Strength Index)
            if 'RSI' in indicators and len(closes) >= 14:
                rsi = self._calculate_rsi(closes, 14)
                result['RSI'] = {
                    'value': rsi,
                    'signal': 'SELL' if rsi > 70 else ('BUY' if rsi < 30 else 'HOLD')
                }
            
            # MACD
            if 'MACD' in indicators and len(closes) >= 26:
                macd_line, signal_line = self._calculate_macd(closes)
                result['MACD'] = {
                    'MACD_line': macd_line,
                    'signal_line': signal_line,
                    'signal': 'BUY' if macd_line > signal_line else 'SELL'
                }
            
            # Bollinger Bands
            if 'Bollinger Bands' in indicators and len(closes) >= 20:
                bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(closes, 20)
                current_price = closes[-1]
                
                if current_price > bb_upper:
                    bb_signal = 'SELL'  # 과매수
                elif current_price < bb_lower:
                    bb_signal = 'BUY'   # 과매도
                else:
                    bb_signal = 'HOLD'
                
                result['Bollinger_Bands'] = {
                    'upper': bb_upper,
                    'middle': bb_middle,
                    'lower': bb_lower,
                    'signal': bb_signal
                }
            
            # Volume Analysis
            if 'Volume' in indicators and len(volumes) >= 10:
                avg_volume = sum(volumes[-10:]) / 10
                current_volume = volumes[-1]
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
                
                result['Volume'] = {
                    'current_volume': current_volume,
                    'average_volume': avg_volume,
                    'volume_ratio': volume_ratio,
                    'signal': 'HIGH_VOLUME' if volume_ratio > 2 else ('LOW_VOLUME' if volume_ratio < 0.5 else 'NORMAL')
                }
            
            return result
            
        except Exception as e:
            logger.error(f"지표 계산 실패: {str(e)}")
            return {}
    
    def _calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        """RSI 계산"""
        try:
            if len(closes) < period + 1:
                return 50.0
            
            deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
            gains = [d if d > 0 else 0 for d in deltas]
            losses = [-d if d < 0 else 0 for d in deltas]
            
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
            
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception:
            return 50.0
    
    def _calculate_macd(self, closes: List[float]) -> Tuple[float, float]:
        """MACD 계산"""
        try:
            if len(closes) < 26:
                return 0.0, 0.0
            
            # 지수이동평균 계산 (간단한 근사)
            ema_12 = closes[-1]  # 실제로는 12일 EMA
            ema_26 = sum(closes[-26:]) / 26  # 실제로는 26일 EMA
            
            macd_line = ema_12 - ema_26
            signal_line = macd_line  # 실제로는 9일 EMA of MACD
            
            return macd_line, signal_line
            
        except Exception:
            return 0.0, 0.0
    
    def _calculate_bollinger_bands(
        self, 
        closes: List[float], 
        period: int = 20
    ) -> Tuple[float, float, float]:
        """볼린저 밴드 계산"""
        try:
            if len(closes) < period:
                return 0.0, 0.0, 0.0
            
            sma = sum(closes[-period:]) / period
            variance = sum((x - sma) ** 2 for x in closes[-period:]) / period
            std_dev = variance ** 0.5
            
            upper = sma + (2 * std_dev)
            lower = sma - (2 * std_dev)
            
            return upper, sma, lower
            
        except Exception:
            return 0.0, 0.0, 0.0
    
    def _detect_patterns(self, price_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """차트 패턴 감지"""
        try:
            patterns = []
            
            if len(price_data) < 10:
                return patterns
            
            closes = [float(d['close']) for d in price_data]
            
            # 단순한 패턴 감지
            recent_closes = closes[-5:]
            
            # 상승 트렌드
            if all(recent_closes[i] >= recent_closes[i-1] for i in range(1, len(recent_closes))):
                patterns.append({
                    'pattern': 'uptrend',
                    'confidence': 0.7,
                    'description': '최근 5일간 상승 추세'
                })
            
            # 하락 트렌드
            elif all(recent_closes[i] <= recent_closes[i-1] for i in range(1, len(recent_closes))):
                patterns.append({
                    'pattern': 'downtrend',
                    'confidence': 0.7,
                    'description': '최근 5일간 하락 추세'
                })
            
            # 변동성 증가
            recent_volatility = np.std(recent_closes)
            total_volatility = np.std(closes)
            
            if recent_volatility > total_volatility * 1.5:
                patterns.append({
                    'pattern': 'high_volatility',
                    'confidence': 0.6,
                    'description': '최근 변동성 증가'
                })
            
            return patterns
            
        except Exception as e:
            logger.error(f"패턴 감지 실패: {str(e)}")
            return []
    
    def _create_error_technical_result(self, symbol: str, error: str) -> Dict[str, Any]:
        """오류시 기술적 분석 결과 생성"""
        return {
            "overall_signal": "HOLD",
            "signal_strength": 0.0,
            "confidence": 0.0,
            "key_indicators": [],
            "support_levels": [],
            "resistance_levels": [],
            "target_price": None,
            "stop_loss": None,
            "timeframe_outlook": {
                "short_term": "분석 불가",
                "medium_term": "분석 불가", 
                "long_term": "분석 불가"
            },
            "risk_assessment": "UNKNOWN",
            "reasoning": f"분석 중 오류 발생: {error}"
        }
    
    def _parse_text_technical_response(self, response_text: str) -> Dict[str, Any]:
        """텍스트 응답에서 기술적 분석 정보 추출"""
        try:
            # 간단한 텍스트 파싱 로직
            signal = "HOLD"
            response_lower = response_text.lower()
            
            if any(word in response_lower for word in ['매수', 'buy', '상승']):
                signal = "BUY"
            elif any(word in response_lower for word in ['매도', 'sell', '하락']):
                signal = "SELL"
            
            return {
                "overall_signal": signal,
                "signal_strength": 0.5,
                "confidence": 0.3,
                "key_indicators": ["텍스트 분석 기반"],
                "support_levels": [],
                "resistance_levels": [],
                "target_price": None,
                "stop_loss": None,
                "timeframe_outlook": {
                    "short_term": "텍스트 분석 기반 추정",
                    "medium_term": "추가 분석 필요",
                    "long_term": "추가 분석 필요"
                },
                "risk_assessment": "MEDIUM",
                "reasoning": "텍스트 분석을 통한 기본적 추정"
            }
            
        except Exception as e:
            logger.error(f"텍스트 기술적 분석 파싱 실패: {str(e)}")
            return self._create_error_technical_result("", str(e))


class AnalysisEngine:
    """AI 분석 엔진 메인 클래스"""
    
    def __init__(
        self,
        model_router: ModelRouter,
        document_retriever: DocumentRetriever,
        context_builder: ContextBuilder
    ):
        self.model_router = model_router
        self.document_retriever = document_retriever
        self.context_builder = context_builder
        
        # 분석기 인스턴스
        self.sentiment_analyzer = SentimentAnalyzer(model_router)
        self.technical_analyzer = TechnicalAnalyzer(model_router)
        
        # 분석 요청 큐
        self.analysis_queue = asyncio.Queue()
        self.is_running = False
        
        # 결과 캐시
        self.result_cache: Dict[str, AnalysisResult] = {}
        self.cache_ttl = 3600  # 1시간
    
    async def start_engine(self):
        """분석 엔진 시작"""
        try:
            logger.info("AI 분석 엔진 시작")
            self.is_running = True
            
            # 분석 워커 시작
            await asyncio.create_task(self._run_analysis_worker())
            
        except Exception as e:
            logger.error(f"분석 엔진 시작 실패: {str(e)}")
            self.is_running = False
    
    async def stop_engine(self):
        """분석 엔진 중지"""
        logger.info("AI 분석 엔진 중지")
        self.is_running = False
    
    async def request_analysis(self, request: AnalysisRequest) -> str:
        """분석 요청 제출"""
        try:
            # 캐시 확인
            cache_key = self._generate_cache_key(request)
            cached_result = self.result_cache.get(cache_key)
            
            if cached_result and self._is_result_valid(cached_result):
                logger.info(f"캐시된 분석 결과 반환: {request.request_id}")
                return request.request_id
            
            # 큐에 요청 추가
            await self.analysis_queue.put(request)
            logger.info(f"분석 요청 큐에 추가: {request.request_id}")
            
            return request.request_id
            
        except Exception as e:
            logger.error(f"분석 요청 실패: {str(e)}")
            raise
    
    async def get_analysis_result(self, request_id: str) -> Optional[AnalysisResult]:
        """분석 결과 조회"""
        try:
            # 모든 캐시에서 검색
            for result in self.result_cache.values():
                if result.request_id == request_id:
                    if self._is_result_valid(result):
                        return result
                    else:
                        # 만료된 결과 제거
                        cache_key = self._generate_cache_key_from_result(result)
                        if cache_key in self.result_cache:
                            del self.result_cache[cache_key]
                        break
            
            return None
            
        except Exception as e:
            logger.error(f"분석 결과 조회 실패: {str(e)}")
            return None
    
    async def _run_analysis_worker(self):
        """분석 워커 실행"""
        while self.is_running:
            try:
                # 큐에서 요청 가져오기
                request = await asyncio.wait_for(
                    self.analysis_queue.get(), 
                    timeout=5.0
                )
                
                # 분석 실행
                await self._execute_analysis(request)
                
            except asyncio.TimeoutError:
                # 타임아웃은 정상 (큐가 비어있음)
                continue
            except Exception as e:
                logger.error(f"분석 워커 오류: {str(e)}")
                await asyncio.sleep(1)
    
    async def _execute_analysis(self, request: AnalysisRequest):
        """개별 분석 실행"""
        try:
            logger.info(f"분석 실행 시작: {request.request_id} ({request.analysis_type.value})")
            
            result = None
            
            if request.analysis_type == AnalysisType.SENTIMENT:
                result = await self._execute_sentiment_analysis(request)
            elif request.analysis_type == AnalysisType.TECHNICAL:
                result = await self._execute_technical_analysis(request)
            elif request.analysis_type == AnalysisType.FUNDAMENTAL:
                result = await self._execute_fundamental_analysis(request)
            elif request.analysis_type == AnalysisType.STRATEGY_GENERATION:
                result = await self._execute_strategy_generation(request)
            else:
                logger.warning(f"지원하지 않는 분석 유형: {request.analysis_type}")
                result = self._create_error_result(request, "지원하지 않는 분석 유형")
            
            if result:
                # 결과 캐시 저장
                cache_key = self._generate_cache_key(request)
                self.result_cache[cache_key] = result
                
                logger.info(f"분석 완료: {request.request_id}")
            
        except Exception as e:
            logger.error(f"분석 실행 실패: {request.request_id} - {str(e)}")
            
            # 오류 결과 생성
            error_result = self._create_error_result(request, str(e))
            cache_key = self._generate_cache_key(request)
            self.result_cache[cache_key] = error_result
    
    async def _execute_sentiment_analysis(self, request: AnalysisRequest) -> AnalysisResult:
        """감성 분석 실행"""
        try:
            # 관련 뉴스 데이터 검색
            search_query = SearchQuery(
                text=f"{request.symbol} 뉴스 감성",
                query_type="news",
                max_results=20,
                document_types=["news"],
                boost_recent=True
            )
            
            search_results = await self.document_retriever.search(search_query)
            
            # 뉴스 데이터 추출
            news_data = []
            for search_result in search_results:
                doc = search_result.document
                news_data.append({
                    'title': doc.metadata.get('title', ''),
                    'content': doc.content,
                    'published_at': doc.created_at,
                    'source': doc.metadata.get('source', ''),
                    'sentiment_score': doc.metadata.get('sentiment_score', 0)
                })
            
            # 감성 분석 실행
            sentiment_result = await self.sentiment_analyzer.analyze_sentiment(
                request.symbol, 
                news_data
            )
            
            # AnalysisResult 형태로 변환
            recommendation = "HOLD"
            if sentiment_result['overall_sentiment'] == 'positive' and sentiment_result['sentiment_score'] > 0.3:
                recommendation = "BUY"
            elif sentiment_result['overall_sentiment'] == 'negative' and sentiment_result['sentiment_score'] < -0.3:
                recommendation = "SELL"
            
            return AnalysisResult(
                request_id=request.request_id,
                analysis_type=request.analysis_type,
                symbol=request.symbol,
                confidence=sentiment_result.get('confidence', 0.5),
                recommendation=recommendation,
                analysis_summary=sentiment_result.get('reasoning', ''),
                detailed_analysis=sentiment_result,
                risk_factors=[f"시장 심리: {sentiment_result.get('market_impact', 'unknown')}"],
                supporting_data=[{'type': 'sentiment', 'data': sentiment_result}],
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=6)  # 6시간 유효
            )
            
        except Exception as e:
            logger.error(f"감성 분석 실행 실패: {str(e)}")
            return self._create_error_result(request, str(e))
    
    async def _execute_technical_analysis(self, request: AnalysisRequest) -> AnalysisResult:
        """기술적 분석 실행"""
        try:
            # 가격 데이터 검색
            search_query = SearchQuery(
                text=f"{request.symbol} 주가 데이터",
                query_type="technical",
                max_results=50,
                document_types=["price_data"],
                boost_recent=True
            )
            
            search_results = await self.document_retriever.search(search_query)
            
            # 가격 데이터 추출
            price_data = []
            for search_result in search_results:
                doc = search_result.document
                price_info = {
                    'date': doc.created_at,
                    'open': doc.metadata.get('open_price', 0),
                    'high': doc.metadata.get('high_price', 0),
                    'low': doc.metadata.get('low_price', 0),
                    'close': doc.metadata.get('close_price', 0),
                    'volume': doc.metadata.get('volume', 0)
                }
                price_data.append(price_info)
            
            # 기술적 분석 실행
            technical_result = await self.technical_analyzer.analyze_technical(
                request.symbol,
                price_data
            )
            
            # AnalysisResult 변환
            return AnalysisResult(
                request_id=request.request_id,
                analysis_type=request.analysis_type,
                symbol=request.symbol,
                confidence=technical_result.get('confidence', 0.5),
                recommendation=technical_result.get('overall_signal', 'HOLD'),
                target_price=technical_result.get('target_price'),
                stop_loss=technical_result.get('stop_loss'),
                analysis_summary=technical_result.get('reasoning', ''),
                detailed_analysis=technical_result,
                risk_factors=[f"위험도: {technical_result.get('risk_assessment', 'unknown')}"],
                supporting_data=[{'type': 'technical', 'data': technical_result}],
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=4)  # 4시간 유효
            )
            
        except Exception as e:
            logger.error(f"기술적 분석 실행 실패: {str(e)}")
            return self._create_error_result(request, str(e))
    
    async def _execute_fundamental_analysis(self, request: AnalysisRequest) -> AnalysisResult:
        """펀더멘털 분석 실행 (구현 예시)"""
        # 실제 구현시 재무 데이터 분석 로직 추가
        return self._create_error_result(request, "펀더멘털 분석 미구현")
    
    async def _execute_strategy_generation(self, request: AnalysisRequest) -> AnalysisResult:
        """투자 전략 생성 실행 (구현 예시)"""
        # 실제 구현시 종합 전략 생성 로직 추가
        return self._create_error_result(request, "전략 생성 미구현")
    
    def _generate_cache_key(self, request: AnalysisRequest) -> str:
        """캐시 키 생성"""
        return f"{request.analysis_type.value}_{request.symbol}_{request.timeframe}_{request.lookback_period}"
    
    def _generate_cache_key_from_result(self, result: AnalysisResult) -> str:
        """결과에서 캐시 키 생성"""
        return f"{result.analysis_type.value}_{result.symbol}_default_default"
    
    def _is_result_valid(self, result: AnalysisResult) -> bool:
        """결과 유효성 확인"""
        if result.expires_at and result.expires_at < datetime.utcnow():
            return False
        return True
    
    def _create_error_result(self, request: AnalysisRequest, error: str) -> AnalysisResult:
        """오류 결과 생성"""
        return AnalysisResult(
            request_id=request.request_id,
            analysis_type=request.analysis_type,
            symbol=request.symbol,
            confidence=0.0,
            recommendation="HOLD",
            analysis_summary=f"분석 실패: {error}",
            detailed_analysis={"error": error},
            risk_factors=["분석 오류"],
            created_at=datetime.utcnow()
        )
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """엔진 통계 정보"""
        return {
            "is_running": self.is_running,
            "queue_size": self.analysis_queue.qsize(),
            "cached_results": len(self.result_cache),
            "cache_hit_rate": 0.0,  # 실제 구현시 히트율 계산
            "analysis_types_supported": [t.value for t in AnalysisType]
        }