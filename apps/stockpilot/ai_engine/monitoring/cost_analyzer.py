"""
비용 분석 모듈 - AI 엔진 비용을 심층 분석하고 최적화 방안 제시
"""

import logging
import asyncio
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import json
from collections import defaultdict, deque
import matplotlib.pyplot as plt
import io
import base64

from .usage_tracker import UsageTracker, ModelUsageRecord, MetricType
from ..config.model_policy import ModelTier, MODEL_CONFIGS

logger = logging.getLogger(__name__)

class CostCategory(Enum):
    """비용 카테고리"""
    MODEL_INFERENCE = "model_inference"
    EMBEDDING_GENERATION = "embedding_generation"
    VECTOR_STORAGE = "vector_storage"
    CACHE_STORAGE = "cache_storage"
    DATA_TRANSFER = "data_transfer"

class AlertType(Enum):
    """알림 타입"""
    BUDGET_EXCEEDED = "budget_exceeded"
    UNUSUAL_SPIKE = "unusual_spike"
    EFFICIENCY_DROP = "efficiency_drop"
    EXPENSIVE_QUERY = "expensive_query"
    MODEL_UNDERUTILIZATION = "model_underutilization"

@dataclass
class CostAlert:
    """비용 알림"""
    alert_type: AlertType
    severity: str  # "low", "medium", "high", "critical"
    message: str
    current_value: float
    threshold: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    recommended_actions: List[str] = field(default_factory=list)

@dataclass
class CostForecast:
    """비용 예측"""
    period_days: int
    predicted_cost: float
    confidence_interval: Tuple[float, float]
    prediction_method: str
    factors: Dict[str, float]
    timestamp: datetime

@dataclass
class EfficiencyMetric:
    """효율성 메트릭"""
    metric_name: str
    current_value: float
    target_value: float
    improvement_potential: float
    unit: str
    recommendations: List[str]

@dataclass
class CostOptimizationRecommendation:
    """비용 최적화 권고"""
    category: str
    priority: str  # "high", "medium", "low"
    description: str
    estimated_savings: float
    implementation_effort: str  # "easy", "medium", "hard"
    impact_on_quality: str  # "none", "minimal", "moderate", "high"
    action_items: List[str]

class CostAnalyzer:
    """비용 분석기"""
    
    def __init__(self, usage_tracker: UsageTracker):
        self.usage_tracker = usage_tracker
        self.budget_limits = {}  # 예산 한도
        self.alert_thresholds = {
            AlertType.BUDGET_EXCEEDED: 0.9,  # 예산의 90%
            AlertType.UNUSUAL_SPIKE: 2.0,    # 평균의 200%
            AlertType.EFFICIENCY_DROP: 0.7,  # 효율성 70% 미만
            AlertType.EXPENSIVE_QUERY: 1.0,  # $1 이상
            AlertType.MODEL_UNDERUTILIZATION: 0.3  # 활용도 30% 미만
        }
        self.cost_history = deque(maxlen=1000)
        self.alerts = deque(maxlen=100)
    
    def set_budget_limit(self, period: str, amount: float):
        """예산 한도 설정"""
        self.budget_limits[period] = amount
        logger.info(f"Budget limit set: {period} = ${amount:.2f}")
    
    async def analyze_cost_trends(self, days: int = 30) -> Dict[str, Any]:
        """비용 트렌드 분석"""
        try:
            cost_analysis = await self.usage_tracker.get_cost_analysis(days)
            
            # 트렌드 계산
            daily_costs = cost_analysis.get("daily_costs", {})
            if len(daily_costs) < 7:
                return {"error": "Insufficient data for trend analysis"}
            
            # 일별 비용을 시계열로 변환
            dates = sorted(daily_costs.keys())
            costs = [daily_costs[d] for d in dates]
            
            # 이동 평균 계산
            window_size = min(7, len(costs))
            moving_avg = self._calculate_moving_average(costs, window_size)
            
            # 트렌드 방향 및 강도
            trend_direction, trend_strength = self._calculate_trend(costs)
            
            # 계절성 패턴 분석
            seasonal_pattern = self._analyze_seasonal_patterns(daily_costs)
            
            # 변동성 분석
            volatility = np.std(costs) if len(costs) > 1 else 0
            
            # 예측 생성
            forecast = await self._generate_cost_forecast(costs, 7)
            
            return {
                "period": f"Last {days} days",
                "trend_direction": trend_direction,
                "trend_strength": trend_strength,
                "moving_average": moving_avg,
                "volatility": volatility,
                "seasonal_patterns": seasonal_pattern,
                "forecast": forecast,
                "cost_efficiency_score": self._calculate_efficiency_score(cost_analysis),
                "recommendations": self._generate_trend_recommendations(
                    trend_direction, trend_strength, volatility
                )
            }
            
        except Exception as e:
            logger.error(f"Cost trend analysis failed: {e}")
            return {"error": str(e)}
    
    async def analyze_model_efficiency(self) -> Dict[str, Any]:
        """모델 효율성 분석"""
        try:
            # 최근 30일 데이터 조회
            records = await self.usage_tracker.db.get_usage_records(
                start_date=datetime.now() - timedelta(days=30),
                limit=10000
            )
            
            if not records:
                return {"error": "No usage data available"}
            
            # 모델별 효율성 메트릭
            model_metrics = defaultdict(lambda: {
                "total_requests": 0,
                "total_cost": 0.0,
                "total_tokens": 0,
                "avg_response_time": 0.0,
                "success_rate": 0.0,
                "cache_hit_rate": 0.0,
                "cost_per_token": 0.0,
                "cost_per_success": 0.0
            })
            
            for record in records:
                metrics = model_metrics[record.model_name]
                metrics["total_requests"] += 1
                metrics["total_cost"] += record.cost
                metrics["total_tokens"] += record.total_tokens
                metrics["avg_response_time"] += record.response_time_ms
                
                if record.success:
                    metrics["success_rate"] += 1
                if record.cache_hit:
                    metrics["cache_hit_rate"] += 1
            
            # 평균값 계산
            for model, metrics in model_metrics.items():
                if metrics["total_requests"] > 0:
                    metrics["avg_response_time"] /= metrics["total_requests"]
                    metrics["success_rate"] /= metrics["total_requests"]
                    metrics["cache_hit_rate"] /= metrics["total_requests"]
                    
                    if metrics["total_tokens"] > 0:
                        metrics["cost_per_token"] = metrics["total_cost"] / metrics["total_tokens"]
                    
                    successful_requests = metrics["success_rate"] * metrics["total_requests"]
                    if successful_requests > 0:
                        metrics["cost_per_success"] = metrics["total_cost"] / successful_requests
            
            # 효율성 점수 계산
            efficiency_scores = {}
            for model, metrics in model_metrics.items():
                score = self._calculate_model_efficiency_score(metrics)
                efficiency_scores[model] = score
            
            # 최적화 권고
            recommendations = self._generate_efficiency_recommendations(model_metrics)
            
            return {
                "model_metrics": dict(model_metrics),
                "efficiency_scores": efficiency_scores,
                "best_performing_model": max(efficiency_scores, key=efficiency_scores.get) if efficiency_scores else None,
                "worst_performing_model": min(efficiency_scores, key=efficiency_scores.get) if efficiency_scores else None,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Model efficiency analysis failed: {e}")
            return {"error": str(e)}
    
    async def generate_cost_alerts(self) -> List[CostAlert]:
        """비용 알림 생성"""
        alerts = []
        
        try:
            # 현재 비용 상태 확인
            current_stats = await self.usage_tracker.get_real_time_stats()
            daily_summary = await self.usage_tracker.get_usage_summary(
                start_date=date.today(),
                end_date=date.today()
            )
            
            # 예산 초과 확인
            if "daily" in self.budget_limits:
                daily_budget = self.budget_limits["daily"]
                current_cost = daily_summary.get("total_cost", 0)
                
                if current_cost >= daily_budget * self.alert_thresholds[AlertType.BUDGET_EXCEEDED]:
                    alerts.append(CostAlert(
                        alert_type=AlertType.BUDGET_EXCEEDED,
                        severity="high" if current_cost >= daily_budget else "medium",
                        message=f"Daily cost (${current_cost:.2f}) approaching/exceeding budget (${daily_budget:.2f})",
                        current_value=current_cost,
                        threshold=daily_budget,
                        timestamp=datetime.now(),
                        recommended_actions=[
                            "Consider using lower-tier models for non-critical tasks",
                            "Enable more aggressive caching",
                            "Review and optimize high-cost queries"
                        ]
                    ))
            
            # 비정상적 스파이크 확인
            recent_costs = await self._get_recent_hourly_costs(24)
            if len(recent_costs) >= 6:  # 최소 6시간 데이터 필요
                avg_cost = np.mean(recent_costs[:-2])  # 최근 2시간 제외한 평균
                current_cost = np.mean(recent_costs[-2:])  # 최근 2시간 평균
                
                if current_cost > avg_cost * self.alert_thresholds[AlertType.UNUSUAL_SPIKE]:
                    alerts.append(CostAlert(
                        alert_type=AlertType.UNUSUAL_SPIKE,
                        severity="medium",
                        message=f"Unusual cost spike detected: ${current_cost:.2f}/hour vs ${avg_cost:.2f}/hour average",
                        current_value=current_cost,
                        threshold=avg_cost * self.alert_thresholds[AlertType.UNUSUAL_SPIKE],
                        timestamp=datetime.now(),
                        recommended_actions=[
                            "Investigate recent high-cost requests",
                            "Check for runaway processes or bulk operations",
                            "Review current model selection strategy"
                        ]
                    ))
            
            # 비싼 쿼리 확인
            expensive_threshold = self.alert_thresholds[AlertType.EXPENSIVE_QUERY]
            recent_records = await self.usage_tracker.db.get_usage_records(
                start_date=datetime.now() - timedelta(hours=1),
                limit=100
            )
            
            expensive_queries = [r for r in recent_records if r.cost > expensive_threshold]
            if expensive_queries:
                alerts.append(CostAlert(
                    alert_type=AlertType.EXPENSIVE_QUERY,
                    severity="low",
                    message=f"Found {len(expensive_queries)} expensive queries (>${expensive_threshold:.2f}) in the last hour",
                    current_value=len(expensive_queries),
                    threshold=0,
                    timestamp=datetime.now(),
                    metadata={"expensive_queries": [
                        {"request_id": q.request_id, "cost": q.cost, "model": q.model_name}
                        for q in expensive_queries[:5]
                    ]},
                    recommended_actions=[
                        "Review query optimization techniques",
                        "Consider prompt compression for large inputs",
                        "Use model tier downgrade for appropriate tasks"
                    ]
                ))
            
            # 알림 저장
            for alert in alerts:
                self.alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Cost alert generation failed: {e}")
            return []
    
    async def generate_optimization_recommendations(self) -> List[CostOptimizationRecommendation]:
        """비용 최적화 권고사항 생성"""
        recommendations = []
        
        try:
            # 모델 효율성 분석 기반 권고
            efficiency_analysis = await self.analyze_model_efficiency()
            model_metrics = efficiency_analysis.get("model_metrics", {})
            
            # 낮은 활용도 모델 확인
            for model, metrics in model_metrics.items():
                if metrics["total_requests"] > 0 and metrics["success_rate"] < 0.8:
                    recommendations.append(CostOptimizationRecommendation(
                        category="model_selection",
                        priority="medium",
                        description=f"Model {model} has low success rate ({metrics['success_rate']:.1%})",
                        estimated_savings=metrics["total_cost"] * (1 - metrics["success_rate"]) * 0.5,
                        implementation_effort="easy",
                        impact_on_quality="minimal",
                        action_items=[
                            f"Review error patterns for {model}",
                            "Consider alternative models for failed tasks",
                            "Implement better error handling and retry logic"
                        ]
                    ))
            
            # 캐시 활용도 개선
            overall_cache_hit_rate = await self._get_overall_cache_hit_rate()
            if overall_cache_hit_rate < 0.6:
                estimated_savings = await self._estimate_cache_savings(overall_cache_hit_rate)
                
                recommendations.append(CostOptimizationRecommendation(
                    category="caching",
                    priority="high",
                    description=f"Low cache hit rate ({overall_cache_hit_rate:.1%}) indicates optimization opportunity",
                    estimated_savings=estimated_savings,
                    implementation_effort="medium",
                    impact_on_quality="none",
                    action_items=[
                        "Increase cache TTL for stable content",
                        "Implement prompt normalization for better cache hits",
                        "Add semantic caching for similar queries"
                    ]
                ))
            
            # 토큰 효율성 개선
            high_token_models = await self._identify_high_token_usage_patterns()
            if high_token_models:
                recommendations.append(CostOptimizationRecommendation(
                    category="token_optimization",
                    priority="medium",
                    description="High token usage detected in certain request patterns",
                    estimated_savings=sum(pattern["potential_savings"] for pattern in high_token_models),
                    implementation_effort="medium",
                    impact_on_quality="minimal",
                    action_items=[
                        "Implement prompt compression techniques",
                        "Use summarization for long context inputs",
                        "Optimize system prompts for brevity"
                    ]
                ))
            
            # 모델 티어 최적화
            tier_optimization = await self._analyze_tier_optimization_opportunities()
            if tier_optimization["potential_savings"] > 0:
                recommendations.append(CostOptimizationRecommendation(
                    category="model_tier",
                    priority="high",
                    description="Opportunities to use lower-cost model tiers for suitable tasks",
                    estimated_savings=tier_optimization["potential_savings"],
                    implementation_effort="easy",
                    impact_on_quality="moderate",
                    action_items=[
                        "Implement smarter model selection based on task complexity",
                        "Use A/B testing to validate model tier downgrades",
                        "Set up quality gates for tier selection validation"
                    ]
                ))
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Optimization recommendation generation failed: {e}")
            return []
    
    async def generate_cost_report(self, period_days: int = 30) -> Dict[str, Any]:
        """종합 비용 리포트 생성"""
        try:
            # 기본 비용 분석
            cost_analysis = await self.usage_tracker.get_cost_analysis(period_days)
            
            # 트렌드 분석
            trend_analysis = await self.analyze_cost_trends(period_days)
            
            # 모델 효율성 분석
            efficiency_analysis = await self.analyze_model_efficiency()
            
            # 알림 및 권고사항
            alerts = await self.generate_cost_alerts()
            recommendations = await self.generate_optimization_recommendations()
            
            # 예측
            forecast = await self._generate_detailed_forecast(period_days)
            
            # ROI 계산
            roi_analysis = await self._calculate_roi_metrics()
            
            return {
                "report_period": f"Last {period_days} days",
                "generated_at": datetime.now().isoformat(),
                "executive_summary": {
                    "total_cost": cost_analysis.get("total_cost", 0),
                    "daily_average": cost_analysis.get("daily_average", 0),
                    "cost_trend": trend_analysis.get("trend_direction", "unknown"),
                    "efficiency_score": efficiency_analysis.get("efficiency_scores", {}).get("overall", 0),
                    "active_alerts": len([a for a in alerts if a.severity in ["high", "critical"]]),
                    "optimization_potential": sum(r.estimated_savings for r in recommendations)
                },
                "detailed_analysis": {
                    "cost_breakdown": cost_analysis,
                    "trend_analysis": trend_analysis,
                    "model_efficiency": efficiency_analysis,
                    "roi_metrics": roi_analysis
                },
                "alerts": [self._serialize_alert(alert) for alert in alerts],
                "recommendations": [self._serialize_recommendation(rec) for rec in recommendations],
                "forecast": forecast,
                "charts": await self._generate_charts(cost_analysis, trend_analysis)
            }
            
        except Exception as e:
            logger.error(f"Cost report generation failed: {e}")
            return {"error": str(e)}
    
    def _calculate_moving_average(self, values: List[float], window_size: int) -> List[float]:
        """이동 평균 계산"""
        if len(values) < window_size:
            return values
        
        moving_avg = []
        for i in range(len(values) - window_size + 1):
            avg = sum(values[i:i + window_size]) / window_size
            moving_avg.append(avg)
        
        return moving_avg
    
    def _calculate_trend(self, values: List[float]) -> Tuple[str, float]:
        """트렌드 방향과 강도 계산"""
        if len(values) < 3:
            return "insufficient_data", 0.0
        
        # 선형 회귀를 통한 트렌드 계산
        x = np.arange(len(values))
        y = np.array(values)
        
        # 기울기 계산
        slope = np.polyfit(x, y, 1)[0]
        
        # 트렌드 방향 결정
        if abs(slope) < 0.01:
            direction = "stable"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"
        
        # 트렌드 강도 (R-squared 기반)
        p = np.poly1d(np.polyfit(x, y, 1))
        yhat = p(x)
        ybar = np.sum(y) / len(y)
        ssreg = np.sum((yhat - ybar) ** 2)
        sstot = np.sum((y - ybar) ** 2)
        strength = ssreg / sstot if sstot > 0 else 0.0
        
        return direction, strength
    
    def _analyze_seasonal_patterns(self, daily_costs: Dict[date, float]) -> Dict[str, Any]:
        """계절성 패턴 분석"""
        if len(daily_costs) < 14:
            return {"pattern": "insufficient_data"}
        
        # 요일별 패턴
        weekday_costs = defaultdict(list)
        for date_key, cost in daily_costs.items():
            if isinstance(date_key, str):
                date_obj = datetime.fromisoformat(date_key).date()
            else:
                date_obj = date_key
            
            weekday = date_obj.weekday()
            weekday_costs[weekday].append(cost)
        
        weekday_averages = {
            day: np.mean(costs) for day, costs in weekday_costs.items()
        }
        
        return {
            "weekday_pattern": weekday_averages,
            "highest_cost_day": max(weekday_averages, key=weekday_averages.get),
            "lowest_cost_day": min(weekday_averages, key=weekday_averages.get),
            "weekday_variation": np.std(list(weekday_averages.values()))
        }
    
    def _calculate_efficiency_score(self, cost_analysis: Dict[str, Any]) -> float:
        """효율성 점수 계산"""
        try:
            # 여러 메트릭을 종합한 효율성 점수
            total_cost = cost_analysis.get("total_cost", 0)
            total_requests = cost_analysis.get("total_requests", 0)  # 사용량 요약에서 가져와야 함
            
            if total_requests == 0:
                return 0.0
            
            # 비용 효율성 (낮을수록 좋음)
            cost_per_request = total_cost / total_requests
            cost_efficiency = min(1.0, 1.0 / (1.0 + cost_per_request))
            
            # 성능 효율성은 추가 데이터가 필요하므로 기본값 사용
            performance_efficiency = 0.8  # 기본 성능 점수
            
            # 가중 평균
            efficiency_score = (cost_efficiency * 0.6 + performance_efficiency * 0.4)
            
            return efficiency_score
            
        except Exception:
            return 0.5  # 기본값
    
    def _generate_trend_recommendations(
        self, 
        trend_direction: str, 
        trend_strength: float, 
        volatility: float
    ) -> List[str]:
        """트렌드 기반 권고사항 생성"""
        recommendations = []
        
        if trend_direction == "increasing" and trend_strength > 0.5:
            recommendations.append("Cost is increasing significantly - investigate usage patterns")
            recommendations.append("Consider implementing cost controls and budget alerts")
        
        if volatility > 0.5:
            recommendations.append("High cost volatility detected - review irregular usage patterns")
            recommendations.append("Implement more consistent caching strategies")
        
        if trend_direction == "stable":
            recommendations.append("Costs are stable - good opportunity to optimize for efficiency")
        
        return recommendations
    
    def _calculate_model_efficiency_score(self, metrics: Dict[str, Any]) -> float:
        """모델 효율성 점수 계산"""
        try:
            # 여러 메트릭을 조합한 효율성 점수
            success_rate = metrics.get("success_rate", 0)
            cache_hit_rate = metrics.get("cache_hit_rate", 0)
            cost_per_token = metrics.get("cost_per_token", float('inf'))
            
            # 각 메트릭을 0-1 스케일로 정규화
            success_score = success_rate
            cache_score = cache_hit_rate
            
            # 비용 효율성 (낮을수록 좋음)
            if cost_per_token == 0 or cost_per_token == float('inf'):
                cost_score = 0.5
            else:
                cost_score = min(1.0, 1.0 / (1.0 + cost_per_token * 10000))  # 스케일링
            
            # 가중 평균
            efficiency_score = (success_score * 0.4 + cache_score * 0.3 + cost_score * 0.3)
            
            return efficiency_score
            
        except Exception:
            return 0.5
    
    def _generate_efficiency_recommendations(
        self, 
        model_metrics: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """효율성 기반 권고사항 생성"""
        recommendations = []
        
        # 성공률이 낮은 모델 식별
        low_success_models = [
            model for model, metrics in model_metrics.items()
            if metrics.get("success_rate", 0) < 0.8 and metrics.get("total_requests", 0) > 10
        ]
        
        if low_success_models:
            recommendations.append(f"Review models with low success rates: {', '.join(low_success_models)}")
        
        # 캐시 활용도가 낮은 모델 식별
        low_cache_models = [
            model for model, metrics in model_metrics.items()
            if metrics.get("cache_hit_rate", 0) < 0.3 and metrics.get("total_requests", 0) > 10
        ]
        
        if low_cache_models:
            recommendations.append(f"Improve caching for models: {', '.join(low_cache_models)}")
        
        # 높은 비용 대비 성능 모델 식별
        expensive_models = [
            model for model, metrics in model_metrics.items()
            if metrics.get("cost_per_success", 0) > 0.1 and metrics.get("total_requests", 0) > 10
        ]
        
        if expensive_models:
            recommendations.append(f"Consider cost optimization for: {', '.join(expensive_models)}")
        
        return recommendations
    
    async def _get_recent_hourly_costs(self, hours: int) -> List[float]:
        """최근 시간별 비용 조회"""
        try:
            records = await self.usage_tracker.db.get_usage_records(
                start_date=datetime.now() - timedelta(hours=hours),
                limit=10000
            )
            
            # 시간별 비용 집계
            hourly_costs = defaultdict(float)
            for record in records:
                hour_key = record.timestamp.replace(minute=0, second=0, microsecond=0)
                hourly_costs[hour_key] += record.cost
            
            # 시간순 정렬하여 리스트로 반환
            sorted_hours = sorted(hourly_costs.keys())
            return [hourly_costs[hour] for hour in sorted_hours]
            
        except Exception:
            return []
    
    async def _get_overall_cache_hit_rate(self) -> float:
        """전체 캐시 히트율 조회"""
        try:
            records = await self.usage_tracker.db.get_usage_records(
                start_date=datetime.now() - timedelta(days=7),
                limit=5000
            )
            
            if not records:
                return 0.0
            
            cache_hits = sum(1 for r in records if r.cache_hit)
            return cache_hits / len(records)
            
        except Exception:
            return 0.0
    
    async def _estimate_cache_savings(self, current_hit_rate: float) -> float:
        """캐시 개선으로 인한 예상 절약액"""
        try:
            # 최근 7일 비용 조회
            records = await self.usage_tracker.db.get_usage_records(
                start_date=datetime.now() - timedelta(days=7),
                limit=5000
            )
            
            total_cost = sum(r.cost for r in records if not r.cache_hit)
            
            # 캐시 히트율을 80%로 개선했을 때의 절약액 추정
            target_hit_rate = 0.8
            if target_hit_rate > current_hit_rate:
                potential_cached_cost = total_cost * ((target_hit_rate - current_hit_rate) / (1 - current_hit_rate))
                return potential_cached_cost * 7  # 주간 절약액
            
            return 0.0
            
        except Exception:
            return 0.0
    
    async def _identify_high_token_usage_patterns(self) -> List[Dict[str, Any]]:
        """높은 토큰 사용 패턴 식별"""
        try:
            records = await self.usage_tracker.db.get_usage_records(
                start_date=datetime.now() - timedelta(days=7),
                limit=5000
            )
            
            # 토큰 사용량이 높은 요청들 분석
            high_token_requests = [r for r in records if r.total_tokens > 2000]
            
            if not high_token_requests:
                return []
            
            # 패턴별 그룹화 (task_type 기준)
            patterns = defaultdict(list)
            for request in high_token_requests:
                patterns[request.task_type].append(request)
            
            # 패턴별 절약 가능성 계산
            pattern_analysis = []
            for task_type, requests in patterns.items():
                avg_tokens = np.mean([r.total_tokens for r in requests])
                total_cost = sum(r.cost for r in requests)
                
                # 30% 토큰 압축 가정
                potential_savings = total_cost * 0.3
                
                pattern_analysis.append({
                    "task_type": task_type,
                    "request_count": len(requests),
                    "avg_tokens": avg_tokens,
                    "total_cost": total_cost,
                    "potential_savings": potential_savings
                })
            
            return pattern_analysis
            
        except Exception:
            return []
    
    async def _analyze_tier_optimization_opportunities(self) -> Dict[str, Any]:
        """티어 최적화 기회 분석"""
        try:
            records = await self.usage_tracker.db.get_usage_records(
                start_date=datetime.now() - timedelta(days=7),
                limit=5000
            )
            
            # 티어별 성공률과 비용 분석
            tier_analysis = defaultdict(lambda: {"requests": 0, "cost": 0, "success": 0})
            
            for record in records:
                tier = record.model_tier.value
                tier_analysis[tier]["requests"] += 1
                tier_analysis[tier]["cost"] += record.cost
                if record.success:
                    tier_analysis[tier]["success"] += 1
            
            # 높은 티어에서 단순한 작업 수행하는 케이스 식별
            potential_savings = 0.0
            optimization_opportunities = []
            
            for tier, data in tier_analysis.items():
                if data["requests"] > 0:
                    success_rate = data["success"] / data["requests"]
                    
                    # 높은 티어이면서 성공률이 매우 높은 경우 (단순 작업 가능성)
                    if tier in ["standard", "o3"] and success_rate > 0.95:
                        # 한 단계 낮은 티어 사용 시 30% 비용 절감 추정
                        estimated_savings = data["cost"] * 0.3
                        potential_savings += estimated_savings
                        
                        optimization_opportunities.append({
                            "tier": tier,
                            "success_rate": success_rate,
                            "potential_savings": estimated_savings
                        })
            
            return {
                "potential_savings": potential_savings,
                "opportunities": optimization_opportunities
            }
            
        except Exception:
            return {"potential_savings": 0.0, "opportunities": []}
    
    async def _generate_cost_forecast(self, historical_costs: List[float], forecast_days: int) -> CostForecast:
        """비용 예측 생성"""
        try:
            if len(historical_costs) < 7:
                return CostForecast(
                    period_days=forecast_days,
                    predicted_cost=0.0,
                    confidence_interval=(0.0, 0.0),
                    prediction_method="insufficient_data",
                    factors={},
                    timestamp=datetime.now()
                )
            
            # 단순 선형 예측
            recent_avg = np.mean(historical_costs[-7:])  # 최근 7일 평균
            trend_factor = (historical_costs[-1] - historical_costs[0]) / len(historical_costs)
            
            predicted_daily = recent_avg + (trend_factor * forecast_days / 2)
            predicted_total = predicted_daily * forecast_days
            
            # 신뢰구간 (간단한 추정)
            volatility = np.std(historical_costs)
            confidence_margin = volatility * 1.96  # 95% 신뢰구간
            
            return CostForecast(
                period_days=forecast_days,
                predicted_cost=predicted_total,
                confidence_interval=(
                    max(0, predicted_total - confidence_margin * forecast_days),
                    predicted_total + confidence_margin * forecast_days
                ),
                prediction_method="linear_trend",
                factors={
                    "recent_avg": recent_avg,
                    "trend_factor": trend_factor,
                    "volatility": volatility
                },
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Cost forecast generation failed: {e}")
            return CostForecast(
                period_days=forecast_days,
                predicted_cost=0.0,
                confidence_interval=(0.0, 0.0),
                prediction_method="error",
                factors={"error": str(e)},
                timestamp=datetime.now()
            )
    
    async def _generate_detailed_forecast(self, period_days: int) -> Dict[str, Any]:
        """상세 예측 생성"""
        try:
            cost_analysis = await self.usage_tracker.get_cost_analysis(period_days)
            daily_costs = cost_analysis.get("daily_costs", {})
            
            if not daily_costs:
                return {"error": "No historical data for forecast"}
            
            costs = list(daily_costs.values())
            forecast = await self._generate_cost_forecast(costs, 7)  # 7일 예측
            
            return {
                "next_7_days": {
                    "predicted_cost": forecast.predicted_cost,
                    "confidence_interval": forecast.confidence_interval,
                    "method": forecast.prediction_method
                },
                "factors": forecast.factors,
                "recommendations": [
                    "Monitor daily spend against prediction",
                    "Adjust usage if exceeding upper confidence interval",
                    "Consider cost optimization if trend is increasing"
                ]
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _calculate_roi_metrics(self) -> Dict[str, Any]:
        """ROI 메트릭 계산"""
        try:
            # 간단한 ROI 메트릭 (실제 구현시 비즈니스 가치 측정 필요)
            summary = await self.usage_tracker.get_usage_summary(days=30)
            
            total_cost = summary.get("total_cost", 0)
            total_requests = summary.get("total_requests", 0)
            success_rate = summary.get("success_rate", 0)
            
            # 가정: 성공적인 요청 당 $2의 비즈니스 가치
            estimated_value_per_success = 2.0
            total_value = total_requests * success_rate * estimated_value_per_success
            
            roi = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0
            
            return {
                "total_cost": total_cost,
                "estimated_value": total_value,
                "roi_percentage": roi,
                "cost_per_success": total_cost / (total_requests * success_rate) if total_requests * success_rate > 0 else 0,
                "note": "ROI calculation based on estimated business value"
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _generate_charts(self, cost_analysis: Dict, trend_analysis: Dict) -> Dict[str, str]:
        """차트 생성 (base64 인코딩된 이미지)"""
        charts = {}
        
        try:
            # 일별 비용 차트
            daily_costs = cost_analysis.get("daily_costs", {})
            if daily_costs:
                plt.figure(figsize=(10, 6))
                dates = list(daily_costs.keys())
                costs = list(daily_costs.values())
                
                plt.plot(dates, costs, marker='o')
                plt.title('Daily Cost Trend')
                plt.xlabel('Date')
                plt.ylabel('Cost ($)')
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                buffer = io.BytesIO()
                plt.savefig(buffer, format='png')
                buffer.seek(0)
                charts["daily_cost_trend"] = base64.b64encode(buffer.getvalue()).decode()
                plt.close()
            
            # 모델별 비용 분포 차트
            tier_breakdown = cost_analysis.get("tier_breakdown", {})
            if tier_breakdown:
                plt.figure(figsize=(8, 8))
                plt.pie(tier_breakdown.values(), labels=tier_breakdown.keys(), autopct='%1.1f%%')
                plt.title('Cost Distribution by Model Tier')
                
                buffer = io.BytesIO()
                plt.savefig(buffer, format='png')
                buffer.seek(0)
                charts["tier_distribution"] = base64.b64encode(buffer.getvalue()).decode()
                plt.close()
                
        except Exception as e:
            logger.error(f"Chart generation failed: {e}")
        
        return charts
    
    def _serialize_alert(self, alert: CostAlert) -> Dict[str, Any]:
        """CostAlert를 직렬화"""
        return {
            "type": alert.alert_type.value,
            "severity": alert.severity,
            "message": alert.message,
            "current_value": alert.current_value,
            "threshold": alert.threshold,
            "timestamp": alert.timestamp.isoformat(),
            "metadata": alert.metadata,
            "recommended_actions": alert.recommended_actions
        }
    
    def _serialize_recommendation(self, rec: CostOptimizationRecommendation) -> Dict[str, Any]:
        """CostOptimizationRecommendation을 직렬화"""
        return {
            "category": rec.category,
            "priority": rec.priority,
            "description": rec.description,
            "estimated_savings": rec.estimated_savings,
            "implementation_effort": rec.implementation_effort,
            "impact_on_quality": rec.impact_on_quality,
            "action_items": rec.action_items
        }

# 글로벌 비용 분석기
cost_analyzer = None

async def initialize_cost_analyzer(usage_tracker: UsageTracker):
    """비용 분석기 초기화"""
    global cost_analyzer
    cost_analyzer = CostAnalyzer(usage_tracker)
    logger.info("Cost analyzer initialized")

async def generate_cost_report(period_days: int = 30) -> Dict[str, Any]:
    """비용 리포트 생성"""
    if not cost_analyzer:
        return {"error": "Cost analyzer not initialized"}
    return await cost_analyzer.generate_cost_report(period_days)

async def get_cost_alerts() -> List[Dict[str, Any]]:
    """비용 알림 조회"""
    if not cost_analyzer:
        return []
    alerts = await cost_analyzer.generate_cost_alerts()
    return [cost_analyzer._serialize_alert(alert) for alert in alerts]

async def get_optimization_recommendations() -> List[Dict[str, Any]]:
    """최적화 권고사항 조회"""
    if not cost_analyzer:
        return []
    recommendations = await cost_analyzer.generate_optimization_recommendations()
    return [cost_analyzer._serialize_recommendation(rec) for rec in recommendations]