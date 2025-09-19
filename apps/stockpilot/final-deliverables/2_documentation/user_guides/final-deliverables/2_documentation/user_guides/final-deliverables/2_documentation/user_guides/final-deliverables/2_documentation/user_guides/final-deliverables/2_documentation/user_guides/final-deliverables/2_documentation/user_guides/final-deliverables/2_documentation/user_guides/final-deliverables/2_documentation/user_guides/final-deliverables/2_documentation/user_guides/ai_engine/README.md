# StockPilot AI Engine

StockPilot의 고도화된 AI 분석 엔진입니다. RAG(Retrieval Augmented Generation) 시스템, 스마트 모델 라우팅, 비용 최적화, 품질 관문 등 최신 AI 기술을 적용하여 정확하고 효율적인 주식 분석을 제공합니다.

## 🏗️ 아키텍처

### 1. RAG 검색 시스템 (`rag/`)
- **embedder.py**: OpenAI text-embedding-3-large 모델로 텍스트 벡터화
- **indexer.py**: FAISS 기반 고성능 벡터 인덱싱 및 저장
- **retriever.py**: MMR 알고리즘 기반 유사성 검색 및 결과 다양화
- **context_builder.py**: 토큰 제한 내에서 최적 컨텍스트 구성

### 2. 분석 파이프라인 (`pipeline/`)
- **ingest_module.py**: 주식/뉴스 데이터 수집 및 벡터 색인화
- **analysis_module.py**: 감정분석, 기술적분석 등 종합 AI 분석
- **signal_module.py**: 포트폴리오 최적화 기반 매매 신호 생성
- **quality_gate.py**: 다층 품질 검증 및 신뢰도 측정

### 3. 스마트 라우팅 (`routing/`)
- **model_router.py**: 작업 복잡도 기반 최적 모델 선택 (nano→mini→standard→o3)
- **cost_optimizer.py**: 프롬프트 압축, 토큰 최적화, 예산 관리
- **cache_manager.py**: Redis/메모리 기반 멀티레벨 캐싱

### 4. 모니터링 시스템 (`monitoring/`)
- **usage_tracker.py**: 실시간 사용량 추적 및 성능 메트릭
- **cost_analyzer.py**: 비용 분석, 예측, 최적화 권고

## 🚀 빠른 시작

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정
```bash
export OPENAI_API_KEY="your-openai-api-key"
export REDIS_URL="redis://localhost:6379"  # 선택사항
```

### 3. 기본 사용법
```python
import asyncio
from ai_engine.main import create_ai_engine, create_default_config

async def main():
    # 설정 생성
    config = create_default_config(
        openai_api_key="your-openai-api-key",
        redis_url="redis://localhost:6379",  # 선택사항
        daily_budget=100.0  # 일일 예산 (USD)
    )
    
    # AI 엔진 초기화
    engine = await create_ai_engine(config)
    
    try:
        # 주식 분석
        result = await engine.process_stock_data(
            symbol="AAPL",
            price_data=[{
                "date": "2024-01-01",
                "open": 150.0,
                "high": 155.0,
                "low": 149.0,
                "close": 152.0,
                "volume": 1000000
            }],
            news_data=[{
                "title": "Apple Reports Strong Q4 Earnings",
                "content": "Apple Inc. reported better-than-expected earnings...",
                "published_date": "2024-01-01T10:00:00Z",
                "source": "Reuters"
            }],
            analysis_type="comprehensive"
        )
        
        print(f"Analysis completed: {result['analysis_result']['summary']}")
        
        # 포트폴리오 분석
        portfolio_result = await engine.generate_portfolio_analysis(
            portfolio_symbols=["AAPL", "GOOGL", "MSFT"],
            portfolio_weights={"AAPL": 0.4, "GOOGL": 0.3, "MSFT": 0.3}
        )
        
        print(f"Portfolio recommendation: {portfolio_result['portfolio_signal']['overall_recommendation']}")
        
        # 시장 인사이트 검색
        search_result = await engine.search_market_insights(
            query="technology sector outlook 2024",
            symbols=["AAPL", "GOOGL", "MSFT"]
        )
        
        print(f"Found {len(search_result['results'])} relevant insights")
        
    finally:
        await engine.shutdown()

# 실행
asyncio.run(main())
```

## ⚙️ 고급 설정

### 모델 정책 커스터마이징
```python
from ai_engine.config.model_policy import StockPilotModelPolicy, TaskComplexity, ContentType

# 커스텀 정책 생성
policy = StockPilotModelPolicy()

# 특정 작업에 대한 모델 티어 확인
model_tier = policy.get_model_for_task(
    task_type="signal_generation",
    complexity=TaskComplexity.COMPLEX,
    content_type=ContentType.MIXED
)
print(f"Recommended model tier: {model_tier}")
```

### 비용 최적화 설정
```python
from ai_engine.routing.cost_optimizer import OptimizationStrategy

# AI 엔진 설정에서 비용 최적화 전략 선택
config.cost_optimization_level = "aggressive"  # "conservative", "balanced", "aggressive"

# 또는 직접 컨텐츠 압축
from ai_engine.routing.cost_optimizer import optimize_content

optimized = await optimize_content(
    content="Your long prompt here...",
    model_name="gpt-4",
    strategy=OptimizationStrategy.BALANCED
)
print(f"Token savings: {optimized.token_savings}")
```

### 품질 관문 설정
```python
from ai_engine.pipeline.quality_gate import QualityLevel

# 더 엄격한 품질 기준 적용
result = await engine.process_stock_data(
    symbol="AAPL",
    price_data=price_data,
    news_data=news_data,
    quality_level=QualityLevel.CRITICAL  # CRITICAL, HIGH, MEDIUM, LOW
)
```

## 📊 모니터링 및 분석

### 실시간 메트릭 조회
```python
# 시스템 상태 확인
status = await engine.get_system_status()
print(f"Cache hit rate: {status['cache_status']['overall']['hit_rate']:.2%}")

# 비용 분석
from ai_engine.monitoring.cost_analyzer import get_cost_analysis_report
cost_report = await get_cost_analysis_report(days=30)
print(f"Monthly cost: ${cost_report['total_cost']:.2f}")

# 사용량 통계
from ai_engine.monitoring.usage_tracker import get_usage_statistics
usage_stats = await get_usage_statistics(days=7)
print(f"Weekly requests: {usage_stats['total_requests']}")
```

### 비용 알림 및 최적화 권고
```python
from ai_engine.monitoring.cost_analyzer import get_cost_alerts, get_optimization_recommendations

# 비용 알림 확인
alerts = await get_cost_alerts()
for alert in alerts:
    if alert['severity'] in ['high', 'critical']:
        print(f"Alert: {alert['message']}")

# 최적화 권고사항
recommendations = await get_optimization_recommendations()
for rec in recommendations:
    if rec['priority'] == 'high':
        print(f"Recommendation: {rec['description']} (${rec['estimated_savings']:.2f} savings)")
```

## 🔧 개발자 가이드

### 커스텀 분석 모듈 추가
```python
from ai_engine.pipeline.analysis_module import AnalysisModule

class CustomAnalyzer(AnalysisModule):
    async def analyze_custom_metric(self, data):
        # 커스텀 분석 로직
        return analysis_result
```

### 새로운 데이터 소스 통합
```python
from ai_engine.pipeline.ingest_module import DataIngestor

# 커스텀 데이터 소스 추가
ingestor = DataIngestor()
await ingestor.ingest_custom_data(
    source="custom_api",
    data=custom_data,
    metadata={"type": "alternative_data"}
)
```

## 🛠️ 트러블슈팅

### 일반적인 문제

1. **OpenAI API 키 오류**
   ```bash
   export OPENAI_API_KEY="your-actual-api-key"
   ```

2. **Redis 연결 실패**
   ```bash
   # Redis 없이 실행 (메모리 캐시만 사용)
   config.redis_url = None
   ```

3. **FAISS 설치 문제**
   ```bash
   # CPU 버전 사용 (기본)
   pip install faiss-cpu
   
   # GPU 버전 (CUDA 필요)
   pip install faiss-gpu
   ```

4. **메모리 부족**
   ```python
   # 벡터 인덱스 크기 제한
   config.max_index_size = 10000
   
   # 캐시 크기 조정
   config.memory_cache_size = 500
   ```

### 로깅 활성화
```python
import logging
logging.basicConfig(level=logging.INFO)

# 상세 디버그 로그
logging.getLogger("ai_engine").setLevel(logging.DEBUG)
```

## 📈 성능 최적화

1. **Redis 캐시 사용**: 분산 환경에서 캐시 공유
2. **배치 임베딩**: 여러 텍스트를 한 번에 임베딩
3. **벡터 인덱스 최적화**: FAISS 인덱스 타입 조정
4. **프롬프트 캐싱**: 유사한 요청에 대한 응답 재사용
5. **모델 티어 최적화**: 작업 복잡도에 맞는 모델 선택

## 🔐 보안 고려사항

- API 키는 환경 변수로 관리
- 사용자 데이터는 벡터화 후 원본 삭제
- Redis 연결 시 인증 활성화
- 요청 로깅에서 민감 정보 제외

## 📚 추가 자료

- [OpenAI API 문서](https://platform.openai.com/docs)
- [FAISS 문서](https://github.com/facebookresearch/faiss)
- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [Redis 문서](https://redis.io/documentation)