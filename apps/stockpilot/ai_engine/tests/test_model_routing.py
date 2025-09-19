"""
모델 라우팅 시스템 테스트
스마트 모델 선택, 비용 최적화, 캐시 관리 검증
"""

import pytest
import asyncio
import os
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
from typing import Dict, Any

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from ai_engine.config.model_policy import (
    StockPilotModelPolicy, ModelTier, TaskComplexity, 
    model_policy
)
from ai_engine.config.types import ContentType

from ai_engine.routing.model_router import (
    SmartModelRouter, ModelRequest, ModelResponse, RoutingDecision,
    ComplexityAnalyzer, ModelLoadBalancer
)

from ai_engine.routing.cost_optimizer import (
    CostOptimizer, OptimizationStrategy, OptimizationResult,
    ContentCompressor, BudgetManager, TokenCounter
)

from ai_engine.routing.cache_manager import (
    CacheManager, CacheType, CacheEntry, LRUCache, PromptCache, VectorCache
)

class TestModelPolicy:
    """모델 정책 테스트"""
    
    def test_policy_initialization(self):
        """정책 초기화 테스트"""
        policy = StockPilotModelPolicy()
        
        assert policy is not None
        assert hasattr(policy, 'model_tiers')
        assert hasattr(policy, 'task_complexities')
    
    def test_model_selection_for_tasks(self):
        """작업별 모델 선택 테스트"""
        policy = StockPilotModelPolicy()
        
        # 간단한 작업 - nano 모델
        model = policy.get_model_for_task(
            "data_query", 
            TaskComplexity.SIMPLE, 
            ContentType.TEXT
        )
        assert model == ModelTier.NANO
        
        # 복잡한 분석 - 상위 모델
        model = policy.get_model_for_task(
            "portfolio_optimization", 
            TaskComplexity.HIGHLY_COMPLEX, 
            ContentType.MIXED
        )
        assert model in [ModelTier.STANDARD, ModelTier.PREMIUM]
        
        # 중간 복잡도 작업
        model = policy.get_model_for_task(
            "sentiment_analysis", 
            TaskComplexity.MODERATE, 
            ContentType.TEXT
        )
        assert model in [ModelTier.MINI, ModelTier.STANDARD]
    
    def test_escalation_rules(self):
        """에스컬레이션 규칙 테스트"""
        policy = StockPilotModelPolicy()
        
        # 신뢰도가 낮으면 상위 모델 추천
        should_escalate = policy.should_escalate_model(
            current_tier=ModelTier.MINI,
            confidence_score=0.5,  # 낮은 신뢰도
            task_complexity=TaskComplexity.COMPLEX
        )
        assert should_escalate
        
        # 신뢰도가 높으면 에스컬레이션 불필요
        should_escalate = policy.should_escalate_model(
            current_tier=ModelTier.MINI,
            confidence_score=0.9,  # 높은 신뢰도
            task_complexity=TaskComplexity.SIMPLE
        )
        assert not should_escalate
    
    def test_cost_vs_quality_balance(self):
        """비용 대비 품질 균형 테스트"""
        policy = StockPilotModelPolicy()
        
        # 높은 품질 요구사항
        model = policy.get_optimal_model(
            task_type="signal_generation",
            quality_requirement=0.95,
            budget_limit=None
        )
        assert model in [ModelTier.STANDARD, ModelTier.PREMIUM]
        
        # 예산 제한이 있는 경우
        model = policy.get_optimal_model(
            task_type="signal_generation",
            quality_requirement=0.7,
            budget_limit=0.01  # 매우 낮은 예산
        )
        assert model in [ModelTier.NANO, ModelTier.MINI]

class TestComplexityAnalyzer:
    """복잡도 분석기 테스트"""
    
    def test_complexity_analyzer_initialization(self):
        """복잡도 분석기 초기화 테스트"""
        analyzer = ComplexityAnalyzer()
        
        assert analyzer is not None
        assert hasattr(analyzer, 'complexity_cache')
        assert hasattr(analyzer, 'analysis_patterns')
    
    def test_length_based_complexity(self):
        """길이 기반 복잡도 분석 테스트"""
        analyzer = ComplexityAnalyzer()
        
        # 짧은 텍스트 - 단순
        short_request = ModelRequest(
            task_id="test1",
            task_type="data_query", 
            content="삼성전자 현재가는?",
            content_type=ContentType.TEXT
        )
        complexity = analyzer.analyze_complexity(short_request)
        assert complexity == TaskComplexity.SIMPLE
        
        # 긴 텍스트 - 복잡
        long_content = "삼성전자의 2024년 실적을 상세히 분석하고, 향후 투자 전략을 수립하며, 포트폴리오 최적화 방안을 제시해주세요. " * 10
        long_request = ModelRequest(
            task_id="test2",
            task_type="portfolio_optimization",
            content=long_content,
            content_type=ContentType.MIXED
        )
        complexity = analyzer.analyze_complexity(long_request)
        assert complexity in [TaskComplexity.COMPLEX, TaskComplexity.HIGHLY_COMPLEX]
    
    def test_pattern_based_complexity(self):
        """패턴 기반 복잡도 분석 테스트"""
        analyzer = ComplexityAnalyzer()
        
        # 간단한 쿼리 패턴
        simple_request = ModelRequest(
            task_id="test3",
            task_type="data_query",
            content="현재가 알려주세요",
            content_type=ContentType.TEXT
        )
        complexity = analyzer.analyze_complexity(simple_request)
        assert complexity == TaskComplexity.SIMPLE
        
        # 복잡한 분석 패턴
        complex_request = ModelRequest(
            task_id="test4", 
            task_type="analysis",
            content="포트폴리오 최적화 전략을 수립하고 리스크 모델링을 통해 시뮬레이션해주세요",
            content_type=ContentType.MIXED
        )
        complexity = analyzer.analyze_complexity(complex_request)
        assert complexity in [TaskComplexity.COMPLEX, TaskComplexity.HIGHLY_COMPLEX]
    
    def test_task_type_complexity(self):
        """작업 유형별 복잡도 테스트"""
        analyzer = ComplexityAnalyzer()
        
        # 데이터 쿼리 - 단순
        query_request = ModelRequest(
            task_id="test5",
            task_type="data_query",
            content="test",
            content_type=ContentType.TEXT
        )
        complexity = analyzer.analyze_complexity(query_request)
        assert complexity == TaskComplexity.SIMPLE
        
        # 포트폴리오 최적화 - 매우 복잡
        portfolio_request = ModelRequest(
            task_id="test6",
            task_type="portfolio_optimization", 
            content="test",
            content_type=ContentType.MIXED
        )
        complexity = analyzer.analyze_complexity(portfolio_request)
        assert complexity == TaskComplexity.HIGHLY_COMPLEX

class TestModelLoadBalancer:
    """모델 로드밸런서 테스트"""
    
    def test_load_balancer_initialization(self):
        """로드밸런서 초기화 테스트"""
        balancer = ModelLoadBalancer()
        
        assert balancer is not None
        assert hasattr(balancer, 'model_usage')
        assert hasattr(balancer, 'model_queue_sizes')
        assert hasattr(balancer, 'model_response_times')
    
    def test_best_model_selection(self):
        """최적 모델 선택 테스트"""
        balancer = ModelLoadBalancer()
        
        # 특정 티어에서 최적 모델 선택
        best_model = balancer.get_best_model_for_tier(ModelTier.STANDARD)
        assert best_model is not None
        assert isinstance(best_model, str)
    
    def test_model_stats_update(self):
        """모델 통계 업데이트 테스트"""
        balancer = ModelLoadBalancer()
        
        model_name = "gpt-4"
        response_time = 1500.0  # 1.5초
        
        # 성공 케이스
        balancer.update_model_stats(model_name, response_time, success=True)
        assert balancer.model_usage[model_name] == 1
        assert len(balancer.model_response_times[model_name]) == 1
        
        # 실패 케이스
        balancer.update_model_stats(model_name, response_time, success=False)
        assert not balancer.model_availability[model_name]
    
    def test_queue_management(self):
        """큐 관리 테스트"""
        balancer = ModelLoadBalancer()
        
        model_name = "gpt-3.5-turbo"
        
        # 큐 크기 증가
        balancer.increment_queue(model_name)
        assert balancer.model_queue_sizes[model_name] == 1
        
        # 큐 크기 감소
        balancer.decrement_queue(model_name)
        assert balancer.model_queue_sizes[model_name] == 0

class TestSmartModelRouter:
    """스마트 모델 라우터 테스트"""
    
    def test_router_initialization(self):
        """라우터 초기화 테스트"""
        router = SmartModelRouter()
        
        assert router.policy is not None
        assert router.load_balancer is not None
        assert router.complexity_analyzer is not None
    
    @pytest.mark.asyncio
    async def test_request_routing(self):
        """요청 라우팅 테스트"""
        router = SmartModelRouter()
        
        request = ModelRequest(
            task_id="test_routing",
            task_type="sentiment_analysis",
            content="삼성전자 실적이 좋아 보입니다.",
            content_type=ContentType.TEXT
        )
        
        decision = await router.route_request(request)
        
        assert isinstance(decision, RoutingDecision)
        assert decision.model_tier is not None
        assert decision.model_name is not None
        assert decision.estimated_cost >= 0
        assert 0 <= decision.expected_quality <= 1
        assert len(decision.alternatives) >= 0
    
    @pytest.mark.asyncio
    async def test_escalation_decision(self):
        """에스컬레이션 판단 테스트"""
        router = SmartModelRouter()
        
        request = ModelRequest(
            task_id="test_escalation",
            task_type="signal_generation",
            content="복잡한 투자 신호 분석 요청",
            content_type=ContentType.MIXED
        )
        
        # 낮은 신뢰도 응답 시뮬레이션
        low_confidence_response = ModelResponse(
            content="분석 결과",
            model_tier=ModelTier.MINI,
            model_name="gpt-3.5-turbo",
            usage={"total_tokens": 100},
            cost=0.01,
            processing_time_ms=1000,
            confidence_score=0.5  # 낮은 신뢰도
        )
        
        escalation = await router.should_escalate(request, low_confidence_response)
        
        if escalation:  # 에스컬레이션 발생
            assert escalation.model_tier != ModelTier.MINI
            assert escalation.estimated_cost > low_confidence_response.cost
    
    @pytest.mark.asyncio
    async def test_routing_statistics(self):
        """라우팅 통계 테스트"""
        router = SmartModelRouter()
        
        # 여러 요청 시뮬레이션
        for i in range(3):
            request = ModelRequest(
                task_id=f"test_stats_{i}",
                task_type="sentiment_analysis",
                content=f"테스트 내용 {i}",
                content_type=ContentType.TEXT
            )
            await router.route_request(request)
        
        stats = await router.get_routing_statistics()
        
        assert "total_requests" in stats
        assert stats["total_requests"] >= 3
        assert "tier_usage_distribution" in stats

class TestCostOptimizer:
    """비용 최적화기 테스트"""
    
    def test_token_counter(self):
        """토큰 카운터 테스트"""
        counter = TokenCounter()
        
        # 한국어 텍스트 토큰 계산
        korean_text = "삼성전자의 실적이 향상되었습니다."
        token_count = counter.count_tokens(korean_text, "gpt-4")
        
        assert token_count > 0
        assert isinstance(token_count, int)
        
        # 비용 추정
        cost = counter.estimate_cost(korean_text, "gpt-4", is_input=True)
        assert cost > 0
        assert isinstance(cost, float)
    
    def test_content_compressor(self):
        """컨텐츠 압축기 테스트"""
        compressor = ContentCompressor()
        
        # 중복이 많은 텍스트
        redundant_text = """
        삼성전자가 좋습니다. 삼성전자가 정말 좋습니다.
        실적이 좋습니다. 실적이 아주 좋습니다.
        매출이 증가했습니다!!! 매출이 크게 증가했습니다!!!
        """
        
        result = compressor.compress_content(
            redundant_text, 
            target_reduction=0.3,
            strategy=OptimizationStrategy.BALANCED
        )
        
        assert isinstance(result, OptimizationResult)
        assert len(result.optimized_content) < len(result.original_content)
        assert result.token_savings > 0
        assert result.compression_ratio < 1.0
        assert 0 <= result.quality_impact <= 1.0
    
    def test_budget_manager(self):
        """예산 관리자 테스트"""
        budget_manager = BudgetManager()
        
        # 일일 예산 설정
        budget_manager.set_daily_budget(100.0)  # $100
        
        # 예산 가용성 확인
        is_available, remaining = budget_manager.check_budget_availability(10.0)
        assert is_available
        assert remaining == 100.0
        
        # 사용량 기록
        budget_manager.record_usage(25.0, "gpt-4")
        is_available, remaining = budget_manager.check_budget_availability(10.0)
        assert is_available
        assert remaining == 75.0
        
        # 사용량 요약
        summary = budget_manager.get_usage_summary()
        assert summary["total_usage"] == 25.0
        assert summary["remaining_budget"] == 75.0
    
    @pytest.mark.asyncio
    async def test_cost_optimizer_integration(self):
        """비용 최적화기 통합 테스트"""
        optimizer = CostOptimizer()
        
        # 긴 한국어 텍스트
        long_text = """
        삼성전자는 대한민국의 대표적인 기술 기업입니다. 
        반도체, 디스플레이, 모바일 등 다양한 사업을 영위하고 있으며,
        글로벌 시장에서 선도적인 위치를 차지하고 있습니다.
        최근 AI 반도체 시장에서의 성과가 주목받고 있으며,
        HBM(High Bandwidth Memory) 분야에서 독보적인 기술력을 보유하고 있습니다.
        """ * 3  # 내용 반복으로 긴 텍스트 생성
        
        result = await optimizer.optimize_request(
            content=long_text,
            model_name="gpt-4",
            strategy=OptimizationStrategy.BALANCED
        )
        
        assert isinstance(result, OptimizationResult)
        assert result.token_savings > 0
        assert result.cost_savings > 0
        assert len(result.optimized_content) < len(result.original_content)
    
    def test_model_recommendation(self):
        """모델 추천 테스트"""
        optimizer = CostOptimizer()
        
        # 품질 요구사항과 예산을 고려한 모델 추천
        tier, model_name = optimizer.recommend_model_tier(
            content="간단한 질문입니다.",
            quality_requirement=0.7,
            budget_limit=0.01
        )
        
        assert tier in [ModelTier.NANO, ModelTier.MINI, ModelTier.STANDARD, ModelTier.O3]
        assert isinstance(model_name, str)

class TestCacheManager:
    """캐시 매니저 테스트"""
    
    def test_lru_cache(self):
        """LRU 캐시 테스트"""
        cache = LRUCache(max_size=3)
        
        # 캐시 항목 추가
        entry1 = CacheEntry(
            key="test1",
            value="value1",
            cache_type=CacheType.PROMPT,
            created_at=datetime.now(),
            accessed_at=datetime.now(),
            access_count=0
        )
        
        cache.put(entry1)
        assert cache.get("test1") is not None
        assert cache.get("nonexistent") is None
        
        # 최대 크기 초과 시 LRU 제거 확인
        for i in range(5):
            entry = CacheEntry(
                key=f"test{i}",
                value=f"value{i}",
                cache_type=CacheType.PROMPT,
                created_at=datetime.now(),
                accessed_at=datetime.now(),
                access_count=0
            )
            cache.put(entry)
        
        assert len(cache.cache) <= 3  # 최대 크기 유지
    
    @pytest.mark.asyncio
    async def test_cache_manager(self):
        """캐시 매니저 테스트"""
        cache_manager = CacheManager()
        await cache_manager.initialize()
        
        # 캐시 저장
        test_content = "삼성전자 분석 테스트"
        test_value = {"result": "분석 완료"}
        
        await cache_manager.put(
            content=test_content,
            value=test_value,
            cache_type=CacheType.ANALYSIS
        )
        
        # 캐시 조회
        cached_result = await cache_manager.get(
            content=test_content,
            cache_type=CacheType.ANALYSIS
        )
        
        assert cached_result == test_value
        
        # 캐시 무효화
        await cache_manager.invalidate(
            content=test_content,
            cache_type=CacheType.ANALYSIS
        )
        
        invalidated_result = await cache_manager.get(
            content=test_content,
            cache_type=CacheType.ANALYSIS
        )
        
        assert invalidated_result is None
    
    @pytest.mark.asyncio
    async def test_prompt_cache(self):
        """프롬프트 캐시 테스트"""
        cache_manager = CacheManager()
        await cache_manager.initialize()
        
        prompt_cache = PromptCache(cache_manager)
        
        # 프롬프트 응답 캐시
        prompt = "삼성전자에 대해 분석해주세요."
        response = "삼성전자는 우수한 기업입니다."
        
        await prompt_cache.cache_prompt_response(
            prompt=prompt,
            response=response,
            model_name="gpt-4"
        )
        
        # 캐시된 응답 조회
        cached_response = await prompt_cache.get_cached_prompt_response(
            prompt=prompt,
            model_name="gpt-4"
        )
        
        assert cached_response == response
    
    @pytest.mark.asyncio
    async def test_vector_cache(self):
        """벡터 캐시 테스트"""
        cache_manager = CacheManager()
        await cache_manager.initialize()
        
        vector_cache = VectorCache(cache_manager)
        
        # 임베딩 캐시
        text = "삼성전자 주가 분석"
        embedding = [0.1, 0.2, 0.3] * 512  # 1536차원 벡터
        
        await vector_cache.cache_embedding(
            text=text,
            embedding=embedding,
            model="text-embedding-3-large"
        )
        
        # 캐시된 임베딩 조회
        cached_embedding = await vector_cache.get_cached_embedding(
            text=text,
            model="text-embedding-3-large"
        )
        
        assert cached_embedding is not None
        assert len(cached_embedding) == len(embedding)

class TestIntegrationScenarios:
    """통합 시나리오 테스트"""
    
    @pytest.mark.asyncio
    async def test_full_routing_pipeline(self):
        """전체 라우팅 파이프라인 테스트"""
        # 1. 요청 생성
        request = ModelRequest(
            task_id="integration_test",
            task_type="stock_analysis",
            content="삼성전자(005930)의 2024년 실적을 상세히 분석하고 투자 의견을 제시해주세요.",
            content_type=ContentType.MIXED
        )
        
        # 2. 복잡도 분석
        analyzer = ComplexityAnalyzer()
        complexity = analyzer.analyze_complexity(request)
        assert complexity in [TaskComplexity.MODERATE, TaskComplexity.COMPLEX, TaskComplexity.HIGHLY_COMPLEX]
        
        # 3. 모델 라우팅
        router = SmartModelRouter()
        routing_decision = await router.route_request(request)
        assert routing_decision.model_tier is not None
        
        # 4. 비용 최적화
        optimizer = CostOptimizer()
        optimization = await optimizer.optimize_request(
            content=request.content,
            model_name=routing_decision.model_name
        )
        assert optimization.token_savings >= 0
        
        # 5. 캐시 확인
        cache_manager = CacheManager()
        await cache_manager.initialize()
        
        cached_result = await cache_manager.get(
            content=request.content,
            cache_type=CacheType.ANALYSIS
        )
        # 첫 번째 요청이므로 캐시 미스 예상
        assert cached_result is None
    
    @pytest.mark.asyncio
    async def test_budget_constrained_routing(self):
        """예산 제약 라우팅 테스트"""
        # 낮은 예산 설정
        optimizer = CostOptimizer()
        optimizer.budget_manager.set_daily_budget(1.0)  # $1
        
        # 비용이 많이 드는 요청
        expensive_request = ModelRequest(
            task_id="expensive_test",
            task_type="portfolio_optimization",
            content="포트폴리오 최적화를 위한 상세한 분석" * 100,  # 매우 긴 내용
            content_type=ContentType.MIXED
        )
        
        # 예산 제약으로 인한 적극적 최적화
        optimization = await optimizer.optimize_request(
            content=expensive_request.content,
            model_name="gpt-4",
            strategy=OptimizationStrategy.AGGRESSIVE  # 적극적 압축
        )
        
        assert optimization.token_savings > 0
        assert optimization.compression_ratio < 0.8  # 20% 이상 압축

# 성능 테스트
class TestPerformance:
    """성능 테스트"""
    
    @pytest.mark.asyncio
    async def test_cache_performance(self):
        """캐시 성능 테스트"""
        cache = LRUCache(max_size=1000)
        
        # 대량 캐시 항목 생성
        start_time = asyncio.get_event_loop().time()
        
        for i in range(1000):
            entry = CacheEntry(
                key=f"perf_test_{i}",
                value=f"value_{i}",
                cache_type=CacheType.PROMPT,
                created_at=datetime.now(),
                accessed_at=datetime.now(),
                access_count=0
            )
            cache.put(entry)
        
        put_time = asyncio.get_event_loop().time() - start_time
        
        # 캐시 조회 성능
        start_time = asyncio.get_event_loop().time()
        
        for i in range(100):
            cache.get(f"perf_test_{i}")
        
        get_time = asyncio.get_event_loop().time() - start_time
        
        # 성능 기준 (매우 관대하게 설정)
        assert put_time < 1.0  # 1000개 저장에 1초 이내
        assert get_time < 0.1  # 100개 조회에 0.1초 이내
    
    @pytest.mark.asyncio
    async def test_routing_performance(self):
        """라우팅 성능 테스트"""
        router = SmartModelRouter()
        
        # 여러 요청 동시 처리
        requests = []
        for i in range(10):
            request = ModelRequest(
                task_id=f"perf_test_{i}",
                task_type="sentiment_analysis",
                content=f"성능 테스트 내용 {i}",
                content_type=ContentType.TEXT
            )
            requests.append(request)
        
        start_time = asyncio.get_event_loop().time()
        
        # 동시 라우팅 처리
        tasks = [router.route_request(req) for req in requests]
        results = await asyncio.gather(*tasks)
        
        processing_time = asyncio.get_event_loop().time() - start_time
        
        assert len(results) == 10
        assert all(isinstance(result, RoutingDecision) for result in results)
        assert processing_time < 2.0  # 10개 요청 처리에 2초 이내

# 테스트 실행
if __name__ == "__main__":
    pytest.main([__file__, "-v"])