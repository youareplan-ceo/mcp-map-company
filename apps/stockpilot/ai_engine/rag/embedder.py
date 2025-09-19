"""
텍스트 임베딩 생성 모듈
OpenAI text-embedding-3-large 모델을 활용한 벡터 임베딩 생성
비용 최적화 및 캐시 기능 포함
"""

import asyncio
import hashlib
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
import openai
from openai import AsyncOpenAI
import redis
import pickle
from dataclasses import dataclass

from ..config.model_policy import model_policy

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingRequest:
    """임베딩 요청 데이터 구조"""
    text: str
    document_type: str  # 'news', 'price_data', 'analysis', 'strategy'
    metadata: Dict[str, Any]
    priority: int = 1  # 1(낮음) ~ 5(높음)
    use_cache: bool = True


@dataclass 
class EmbeddingResult:
    """임베딩 결과 데이터 구조"""
    embedding: List[float]
    text_hash: str
    model_version: str
    token_count: int
    cost: float
    created_at: datetime
    cached: bool = False


class TextEmbedder:
    """
    텍스트 임베딩 생성 및 관리 클래스
    OpenAI text-embedding-3 모델 활용
    """
    
    def __init__(
        self, 
        openai_api_key: str,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 1
    ):
        """
        초기화
        
        Args:
            openai_api_key: OpenAI API 키
            redis_host: Redis 호스트
            redis_port: Redis 포트
            redis_db: Redis 데이터베이스 번호
        """
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.redis_client = redis.Redis(
            host=redis_host, 
            port=redis_port, 
            db=redis_db,
            decode_responses=False
        )
        
        # 모델 설정
        self.embedding_models = {
            "standard": "text-embedding-3-large",    # 3072차원, 고품질
            "efficient": "text-embedding-3-small",   # 1536차원, 경제적
        }
        
        # 비용 정보 (1M 토큰당)
        self.embedding_costs = {
            "text-embedding-3-large": 0.00013,   # $0.13/1M tokens
            "text-embedding-3-small": 0.00002,   # $0.02/1M tokens
        }
        
        # 캐시 설정
        self.cache_ttl = 86400 * 7  # 7일
        self.cache_prefix = "stockpilot:embedding:"
        
        # 배치 처리 설정
        self.batch_size = 100
        self.max_concurrent = 10
        
    def _generate_text_hash(self, text: str, model: str) -> str:
        """
        텍스트와 모델 조합의 해시 생성 (캐시 키용)
        
        Args:
            text: 입력 텍스트
            model: 모델명
            
        Returns:
            str: SHA256 해시
        """
        content = f"{model}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _get_cached_embedding(self, text_hash: str) -> Optional[EmbeddingResult]:
        """
        캐시된 임베딩 조회
        
        Args:
            text_hash: 텍스트 해시
            
        Returns:
            Optional[EmbeddingResult]: 캐시된 결과 또는 None
        """
        try:
            cache_key = f"{self.cache_prefix}{text_hash}"
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                result = pickle.loads(cached_data)
                result.cached = True
                logger.debug(f"캐시에서 임베딩 조회: {text_hash[:8]}...")
                return result
                
        except Exception as e:
            logger.warning(f"캐시 조회 실패: {str(e)}")
            
        return None
    
    def _cache_embedding(self, text_hash: str, result: EmbeddingResult):
        """
        임베딩 결과 캐시 저장
        
        Args:
            text_hash: 텍스트 해시
            result: 임베딩 결과
        """
        try:
            cache_key = f"{self.cache_prefix}{text_hash}"
            cached_data = pickle.dumps(result)
            self.redis_client.setex(cache_key, self.cache_ttl, cached_data)
            logger.debug(f"임베딩 캐시 저장: {text_hash[:8]}...")
            
        except Exception as e:
            logger.warning(f"캐시 저장 실패: {str(e)}")
    
    def _choose_model(self, document_type: str, text_length: int) -> str:
        """
        문서 유형과 길이에 따른 최적 임베딩 모델 선택
        
        Args:
            document_type: 문서 유형
            text_length: 텍스트 길이
            
        Returns:
            str: 선택된 모델명
        """
        # 중요한 분석이나 긴 텍스트는 고품질 모델 사용
        if (document_type in ['strategy', 'analysis'] or 
            text_length > 5000):
            return self.embedding_models["standard"]
        
        # 일반적인 경우 경제적 모델 사용
        return self.embedding_models["efficient"]
    
    def _estimate_tokens(self, text: str) -> int:
        """
        텍스트의 대략적인 토큰 수 추정
        
        Args:
            text: 입력 텍스트
            
        Returns:
            int: 추정 토큰 수
        """
        # 영어: 대략 4글자당 1토큰, 한글: 대략 2글자당 1토큰
        char_count = len(text)
        korean_chars = sum(1 for char in text if '가' <= char <= '힣')
        english_chars = char_count - korean_chars
        
        estimated_tokens = (korean_chars // 2) + (english_chars // 4)
        return max(estimated_tokens, 1)  # 최소 1토큰
    
    async def _create_embedding(
        self, 
        text: str, 
        model: str
    ) -> Tuple[List[float], int]:
        """
        OpenAI API를 통한 임베딩 생성
        
        Args:
            text: 입력 텍스트
            model: 임베딩 모델명
            
        Returns:
            Tuple[List[float], int]: (임베딩 벡터, 사용된 토큰 수)
        """
        try:
            response = await self.client.embeddings.create(
                input=text,
                model=model
            )
            
            embedding = response.data[0].embedding
            token_count = response.usage.total_tokens
            
            return embedding, token_count
            
        except Exception as e:
            logger.error(f"임베딩 생성 실패: {str(e)}")
            raise
    
    async def embed_text(self, request: EmbeddingRequest) -> EmbeddingResult:
        """
        단일 텍스트의 임베딩 생성
        
        Args:
            request: 임베딩 요청
            
        Returns:
            EmbeddingResult: 임베딩 결과
        """
        try:
            # 모델 선택
            model = self._choose_model(request.document_type, len(request.text))
            text_hash = self._generate_text_hash(request.text, model)
            
            # 캐시 확인
            if request.use_cache:
                cached_result = self._get_cached_embedding(text_hash)
                if cached_result:
                    return cached_result
            
            # 토큰 수 추정 및 비용 계산
            estimated_tokens = self._estimate_tokens(request.text)
            estimated_cost = (estimated_tokens / 1000000) * self.embedding_costs[model]
            
            logger.info(f"임베딩 생성 시작: {request.document_type}, "
                       f"예상 토큰: {estimated_tokens}, 예상 비용: ${estimated_cost:.6f}")
            
            # 임베딩 생성
            embedding, actual_tokens = await self._create_embedding(request.text, model)
            actual_cost = (actual_tokens / 1000000) * self.embedding_costs[model]
            
            # 결과 생성
            result = EmbeddingResult(
                embedding=embedding,
                text_hash=text_hash,
                model_version=model,
                token_count=actual_tokens,
                cost=actual_cost,
                created_at=datetime.utcnow(),
                cached=False
            )
            
            # 캐시 저장
            if request.use_cache:
                self._cache_embedding(text_hash, result)
            
            logger.info(f"임베딩 생성 완료: 실제 토큰: {actual_tokens}, "
                       f"실제 비용: ${actual_cost:.6f}")
            
            return result
            
        except Exception as e:
            logger.error(f"임베딩 생성 실패: {str(e)}")
            raise
    
    async def embed_batch(
        self, 
        requests: List[EmbeddingRequest]
    ) -> List[EmbeddingResult]:
        """
        배치 임베딩 생성 (비용 효율화)
        
        Args:
            requests: 임베딩 요청 리스트
            
        Returns:
            List[EmbeddingResult]: 임베딩 결과 리스트
        """
        try:
            logger.info(f"배치 임베딩 시작: {len(requests)}개 텍스트")
            
            # 우선순위별 정렬
            sorted_requests = sorted(requests, key=lambda x: x.priority, reverse=True)
            
            # 배치 단위로 분할
            batches = [
                sorted_requests[i:i + self.batch_size] 
                for i in range(0, len(sorted_requests), self.batch_size)
            ]
            
            all_results = []
            
            # 동시 처리를 위한 세마포어
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            async def process_batch(batch):
                async with semaphore:
                    batch_results = []
                    for request in batch:
                        try:
                            result = await self.embed_text(request)
                            batch_results.append(result)
                            # API 호출 제한 준수
                            await asyncio.sleep(0.01)  # 10ms 지연
                        except Exception as e:
                            logger.error(f"배치 내 임베딩 실패: {str(e)}")
                            # 오류 발생시 더미 결과 생성
                            batch_results.append(None)
                    return batch_results
            
            # 모든 배치 동시 처리
            batch_tasks = [process_batch(batch) for batch in batches]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # 결과 평탄화
            for batch_result in batch_results:
                if isinstance(batch_result, Exception):
                    logger.error(f"배치 처리 실패: {str(batch_result)}")
                    continue
                all_results.extend(batch_result)
            
            # None 값 제거 (실패한 임베딩)
            valid_results = [r for r in all_results if r is not None]
            
            # 통계 정보
            total_cost = sum(r.cost for r in valid_results)
            total_tokens = sum(r.token_count for r in valid_results)
            cached_count = sum(1 for r in valid_results if r.cached)
            
            logger.info(f"배치 임베딩 완료: {len(valid_results)}/{len(requests)} 성공, "
                       f"캐시 히트: {cached_count}, 총 비용: ${total_cost:.6f}, "
                       f"총 토큰: {total_tokens}")
            
            return valid_results
            
        except Exception as e:
            logger.error(f"배치 임베딩 실패: {str(e)}")
            raise
    
    def calculate_similarity(
        self, 
        embedding1: List[float], 
        embedding2: List[float]
    ) -> float:
        """
        두 임베딩 벡터 간의 코사인 유사도 계산
        
        Args:
            embedding1: 첫 번째 임베딩 벡터
            embedding2: 두 번째 임베딩 벡터
            
        Returns:
            float: 코사인 유사도 (-1 ~ 1)
        """
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # 코사인 유사도 계산
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"유사도 계산 실패: {str(e)}")
            return 0.0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 정보 반환
        
        Returns:
            Dict: 캐시 통계
        """
        try:
            # 캐시 키 패턴으로 검색
            pattern = f"{self.cache_prefix}*"
            cache_keys = self.redis_client.keys(pattern)
            
            stats = {
                "total_cached_embeddings": len(cache_keys),
                "cache_size_bytes": sum(
                    self.redis_client.memory_usage(key) or 0 
                    for key in cache_keys[:100]  # 샘플링
                ),
                "cache_ttl": self.cache_ttl,
                "redis_memory_info": self.redis_client.info("memory")
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"캐시 통계 조회 실패: {str(e)}")
            return {"error": str(e)}
    
    def clear_cache(self, pattern: str = None) -> int:
        """
        캐시 삭제
        
        Args:
            pattern: 삭제할 키 패턴 (None이면 모든 임베딩 캐시)
            
        Returns:
            int: 삭제된 키 개수
        """
        try:
            if pattern is None:
                pattern = f"{self.cache_prefix}*"
            
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted_count = self.redis_client.delete(*keys)
                logger.info(f"캐시 삭제 완료: {deleted_count}개 키")
                return deleted_count
            
            return 0
            
        except Exception as e:
            logger.error(f"캐시 삭제 실패: {str(e)}")
            return 0
    
    async def embed_documents(
        self, 
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        문서들의 임베딩 생성 및 메타데이터 첨부
        
        Args:
            documents: 문서 리스트 (각 문서는 'content', 'type', 'metadata' 포함)
            
        Returns:
            List[Dict]: 임베딩이 첨부된 문서 리스트
        """
        try:
            # 임베딩 요청 생성
            embed_requests = []
            for i, doc in enumerate(documents):
                request = EmbeddingRequest(
                    text=doc.get('content', ''),
                    document_type=doc.get('type', 'unknown'),
                    metadata=doc.get('metadata', {}),
                    priority=doc.get('priority', 1),
                    use_cache=doc.get('use_cache', True)
                )
                embed_requests.append(request)
            
            # 배치 임베딩 생성
            embedding_results = await self.embed_batch(embed_requests)
            
            # 문서에 임베딩 결과 첨부
            enriched_documents = []
            for doc, result in zip(documents, embedding_results):
                if result:
                    enriched_doc = doc.copy()
                    enriched_doc.update({
                        'embedding': result.embedding,
                        'embedding_model': result.model_version,
                        'embedding_cost': result.cost,
                        'embedding_tokens': result.token_count,
                        'embedding_hash': result.text_hash,
                        'embedding_cached': result.cached,
                        'embedding_created_at': result.created_at.isoformat()
                    })
                    enriched_documents.append(enriched_doc)
                else:
                    logger.warning(f"문서 임베딩 실패, 원본 문서 유지: {doc.get('metadata', {}).get('id', 'unknown')}")
                    enriched_documents.append(doc)
            
            return enriched_documents
            
        except Exception as e:
            logger.error(f"문서 임베딩 처리 실패: {str(e)}")
            raise