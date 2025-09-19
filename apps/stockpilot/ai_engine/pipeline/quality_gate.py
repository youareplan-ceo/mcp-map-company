"""
품질 관문 모듈 - AI 분석 및 신호의 품질을 검증하고 관리
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import numpy as np
from collections import defaultdict, Counter
import json

from ..config.model_policy import TaskComplexity, ContentType
from .analysis_module import AnalysisResult, SentimentResult, TechnicalResult
from .signal_module import TradingSignal, SignalStrength, PortfolioSignal

logger = logging.getLogger(__name__)

class QualityLevel(Enum):
    """품질 수준 정의"""
    CRITICAL = "critical"  # 매우 높은 품질 요구 (실제 거래 신호)
    HIGH = "high"         # 높은 품질 (포트폴리오 분석)
    MEDIUM = "medium"     # 중간 품질 (일반 분석)
    LOW = "low"          # 낮은 품질 (탐색적 분석)

class ValidationResult(Enum):
    """검증 결과"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"

@dataclass
class QualityMetric:
    """품질 메트릭"""
    name: str
    score: float  # 0.0 - 1.0
    threshold: float
    weight: float = 1.0
    details: Dict[str, Any] = field(default_factory=dict)
    status: ValidationResult = ValidationResult.PASS

@dataclass
class QualityReport:
    """품질 보고서"""
    overall_score: float
    quality_level: QualityLevel
    validation_result: ValidationResult
    metrics: List[QualityMetric]
    recommendations: List[str]
    timestamp: datetime
    processing_time_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)

class DataQualityValidator:
    """데이터 품질 검증기"""
    
    def __init__(self):
        self.thresholds = {
            QualityLevel.CRITICAL: 0.95,
            QualityLevel.HIGH: 0.85,
            QualityLevel.MEDIUM: 0.75,
            QualityLevel.LOW: 0.60
        }
    
    def validate_price_data(self, price_data: List[Dict]) -> QualityMetric:
        """가격 데이터 품질 검증"""
        if not price_data:
            return QualityMetric(
                name="price_data_completeness",
                score=0.0,
                threshold=0.8,
                status=ValidationResult.FAIL,
                details={"error": "No price data available"}
            )
        
        # 완전성 검사
        total_expected = len(price_data)
        valid_records = sum(1 for data in price_data 
                          if all(key in data and data[key] is not None 
                               for key in ['open', 'high', 'low', 'close', 'volume']))
        
        completeness_score = valid_records / total_expected if total_expected > 0 else 0.0
        
        # 이상치 검사
        closes = [float(data['close']) for data in price_data if 'close' in data and data['close'] is not None]
        outlier_score = 1.0
        if len(closes) > 5:
            q1, q3 = np.percentile(closes, [25, 75])
            iqr = q3 - q1
            outliers = [c for c in closes if c < q1 - 1.5 * iqr or c > q3 + 1.5 * iqr]
            outlier_score = 1.0 - (len(outliers) / len(closes))
        
        overall_score = (completeness_score * 0.7 + outlier_score * 0.3)
        
        return QualityMetric(
            name="price_data_quality",
            score=overall_score,
            threshold=0.8,
            details={
                "total_records": total_expected,
                "valid_records": valid_records,
                "completeness": completeness_score,
                "outlier_score": outlier_score
            },
            status=ValidationResult.PASS if overall_score >= 0.8 else ValidationResult.WARNING
        )
    
    def validate_news_data(self, news_data: List[Dict]) -> QualityMetric:
        """뉴스 데이터 품질 검증"""
        if not news_data:
            return QualityMetric(
                name="news_data_availability",
                score=0.5,
                threshold=0.6,
                status=ValidationResult.WARNING,
                details={"warning": "No news data available"}
            )
        
        # 뉴스 품질 메트릭
        total_news = len(news_data)
        valid_news = sum(1 for news in news_data 
                        if all(key in news and news[key] 
                              for key in ['title', 'content', 'published_date']))
        
        # 최신성 검사 (24시간 이내)
        recent_threshold = datetime.now() - timedelta(hours=24)
        recent_news = sum(1 for news in news_data 
                         if 'published_date' in news and 
                         datetime.fromisoformat(news['published_date']) > recent_threshold)
        
        completeness_score = valid_news / total_news if total_news > 0 else 0.0
        freshness_score = min(1.0, recent_news / max(1, total_news * 0.3))  # 30% 이상이 최신이면 1.0
        
        overall_score = (completeness_score * 0.6 + freshness_score * 0.4)
        
        return QualityMetric(
            name="news_data_quality",
            score=overall_score,
            threshold=0.6,
            details={
                "total_news": total_news,
                "valid_news": valid_news,
                "recent_news": recent_news,
                "completeness": completeness_score,
                "freshness": freshness_score
            },
            status=ValidationResult.PASS if overall_score >= 0.6 else ValidationResult.WARNING
        )

class AnalysisQualityValidator:
    """분석 품질 검증기"""
    
    def validate_sentiment_analysis(self, sentiment_result: SentimentResult) -> QualityMetric:
        """감정 분석 품질 검증"""
        score = sentiment_result.confidence
        
        # 신뢰도 기반 검증
        if score >= 0.8:
            status = ValidationResult.PASS
        elif score >= 0.6:
            status = ValidationResult.WARNING
        else:
            status = ValidationResult.FAIL
        
        return QualityMetric(
            name="sentiment_analysis_quality",
            score=score,
            threshold=0.6,
            details={
                "sentiment": sentiment_result.sentiment.value,
                "confidence": sentiment_result.confidence,
                "score_magnitude": abs(sentiment_result.score)
            },
            status=status
        )
    
    def validate_technical_analysis(self, technical_result: TechnicalResult) -> QualityMetric:
        """기술적 분석 품질 검증"""
        indicators = technical_result.indicators
        
        # 지표 완전성 검사
        expected_indicators = ['rsi', 'macd', 'bollinger_bands', 'moving_averages']
        available_indicators = list(indicators.keys())
        completeness = len(set(available_indicators) & set(expected_indicators)) / len(expected_indicators)
        
        # 지표 값 유효성 검사
        validity_scores = []
        for indicator, value in indicators.items():
            if indicator == 'rsi' and isinstance(value, (int, float)):
                validity_scores.append(1.0 if 0 <= value <= 100 else 0.5)
            elif indicator == 'macd' and isinstance(value, dict):
                validity_scores.append(1.0 if all(k in value for k in ['macd', 'signal', 'histogram']) else 0.5)
            else:
                validity_scores.append(0.8)  # 기본 유효성 점수
        
        validity = np.mean(validity_scores) if validity_scores else 0.0
        overall_score = (completeness * 0.4 + validity * 0.6)
        
        return QualityMetric(
            name="technical_analysis_quality",
            score=overall_score,
            threshold=0.7,
            details={
                "completeness": completeness,
                "validity": validity,
                "available_indicators": available_indicators,
                "confidence": technical_result.confidence
            },
            status=ValidationResult.PASS if overall_score >= 0.7 else ValidationResult.WARNING
        )

class SignalQualityValidator:
    """신호 품질 검증기"""
    
    def __init__(self):
        self.signal_history = defaultdict(list)
    
    def validate_trading_signal(self, signal: TradingSignal) -> QualityMetric:
        """거래 신호 품질 검증"""
        score_components = []
        
        # 신호 강도와 신뢰도 검증
        strength_score = self._get_strength_score(signal.strength)
        confidence_score = signal.confidence
        
        score_components.extend([strength_score, confidence_score])
        
        # 가격 목표와 현재가 비교
        price_logic_score = 1.0
        if signal.target_price and signal.current_price:
            if signal.action == "BUY" and signal.target_price <= signal.current_price:
                price_logic_score = 0.3  # 매수 신호인데 목표가가 현재가보다 낮음
            elif signal.action == "SELL" and signal.target_price >= signal.current_price:
                price_logic_score = 0.3  # 매도 신호인데 목표가가 현재가보다 높음
        
        score_components.append(price_logic_score)
        
        # 위험 관리 요소 검증
        risk_mgmt_score = 1.0
        if not signal.stop_loss:
            risk_mgmt_score -= 0.3
        if not signal.position_size or signal.position_size <= 0:
            risk_mgmt_score -= 0.2
        
        score_components.append(max(0.0, risk_mgmt_score))
        
        # 일관성 검사 (최근 신호들과 비교)
        consistency_score = self._check_signal_consistency(signal)
        score_components.append(consistency_score)
        
        overall_score = np.mean(score_components)
        
        return QualityMetric(
            name="trading_signal_quality",
            score=overall_score,
            threshold=0.8,
            details={
                "strength_score": strength_score,
                "confidence_score": confidence_score,
                "price_logic_score": price_logic_score,
                "risk_mgmt_score": max(0.0, risk_mgmt_score),
                "consistency_score": consistency_score,
                "components": score_components
            },
            status=ValidationResult.PASS if overall_score >= 0.8 else ValidationResult.WARNING
        )
    
    def _get_strength_score(self, strength: SignalStrength) -> float:
        """신호 강도 점수 변환"""
        strength_scores = {
            SignalStrength.VERY_STRONG: 1.0,
            SignalStrength.STRONG: 0.8,
            SignalStrength.MODERATE: 0.6,
            SignalStrength.WEAK: 0.4,
            SignalStrength.VERY_WEAK: 0.2
        }
        return strength_scores.get(strength, 0.5)
    
    def _check_signal_consistency(self, signal: TradingSignal) -> float:
        """신호 일관성 검사"""
        symbol = signal.symbol
        recent_signals = self.signal_history[symbol][-5:]  # 최근 5개 신호
        
        if len(recent_signals) < 2:
            return 0.8  # 충분한 이력이 없으면 중립 점수
        
        # 액션 일관성 (너무 자주 바뀌는지 확인)
        actions = [s.action for s in recent_signals]
        action_changes = sum(1 for i in range(1, len(actions)) if actions[i] != actions[i-1])
        consistency_penalty = min(0.3, action_changes * 0.1)
        
        return max(0.5, 1.0 - consistency_penalty)

class QualityGate:
    """품질 관문 - 모든 품질 검증을 통합 관리"""
    
    def __init__(self):
        self.data_validator = DataQualityValidator()
        self.analysis_validator = AnalysisQualityValidator()
        self.signal_validator = SignalQualityValidator()
        
        # 품질 가중치 설정
        self.quality_weights = {
            "data_quality": 0.25,
            "analysis_quality": 0.35,
            "signal_quality": 0.40
        }
    
    async def validate_analysis_pipeline(
        self,
        symbol: str,
        price_data: List[Dict],
        news_data: List[Dict],
        analysis_result: AnalysisResult,
        quality_level: QualityLevel = QualityLevel.MEDIUM
    ) -> QualityReport:
        """분석 파이프라인 전체 품질 검증"""
        start_time = datetime.now()
        
        try:
            metrics = []
            
            # 데이터 품질 검증
            price_metric = self.data_validator.validate_price_data(price_data)
            news_metric = self.data_validator.validate_news_data(news_data)
            metrics.extend([price_metric, news_metric])
            
            # 분석 품질 검증
            if analysis_result.sentiment:
                sentiment_metric = self.analysis_validator.validate_sentiment_analysis(analysis_result.sentiment)
                metrics.append(sentiment_metric)
            
            if analysis_result.technical:
                technical_metric = self.analysis_validator.validate_technical_analysis(analysis_result.technical)
                metrics.append(technical_metric)
            
            # 전체 품질 점수 계산
            data_scores = [price_metric.score, news_metric.score]
            analysis_scores = [m.score for m in metrics if m.name.endswith('_analysis_quality')]
            
            weighted_score = (
                np.mean(data_scores) * self.quality_weights["data_quality"] +
                (np.mean(analysis_scores) if analysis_scores else 0.7) * self.quality_weights["analysis_quality"] +
                0.7 * self.quality_weights["signal_quality"]  # 신호가 없을 때 기본값
            )
            
            # 검증 결과 결정
            threshold = self.data_validator.thresholds[quality_level]
            validation_result = (
                ValidationResult.PASS if weighted_score >= threshold
                else ValidationResult.WARNING if weighted_score >= threshold - 0.1
                else ValidationResult.FAIL
            )
            
            # 개선 권고사항 생성
            recommendations = self._generate_recommendations(metrics, validation_result)
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return QualityReport(
                overall_score=weighted_score,
                quality_level=quality_level,
                validation_result=validation_result,
                metrics=metrics,
                recommendations=recommendations,
                timestamp=start_time,
                processing_time_ms=processing_time,
                metadata={"symbol": symbol, "data_points": len(price_data), "news_count": len(news_data)}
            )
            
        except Exception as e:
            logger.error(f"Quality validation failed for {symbol}: {e}")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return QualityReport(
                overall_score=0.0,
                quality_level=quality_level,
                validation_result=ValidationResult.FAIL,
                metrics=[],
                recommendations=[f"Quality validation failed: {str(e)}"],
                timestamp=start_time,
                processing_time_ms=processing_time,
                metadata={"symbol": symbol, "error": str(e)}
            )
    
    async def validate_trading_signal(
        self,
        signal: TradingSignal,
        quality_level: QualityLevel = QualityLevel.CRITICAL
    ) -> QualityReport:
        """거래 신호 품질 검증"""
        start_time = datetime.now()
        
        try:
            # 신호 품질 검증
            signal_metric = self.signal_validator.validate_trading_signal(signal)
            
            # 신호 이력에 추가
            self.signal_validator.signal_history[signal.symbol].append(signal)
            
            # 전체 품질 점수
            overall_score = signal_metric.score
            
            # 검증 결과 결정
            threshold = self.data_validator.thresholds[quality_level]
            validation_result = signal_metric.status
            
            if overall_score < threshold:
                validation_result = ValidationResult.FAIL
            
            # 권고사항 생성
            recommendations = self._generate_signal_recommendations(signal_metric, signal)
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return QualityReport(
                overall_score=overall_score,
                quality_level=quality_level,
                validation_result=validation_result,
                metrics=[signal_metric],
                recommendations=recommendations,
                timestamp=start_time,
                processing_time_ms=processing_time,
                metadata={"symbol": signal.symbol, "action": signal.action, "strength": signal.strength.value}
            )
            
        except Exception as e:
            logger.error(f"Signal quality validation failed for {signal.symbol}: {e}")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return QualityReport(
                overall_score=0.0,
                quality_level=quality_level,
                validation_result=ValidationResult.FAIL,
                metrics=[],
                recommendations=[f"Signal validation failed: {str(e)}"],
                timestamp=start_time,
                processing_time_ms=processing_time,
                metadata={"symbol": signal.symbol, "error": str(e)}
            )
    
    async def validate_portfolio_signals(
        self,
        portfolio_signal: PortfolioSignal,
        quality_level: QualityLevel = QualityLevel.HIGH
    ) -> QualityReport:
        """포트폴리오 신호 품질 검증"""
        start_time = datetime.now()
        
        try:
            metrics = []
            
            # 개별 신호들 검증
            individual_scores = []
            for signal in portfolio_signal.signals:
                signal_metric = self.signal_validator.validate_trading_signal(signal)
                metrics.append(signal_metric)
                individual_scores.append(signal_metric.score)
            
            # 포트폴리오 수준 검증
            portfolio_metrics = self._validate_portfolio_level(portfolio_signal)
            metrics.extend(portfolio_metrics)
            
            # 전체 점수 계산
            individual_avg = np.mean(individual_scores) if individual_scores else 0.0
            portfolio_avg = np.mean([m.score for m in portfolio_metrics])
            
            overall_score = individual_avg * 0.7 + portfolio_avg * 0.3
            
            # 검증 결과 결정
            threshold = self.data_validator.thresholds[quality_level]
            validation_result = (
                ValidationResult.PASS if overall_score >= threshold
                else ValidationResult.WARNING if overall_score >= threshold - 0.1
                else ValidationResult.FAIL
            )
            
            # 권고사항 생성
            recommendations = self._generate_portfolio_recommendations(metrics, portfolio_signal)
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return QualityReport(
                overall_score=overall_score,
                quality_level=quality_level,
                validation_result=validation_result,
                metrics=metrics,
                recommendations=recommendations,
                timestamp=start_time,
                processing_time_ms=processing_time,
                metadata={
                    "portfolio_id": portfolio_signal.portfolio_id,
                    "signal_count": len(portfolio_signal.signals),
                    "total_allocation": sum(s.position_size or 0 for s in portfolio_signal.signals)
                }
            )
            
        except Exception as e:
            logger.error(f"Portfolio validation failed: {e}")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return QualityReport(
                overall_score=0.0,
                quality_level=quality_level,
                validation_result=ValidationResult.FAIL,
                metrics=[],
                recommendations=[f"Portfolio validation failed: {str(e)}"],
                timestamp=start_time,
                processing_time_ms=processing_time,
                metadata={"error": str(e)}
            )
    
    def _validate_portfolio_level(self, portfolio_signal: PortfolioSignal) -> List[QualityMetric]:
        """포트폴리오 수준 검증"""
        metrics = []
        
        # 분산 투자 검증
        sectors = [signal.metadata.get('sector', 'unknown') for signal in portfolio_signal.signals]
        sector_counts = Counter(sectors)
        diversification_score = min(1.0, len(sector_counts) / max(1, len(portfolio_signal.signals) * 0.5))
        
        metrics.append(QualityMetric(
            name="portfolio_diversification",
            score=diversification_score,
            threshold=0.6,
            details={"sector_distribution": dict(sector_counts)},
            status=ValidationResult.PASS if diversification_score >= 0.6 else ValidationResult.WARNING
        ))
        
        # 포지션 사이즈 분배 검증
        position_sizes = [signal.position_size or 0 for signal in portfolio_signal.signals]
        total_allocation = sum(position_sizes)
        
        allocation_score = 1.0
        if total_allocation > 1.0:  # 100% 초과
            allocation_score = 0.3
        elif total_allocation < 0.8:  # 80% 미만
            allocation_score = 0.7
        
        metrics.append(QualityMetric(
            name="portfolio_allocation",
            score=allocation_score,
            threshold=0.7,
            details={"total_allocation": total_allocation, "position_sizes": position_sizes},
            status=ValidationResult.PASS if allocation_score >= 0.7 else ValidationResult.WARNING
        ))
        
        return metrics
    
    def _generate_recommendations(self, metrics: List[QualityMetric], validation_result: ValidationResult) -> List[str]:
        """개선 권고사항 생성"""
        recommendations = []
        
        for metric in metrics:
            if metric.status == ValidationResult.FAIL:
                if metric.name == "price_data_quality":
                    recommendations.append("가격 데이터 품질 개선 필요 - 데이터 소스 확인 및 이상치 제거")
                elif metric.name == "news_data_quality":
                    recommendations.append("뉴스 데이터 보강 필요 - 최신 뉴스 수집 및 데이터 완전성 개선")
                elif metric.name == "sentiment_analysis_quality":
                    recommendations.append("감정 분석 신뢰도 향상 필요 - 모델 재학습 또는 데이터 전처리 개선")
                elif metric.name == "technical_analysis_quality":
                    recommendations.append("기술적 분석 지표 보완 필요 - 추가 지표 계산 및 검증")
            
            elif metric.status == ValidationResult.WARNING:
                recommendations.append(f"{metric.name} 품질 주의 - 점수: {metric.score:.2f}")
        
        if validation_result == ValidationResult.FAIL:
            recommendations.append("전체 품질이 임계값 미달 - 상위 모델 사용 또는 분석 재실행 권장")
        
        return recommendations
    
    def _generate_signal_recommendations(self, metric: QualityMetric, signal: TradingSignal) -> List[str]:
        """신호 권고사항 생성"""
        recommendations = []
        
        if metric.score < 0.8:
            recommendations.append("신호 품질 향상 필요")
            
        if not signal.stop_loss:
            recommendations.append("손절가 설정 권장")
            
        if not signal.position_size or signal.position_size <= 0:
            recommendations.append("포지션 사이즈 조정 필요")
            
        if signal.confidence < 0.7:
            recommendations.append("신호 신뢰도 낮음 - 추가 분석 권장")
        
        return recommendations
    
    def _generate_portfolio_recommendations(
        self, 
        metrics: List[QualityMetric], 
        portfolio_signal: PortfolioSignal
    ) -> List[str]:
        """포트폴리오 권고사항 생성"""
        recommendations = []
        
        for metric in metrics:
            if metric.name == "portfolio_diversification" and metric.score < 0.6:
                recommendations.append("포트폴리오 분산 투자 개선 필요 - 다양한 섹터 포함")
                
            if metric.name == "portfolio_allocation" and metric.score < 0.7:
                if metric.details.get("total_allocation", 0) > 1.0:
                    recommendations.append("포트폴리오 할당 비율 조정 필요 - 총 할당 100% 초과")
                else:
                    recommendations.append("포트폴리오 할당 비율 최적화 필요")
        
        # 개별 신호 품질이 낮은 경우
        low_quality_signals = [m for m in metrics if m.name == "trading_signal_quality" and m.score < 0.6]
        if low_quality_signals:
            recommendations.append(f"품질이 낮은 신호 {len(low_quality_signals)}개 재검토 필요")
        
        return recommendations

# 품질 관문 인스턴스 생성
quality_gate = QualityGate()

async def validate_analysis(
    symbol: str,
    price_data: List[Dict],
    news_data: List[Dict],
    analysis_result: AnalysisResult,
    quality_level: QualityLevel = QualityLevel.MEDIUM
) -> QualityReport:
    """분석 결과 품질 검증"""
    return await quality_gate.validate_analysis_pipeline(
        symbol, price_data, news_data, analysis_result, quality_level
    )

async def validate_signal(
    signal: TradingSignal,
    quality_level: QualityLevel = QualityLevel.CRITICAL
) -> QualityReport:
    """거래 신호 품질 검증"""
    return await quality_gate.validate_trading_signal(signal, quality_level)

async def validate_portfolio(
    portfolio_signal: PortfolioSignal,
    quality_level: QualityLevel = QualityLevel.HIGH
) -> QualityReport:
    """포트폴리오 신호 품질 검증"""
    return await quality_gate.validate_portfolio_signals(portfolio_signal, quality_level)