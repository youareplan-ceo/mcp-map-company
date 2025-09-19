"""
StockPilot AI Engine - 메인 통합 모듈
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json

# RAG 시스템
from .rag.embedder import TextEmbedder, initialize_embedder
from .rag.indexer import VectorIndexer, initialize_indexer
from .rag.retriever import VectorRetriever, initialize_retriever
from .rag.context_builder import ContextBuilder, initialize_context_builder

# 파이프라인 모듈들
from .pipeline.ingest_module import DataIngestor, initialize_ingestor
from .pipeline.analysis_module import AnalysisEngine, initialize_analysis_engine
from .pipeline.signal_module import SignalEngine, initialize_signal_engine
from .pipeline.quality_gate import QualityGate, initialize_quality_gate

# 라우팅 및 최적화
from .routing.model_router import SmartModelRouter, initialize_router
from .routing.cost_optimizer import CostOptimizer, initialize_cost_optimizer
from .routing.cache_manager import CacheManager, initialize_cache

# 모니터링
from .monitoring.usage_tracker import UsageTracker, initialize_usage_tracking
from .monitoring.cost_analyzer import CostAnalyzer, initialize_cost_analyzer

# 설정
from .config.model_policy import StockPilotModelPolicy

logger = logging.getLogger(__name__)

@dataclass
class AIEngineConfig:
    """AI 엔진 설정"""
    # OpenAI 설정
    openai_api_key: str
    openai_base_url: Optional[str] = None
    
    # 벡터 DB 설정
    vector_db_path: str = "./vector_db"
    embedding_model: str = "text-embedding-3-large"
    
    # 캐시 설정
    redis_url: Optional[str] = None
    enable_cache: bool = True
    
    # 모니터링 설정
    usage_db_path: str = "./usage.db"
    enable_monitoring: bool = True
    
    # 품질 설정
    min_confidence_threshold: float = 0.7
    enable_quality_gates: bool = True
    
    # 비용 제한
    daily_budget: Optional[float] = None
    cost_optimization_level: str = "balanced"  # aggressive, balanced, conservative

class StockPilotAIEngine:
    """StockPilot AI 엔진 메인 클래스"""
    
    def __init__(self, config: AIEngineConfig):
        self.config = config
        self.policy = StockPilotModelPolicy()
        
        # 컴포넌트들
        self.embedder: Optional[TextEmbedder] = None
        self.indexer: Optional[VectorIndexer] = None
        self.retriever: Optional[VectorRetriever] = None
        self.context_builder: Optional[ContextBuilder] = None
        
        self.ingestor: Optional[DataIngestor] = None
        self.analyzer: Optional[AnalysisEngine] = None
        self.signal_engine: Optional[SignalEngine] = None
        self.quality_gate: Optional[QualityGate] = None
        
        self.router: Optional[SmartModelRouter] = None
        self.optimizer: Optional[CostOptimizer] = None
        self.cache_manager: Optional[CacheManager] = None
        
        self.usage_tracker: Optional[UsageTracker] = None
        self.cost_analyzer: Optional[CostAnalyzer] = None
        
        self.initialized = False
    
    async def initialize(self):
        """AI 엔진 초기화"""
        logger.info("Initializing StockPilot AI Engine...")
        
        try:
            # 환경 변수 설정
            os.environ["OPENAI_API_KEY"] = self.config.openai_api_key
            if self.config.openai_base_url:
                os.environ["OPENAI_BASE_URL"] = self.config.openai_base_url
            
            # RAG 시스템 초기화
            logger.info("Initializing RAG system...")
            self.embedder = await initialize_embedder(
                model_name=self.config.embedding_model
            )
            
            self.indexer = await initialize_indexer(
                storage_path=self.config.vector_db_path,
                embedder=self.embedder
            )
            
            self.retriever = await initialize_retriever(
                indexer=self.indexer
            )
            
            self.context_builder = await initialize_context_builder()
            
            # 캐시 시스템 초기화
            if self.config.enable_cache:
                logger.info("Initializing cache system...")
                self.cache_manager = await initialize_cache(self.config.redis_url)
            
            # 파이프라인 모듈 초기화
            logger.info("Initializing pipeline modules...")
            self.ingestor = await initialize_ingestor(
                indexer=self.indexer,
                cache_manager=self.cache_manager
            )
            
            self.analyzer = await initialize_analysis_engine(
                embedder=self.embedder,
                retriever=self.retriever,
                context_builder=self.context_builder
            )
            
            self.signal_engine = await initialize_signal_engine(
                analyzer=self.analyzer
            )
            
            if self.config.enable_quality_gates:
                self.quality_gate = await initialize_quality_gate()
            
            # 라우팅 및 최적화 초기화
            logger.info("Initializing routing and optimization...")
            self.router = await initialize_router()
            self.optimizer = await initialize_cost_optimizer()
            
            # 예산 설정
            if self.config.daily_budget:
                self.optimizer.budget_manager.set_daily_budget(self.config.daily_budget)
            
            # 모니터링 초기화
            if self.config.enable_monitoring:
                logger.info("Initializing monitoring system...")
                self.usage_tracker = await initialize_usage_tracking(
                    self.config.usage_db_path
                )
                self.cost_analyzer = await initialize_cost_analyzer(self.usage_tracker)
            
            self.initialized = True
            logger.info("StockPilot AI Engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI Engine: {e}")
            raise
    
    async def process_stock_data(
        self,
        symbol: str,
        price_data: List[Dict],
        news_data: List[Dict],
        analysis_type: str = "comprehensive",
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """주식 데이터 종합 처리"""
        if not self.initialized:
            raise RuntimeError("AI Engine not initialized")
        
        start_time = datetime.now()
        request_id = f"stock_analysis_{symbol}_{int(start_time.timestamp())}"
        
        try:
            logger.info(f"Processing stock data for {symbol} (request: {request_id})")
            
            # 1. 데이터 수집 및 색인화
            if self.ingestor:
                ingest_result = await self.ingestor.ingest_stock_data(
                    symbol=symbol,
                    price_data=price_data,
                    news_data=news_data,
                    metadata={"analysis_type": analysis_type, "user_id": user_id}
                )
                logger.debug(f"Data ingestion completed: {ingest_result.total_documents} documents indexed")
            
            # 2. AI 분석 수행
            if self.analyzer:
                analysis_result = await self.analyzer.analyze_stock_comprehensive(
                    symbol=symbol,
                    price_data=price_data,
                    news_data=news_data,
                    analysis_depth="detailed" if analysis_type == "comprehensive" else "standard"
                )
                logger.debug(f"Analysis completed for {symbol}")
            else:
                raise RuntimeError("Analysis engine not available")
            
            # 3. 품질 검증
            quality_report = None
            if self.quality_gate:
                quality_report = await self.quality_gate.validate_analysis_pipeline(
                    symbol=symbol,
                    price_data=price_data,
                    news_data=news_data,
                    analysis_result=analysis_result
                )
                logger.debug(f"Quality validation score: {quality_report.overall_score:.2f}")
            
            # 4. 신호 생성
            signals = None
            if self.signal_engine and quality_report and quality_report.overall_score >= self.config.min_confidence_threshold:
                signals = await self.signal_engine.generate_trading_signal(
                    symbol=symbol,
                    analysis_result=analysis_result,
                    risk_profile="moderate",
                    portfolio_context={}
                )
                logger.debug(f"Trading signal generated: {signals.action} ({signals.strength.value})")
            
            # 5. 결과 패키징
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            result = {
                "request_id": request_id,
                "symbol": symbol,
                "analysis_type": analysis_type,
                "timestamp": start_time.isoformat(),
                "processing_time_ms": processing_time,
                "analysis_result": {
                    "sentiment": analysis_result.sentiment.__dict__ if analysis_result.sentiment else None,
                    "technical": analysis_result.technical.__dict__ if analysis_result.technical else None,
                    "summary": analysis_result.summary,
                    "confidence": analysis_result.confidence,
                    "key_insights": analysis_result.key_insights,
                    "risk_factors": analysis_result.risk_factors
                },
                "quality_report": {
                    "overall_score": quality_report.overall_score if quality_report else None,
                    "validation_result": quality_report.validation_result.value if quality_report else None,
                    "recommendations": quality_report.recommendations if quality_report else []
                } if quality_report else None,
                "trading_signal": {
                    "action": signals.action,
                    "strength": signals.strength.value,
                    "confidence": signals.confidence,
                    "target_price": signals.target_price,
                    "stop_loss": signals.stop_loss,
                    "position_size": signals.position_size,
                    "reasoning": signals.reasoning
                } if signals else None,
                "metadata": {
                    "data_quality": {
                        "price_data_points": len(price_data),
                        "news_items": len(news_data)
                    },
                    "cost_info": {
                        "estimated_cost": 0.0  # 실제 비용은 사용량 추적에서 계산
                    }
                }
            }
            
            # 6. 사용량 추적 (백그라운드)
            if self.usage_tracker:
                asyncio.create_task(self._track_usage(
                    request_id=request_id,
                    symbol=symbol,
                    processing_time_ms=processing_time,
                    success=True,
                    user_id=user_id
                ))
            
            logger.info(f"Stock data processing completed for {symbol} in {processing_time:.0f}ms")
            return result
            
        except Exception as e:
            logger.error(f"Stock data processing failed for {symbol}: {e}")
            
            # 오류 추적
            if self.usage_tracker:
                asyncio.create_task(self._track_error(
                    request_id=request_id,
                    symbol=symbol,
                    error=str(e),
                    user_id=user_id
                ))
            
            return {
                "request_id": request_id,
                "symbol": symbol,
                "error": str(e),
                "timestamp": start_time.isoformat(),
                "processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000
            }
    
    async def generate_portfolio_analysis(
        self,
        portfolio_symbols: List[str],
        portfolio_weights: Optional[Dict[str, float]] = None,
        rebalancing_constraints: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """포트폴리오 분석 및 최적화"""
        if not self.initialized:
            raise RuntimeError("AI Engine not initialized")
        
        if not self.signal_engine:
            raise RuntimeError("Signal engine not available")
        
        start_time = datetime.now()
        request_id = f"portfolio_analysis_{int(start_time.timestamp())}"
        
        try:
            logger.info(f"Generating portfolio analysis for {len(portfolio_symbols)} symbols")
            
            # 각 종목별 분석 수행 (간소화된 버전)
            symbol_analyses = {}
            for symbol in portfolio_symbols:
                # 여기서는 간단한 분석만 수행 (실제로는 최신 데이터 필요)
                analysis_result = await self.analyzer.analyze_stock_quick(symbol)
                symbol_analyses[symbol] = analysis_result
            
            # 포트폴리오 수준 신호 생성
            portfolio_signal = await self.signal_engine.generate_portfolio_signals(
                portfolio_symbols=portfolio_symbols,
                analysis_results_by_symbol=symbol_analyses,
                portfolio_constraints=rebalancing_constraints or {}
            )
            
            # 품질 검증
            quality_report = None
            if self.quality_gate:
                quality_report = await self.quality_gate.validate_portfolio_signals(
                    portfolio_signal
                )
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            result = {
                "request_id": request_id,
                "portfolio_symbols": portfolio_symbols,
                "timestamp": start_time.isoformat(),
                "processing_time_ms": processing_time,
                "portfolio_signal": {
                    "portfolio_id": portfolio_signal.portfolio_id,
                    "overall_recommendation": portfolio_signal.overall_recommendation,
                    "confidence": portfolio_signal.confidence,
                    "individual_signals": [
                        {
                            "symbol": signal.symbol,
                            "action": signal.action,
                            "strength": signal.strength.value,
                            "position_size": signal.position_size
                        }
                        for signal in portfolio_signal.signals
                    ],
                    "risk_metrics": portfolio_signal.risk_metrics,
                    "rebalancing_suggestions": portfolio_signal.rebalancing_suggestions
                },
                "quality_report": {
                    "overall_score": quality_report.overall_score if quality_report else None,
                    "validation_result": quality_report.validation_result.value if quality_report else None,
                    "recommendations": quality_report.recommendations if quality_report else []
                } if quality_report else None
            }
            
            logger.info(f"Portfolio analysis completed in {processing_time:.0f}ms")
            return result
            
        except Exception as e:
            logger.error(f"Portfolio analysis failed: {e}")
            return {
                "request_id": request_id,
                "error": str(e),
                "timestamp": start_time.isoformat(),
                "processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000
            }
    
    async def search_market_insights(
        self,
        query: str,
        symbols: Optional[List[str]] = None,
        max_results: int = 10,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """시장 인사이트 검색"""
        if not self.initialized or not self.retriever:
            raise RuntimeError("AI Engine or retriever not available")
        
        start_time = datetime.now()
        request_id = f"search_{int(start_time.timestamp())}"
        
        try:
            logger.info(f"Searching market insights for query: {query}")
            
            # 벡터 검색 수행
            search_results = await self.retriever.search_similar(
                query=query,
                limit=max_results,
                filters={"symbols": symbols} if symbols else None
            )
            
            # 컨텍스트 구성
            if self.context_builder:
                context = await self.context_builder.build_search_context(
                    query=query,
                    search_results=search_results.results
                )
            else:
                context = {"raw_results": [r.__dict__ for r in search_results.results]}
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            result = {
                "request_id": request_id,
                "query": query,
                "symbols_filter": symbols,
                "timestamp": start_time.isoformat(),
                "processing_time_ms": processing_time,
                "results": [
                    {
                        "content": result.content,
                        "score": result.similarity_score,
                        "metadata": result.metadata,
                        "source": result.metadata.get("source", "unknown")
                    }
                    for result in search_results.results
                ],
                "context": context,
                "total_results": len(search_results.results)
            }
            
            logger.info(f"Market insights search completed: {len(search_results.results)} results in {processing_time:.0f}ms")
            return result
            
        except Exception as e:
            logger.error(f"Market insights search failed: {e}")
            return {
                "request_id": request_id,
                "query": query,
                "error": str(e),
                "timestamp": start_time.isoformat(),
                "processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000
            }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 조회"""
        try:
            status = {
                "engine_status": "running" if self.initialized else "not_initialized",
                "timestamp": datetime.now().isoformat(),
                "components": {
                    "rag_system": {
                        "embedder": self.embedder is not None,
                        "indexer": self.indexer is not None,
                        "retriever": self.retriever is not None,
                        "context_builder": self.context_builder is not None
                    },
                    "pipeline": {
                        "ingestor": self.ingestor is not None,
                        "analyzer": self.analyzer is not None,
                        "signal_engine": self.signal_engine is not None,
                        "quality_gate": self.quality_gate is not None
                    },
                    "routing": {
                        "router": self.router is not None,
                        "optimizer": self.optimizer is not None,
                        "cache_manager": self.cache_manager is not None
                    },
                    "monitoring": {
                        "usage_tracker": self.usage_tracker is not None,
                        "cost_analyzer": self.cost_analyzer is not None
                    }
                }
            }
            
            # 추가 통계 정보
            if self.usage_tracker:
                try:
                    usage_stats = await self.usage_tracker.get_real_time_stats()
                    status["real_time_metrics"] = usage_stats
                except Exception as e:
                    status["real_time_metrics"] = {"error": str(e)}
            
            if self.cache_manager:
                try:
                    cache_stats = await self.cache_manager.get_cache_stats()
                    status["cache_status"] = cache_stats
                except Exception as e:
                    status["cache_status"] = {"error": str(e)}
            
            return status
            
        except Exception as e:
            return {
                "engine_status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _track_usage(
        self, 
        request_id: str, 
        symbol: str, 
        processing_time_ms: float, 
        success: bool, 
        user_id: Optional[str] = None
    ):
        """사용량 추적 (내부 메서드)"""
        if not self.usage_tracker:
            return
        
        try:
            # 간소화된 사용량 기록
            from .routing.model_router import ModelRequest, ModelResponse
            from .config.model_policy import ContentType, ModelTier
            
            # 임시 요청/응답 객체 생성
            request = ModelRequest(
                task_id=request_id,
                task_type="stock_analysis",
                content=f"Analysis for {symbol}",
                content_type=ContentType.MIXED
            )
            
            response = ModelResponse(
                content="Analysis completed",
                model_tier=ModelTier.STANDARD,
                model_name="gpt-4",
                usage={"prompt_tokens": 500, "completion_tokens": 300, "total_tokens": 800},
                cost=0.024,  # 추정 비용
                processing_time_ms=processing_time_ms
            )
            
            await self.usage_tracker.track_model_usage(request, response, False, user_id)
            
        except Exception as e:
            logger.error(f"Failed to track usage: {e}")
    
    async def _track_error(
        self, 
        request_id: str, 
        symbol: str, 
        error: str, 
        user_id: Optional[str] = None
    ):
        """오류 추적 (내부 메서드)"""
        if not self.usage_tracker:
            return
        
        try:
            from .routing.model_router import ModelRequest
            from .config.model_policy import ContentType
            
            request = ModelRequest(
                task_id=request_id,
                task_type="stock_analysis",
                content=f"Analysis for {symbol}",
                content_type=ContentType.MIXED
            )
            
            await self.usage_tracker.track_error(request, error, user_id)
            
        except Exception as e:
            logger.error(f"Failed to track error: {e}")
    
    async def shutdown(self):
        """AI 엔진 종료"""
        logger.info("Shutting down StockPilot AI Engine...")
        
        try:
            # 각 컴포넌트 정리
            if self.cache_manager:
                await self.cache_manager.cleanup_expired()
            
            # 추가 정리 작업들...
            
            self.initialized = False
            logger.info("AI Engine shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# 편의 함수들
async def create_ai_engine(config: AIEngineConfig) -> StockPilotAIEngine:
    """AI 엔진 생성 및 초기화"""
    engine = StockPilotAIEngine(config)
    await engine.initialize()
    return engine

def create_default_config(
    openai_api_key: str,
    redis_url: Optional[str] = None,
    daily_budget: Optional[float] = None
) -> AIEngineConfig:
    """기본 설정으로 AIEngineConfig 생성"""
    return AIEngineConfig(
        openai_api_key=openai_api_key,
        redis_url=redis_url,
        daily_budget=daily_budget,
        vector_db_path="./stockpilot_vector_db",
        usage_db_path="./stockpilot_usage.db",
        embedding_model="text-embedding-3-large",
        enable_cache=True,
        enable_monitoring=True,
        enable_quality_gates=True,
        min_confidence_threshold=0.7,
        cost_optimization_level="balanced"
    )

# 실제 사용 예시
async def example_usage():
    """사용 예시"""
    
    # 설정 생성
    config = create_default_config(
        openai_api_key="your-openai-api-key",
        redis_url="redis://localhost:6379",
        daily_budget=100.0
    )
    
    # AI 엔진 생성
    engine = await create_ai_engine(config)
    
    try:
        # 주식 분석
        result = await engine.process_stock_data(
            symbol="AAPL",
            price_data=[{"date": "2024-01-01", "open": 150, "close": 152, "volume": 1000000}],
            news_data=[{"title": "Apple news", "content": "Apple reports strong earnings"}],
            analysis_type="comprehensive"
        )
        
        print(f"Analysis result: {result}")
        
        # 포트폴리오 분석
        portfolio_result = await engine.generate_portfolio_analysis(
            portfolio_symbols=["AAPL", "GOOGL", "MSFT"],
            portfolio_weights={"AAPL": 0.4, "GOOGL": 0.3, "MSFT": 0.3}
        )
        
        print(f"Portfolio analysis: {portfolio_result}")
        
        # 시장 검색
        search_result = await engine.search_market_insights(
            query="technology sector outlook",
            symbols=["AAPL", "GOOGL"]
        )
        
        print(f"Search results: {search_result}")
        
        # 시스템 상태 확인
        status = await engine.get_system_status()
        print(f"System status: {status}")
        
    finally:
        await engine.shutdown()

if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(level=logging.INFO)
    
    # 예시 실행
    asyncio.run(example_usage())