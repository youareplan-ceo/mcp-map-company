"""
AI 시그널 생성 및 관리 모듈
분석 결과를 바탕으로 실행 가능한 투자 시그널을 생성
시그널 우선순위, 리스크 관리, 포트폴리오 최적화 기능 포함
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
import numpy as np
from collections import defaultdict, deque

from .analysis_module import AnalysisResult, AnalysisType
from ..config.model_policy import ModelTier, model_policy

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """시그널 유형"""
    BUY = "buy"                      # 매수 시그널
    SELL = "sell"                    # 매도 시그널
    HOLD = "hold"                    # 보유 시그널
    STOP_LOSS = "stop_loss"          # 손절 시그널
    TAKE_PROFIT = "take_profit"      # 익절 시그널
    REBALANCE = "rebalance"          # 리밸런싱 시그널
    HEDGE = "hedge"                  # 헤지 시그널
    ALERT = "alert"                  # 주의 시그널


class SignalStrength(Enum):
    """시그널 강도"""
    WEAK = 1
    MODERATE = 2  
    STRONG = 3
    VERY_STRONG = 4
    EXTREME = 5


class RiskLevel(Enum):
    """위험 수준"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class TradingSignal:
    """거래 시그널"""
    signal_id: str
    symbol: str
    signal_type: SignalType
    strength: SignalStrength
    confidence: float                  # 0.0 ~ 1.0
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    position_size: Optional[float] = None  # 포지션 크기 (비율)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    timeframe: str = "1d"             # 시간프레임
    expires_at: Optional[datetime] = None
    analysis_sources: List[str] = None # 분석 소스들
    reasoning: str = ""
    metadata: Dict[str, Any] = None
    created_at: datetime = None
    updated_at: datetime = None


@dataclass
class PortfolioSignal:
    """포트폴리오 레벨 시그널"""
    portfolio_id: str
    signals: List[TradingSignal]
    overall_direction: str             # "bullish", "bearish", "neutral"
    risk_score: float                  # 0.0 ~ 1.0
    diversification_score: float      # 다양성 점수
    correlation_warning: bool = False
    rebalance_needed: bool = False
    suggested_actions: List[Dict[str, Any]] = None
    created_at: datetime = None


class SignalAggregator:
    """시그널 집계기"""
    
    def __init__(self):
        self.signal_weights = {
            AnalysisType.TECHNICAL: 0.4,
            AnalysisType.SENTIMENT: 0.3,
            AnalysisType.FUNDAMENTAL: 0.2,
            AnalysisType.NEWS_IMPACT: 0.1
        }
        
        # 시그널 강도 임계값
        self.strength_thresholds = {
            SignalStrength.WEAK: 0.3,
            SignalStrength.MODERATE: 0.5,
            SignalStrength.STRONG: 0.7,
            SignalStrength.VERY_STRONG: 0.85,
            SignalStrength.EXTREME: 0.95
        }
    
    def aggregate_analysis_results(
        self, 
        symbol: str,
        analysis_results: List[AnalysisResult]
    ) -> Optional[TradingSignal]:
        """
        여러 분석 결과를 집계하여 단일 시그널 생성
        
        Args:
            symbol: 주식 심볼
            analysis_results: 분석 결과 리스트
            
        Returns:
            Optional[TradingSignal]: 집계된 시그널
        """
        try:
            if not analysis_results:
                return None
            
            logger.info(f"시그널 집계 시작: {symbol}, {len(analysis_results)}개 분석")
            
            # 유효한 분석 결과만 필터링
            valid_results = [
                r for r in analysis_results 
                if r.confidence > 0.1 and self._is_result_fresh(r)
            ]
            
            if not valid_results:
                logger.warning(f"유효한 분석 결과 없음: {symbol}")
                return None
            
            # 가중 평균 신뢰도 계산
            total_confidence = 0.0
            total_weight = 0.0
            
            # 추천 점수 계산
            recommendation_scores = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}
            
            # 가격 목표 수집
            target_prices = []
            stop_losses = []
            
            # 분석 소스 추적
            analysis_sources = []
            reasoning_parts = []
            
            for result in valid_results:
                # 가중치 적용
                weight = self.signal_weights.get(result.analysis_type, 0.1)
                confidence_weighted = result.confidence * weight
                
                total_confidence += confidence_weighted
                total_weight += weight
                
                # 추천 점수에 가중치 적용
                recommendation_scores[result.recommendation] += confidence_weighted
                
                # 가격 정보 수집
                if result.target_price:
                    target_prices.append(result.target_price)
                if result.stop_loss:
                    stop_losses.append(result.stop_loss)
                
                # 소스 정보
                analysis_sources.append(result.analysis_type.value)
                reasoning_parts.append(f"{result.analysis_type.value}: {result.analysis_summary}")
            
            # 최종 신뢰도 계산
            final_confidence = total_confidence / total_weight if total_weight > 0 else 0.0
            
            # 최종 추천 결정
            final_recommendation = max(recommendation_scores, key=recommendation_scores.get)
            final_recommendation_score = recommendation_scores[final_recommendation] / total_weight
            
            # 시그널 타입 매핑
            if final_recommendation == "BUY":
                signal_type = SignalType.BUY
            elif final_recommendation == "SELL":
                signal_type = SignalType.SELL
            else:
                signal_type = SignalType.HOLD
            
            # 시그널 강도 계산
            strength = self._calculate_signal_strength(final_recommendation_score, final_confidence)
            
            # 목표가 및 손절가 계산
            target_price = np.median(target_prices) if target_prices else None
            stop_loss = np.median(stop_losses) if stop_losses else None
            
            # 위험 수준 평가
            risk_level = self._assess_risk_level(valid_results, final_confidence)
            
            # 시그널 생성
            signal = TradingSignal(
                signal_id=f"{symbol}_{int(datetime.utcnow().timestamp())}",
                symbol=symbol,
                signal_type=signal_type,
                strength=strength,
                confidence=final_confidence,
                target_price=target_price,
                stop_loss=stop_loss,
                risk_level=risk_level,
                expires_at=datetime.utcnow() + timedelta(hours=24),
                analysis_sources=analysis_sources,
                reasoning="; ".join(reasoning_parts),
                metadata={
                    "recommendation_scores": recommendation_scores,
                    "source_count": len(valid_results),
                    "aggregation_method": "weighted_average"
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            logger.info(f"시그널 집계 완료: {symbol}, {signal_type.value}, 강도: {strength.value}")
            return signal
            
        except Exception as e:
            logger.error(f"시그널 집계 실패: {symbol} - {str(e)}")
            return None
    
    def _is_result_fresh(self, result: AnalysisResult) -> bool:
        """분석 결과 신선도 확인"""
        try:
            if not result.created_at:
                return False
            
            # 분석 유형별 유효 기간
            validity_hours = {
                AnalysisType.TECHNICAL: 4,      # 4시간
                AnalysisType.SENTIMENT: 12,     # 12시간
                AnalysisType.FUNDAMENTAL: 168,  # 1주일
                AnalysisType.NEWS_IMPACT: 6     # 6시간
            }
            
            max_age = validity_hours.get(result.analysis_type, 24)
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age)
            
            return result.created_at > cutoff_time
            
        except Exception:
            return False
    
    def _calculate_signal_strength(self, recommendation_score: float, confidence: float) -> SignalStrength:
        """시그널 강도 계산"""
        try:
            # 추천 점수와 신뢰도의 기하평균
            combined_score = (recommendation_score * confidence) ** 0.5
            
            for strength, threshold in reversed(list(self.strength_thresholds.items())):
                if combined_score >= threshold:
                    return strength
            
            return SignalStrength.WEAK
            
        except Exception:
            return SignalStrength.WEAK
    
    def _assess_risk_level(self, results: List[AnalysisResult], confidence: float) -> RiskLevel:
        """위험 수준 평가"""
        try:
            # 위험 요소 확인
            risk_factors_count = 0
            high_volatility_mentioned = False
            
            for result in results:
                if result.risk_factors:
                    risk_factors_count += len(result.risk_factors)
                    
                    # 고변동성 키워드 확인
                    risk_text = " ".join(result.risk_factors).lower()
                    if any(keyword in risk_text for keyword in ['변동성', '위험', '불확실', '급등', '급락']):
                        high_volatility_mentioned = True
            
            # 위험 수준 결정
            if confidence < 0.3 or risk_factors_count > 5:
                return RiskLevel.EXTREME
            elif confidence < 0.5 or risk_factors_count > 3 or high_volatility_mentioned:
                return RiskLevel.HIGH
            elif confidence < 0.7 or risk_factors_count > 1:
                return RiskLevel.MEDIUM
            else:
                return RiskLevel.LOW
                
        except Exception:
            return RiskLevel.MEDIUM


class RiskManager:
    """리스크 관리자"""
    
    def __init__(self):
        self.max_position_sizes = {
            RiskLevel.LOW: 0.1,      # 10%
            RiskLevel.MEDIUM: 0.05,  # 5%
            RiskLevel.HIGH: 0.02,    # 2%
            RiskLevel.EXTREME: 0.01  # 1%
        }
        
        self.max_portfolio_risk = 0.15  # 15%
        self.correlation_threshold = 0.7
        
    def calculate_position_size(
        self, 
        signal: TradingSignal, 
        portfolio_value: float,
        current_portfolio_risk: float = 0.0
    ) -> float:
        """
        포지션 크기 계산
        
        Args:
            signal: 거래 시그널
            portfolio_value: 포트폴리오 총 가치
            current_portfolio_risk: 현재 포트폴리오 위험도
            
        Returns:
            float: 권장 포지션 크기 (비율)
        """
        try:
            # 기본 포지션 크기 (위험 수준별)
            base_position = self.max_position_sizes.get(signal.risk_level, 0.05)
            
            # 신뢰도 조정
            confidence_adjusted = base_position * signal.confidence
            
            # 시그널 강도 조정
            strength_multiplier = {
                SignalStrength.WEAK: 0.5,
                SignalStrength.MODERATE: 0.7,
                SignalStrength.STRONG: 1.0,
                SignalStrength.VERY_STRONG: 1.2,
                SignalStrength.EXTREME: 1.5
            }
            
            strength_adjusted = confidence_adjusted * strength_multiplier.get(signal.strength, 1.0)
            
            # 포트폴리오 리스크 한도 확인
            remaining_risk_budget = self.max_portfolio_risk - current_portfolio_risk
            risk_constrained = min(strength_adjusted, remaining_risk_budget)
            
            # 최종 포지션 크기 (최소 0.5%, 최대 10%)
            final_position = max(0.005, min(risk_constrained, 0.1))
            
            return final_position
            
        except Exception as e:
            logger.error(f"포지션 크기 계산 실패: {str(e)}")
            return 0.01  # 기본값 1%
    
    def validate_signal(
        self, 
        signal: TradingSignal,
        existing_positions: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        시그널 유효성 검증
        
        Args:
            signal: 검증할 시그널
            existing_positions: 기존 포지션 정보
            
        Returns:
            Dict: 검증 결과
        """
        try:
            validation_result = {
                "valid": True,
                "warnings": [],
                "blockers": [],
                "risk_assessment": {
                    "individual_risk": signal.risk_level.value,
                    "portfolio_impact": "unknown"
                }
            }
            
            # 시그널 만료 확인
            if signal.expires_at and signal.expires_at < datetime.utcnow():
                validation_result["valid"] = False
                validation_result["blockers"].append("시그널이 만료되었습니다")
            
            # 신뢰도 임계값 확인
            if signal.confidence < 0.2:
                validation_result["valid"] = False
                validation_result["blockers"].append("신뢰도가 너무 낮습니다")
            elif signal.confidence < 0.5:
                validation_result["warnings"].append("신뢰도가 낮습니다")
            
            # 가격 정보 일관성 확인
            if signal.target_price and signal.stop_loss:
                if signal.signal_type == SignalType.BUY:
                    if signal.target_price <= signal.stop_loss:
                        validation_result["warnings"].append("목표가가 손절가보다 낮습니다")
                elif signal.signal_type == SignalType.SELL:
                    if signal.target_price >= signal.stop_loss:
                        validation_result["warnings"].append("목표가가 손절가보다 높습니다")
            
            # 기존 포지션과의 충돌 확인
            if existing_positions:
                for position in existing_positions:
                    if position.get("symbol") == signal.symbol:
                        if position.get("direction") != signal.signal_type.value:
                            validation_result["warnings"].append(f"기존 포지션과 반대 방향입니다")
            
            # 고위험 시그널 경고
            if signal.risk_level in [RiskLevel.HIGH, RiskLevel.EXTREME]:
                validation_result["warnings"].append(f"고위험 시그널입니다: {signal.risk_level.value}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"시그널 검증 실패: {str(e)}")
            return {
                "valid": False,
                "warnings": [],
                "blockers": [f"검증 중 오류: {str(e)}"]
            }


class SignalOptimizer:
    """시그널 최적화기"""
    
    def __init__(self):
        self.correlation_data = {}  # 심볼 간 상관관계 캐시
        self.sector_mapping = {}    # 심볼별 섹터 매핑
        
    def optimize_portfolio_signals(
        self,
        signals: List[TradingSignal],
        portfolio_constraints: Dict[str, Any] = None
    ) -> List[TradingSignal]:
        """
        포트폴리오 레벨 시그널 최적화
        
        Args:
            signals: 개별 시그널들
            portfolio_constraints: 포트폴리오 제약사항
            
        Returns:
            List[TradingSignal]: 최적화된 시그널들
        """
        try:
            logger.info(f"포트폴리오 시그널 최적화: {len(signals)}개 시그널")
            
            if not signals:
                return []
            
            constraints = portfolio_constraints or {}
            max_positions = constraints.get("max_positions", 10)
            max_sector_weight = constraints.get("max_sector_weight", 0.3)
            
            # 시그널 정렬 (강도 및 신뢰도 기준)
            sorted_signals = sorted(
                signals,
                key=lambda s: (s.strength.value * s.confidence),
                reverse=True
            )
            
            # 다양성 필터링
            diversified_signals = self._apply_diversification_filter(
                sorted_signals,
                max_positions,
                max_sector_weight
            )
            
            # 상관관계 기반 최적화
            correlation_optimized = self._optimize_by_correlation(diversified_signals)
            
            # 위험 조정
            risk_adjusted = self._apply_risk_adjustment(correlation_optimized, constraints)
            
            logger.info(f"최적화 완료: {len(risk_adjusted)}개 시그널 선택")
            return risk_adjusted
            
        except Exception as e:
            logger.error(f"포트폴리오 시그널 최적화 실패: {str(e)}")
            return signals  # 실패시 원본 반환
    
    def _apply_diversification_filter(
        self,
        signals: List[TradingSignal],
        max_positions: int,
        max_sector_weight: float
    ) -> List[TradingSignal]:
        """다양성 필터 적용"""
        try:
            sector_counts = defaultdict(int)
            sector_weights = defaultdict(float)
            filtered_signals = []
            
            for signal in signals:
                if len(filtered_signals) >= max_positions:
                    break
                
                # 섹터 정보 확인
                sector = self._get_symbol_sector(signal.symbol)
                
                # 섹터 집중도 확인
                current_sector_weight = sector_weights[sector]
                signal_weight = signal.position_size or 0.05
                
                if current_sector_weight + signal_weight <= max_sector_weight:
                    filtered_signals.append(signal)
                    sector_counts[sector] += 1
                    sector_weights[sector] += signal_weight
                else:
                    # 섹터 한도 초과시 다른 섹터 우선
                    continue
            
            return filtered_signals
            
        except Exception as e:
            logger.error(f"다양성 필터 적용 실패: {str(e)}")
            return signals[:10]  # 실패시 상위 10개만
    
    def _optimize_by_correlation(self, signals: List[TradingSignal]) -> List[TradingSignal]:
        """상관관계 기반 최적화"""
        try:
            if len(signals) <= 2:
                return signals
            
            # 상관관계가 높은 쌍 찾기
            high_correlation_pairs = []
            
            for i in range(len(signals)):
                for j in range(i + 1, len(signals)):
                    symbol1 = signals[i].symbol
                    symbol2 = signals[j].symbol
                    
                    correlation = self._get_correlation(symbol1, symbol2)
                    
                    if correlation > 0.7:  # 높은 상관관계
                        high_correlation_pairs.append((i, j, correlation))
            
            # 상관관계가 높은 쌍에서 더 강한 시그널만 유지
            remove_indices = set()
            
            for i, j, correlation in sorted(high_correlation_pairs, key=lambda x: x[2], reverse=True):
                if i in remove_indices or j in remove_indices:
                    continue
                
                signal1 = signals[i]
                signal2 = signals[j]
                
                # 더 약한 시그널 제거
                if (signal1.strength.value * signal1.confidence) >= (signal2.strength.value * signal2.confidence):
                    remove_indices.add(j)
                else:
                    remove_indices.add(i)
            
            # 필터링된 시그널 반환
            optimized_signals = [
                signal for idx, signal in enumerate(signals)
                if idx not in remove_indices
            ]
            
            return optimized_signals
            
        except Exception as e:
            logger.error(f"상관관계 최적화 실패: {str(e)}")
            return signals
    
    def _apply_risk_adjustment(
        self, 
        signals: List[TradingSignal], 
        constraints: Dict[str, Any]
    ) -> List[TradingSignal]:
        """위험 조정 적용"""
        try:
            max_portfolio_risk = constraints.get("max_portfolio_risk", 0.15)
            
            # 위험도별 그룹화
            risk_groups = defaultdict(list)
            for signal in signals:
                risk_groups[signal.risk_level].append(signal)
            
            # 위험도 높은 시그널 수 제한
            adjusted_signals = []
            high_risk_count = 0
            max_high_risk = 2  # 최대 2개의 고위험 포지션
            
            # 낮은 위험부터 추가
            for risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.EXTREME]:
                group_signals = risk_groups[risk_level]
                
                if risk_level in [RiskLevel.HIGH, RiskLevel.EXTREME]:
                    # 고위험 시그널 수 제한
                    available_high_risk_slots = max_high_risk - high_risk_count
                    group_signals = group_signals[:available_high_risk_slots]
                    high_risk_count += len(group_signals)
                
                adjusted_signals.extend(group_signals)
            
            return adjusted_signals
            
        except Exception as e:
            logger.error(f"위험 조정 적용 실패: {str(e)}")
            return signals
    
    def _get_symbol_sector(self, symbol: str) -> str:
        """심볼의 섹터 정보 조회"""
        try:
            # 캐시된 정보 확인
            if symbol in self.sector_mapping:
                return self.sector_mapping[symbol]
            
            # 실제 구현시 데이터베이스나 API에서 조회
            # 여기서는 간단한 매핑 사용
            sector_map = {
                "AAPL": "Technology",
                "MSFT": "Technology", 
                "GOOGL": "Technology",
                "005930.KS": "Technology",  # 삼성전자
                "000660.KS": "Technology",  # SK하이닉스
                "035420.KS": "Technology",  # NAVER
            }
            
            sector = sector_map.get(symbol, "Unknown")
            self.sector_mapping[symbol] = sector
            
            return sector
            
        except Exception:
            return "Unknown"
    
    def _get_correlation(self, symbol1: str, symbol2: str) -> float:
        """두 심볼 간 상관관계 조회"""
        try:
            pair_key = f"{min(symbol1, symbol2)}_{max(symbol1, symbol2)}"
            
            if pair_key in self.correlation_data:
                return self.correlation_data[pair_key]
            
            # 실제 구현시 가격 데이터로 상관관계 계산
            # 여기서는 섹터 기반 추정
            sector1 = self._get_symbol_sector(symbol1)
            sector2 = self._get_symbol_sector(symbol2)
            
            if sector1 == sector2 and sector1 != "Unknown":
                correlation = 0.8  # 같은 섹터는 높은 상관관계
            else:
                correlation = 0.2  # 다른 섹터는 낮은 상관관계
            
            self.correlation_data[pair_key] = correlation
            return correlation
            
        except Exception:
            return 0.0


class SignalEngine:
    """시그널 생성 엔진 메인 클래스"""
    
    def __init__(self):
        self.aggregator = SignalAggregator()
        self.risk_manager = RiskManager()
        self.optimizer = SignalOptimizer()
        
        # 시그널 저장소
        self.active_signals: Dict[str, TradingSignal] = {}
        self.signal_history: Dict[str, List[TradingSignal]] = defaultdict(list)
        
        # 성능 추적
        self.performance_metrics = {
            "signals_generated": 0,
            "signals_executed": 0,
            "avg_confidence": 0.0,
            "success_rate": 0.0
        }
        
    async def generate_signal(
        self,
        symbol: str,
        analysis_results: List[AnalysisResult],
        portfolio_context: Dict[str, Any] = None
    ) -> Optional[TradingSignal]:
        """
        시그널 생성
        
        Args:
            symbol: 주식 심볼
            analysis_results: 분석 결과들
            portfolio_context: 포트폴리오 컨텍스트
            
        Returns:
            Optional[TradingSignal]: 생성된 시그널
        """
        try:
            logger.info(f"시그널 생성 시작: {symbol}")
            
            # 1. 분석 결과 집계
            raw_signal = self.aggregator.aggregate_analysis_results(symbol, analysis_results)
            
            if not raw_signal:
                logger.warning(f"시그널 집계 실패: {symbol}")
                return None
            
            # 2. 포지션 크기 계산
            if portfolio_context:
                portfolio_value = portfolio_context.get("portfolio_value", 100000)
                current_risk = portfolio_context.get("current_risk", 0.0)
                
                position_size = self.risk_manager.calculate_position_size(
                    raw_signal,
                    portfolio_value,
                    current_risk
                )
                raw_signal.position_size = position_size
            
            # 3. 시그널 검증
            existing_positions = portfolio_context.get("positions", []) if portfolio_context else []
            validation = self.risk_manager.validate_signal(raw_signal, existing_positions)
            
            if not validation["valid"]:
                logger.warning(f"시그널 검증 실패: {symbol} - {validation['blockers']}")
                return None
            
            # 4. 경고사항이 있으면 로깅
            if validation["warnings"]:
                logger.warning(f"시그널 경고사항: {symbol} - {validation['warnings']}")
            
            # 5. 활성 시그널에 추가
            self.active_signals[raw_signal.signal_id] = raw_signal
            self.signal_history[symbol].append(raw_signal)
            
            # 6. 성능 메트릭 업데이트
            self.performance_metrics["signals_generated"] += 1
            
            logger.info(f"시그널 생성 완료: {symbol}, ID: {raw_signal.signal_id}")
            return raw_signal
            
        except Exception as e:
            logger.error(f"시그널 생성 실패: {symbol} - {str(e)}")
            return None
    
    async def generate_portfolio_signals(
        self,
        portfolio_symbols: List[str],
        analysis_results_by_symbol: Dict[str, List[AnalysisResult]],
        portfolio_constraints: Dict[str, Any] = None
    ) -> PortfolioSignal:
        """
        포트폴리오 레벨 시그널 생성
        
        Args:
            portfolio_symbols: 포트폴리오 심볼들
            analysis_results_by_symbol: 심볼별 분석 결과
            portfolio_constraints: 포트폴리오 제약사항
            
        Returns:
            PortfolioSignal: 포트폴리오 시그널
        """
        try:
            logger.info(f"포트폴리오 시그널 생성: {len(portfolio_symbols)}개 종목")
            
            # 1. 개별 시그널 생성
            individual_signals = []
            
            for symbol in portfolio_symbols:
                analysis_results = analysis_results_by_symbol.get(symbol, [])
                if analysis_results:
                    signal = await self.generate_signal(symbol, analysis_results)
                    if signal:
                        individual_signals.append(signal)
            
            if not individual_signals:
                logger.warning("생성된 개별 시그널이 없음")
                return self._create_empty_portfolio_signal("default")
            
            # 2. 시그널 최적화
            optimized_signals = self.optimizer.optimize_portfolio_signals(
                individual_signals,
                portfolio_constraints
            )
            
            # 3. 포트폴리오 레벨 분석
            portfolio_analysis = self._analyze_portfolio_signals(optimized_signals)
            
            # 4. 포트폴리오 시그널 생성
            portfolio_signal = PortfolioSignal(
                portfolio_id=portfolio_constraints.get("portfolio_id", "default"),
                signals=optimized_signals,
                overall_direction=portfolio_analysis["direction"],
                risk_score=portfolio_analysis["risk_score"],
                diversification_score=portfolio_analysis["diversification_score"],
                correlation_warning=portfolio_analysis["correlation_warning"],
                rebalance_needed=portfolio_analysis["rebalance_needed"],
                suggested_actions=portfolio_analysis["suggested_actions"],
                created_at=datetime.utcnow()
            )
            
            logger.info(f"포트폴리오 시그널 생성 완료: {len(optimized_signals)}개 시그널")
            return portfolio_signal
            
        except Exception as e:
            logger.error(f"포트폴리오 시그널 생성 실패: {str(e)}")
            return self._create_empty_portfolio_signal("error")
    
    def _analyze_portfolio_signals(self, signals: List[TradingSignal]) -> Dict[str, Any]:
        """포트폴리오 시그널 분석"""
        try:
            if not signals:
                return {
                    "direction": "neutral",
                    "risk_score": 0.0,
                    "diversification_score": 0.0,
                    "correlation_warning": False,
                    "rebalance_needed": False,
                    "suggested_actions": []
                }
            
            # 전체 방향성 분석
            buy_count = sum(1 for s in signals if s.signal_type == SignalType.BUY)
            sell_count = sum(1 for s in signals if s.signal_type == SignalType.SELL)
            
            if buy_count > sell_count * 2:
                direction = "bullish"
            elif sell_count > buy_count * 2:
                direction = "bearish" 
            else:
                direction = "neutral"
            
            # 위험 점수 계산
            risk_scores = {
                RiskLevel.LOW: 1,
                RiskLevel.MEDIUM: 2,
                RiskLevel.HIGH: 3,
                RiskLevel.EXTREME: 4
            }
            
            avg_risk = sum(risk_scores[s.risk_level] for s in signals) / len(signals)
            risk_score = avg_risk / 4.0  # 0-1 정규화
            
            # 다양성 점수 계산
            sectors = set(self.optimizer._get_symbol_sector(s.symbol) for s in signals)
            diversification_score = min(len(sectors) / 5.0, 1.0)  # 5개 섹터면 최대 점수
            
            # 상관관계 경고
            correlation_warning = len(signals) > len(sectors) * 2  # 섹터당 2개 이상
            
            # 리밸런싱 필요성
            rebalance_needed = risk_score > 0.7 or not diversification_score > 0.5
            
            # 제안 액션
            suggested_actions = []
            if risk_score > 0.8:
                suggested_actions.append({"action": "reduce_risk", "priority": "high"})
            if diversification_score < 0.3:
                suggested_actions.append({"action": "improve_diversification", "priority": "medium"})
            if correlation_warning:
                suggested_actions.append({"action": "review_correlation", "priority": "low"})
            
            return {
                "direction": direction,
                "risk_score": risk_score,
                "diversification_score": diversification_score,
                "correlation_warning": correlation_warning,
                "rebalance_needed": rebalance_needed,
                "suggested_actions": suggested_actions
            }
            
        except Exception as e:
            logger.error(f"포트폴리오 분석 실패: {str(e)}")
            return {
                "direction": "unknown",
                "risk_score": 0.5,
                "diversification_score": 0.5,
                "correlation_warning": False,
                "rebalance_needed": False,
                "suggested_actions": []
            }
    
    def _create_empty_portfolio_signal(self, portfolio_id: str) -> PortfolioSignal:
        """빈 포트폴리오 시그널 생성"""
        return PortfolioSignal(
            portfolio_id=portfolio_id,
            signals=[],
            overall_direction="neutral",
            risk_score=0.0,
            diversification_score=0.0,
            correlation_warning=False,
            rebalance_needed=False,
            suggested_actions=[],
            created_at=datetime.utcnow()
        )
    
    def get_active_signals(self, symbol: str = None) -> List[TradingSignal]:
        """활성 시그널 조회"""
        try:
            current_time = datetime.utcnow()
            active_signals = []
            
            for signal in self.active_signals.values():
                # 만료되지 않은 시그널만
                if not signal.expires_at or signal.expires_at > current_time:
                    if not symbol or signal.symbol == symbol:
                        active_signals.append(signal)
            
            return active_signals
            
        except Exception as e:
            logger.error(f"활성 시그널 조회 실패: {str(e)}")
            return []
    
    def get_signal_performance(self, symbol: str = None) -> Dict[str, Any]:
        """시그널 성능 조회"""
        try:
            # 실제 구현시 실행 결과와 매칭하여 성과 계산
            return {
                "total_signals": self.performance_metrics["signals_generated"],
                "success_rate": self.performance_metrics.get("success_rate", 0.0),
                "avg_confidence": self.performance_metrics.get("avg_confidence", 0.0),
                "symbol_performance": {}  # 심볼별 성과
            }
            
        except Exception as e:
            logger.error(f"시그널 성능 조회 실패: {str(e)}")
            return {}
    
    def cleanup_expired_signals(self):
        """만료된 시그널 정리"""
        try:
            current_time = datetime.utcnow()
            expired_signal_ids = []
            
            for signal_id, signal in self.active_signals.items():
                if signal.expires_at and signal.expires_at <= current_time:
                    expired_signal_ids.append(signal_id)
            
            for signal_id in expired_signal_ids:
                del self.active_signals[signal_id]
            
            if expired_signal_ids:
                logger.info(f"만료된 시그널 정리: {len(expired_signal_ids)}개")
            
        except Exception as e:
            logger.error(f"시그널 정리 실패: {str(e)}")