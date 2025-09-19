"""
캐시 관리자 - 프롬프트 캐시, 벡터 재사용, 응답 캐시 관리
"""

import logging
import asyncio
import hashlib
import json
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import redis.asyncio as redis
import numpy as np
from collections import defaultdict, OrderedDict

logger = logging.getLogger(__name__)

class CacheType(Enum):
    """캐시 타입"""
    PROMPT = "prompt"           # 프롬프트 캐시
    VECTOR = "vector"           # 벡터 캐시  
    RESPONSE = "response"       # 응답 캐시
    ANALYSIS = "analysis"       # 분석 결과 캐시
    EMBEDDING = "embedding"     # 임베딩 캐시

@dataclass
class CacheEntry:
    """캐시 엔트리"""
    key: str
    value: Any
    cache_type: CacheType
    created_at: datetime
    accessed_at: datetime
    access_count: int
    ttl_seconds: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    size_bytes: int = 0

@dataclass 
class CacheStats:
    """캐시 통계"""
    total_entries: int
    hit_rate: float
    miss_rate: float
    total_hits: int
    total_misses: int
    memory_usage_mb: float
    avg_access_time_ms: float
    cache_type_breakdown: Dict[str, int]

class LRUCache:
    """메모리 기반 LRU 캐시"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = OrderedDict()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """캐시에서 값 조회"""
        if key in self.cache:
            # LRU 순서 업데이트
            entry = self.cache.pop(key)
            self.cache[key] = entry
            
            # 통계 및 엔트리 정보 업데이트
            entry.accessed_at = datetime.now()
            entry.access_count += 1
            self.stats["hits"] += 1
            
            # TTL 확인
            if entry.ttl_seconds:
                elapsed = (datetime.now() - entry.created_at).total_seconds()
                if elapsed > entry.ttl_seconds:
                    del self.cache[key]
                    return None
            
            return entry
        
        self.stats["misses"] += 1
        return None
    
    def put(self, entry: CacheEntry):
        """캐시에 값 저장"""
        key = entry.key
        
        # 이미 존재하면 업데이트
        if key in self.cache:
            self.cache.pop(key)
        
        # 크기 제한 확인 및 LRU 제거
        while len(self.cache) >= self.max_size:
            oldest_key, _ = self.cache.popitem(last=False)
            self.stats["evictions"] += 1
            logger.debug(f"Evicted cache entry: {oldest_key}")
        
        self.cache[key] = entry
        entry.size_bytes = self._calculate_size(entry.value)
    
    def remove(self, key: str) -> bool:
        """캐시에서 항목 제거"""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def clear(self):
        """캐시 전체 삭제"""
        self.cache.clear()
        self.stats = {"hits": 0, "misses": 0, "evictions": 0}
    
    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0
        
        total_size = sum(entry.size_bytes for entry in self.cache.values())
        
        return {
            "entries": len(self.cache),
            "hit_rate": hit_rate,
            "total_hits": self.stats["hits"],
            "total_misses": self.stats["misses"],
            "evictions": self.stats["evictions"],
            "memory_usage_bytes": total_size,
            "memory_usage_mb": total_size / 1024 / 1024
        }
    
    def _calculate_size(self, value: Any) -> int:
        """객체 크기 계산"""
        try:
            return len(pickle.dumps(value))
        except:
            return len(str(value).encode('utf-8'))

class RedisCache:
    """Redis 기반 분산 캐시"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        self.stats = {
            "hits": 0,
            "misses": 0
        }
    
    async def connect(self):
        """Redis 연결"""
        try:
            self.redis_client = await redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    async def get(self, key: str) -> Optional[CacheEntry]:
        """캐시에서 값 조회"""
        if not self.redis_client:
            return None
        
        try:
            cached_data = await self.redis_client.get(f"stockpilot:cache:{key}")
            if cached_data:
                entry_dict = json.loads(cached_data)
                entry = self._dict_to_entry(entry_dict)
                
                # 통계 업데이트
                entry.accessed_at = datetime.now()
                entry.access_count += 1
                self.stats["hits"] += 1
                
                # 업데이트된 엔트리 다시 저장
                await self.put(entry)
                
                return entry
            
            self.stats["misses"] += 1
            return None
            
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            self.stats["misses"] += 1
            return None
    
    async def put(self, entry: CacheEntry):
        """캐시에 값 저장"""
        if not self.redis_client:
            return
        
        try:
            entry_dict = self._entry_to_dict(entry)
            cached_data = json.dumps(entry_dict, default=str)
            
            key = f"stockpilot:cache:{entry.key}"
            
            if entry.ttl_seconds:
                await self.redis_client.setex(key, entry.ttl_seconds, cached_data)
            else:
                await self.redis_client.set(key, cached_data)
                
        except Exception as e:
            logger.error(f"Redis put error: {e}")
    
    async def remove(self, key: str) -> bool:
        """캐시에서 항목 제거"""
        if not self.redis_client:
            return False
        
        try:
            result = await self.redis_client.delete(f"stockpilot:cache:{key}")
            return result > 0
        except Exception as e:
            logger.error(f"Redis remove error: {e}")
            return False
    
    async def clear_pattern(self, pattern: str):
        """패턴 매칭 키들 삭제"""
        if not self.redis_client:
            return
        
        try:
            keys = await self.redis_client.keys(f"stockpilot:cache:{pattern}")
            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache entries matching pattern: {pattern}")
        except Exception as e:
            logger.error(f"Redis clear pattern error: {e}")
    
    def _entry_to_dict(self, entry: CacheEntry) -> Dict[str, Any]:
        """CacheEntry를 dict로 변환"""
        return {
            "key": entry.key,
            "value": entry.value,
            "cache_type": entry.cache_type.value,
            "created_at": entry.created_at.isoformat(),
            "accessed_at": entry.accessed_at.isoformat(),
            "access_count": entry.access_count,
            "ttl_seconds": entry.ttl_seconds,
            "metadata": entry.metadata
        }
    
    def _dict_to_entry(self, entry_dict: Dict[str, Any]) -> CacheEntry:
        """dict를 CacheEntry로 변환"""
        return CacheEntry(
            key=entry_dict["key"],
            value=entry_dict["value"],
            cache_type=CacheType(entry_dict["cache_type"]),
            created_at=datetime.fromisoformat(entry_dict["created_at"]),
            accessed_at=datetime.fromisoformat(entry_dict["accessed_at"]),
            access_count=entry_dict["access_count"],
            ttl_seconds=entry_dict.get("ttl_seconds"),
            metadata=entry_dict.get("metadata", {})
        )

class CacheManager:
    """통합 캐시 관리자"""
    
    def __init__(self, redis_url: Optional[str] = None):
        # 메모리 캐시 (빠른 접근용)
        self.memory_caches = {
            CacheType.PROMPT: LRUCache(max_size=500),
            CacheType.VECTOR: LRUCache(max_size=1000),
            CacheType.RESPONSE: LRUCache(max_size=200),
            CacheType.ANALYSIS: LRUCache(max_size=300),
            CacheType.EMBEDDING: LRUCache(max_size=2000)
        }
        
        # Redis 캐시 (영구 저장용)
        self.redis_cache = RedisCache(redis_url) if redis_url else None
        
        # 캐시 정책 설정
        self.cache_policies = {
            CacheType.PROMPT: {"ttl": 3600, "memory_first": True},      # 1시간
            CacheType.VECTOR: {"ttl": 86400, "memory_first": True},     # 24시간
            CacheType.RESPONSE: {"ttl": 1800, "memory_first": True},    # 30분
            CacheType.ANALYSIS: {"ttl": 3600, "memory_first": False},   # 1시간
            CacheType.EMBEDDING: {"ttl": 86400, "memory_first": True}   # 24시간
        }
        
        self.global_stats = defaultdict(int)
    
    async def initialize(self):
        """캐시 매니저 초기화"""
        if self.redis_cache:
            await self.redis_cache.connect()
    
    def _generate_cache_key(self, content: str, cache_type: CacheType, **kwargs) -> str:
        """캐시 키 생성"""
        # 컨텐츠 해시
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        # 추가 파라미터 해시
        params_str = json.dumps(kwargs, sort_keys=True)
        params_hash = hashlib.sha256(params_str.encode()).hexdigest()[:8]
        
        return f"{cache_type.value}:{content_hash}:{params_hash}"
    
    async def get(self, content: str, cache_type: CacheType, **kwargs) -> Optional[Any]:
        """캐시에서 값 조회"""
        cache_key = self._generate_cache_key(content, cache_type, **kwargs)
        
        # 메모리 캐시 우선 확인
        memory_cache = self.memory_caches.get(cache_type)
        if memory_cache:
            entry = memory_cache.get(cache_key)
            if entry:
                self.global_stats[f"{cache_type.value}_memory_hits"] += 1
                logger.debug(f"Memory cache hit for {cache_type.value}: {cache_key}")
                return entry.value
        
        # Redis 캐시 확인
        if self.redis_cache:
            entry = await self.redis_cache.get(cache_key)
            if entry:
                self.global_stats[f"{cache_type.value}_redis_hits"] += 1
                
                # 메모리 캐시에도 저장 (hot data)
                if memory_cache and self.cache_policies[cache_type]["memory_first"]:
                    memory_cache.put(entry)
                
                logger.debug(f"Redis cache hit for {cache_type.value}: {cache_key}")
                return entry.value
        
        self.global_stats[f"{cache_type.value}_misses"] += 1
        return None
    
    async def put(self, content: str, value: Any, cache_type: CacheType, **kwargs):
        """캐시에 값 저장"""
        cache_key = self._generate_cache_key(content, cache_type, **kwargs)
        policy = self.cache_policies[cache_type]
        
        # 캐시 엔트리 생성
        entry = CacheEntry(
            key=cache_key,
            value=value,
            cache_type=cache_type,
            created_at=datetime.now(),
            accessed_at=datetime.now(),
            access_count=0,
            ttl_seconds=policy["ttl"],
            metadata=kwargs
        )
        
        # 메모리 캐시에 저장
        memory_cache = self.memory_caches.get(cache_type)
        if memory_cache and policy["memory_first"]:
            memory_cache.put(entry)
            logger.debug(f"Stored in memory cache: {cache_type.value} - {cache_key}")
        
        # Redis 캐시에 저장
        if self.redis_cache:
            await self.redis_cache.put(entry)
            logger.debug(f"Stored in Redis cache: {cache_type.value} - {cache_key}")
        
        self.global_stats[f"{cache_type.value}_writes"] += 1
    
    async def invalidate(self, content: str, cache_type: CacheType, **kwargs):
        """특정 캐시 무효화"""
        cache_key = self._generate_cache_key(content, cache_type, **kwargs)
        
        # 메모리 캐시에서 제거
        memory_cache = self.memory_caches.get(cache_type)
        if memory_cache:
            memory_cache.remove(cache_key)
        
        # Redis 캐시에서 제거
        if self.redis_cache:
            await self.redis_cache.remove(cache_key)
        
        logger.debug(f"Invalidated cache: {cache_type.value} - {cache_key}")
    
    async def invalidate_pattern(self, pattern: str, cache_type: Optional[CacheType] = None):
        """패턴 매칭 캐시 무효화"""
        # Redis 패턴 무효화
        if self.redis_cache:
            if cache_type:
                await self.redis_cache.clear_pattern(f"{cache_type.value}:*{pattern}*")
            else:
                await self.redis_cache.clear_pattern(f"*{pattern}*")
        
        # 메모리 캐시 패턴 무효화 (간단한 구현)
        if cache_type and cache_type in self.memory_caches:
            memory_cache = self.memory_caches[cache_type]
            keys_to_remove = [key for key in memory_cache.cache.keys() if pattern in key]
            for key in keys_to_remove:
                memory_cache.remove(key)
        
        logger.info(f"Invalidated cache pattern: {pattern} (type: {cache_type})")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """전체 캐시 통계 조회"""
        stats = {
            "global_stats": dict(self.global_stats),
            "memory_cache_stats": {},
            "redis_available": self.redis_cache is not None
        }
        
        # 메모리 캐시 통계
        for cache_type, cache in self.memory_caches.items():
            stats["memory_cache_stats"][cache_type.value] = cache.get_stats()
        
        # 전체 히트율 계산
        total_hits = sum(v for k, v in self.global_stats.items() if "hits" in k)
        total_misses = sum(v for k, v in self.global_stats.items() if "misses" in k)
        total_requests = total_hits + total_misses
        
        stats["overall"] = {
            "total_requests": total_requests,
            "total_hits": total_hits,
            "total_misses": total_misses,
            "hit_rate": total_hits / total_requests if total_requests > 0 else 0
        }
        
        return stats
    
    async def cleanup_expired(self):
        """만료된 캐시 정리"""
        current_time = datetime.now()
        
        # 메모리 캐시 정리
        for cache_type, memory_cache in self.memory_caches.items():
            policy = self.cache_policies[cache_type]
            expired_keys = []
            
            for key, entry in memory_cache.cache.items():
                if entry.ttl_seconds:
                    elapsed = (current_time - entry.created_at).total_seconds()
                    if elapsed > entry.ttl_seconds:
                        expired_keys.append(key)
            
            for key in expired_keys:
                memory_cache.remove(key)
                logger.debug(f"Cleaned up expired cache entry: {key}")
        
        logger.info("Cache cleanup completed")

# 특화된 캐시 헬퍼 함수들

class PromptCache:
    """프롬프트 캐시 특화 기능"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
    
    async def get_cached_prompt_response(
        self, 
        prompt: str, 
        model_name: str, 
        temperature: float = 0.7
    ) -> Optional[str]:
        """캐시된 프롬프트 응답 조회"""
        return await self.cache_manager.get(
            prompt, 
            CacheType.PROMPT,
            model_name=model_name,
            temperature=temperature
        )
    
    async def cache_prompt_response(
        self, 
        prompt: str, 
        response: str, 
        model_name: str, 
        temperature: float = 0.7
    ):
        """프롬프트 응답 캐시"""
        await self.cache_manager.put(
            prompt, 
            response, 
            CacheType.PROMPT,
            model_name=model_name,
            temperature=temperature
        )

class VectorCache:
    """벡터 캐시 특화 기능"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
    
    async def get_cached_embedding(self, text: str, model: str) -> Optional[np.ndarray]:
        """캐시된 임베딩 조회"""
        cached_result = await self.cache_manager.get(
            text, 
            CacheType.EMBEDDING,
            model=model
        )
        
        if cached_result and isinstance(cached_result, list):
            return np.array(cached_result)
        
        return cached_result
    
    async def cache_embedding(self, text: str, embedding: np.ndarray, model: str):
        """임베딩 캐시"""
        # numpy 배열을 리스트로 변환하여 저장
        embedding_list = embedding.tolist() if isinstance(embedding, np.ndarray) else embedding
        
        await self.cache_manager.put(
            text, 
            embedding_list, 
            CacheType.EMBEDDING,
            model=model
        )
    
    async def get_similar_cached_vectors(
        self, 
        query_embedding: np.ndarray, 
        threshold: float = 0.95
    ) -> List[Tuple[str, np.ndarray, float]]:
        """유사한 캐시된 벡터들 조회 (간단한 구현)"""
        # 실제 구현에서는 FAISS나 다른 벡터 데이터베이스 사용 권장
        similar_vectors = []
        
        # 메모리 캐시에서만 검색 (성능상 이유)
        memory_cache = self.cache_manager.memory_caches[CacheType.EMBEDDING]
        
        for key, entry in memory_cache.cache.items():
            cached_embedding = np.array(entry.value)
            similarity = np.dot(query_embedding, cached_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(cached_embedding)
            )
            
            if similarity >= threshold:
                similar_vectors.append((key, cached_embedding, similarity))
        
        # 유사도 순으로 정렬
        similar_vectors.sort(key=lambda x: x[2], reverse=True)
        return similar_vectors

# 글로벌 캐시 매니저
cache_manager = CacheManager()
prompt_cache = PromptCache(cache_manager)
vector_cache = VectorCache(cache_manager)

async def initialize_cache(redis_url: Optional[str] = None):
    """캐시 시스템 초기화"""
    global cache_manager, prompt_cache, vector_cache
    
    cache_manager = CacheManager(redis_url)
    await cache_manager.initialize()
    
    prompt_cache = PromptCache(cache_manager)
    vector_cache = VectorCache(cache_manager)
    
    logger.info("Cache system initialized")

async def get_cache_statistics() -> Dict[str, Any]:
    """캐시 통계 조회"""
    return await cache_manager.get_cache_stats()

async def cleanup_cache():
    """캐시 정리"""
    await cache_manager.cleanup_expired()