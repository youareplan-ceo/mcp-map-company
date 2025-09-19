"""
비용 최적화 모듈 - 토큰 사용량 최적화 및 비용 절감
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import json
import hashlib
from collections import defaultdict, deque
import tiktoken
import numpy as np

from ..config.model_policy import ModelTier, model_policy

logger = logging.getLogger(__name__)

class OptimizationStrategy(Enum):
    """최적화 전략"""
    AGGRESSIVE = "aggressive"  # 최대 비용 절감
    BALANCED = "balanced"     # 비용과 품질 균형
    CONSERVATIVE = "conservative"  # 품질 우선

@dataclass
class TokenUsage:
    """토큰 사용량"""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float
    model_name: str
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class OptimizationResult:
    """최적화 결과"""
    original_content: str
    optimized_content: str
    original_tokens: int
    optimized_tokens: int
    token_savings: int
    cost_savings: float
    compression_ratio: float
    optimization_technique: str
    quality_impact: float  # 0.0-1.0, 1.0은 품질 손실 없음

class TokenCounter:
    """토큰 카운터"""
    
    def __init__(self):
        self.encoders = {}
        self._load_encoders()
    
    def _load_encoders(self):
        """인코더 로드"""
        try:
            # GPT-4 계열
            self.encoders["gpt-4"] = tiktoken.encoding_for_model("gpt-4")
            self.encoders["gpt-3.5-turbo"] = tiktoken.encoding_for_model("gpt-3.5-turbo")
            
            # 기본 인코더
            self.encoders["default"] = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning(f"Failed to load tiktoken encoders: {e}")
            # 폴백: 단어 수 기반 추정
            self.encoders = {}
    
    def count_tokens(self, text: str, model_name: str = "gpt-4") -> int:
        """텍스트의 토큰 수 계산"""
        if not text:
            return 0
        
        # 적절한 인코더 선택
        encoder_key = "default"
        if "gpt-4" in model_name.lower():
            encoder_key = "gpt-4"
        elif "gpt-3.5" in model_name.lower():
            encoder_key = "gpt-3.5-turbo"
        
        if encoder_key in self.encoders:
            try:
                return len(self.encoders[encoder_key].encode(text))
            except Exception as e:
                logger.warning(f"Token encoding failed: {e}")
        
        # 폴백: 단어 수 기반 추정 (평균적으로 1단어 ≈ 1.3토큰)
        word_count = len(text.split())
        return int(word_count * 1.3)
    
    def estimate_cost(self, text: str, model_name: str, is_input: bool = True) -> float:
        """텍스트 처리 비용 추정"""
        tokens = self.count_tokens(text, model_name)
        
        # 모델 설정에서 비용 정보 조회
        model_config = None
        for tier, policy in model_policy.policies.items():
            if policy.tier.value == model_name or tier.value == model_name:
                model_config = policy
                break
        
        if not model_config:
            # 기본 비용 사용
            cost_per_token = 0.0001 if is_input else 0.0002
        else:
            cost_per_token = model_config.cost_per_1k_tokens / 1000
        
        return tokens * cost_per_token

class ContentCompressor:
    """컨텐츠 압축기"""
    
    def __init__(self):
        self.compression_techniques = {
            "remove_redundancy": self._remove_redundancy,
            "abbreviate_common": self._abbreviate_common_terms,
            "compress_whitespace": self._compress_whitespace,
            "summarize_sections": self._summarize_sections,
            "remove_filler": self._remove_filler_words
        }
    
    def compress_content(
        self, 
        content: str, 
        target_reduction: float = 0.3,
        strategy: OptimizationStrategy = OptimizationStrategy.BALANCED
    ) -> OptimizationResult:
        """컨텐츠 압축"""
        original_content = content
        original_tokens = len(content.split()) * 1.3  # 토큰 추정
        
        # 전략별 압축 기법 선택
        techniques = self._select_techniques(strategy)
        
        compressed_content = content
        applied_techniques = []
        
        for technique_name in techniques:
            if technique_name in self.compression_techniques:
                prev_content = compressed_content
                compressed_content = self.compression_techniques[technique_name](compressed_content)
                
                # 압축 효과 확인
                reduction_achieved = (len(prev_content) - len(compressed_content)) / len(prev_content)
                if reduction_achieved > 0.01:  # 1% 이상 압축되면 적용
                    applied_techniques.append(technique_name)
                else:
                    compressed_content = prev_content  # 효과 없으면 되돌리기
                
                # 목표 압축률 달성 시 중단
                current_reduction = (len(original_content) - len(compressed_content)) / len(original_content)
                if current_reduction >= target_reduction:
                    break
        
        final_tokens = len(compressed_content.split()) * 1.3
        token_savings = original_tokens - final_tokens
        compression_ratio = len(compressed_content) / len(original_content)
        
        # 품질 영향도 추정
        quality_impact = self._estimate_quality_impact(applied_techniques, compression_ratio)
        
        return OptimizationResult(
            original_content=original_content,
            optimized_content=compressed_content,
            original_tokens=int(original_tokens),
            optimized_tokens=int(final_tokens),
            token_savings=int(token_savings),
            cost_savings=token_savings * 0.0001,  # 추정 비용 절약
            compression_ratio=compression_ratio,
            optimization_technique=", ".join(applied_techniques),
            quality_impact=quality_impact
        )
    
    def _select_techniques(self, strategy: OptimizationStrategy) -> List[str]:
        """전략별 압축 기법 선택"""
        if strategy == OptimizationStrategy.AGGRESSIVE:
            return ["compress_whitespace", "remove_filler", "abbreviate_common", 
                   "remove_redundancy", "summarize_sections"]
        elif strategy == OptimizationStrategy.BALANCED:
            return ["compress_whitespace", "remove_redundancy", "abbreviate_common"]
        else:  # CONSERVATIVE
            return ["compress_whitespace"]
    
    def _remove_redundancy(self, content: str) -> str:
        """중복 제거"""
        lines = content.split('\n')
        unique_lines = []
        seen_lines = set()
        
        for line in lines:
            line_clean = line.strip().lower()
            if line_clean and line_clean not in seen_lines:
                unique_lines.append(line)
                seen_lines.add(line_clean)
        
        return '\n'.join(unique_lines)
    
    def _abbreviate_common_terms(self, content: str) -> str:
        """일반적인 용어 축약"""
        abbreviations = {
            "artificial intelligence": "AI",
            "machine learning": "ML",
            "natural language processing": "NLP",
            "return on investment": "ROI",
            "year over year": "YoY",
            "quarter over quarter": "QoQ",
            "price to earnings": "P/E",
            "earnings before interest and taxes": "EBIT",
            "moving average": "MA",
            "relative strength index": "RSI"
        }
        
        compressed = content
        for full_term, abbrev in abbreviations.items():
            compressed = compressed.replace(full_term, abbrev)
            compressed = compressed.replace(full_term.title(), abbrev)
        
        return compressed
    
    def _compress_whitespace(self, content: str) -> str:
        """공백 압축"""
        import re
        # 연속된 공백을 단일 공백으로
        compressed = re.sub(r'\s+', ' ', content)
        # 연속된 줄바꿈 정리
        compressed = re.sub(r'\n\s*\n', '\n', compressed)
        return compressed.strip()
    
    def _summarize_sections(self, content: str) -> str:
        """섹션 요약 (간단한 구현)"""
        lines = content.split('\n')
        summarized_lines = []
        
        current_section = []
        for line in lines:
            if line.strip():
                current_section.append(line)
            else:
                if current_section:
                    # 섹션이 5줄 이상이면 요약
                    if len(current_section) > 5:
                        summary = self._simple_summarize(current_section)
                        summarized_lines.append(summary)
                    else:
                        summarized_lines.extend(current_section)
                    current_section = []
                summarized_lines.append(line)
        
        if current_section:
            if len(current_section) > 5:
                summary = self._simple_summarize(current_section)
                summarized_lines.append(summary)
            else:
                summarized_lines.extend(current_section)
        
        return '\n'.join(summarized_lines)
    
    def _simple_summarize(self, lines: List[str]) -> str:
        """간단한 요약 (키워드 기반)"""
        # 첫 번째와 마지막 줄, 그리고 중요 키워드 포함 줄 유지
        important_keywords = ['price', 'volume', 'trend', 'analysis', 'recommendation', 
                            '가격', '거래량', '추세', '분석', '추천']
        
        summary_lines = [lines[0]]  # 첫 줄
        
        for line in lines[1:-1]:
            if any(keyword.lower() in line.lower() for keyword in important_keywords):
                summary_lines.append(line)
        
        if len(lines) > 1:
            summary_lines.append(lines[-1])  # 마지막 줄
        
        return '\n'.join(summary_lines)
    
    def _remove_filler_words(self, content: str) -> str:
        """불필요한 단어 제거"""
        filler_words = [
            "actually", "basically", "essentially", "literally", "really",
            "very", "quite", "rather", "somewhat", "fairly", "pretty",
            "just", "only", "simply", "merely", "particularly"
        ]
        
        words = content.split()
        filtered_words = [word for word in words if word.lower() not in filler_words]
        return ' '.join(filtered_words)
    
    def _estimate_quality_impact(self, techniques: List[str], compression_ratio: float) -> float:
        """품질 영향도 추정"""
        # 기법별 품질 영향도
        impact_scores = {
            "compress_whitespace": 1.0,    # 품질 영향 없음
            "remove_redundancy": 0.95,     # 약간의 영향
            "abbreviate_common": 0.9,      # 중간 영향
            "remove_filler": 0.85,         # 중간 영향
            "summarize_sections": 0.7      # 높은 영향
        }
        
        # 적용된 기법들의 품질 영향도 계산
        quality_scores = [impact_scores.get(tech, 0.8) for tech in techniques]
        avg_quality = np.mean(quality_scores) if quality_scores else 1.0
        
        # 압축비에 따른 추가 페널티
        compression_penalty = max(0.0, (1.0 - compression_ratio - 0.3) * 0.5)
        
        return max(0.0, avg_quality - compression_penalty)

class BudgetManager:
    """예산 관리자"""
    
    def __init__(self):
        self.daily_budgets = {}  # 일일 예산
        self.usage_tracking = defaultdict(lambda: defaultdict(float))  # 날짜별 사용량
        self.model_costs = defaultdict(float)  # 모델별 누적 비용
        
    def set_daily_budget(self, budget: float, date: Optional[datetime] = None):
        """일일 예산 설정"""
        if date is None:
            date = datetime.now().date()
        
        self.daily_budgets[date] = budget
        logger.info(f"Daily budget set to ${budget:.2f} for {date}")
    
    def check_budget_availability(self, estimated_cost: float, date: Optional[datetime] = None) -> Tuple[bool, float]:
        """예산 가용성 확인"""
        if date is None:
            date = datetime.now().date()
        
        daily_budget = self.daily_budgets.get(date, float('inf'))
        current_usage = self.usage_tracking[date].get('total', 0.0)
        remaining_budget = daily_budget - current_usage
        
        is_available = remaining_budget >= estimated_cost
        
        return is_available, remaining_budget
    
    def record_usage(self, cost: float, model_name: str, date: Optional[datetime] = None):
        """사용량 기록"""
        if date is None:
            date = datetime.now().date()
        
        self.usage_tracking[date]['total'] += cost
        self.usage_tracking[date][model_name] += cost
        self.model_costs[model_name] += cost
        
        logger.debug(f"Recorded ${cost:.4f} usage for {model_name} on {date}")
    
    def get_usage_summary(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """사용량 요약 조회"""
        if date is None:
            date = datetime.now().date()
        
        usage = dict(self.usage_tracking[date])
        budget = self.daily_budgets.get(date, 0.0)
        total_usage = usage.get('total', 0.0)
        
        return {
            "date": date.isoformat(),
            "budget": budget,
            "total_usage": total_usage,
            "remaining_budget": budget - total_usage,
            "budget_utilization": (total_usage / budget * 100) if budget > 0 else 0,
            "model_breakdown": {k: v for k, v in usage.items() if k != 'total'},
            "is_over_budget": total_usage > budget
        }
    
    def suggest_cost_reduction(self, current_usage: float, budget: float) -> List[str]:
        """비용 절감 제안"""
        suggestions = []
        
        over_budget = current_usage - budget
        if over_budget > 0:
            over_percentage = (over_budget / budget) * 100
            
            suggestions.append(f"예산 초과: ${over_budget:.2f} ({over_percentage:.1f}%)")
            
            if over_percentage > 50:
                suggestions.append("AGGRESSIVE 압축 전략 사용 권장")
                suggestions.append("더 저렴한 모델 티어 사용 고려")
            elif over_percentage > 20:
                suggestions.append("BALANCED 압축 전략 사용")
                suggestions.append("불필요한 요청 최소화")
            else:
                suggestions.append("토큰 사용량 최적화 권장")
        
        return suggestions

class CostOptimizer:
    """통합 비용 최적화기"""
    
    def __init__(self):
        self.token_counter = TokenCounter()
        self.content_compressor = ContentCompressor()
        self.budget_manager = BudgetManager()
        self.optimization_history = deque(maxlen=1000)
    
    async def optimize_request(
        self,
        content: str,
        model_name: str,
        strategy: OptimizationStrategy = OptimizationStrategy.BALANCED,
        target_reduction: float = 0.3
    ) -> OptimizationResult:
        """요청 최적화"""
        start_time = datetime.now()
        
        try:
            # 현재 비용 계산
            original_cost = self.token_counter.estimate_cost(content, model_name, is_input=True)
            
            # 예산 확인
            is_available, remaining_budget = self.budget_manager.check_budget_availability(original_cost)
            
            # 예산이 부족하면 더 적극적인 최적화
            if not is_available or remaining_budget < original_cost * 2:
                strategy = OptimizationStrategy.AGGRESSIVE
                target_reduction = min(0.5, target_reduction * 1.5)
                logger.warning(f"Budget constraint detected, using aggressive optimization")
            
            # 컨텐츠 압축
            optimization_result = self.content_compressor.compress_content(
                content, target_reduction, strategy
            )
            
            # 최적화된 비용 계산
            optimized_cost = self.token_counter.estimate_cost(
                optimization_result.optimized_content, model_name, is_input=True
            )
            
            optimization_result.cost_savings = original_cost - optimized_cost
            
            # 히스토리 저장
            self.optimization_history.append({
                "timestamp": start_time,
                "original_tokens": optimization_result.original_tokens,
                "optimized_tokens": optimization_result.optimized_tokens,
                "token_savings": optimization_result.token_savings,
                "cost_savings": optimization_result.cost_savings,
                "strategy": strategy.value,
                "model_name": model_name
            })
            
            logger.info(f"Optimized content: {optimization_result.token_savings} tokens saved, "
                       f"${optimization_result.cost_savings:.4f} cost saved")
            
            return optimization_result
            
        except Exception as e:
            logger.error(f"Content optimization failed: {e}")
            # 폴백: 원본 반환
            return OptimizationResult(
                original_content=content,
                optimized_content=content,
                original_tokens=self.token_counter.count_tokens(content, model_name),
                optimized_tokens=self.token_counter.count_tokens(content, model_name),
                token_savings=0,
                cost_savings=0.0,
                compression_ratio=1.0,
                optimization_technique="none (failed)",
                quality_impact=1.0
            )
    
    def recommend_model_tier(
        self,
        content: str,
        quality_requirement: float = 0.8,
        budget_limit: Optional[float] = None
    ) -> Tuple[ModelTier, str]:
        """비용 고려한 모델 티어 추천"""
        
        # 각 티어별 비용과 품질 계산
        tier_options = []
        
        for tier in [ModelTier.NANO, ModelTier.MINI, ModelTier.STANDARD, ModelTier.PREMIUM]:
            # 해당 티어의 대표 모델
            tier_models = [policy.tier.value for policy in model_policy.policies.values() if policy.tier == tier]
            if not tier_models:
                continue
                
            model_name = tier_models[0]
            estimated_cost = self.token_counter.estimate_cost(content, model_name)
            
            # 품질 추정 (티어별 기본 품질 점수)
            tier_quality = {
                ModelTier.NANO: 0.6,
                ModelTier.MINI: 0.75,
                ModelTier.STANDARD: 0.85,
                ModelTier.PREMIUM: 0.95
            }
            
            quality = tier_quality.get(tier, 0.7)
            
            tier_options.append((tier, model_name, estimated_cost, quality))
        
        # 품질 요구사항을 만족하는 옵션들 필터링
        qualified_options = [opt for opt in tier_options if opt[3] >= quality_requirement]
        
        if not qualified_options:
            # 품질 요구사항을 만족하는 옵션이 없으면 가장 높은 품질 선택
            best_quality_option = max(tier_options, key=lambda x: x[3])
            logger.warning(f"No options meet quality requirement {quality_requirement}, "
                          f"selecting best available: {best_quality_option[0].value}")
            return best_quality_option[0], best_quality_option[1]
        
        # 예산 제한이 있으면 추가 필터링
        if budget_limit:
            budget_qualified = [opt for opt in qualified_options if opt[2] <= budget_limit]
            if budget_qualified:
                qualified_options = budget_qualified
            else:
                logger.warning(f"No options within budget ${budget_limit:.4f}")
        
        # 비용 대비 품질이 최고인 옵션 선택
        best_option = min(qualified_options, key=lambda x: x[2] / x[3])
        
        logger.info(f"Recommended model tier: {best_option[0].value} ({best_option[1]}) - "
                   f"Cost: ${best_option[2]:.4f}, Quality: {best_option[3]:.2f}")
        
        return best_option[0], best_option[1]
    
    async def get_optimization_stats(self) -> Dict[str, Any]:
        """최적화 통계 조회"""
        if not self.optimization_history:
            return {}
        
        history = list(self.optimization_history)
        
        total_token_savings = sum(record["token_savings"] for record in history)
        total_cost_savings = sum(record["cost_savings"] for record in history)
        
        # 전략별 통계
        strategy_stats = defaultdict(lambda: {"count": 0, "token_savings": 0, "cost_savings": 0.0})
        for record in history:
            strategy = record["strategy"]
            strategy_stats[strategy]["count"] += 1
            strategy_stats[strategy]["token_savings"] += record["token_savings"]
            strategy_stats[strategy]["cost_savings"] += record["cost_savings"]
        
        # 최근 24시간 통계
        recent_threshold = datetime.now() - timedelta(hours=24)
        recent_records = [r for r in history if r["timestamp"] > recent_threshold]
        
        return {
            "total_optimizations": len(history),
            "recent_optimizations_24h": len(recent_records),
            "total_token_savings": total_token_savings,
            "total_cost_savings": total_cost_savings,
            "average_token_savings": total_token_savings / len(history) if history else 0,
            "average_cost_savings": total_cost_savings / len(history) if history else 0,
            "strategy_breakdown": dict(strategy_stats),
            "budget_summary": self.budget_manager.get_usage_summary()
        }

# 글로벌 최적화기 인스턴스
optimizer = CostOptimizer()

async def optimize_content(
    content: str,
    model_name: str,
    strategy: OptimizationStrategy = OptimizationStrategy.BALANCED
) -> OptimizationResult:
    """컨텐츠 최적화"""
    return await optimizer.optimize_request(content, model_name, strategy)

def set_daily_budget(budget: float):
    """일일 예산 설정"""
    optimizer.budget_manager.set_daily_budget(budget)

def record_model_usage(cost: float, model_name: str):
    """모델 사용량 기록"""
    optimizer.budget_manager.record_usage(cost, model_name)

async def get_cost_optimization_stats() -> Dict[str, Any]:
    """비용 최적화 통계 조회"""
    return await optimizer.get_optimization_stats()