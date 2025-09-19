"""
RAG 검색 및 검색 결과 최적화 모듈
MMR(Maximal Marginal Relevance) 알고리즘을 활용한 다양성 있는 검색 결과 제공
하이브리드 검색, 재랭킹, 컨텍스트 필터링 기능 포함
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any, Set
from dataclasses import dataclass
from collections import defaultdict
import math

from .indexer import VectorIndexer, IndexedDocument
from .embedder import TextEmbedder

logger = logging.getLogger(__name__)


@dataclass
class SearchQuery:
    """검색 쿼리 정보"""
    text: str
    query_type: str = "general"           # general, technical, news, strategy
    max_results: int = 10
    min_relevance: float = 0.5
    time_weight: float = 0.2              # 시간 가중치 (최신성)
    diversity_weight: float = 0.3         # 다양성 가중치 (MMR)
    document_types: Optional[List[str]] = None
    metadata_filters: Optional[Dict[str, Any]] = None
    boost_recent: bool = True             # 최신 문서 부스트 여부
    deduplicate: bool = True              # 중복 제거 여부


@dataclass
class SearchResult:
    """검색 결과"""
    document: IndexedDocument
    relevance_score: float
    time_score: float
    final_score: float
    rank: int
    retrieval_reason: str                 # 검색된 이유
    matched_keywords: List[str]           # 매칭된 키워드


class DocumentRetriever:
    """
    고급 문서 검색 및 랭킹 시스템
    MMR, 시간적 가중치, 하이브리드 검색 지원
    """
    
    def __init__(
        self,
        indexer: VectorIndexer,
        embedder: TextEmbedder
    ):
        """
        초기화
        
        Args:
            indexer: 벡터 인덱서
            embedder: 텍스트 임베더
        """
        self.indexer = indexer
        self.embedder = embedder
        
        # 키워드 검색을 위한 용어 사전 (TF-IDF 대체)
        self.term_frequencies: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.document_frequencies: Dict[str, int] = defaultdict(int)
        
        # 쿼리 타입별 가중치
        self.query_type_weights = {
            "general": {"semantic": 0.8, "keyword": 0.2, "time": 0.2},
            "technical": {"semantic": 0.9, "keyword": 0.1, "time": 0.1},
            "news": {"semantic": 0.6, "keyword": 0.3, "time": 0.5},
            "strategy": {"semantic": 0.7, "keyword": 0.2, "time": 0.3}
        }
        
        self._build_keyword_index()
    
    def _build_keyword_index(self):
        """키워드 검색을 위한 역색인 구축"""
        try:
            logger.info("키워드 인덱스 구축 시작")
            
            # 모든 문서에 대해 키워드 추출
            all_documents = list(self.indexer.documents.values())
            total_docs = len(all_documents)
            
            if total_docs == 0:
                return
            
            # 용어 빈도 계산
            for doc in all_documents:
                words = self._extract_keywords(doc.content)
                doc_word_count = len(words)
                
                # TF 계산
                word_counts = defaultdict(int)
                for word in words:
                    word_counts[word] += 1
                
                for word, count in word_counts.items():
                    tf = count / doc_word_count if doc_word_count > 0 else 0
                    self.term_frequencies[doc.doc_id][word] = tf
                    
                    # DF 계산
                    if word not in self.document_frequencies:
                        self.document_frequencies[word] = 0
                    
                # 문서별 고유 단어에 대해서만 DF 증가
                unique_words = set(word_counts.keys())
                for word in unique_words:
                    self.document_frequencies[word] += 1
            
            logger.info(f"키워드 인덱스 구축 완료: {len(self.document_frequencies)}개 용어")
            
        except Exception as e:
            logger.error(f"키워드 인덱스 구축 실패: {str(e)}")
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        텍스트에서 키워드 추출
        
        Args:
            text: 입력 텍스트
            
        Returns:
            List[str]: 추출된 키워드 리스트
        """
        import re
        
        # 한글, 영어, 숫자만 추출하고 소문자 변환
        words = re.findall(r'[가-힣]+|[a-zA-Z]+|\d+', text.lower())
        
        # 불용어 제거
        stop_words = {
            '이', '가', '을', '를', '은', '는', '과', '와', '에', '의', '에서',
            '으로', '로', '이다', '있다', '없다', '하다', '되다', '같다',
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 
            'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has'
        }
        
        # 최소 길이 및 불용어 필터링
        filtered_words = [
            word for word in words 
            if len(word) >= 2 and word not in stop_words
        ]
        
        return filtered_words
    
    def _calculate_tf_idf_score(self, query_words: List[str], doc_id: str) -> float:
        """
        TF-IDF 점수 계산
        
        Args:
            query_words: 쿼리 키워드
            doc_id: 문서 ID
            
        Returns:
            float: TF-IDF 점수
        """
        try:
            if doc_id not in self.term_frequencies:
                return 0.0
            
            doc_tf = self.term_frequencies[doc_id]
            total_docs = len(self.term_frequencies)
            
            score = 0.0
            matched_terms = 0
            
            for word in query_words:
                if word in doc_tf:
                    tf = doc_tf[word]
                    df = self.document_frequencies.get(word, 1)
                    idf = math.log(total_docs / df) if df > 0 else 0
                    
                    score += tf * idf
                    matched_terms += 1
            
            # 매칭된 용어 비율로 정규화
            if len(query_words) > 0:
                score *= (matched_terms / len(query_words))
            
            return score
            
        except Exception as e:
            logger.warning(f"TF-IDF 계산 실패: {str(e)}")
            return 0.0
    
    def _calculate_time_score(self, doc_created_at: datetime, decay_days: int = 30) -> float:
        """
        시간 기반 점수 계산 (최신 문서일수록 높은 점수)
        
        Args:
            doc_created_at: 문서 생성 시간
            decay_days: 점수 감쇠 기간
            
        Returns:
            float: 시간 점수 (0.0 ~ 1.0)
        """
        try:
            now = datetime.utcnow()
            days_old = (now - doc_created_at).total_seconds() / 86400  # 일 단위
            
            # 지수 감쇠 함수
            time_score = math.exp(-days_old / decay_days)
            return min(max(time_score, 0.0), 1.0)
            
        except Exception as e:
            logger.warning(f"시간 점수 계산 실패: {str(e)}")
            return 0.5  # 기본값
    
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        하이브리드 검색 수행 (벡터 검색 + 키워드 검색)
        
        Args:
            query: 검색 쿼리
            
        Returns:
            List[SearchResult]: 검색 결과 리스트
        """
        try:
            logger.info(f"검색 시작: '{query.text}' (타입: {query.query_type})")
            
            # 1. 쿼리 임베딩 생성
            from ..rag.embedder import EmbeddingRequest
            embed_request = EmbeddingRequest(
                text=query.text,
                document_type="query",
                metadata={"query_type": query.query_type}
            )
            
            embed_result = await self.embedder.embed_text(embed_request)
            query_embedding = embed_result.embedding
            
            # 2. 벡터 유사도 검색
            vector_results = self.indexer.search(
                query_embedding=query_embedding,
                k=query.max_results * 3,  # 더 많이 검색해서 다양성 확보
                document_types=query.document_types,
                metadata_filters=query.metadata_filters,
                min_score=query.min_relevance * 0.7  # 벡터 검색은 더 관대하게
            )
            
            # 3. 키워드 검색
            query_keywords = self._extract_keywords(query.text)
            keyword_scores = {}
            
            for doc_id in self.term_frequencies.keys():
                tf_idf_score = self._calculate_tf_idf_score(query_keywords, doc_id)
                if tf_idf_score > 0:
                    keyword_scores[doc_id] = tf_idf_score
            
            # 4. 하이브리드 점수 계산
            weights = self.query_type_weights.get(query.query_type, self.query_type_weights["general"])
            combined_results = []
            
            # 벡터 검색 결과 처리
            for doc, semantic_score in vector_results:
                keyword_score = keyword_scores.get(doc.doc_id, 0.0)
                time_score = self._calculate_time_score(doc.created_at)
                
                # 가중 평균 계산
                final_score = (
                    semantic_score * weights["semantic"] +
                    keyword_score * weights["keyword"] +
                    time_score * weights["time"] * query.time_weight
                )
                
                # 매칭된 키워드 찾기
                matched_keywords = [
                    word for word in query_keywords 
                    if word in self.term_frequencies.get(doc.doc_id, {})
                ]
                
                result = SearchResult(
                    document=doc,
                    relevance_score=semantic_score,
                    time_score=time_score,
                    final_score=final_score,
                    rank=0,  # 나중에 설정
                    retrieval_reason="hybrid_search",
                    matched_keywords=matched_keywords
                )
                
                combined_results.append(result)
            
            # 키워드 전용 검색 결과 추가 (벡터 검색에서 누락된 경우)
            vector_doc_ids = {result.document.doc_id for result in combined_results}
            
            for doc_id, keyword_score in keyword_scores.items():
                if doc_id not in vector_doc_ids and keyword_score > query.min_relevance * 0.5:
                    doc = self.indexer.get_document_by_id(doc_id)
                    if doc:
                        time_score = self._calculate_time_score(doc.created_at)
                        final_score = (
                            keyword_score * weights["keyword"] +
                            time_score * weights["time"] * query.time_weight
                        )
                        
                        matched_keywords = [
                            word for word in query_keywords 
                            if word in self.term_frequencies.get(doc_id, {})
                        ]
                        
                        result = SearchResult(
                            document=doc,
                            relevance_score=0.0,  # 벡터 유사도 없음
                            time_score=time_score,
                            final_score=final_score,
                            rank=0,
                            retrieval_reason="keyword_only",
                            matched_keywords=matched_keywords
                        )
                        
                        combined_results.append(result)
            
            # 5. 최종 점수 필터링 및 정렬
            filtered_results = [
                result for result in combined_results 
                if result.final_score >= query.min_relevance
            ]
            
            filtered_results.sort(key=lambda x: x.final_score, reverse=True)
            
            # 6. MMR로 다양성 확보
            if query.diversity_weight > 0 and len(filtered_results) > 1:
                diverse_results = self._apply_mmr(
                    filtered_results, 
                    query_embedding, 
                    query.diversity_weight,
                    query.max_results
                )
            else:
                diverse_results = filtered_results[:query.max_results]
            
            # 7. 중복 제거 (선택적)
            if query.deduplicate:
                diverse_results = self._deduplicate_results(diverse_results)
            
            # 8. 랭크 설정
            for i, result in enumerate(diverse_results):
                result.rank = i + 1
            
            logger.info(f"검색 완료: {len(diverse_results)}개 결과")
            return diverse_results
            
        except Exception as e:
            logger.error(f"검색 실패: {str(e)}")
            return []
    
    def _apply_mmr(
        self, 
        results: List[SearchResult], 
        query_embedding: List[float],
        diversity_weight: float,
        max_results: int
    ) -> List[SearchResult]:
        """
        MMR(Maximal Marginal Relevance) 알고리즘 적용
        
        Args:
            results: 검색 결과 리스트
            query_embedding: 쿼리 임베딩
            diversity_weight: 다양성 가중치
            max_results: 최대 결과 수
            
        Returns:
            List[SearchResult]: MMR이 적용된 결과
        """
        try:
            if len(results) <= 1:
                return results
            
            logger.debug(f"MMR 적용: 다양성 가중치 {diversity_weight}")
            
            selected_results = []
            remaining_results = results.copy()
            
            # 첫 번째 결과는 가장 관련성 높은 것 선택
            selected_results.append(remaining_results.pop(0))
            
            while len(selected_results) < max_results and remaining_results:
                best_score = -1
                best_idx = -1
                
                for i, candidate in enumerate(remaining_results):
                    # 쿼리와의 관련성 점수
                    relevance_score = candidate.final_score
                    
                    # 이미 선택된 결과들과의 최대 유사도
                    max_similarity = 0.0
                    for selected in selected_results:
                        similarity = self.embedder.calculate_similarity(
                            candidate.document.embedding,
                            selected.document.embedding
                        )
                        max_similarity = max(max_similarity, similarity)
                    
                    # MMR 점수 계산
                    mmr_score = (
                        (1 - diversity_weight) * relevance_score - 
                        diversity_weight * max_similarity
                    )
                    
                    if mmr_score > best_score:
                        best_score = mmr_score
                        best_idx = i
                
                if best_idx >= 0:
                    selected_results.append(remaining_results.pop(best_idx))
                else:
                    break  # 더 이상 선택할 수 없음
            
            return selected_results
            
        except Exception as e:
            logger.error(f"MMR 적용 실패: {str(e)}")
            return results[:max_results]  # 실패시 상위 결과만 반환
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        중복 결과 제거 (유사한 내용의 문서)
        
        Args:
            results: 검색 결과 리스트
            
        Returns:
            List[SearchResult]: 중복 제거된 결과
        """
        try:
            if len(results) <= 1:
                return results
            
            deduplicated = []
            similarity_threshold = 0.95  # 높은 유사도면 중복으로 간주
            
            for candidate in results:
                is_duplicate = False
                
                for existing in deduplicated:
                    similarity = self.embedder.calculate_similarity(
                        candidate.document.embedding,
                        existing.document.embedding
                    )
                    
                    if similarity > similarity_threshold:
                        is_duplicate = True
                        # 더 높은 점수의 결과를 유지
                        if candidate.final_score > existing.final_score:
                            deduplicated.remove(existing)
                            deduplicated.append(candidate)
                        break
                
                if not is_duplicate:
                    deduplicated.append(candidate)
            
            return deduplicated
            
        except Exception as e:
            logger.error(f"중복 제거 실패: {str(e)}")
            return results
    
    def get_related_documents(
        self, 
        doc_id: str, 
        max_results: int = 5,
        similarity_threshold: float = 0.6
    ) -> List[Tuple[IndexedDocument, float]]:
        """
        특정 문서와 관련된 문서들 검색
        
        Args:
            doc_id: 기준 문서 ID
            max_results: 최대 결과 수
            similarity_threshold: 최소 유사도 임계값
            
        Returns:
            List[Tuple[IndexedDocument, float]]: 관련 문서와 유사도 점수
        """
        try:
            base_doc = self.indexer.get_document_by_id(doc_id)
            if not base_doc:
                logger.warning(f"문서를 찾을 수 없음: {doc_id}")
                return []
            
            # 기준 문서의 임베딩으로 유사 문서 검색
            similar_docs = self.indexer.search(
                query_embedding=base_doc.embedding,
                k=max_results + 1,  # 자기 자신 제외
                min_score=similarity_threshold
            )
            
            # 자기 자신 제외
            related_docs = [
                (doc, score) for doc, score in similar_docs 
                if doc.doc_id != doc_id
            ]
            
            return related_docs[:max_results]
            
        except Exception as e:
            logger.error(f"관련 문서 검색 실패: {str(e)}")
            return []
    
    def search_by_metadata(
        self, 
        metadata_query: Dict[str, Any],
        max_results: int = 10
    ) -> List[IndexedDocument]:
        """
        메타데이터 기반 검색
        
        Args:
            metadata_query: 메타데이터 쿼리
            max_results: 최대 결과 수
            
        Returns:
            List[IndexedDocument]: 매칭된 문서들
        """
        try:
            matching_docs = []
            
            for doc in self.indexer.documents.values():
                if self.indexer._match_metadata_filters(doc.metadata, metadata_query):
                    matching_docs.append(doc)
            
            # 생성 시간 순으로 정렬 (최신 우선)
            matching_docs.sort(key=lambda x: x.created_at, reverse=True)
            
            return matching_docs[:max_results]
            
        except Exception as e:
            logger.error(f"메타데이터 검색 실패: {str(e)}")
            return []
    
    def get_trending_topics(
        self, 
        time_window_hours: int = 24,
        min_docs_per_topic: int = 3
    ) -> List[Dict[str, Any]]:
        """
        트렌딩 토픽 분석
        
        Args:
            time_window_hours: 분석 시간 윈도우
            min_docs_per_topic: 토픽당 최소 문서 수
            
        Returns:
            List[Dict]: 트렌딩 토픽 정보
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
            
            # 최근 문서들의 키워드 빈도 분석
            recent_keyword_counts = defaultdict(int)
            recent_doc_count = 0
            
            for doc in self.indexer.documents.values():
                if doc.created_at >= cutoff_time:
                    recent_doc_count += 1
                    doc_keywords = self._extract_keywords(doc.content)
                    
                    for keyword in doc_keywords:
                        recent_keyword_counts[keyword] += 1
            
            if recent_doc_count == 0:
                return []
            
            # 트렌딩 점수 계산 (빈도 + 최근성)
            trending_topics = []
            
            for keyword, recent_count in recent_keyword_counts.items():
                if recent_count >= min_docs_per_topic:
                    # 전체 대비 최근 빈도 증가율
                    total_count = self.document_frequencies.get(keyword, 0)
                    trend_score = recent_count / max(total_count - recent_count, 1)
                    
                    trending_topics.append({
                        "keyword": keyword,
                        "recent_count": recent_count,
                        "total_count": total_count,
                        "trend_score": trend_score,
                        "growth_rate": (recent_count / total_count) if total_count > 0 else 0
                    })
            
            # 트렌드 점수로 정렬
            trending_topics.sort(key=lambda x: x["trend_score"], reverse=True)
            
            return trending_topics[:20]  # 상위 20개 토픽
            
        except Exception as e:
            logger.error(f"트렌딩 토픽 분석 실패: {str(e)}")
            return []
    
    def update_keyword_index(self, new_documents: List[IndexedDocument]):
        """
        새 문서들로 키워드 인덱스 업데이트
        
        Args:
            new_documents: 새로 추가된 문서들
        """
        try:
            logger.info(f"키워드 인덱스 업데이트: {len(new_documents)}개 문서")
            
            for doc in new_documents:
                words = self._extract_keywords(doc.content)
                doc_word_count = len(words)
                
                if doc_word_count == 0:
                    continue
                
                # TF 계산
                word_counts = defaultdict(int)
                for word in words:
                    word_counts[word] += 1
                
                for word, count in word_counts.items():
                    tf = count / doc_word_count
                    self.term_frequencies[doc.doc_id][word] = tf
                
                # DF 업데이트 (새로운 단어들에 대해)
                unique_words = set(word_counts.keys())
                for word in unique_words:
                    self.document_frequencies[word] += 1
            
            logger.info("키워드 인덱스 업데이트 완료")
            
        except Exception as e:
            logger.error(f"키워드 인덱스 업데이트 실패: {str(e)}")