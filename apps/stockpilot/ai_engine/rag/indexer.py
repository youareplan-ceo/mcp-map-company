"""
벡터 인덱싱 및 저장 모듈
FAISS를 활용한 고성능 벡터 검색 인덱스 구축 및 관리
계층적 인덱싱, 메타데이터 필터링, 백업/복원 기능 포함
"""

import os
import pickle
import logging
import numpy as np
import faiss
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
import json
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class IndexConfig:
    """인덱스 설정"""
    dimension: int = 3072           # text-embedding-3-large 차원수
    index_type: str = "IVF"         # 인덱스 타입 (Flat, IVF, HNSW)
    nlist: int = 100                # IVF 클러스터 수
    nprobe: int = 10                # 검색시 탐색할 클러스터 수
    metric: str = "cosine"          # 거리 메트릭 (cosine, l2, ip)
    train_threshold: int = 10000    # 훈련을 위한 최소 벡터 수
    max_vectors: int = 1000000      # 최대 벡터 수
    backup_interval: int = 3600     # 백업 간격 (초)


@dataclass
class IndexedDocument:
    """인덱싱된 문서 정보"""
    doc_id: str
    content: str
    embedding: List[float]
    document_type: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    vector_id: int = -1  # FAISS 인덱스 내 벡터 ID


class VectorIndexer:
    """
    고성능 벡터 인덱싱 및 검색 시스템
    FAISS 기반 벡터 데이터베이스 구현
    """
    
    def __init__(
        self, 
        index_path: str,
        config: IndexConfig = None
    ):
        """
        초기화
        
        Args:
            index_path: 인덱스 저장 경로
            config: 인덱스 설정
        """
        self.index_path = Path(index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        self.config = config or IndexConfig()
        
        # FAISS 인덱스
        self.index = None
        self.is_trained = False
        
        # 메타데이터 저장소
        self.documents: Dict[int, IndexedDocument] = {}  # vector_id -> document
        self.doc_id_to_vector_id: Dict[str, int] = {}    # doc_id -> vector_id
        self.next_vector_id = 0
        
        # 문서 타입별 인덱스 (필터링용)
        self.type_indices: Dict[str, List[int]] = {}
        
        # 스레드 안전성
        self.lock = threading.RLock()
        
        # 백업 관리
        self.last_backup_time = datetime.utcnow()
        
        # 인덱스 로드
        self._initialize_index()
    
    def _initialize_index(self):
        """인덱스 초기화 또는 로드"""
        try:
            # 기존 인덱스 로드 시도
            if self._load_index():
                logger.info("기존 인덱스 로드 완료")
                return
            
            # 새 인덱스 생성
            self._create_new_index()
            logger.info("새 인덱스 생성 완료")
            
        except Exception as e:
            logger.error(f"인덱스 초기화 실패: {str(e)}")
            raise
    
    def _create_new_index(self):
        """새로운 FAISS 인덱스 생성"""
        try:
            dimension = self.config.dimension
            
            if self.config.index_type == "Flat":
                # 정확한 검색, 작은 데이터셋용
                if self.config.metric == "cosine":
                    self.index = faiss.IndexFlatIP(dimension)  # Inner Product
                else:
                    self.index = faiss.IndexFlatL2(dimension)  # L2 distance
                    
            elif self.config.index_type == "IVF":
                # 빠른 근사 검색, 큰 데이터셋용
                quantizer = faiss.IndexFlatL2(dimension)
                self.index = faiss.IndexIVFFlat(
                    quantizer, 
                    dimension, 
                    self.config.nlist,
                    faiss.METRIC_L2 if self.config.metric == "l2" else faiss.METRIC_INNER_PRODUCT
                )
                
            elif self.config.index_type == "HNSW":
                # 계층적 그래프 기반, 메모리 효율적
                self.index = faiss.IndexHNSWFlat(dimension, 32)
                
            else:
                raise ValueError(f"지원하지 않는 인덱스 타입: {self.config.index_type}")
            
            self.is_trained = self.config.index_type == "Flat"  # Flat 인덱스는 훈련 불필요
            
            logger.info(f"FAISS 인덱스 생성: {self.config.index_type}, 차원: {dimension}")
            
        except Exception as e:
            logger.error(f"인덱스 생성 실패: {str(e)}")
            raise
    
    def _normalize_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        """
        임베딩 벡터 정규화 (코사인 유사도용)
        
        Args:
            embeddings: 임베딩 행렬
            
        Returns:
            np.ndarray: 정규화된 임베딩
        """
        if self.config.metric == "cosine":
            # L2 정규화
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)  # 0으로 나누기 방지
            return embeddings / norms
        return embeddings
    
    def add_documents(self, documents: List[IndexedDocument]) -> List[int]:
        """
        문서들을 인덱스에 추가
        
        Args:
            documents: 추가할 문서 리스트
            
        Returns:
            List[int]: 할당된 벡터 ID 리스트
        """
        with self.lock:
            try:
                if not documents:
                    return []
                
                logger.info(f"문서 인덱싱 시작: {len(documents)}개")
                
                # 임베딩 추출 및 정규화
                embeddings = []
                vector_ids = []
                
                for doc in documents:
                    # 중복 문서 확인
                    if doc.doc_id in self.doc_id_to_vector_id:
                        logger.warning(f"중복 문서 무시: {doc.doc_id}")
                        continue
                    
                    # 벡터 ID 할당
                    vector_id = self.next_vector_id
                    self.next_vector_id += 1
                    
                    # 문서 저장
                    doc.vector_id = vector_id
                    self.documents[vector_id] = doc
                    self.doc_id_to_vector_id[doc.doc_id] = vector_id
                    
                    # 타입별 인덱스 업데이트
                    if doc.document_type not in self.type_indices:
                        self.type_indices[doc.document_type] = []
                    self.type_indices[doc.document_type].append(vector_id)
                    
                    embeddings.append(doc.embedding)
                    vector_ids.append(vector_id)
                
                if not embeddings:
                    logger.warning("추가할 새 문서가 없음")
                    return []
                
                # numpy 배열로 변환 및 정규화
                embedding_matrix = np.array(embeddings, dtype=np.float32)
                embedding_matrix = self._normalize_embeddings(embedding_matrix)
                
                # 인덱스 훈련 (필요시)
                if not self.is_trained and self._should_train():
                    self._train_index()
                
                # 벡터 추가
                if self.is_trained:
                    self.index.add(embedding_matrix)
                    logger.info(f"인덱스에 벡터 추가 완료: {len(embeddings)}개")
                else:
                    logger.warning("인덱스 미훈련으로 벡터 추가 대기")
                
                # 주기적 백업
                if self._should_backup():
                    self._backup_index()
                
                return vector_ids
                
            except Exception as e:
                logger.error(f"문서 인덱싱 실패: {str(e)}")
                raise
    
    def _should_train(self) -> bool:
        """인덱스 훈련 필요 여부 판단"""
        if self.config.index_type == "Flat":
            return False  # Flat 인덱스는 훈련 불필요
        
        return len(self.documents) >= self.config.train_threshold
    
    def _train_index(self):
        """인덱스 훈련"""
        try:
            if self.is_trained:
                return
            
            logger.info("인덱스 훈련 시작")
            
            # 모든 임베딩 수집
            all_embeddings = []
            for doc in self.documents.values():
                all_embeddings.append(doc.embedding)
            
            if len(all_embeddings) < self.config.train_threshold:
                logger.warning(f"훈련 데이터 부족: {len(all_embeddings)} < {self.config.train_threshold}")
                return
            
            # 훈련 데이터 준비
            training_data = np.array(all_embeddings, dtype=np.float32)
            training_data = self._normalize_embeddings(training_data)
            
            # 인덱스 훈련
            self.index.train(training_data)
            self.is_trained = True
            
            # 기존 벡터들을 훈련된 인덱스에 추가
            self.index.add(training_data)
            
            # IVF 인덱스 설정
            if self.config.index_type == "IVF":
                self.index.nprobe = self.config.nprobe
            
            logger.info(f"인덱스 훈련 완료: {len(all_embeddings)}개 벡터")
            
        except Exception as e:
            logger.error(f"인덱스 훈련 실패: {str(e)}")
            raise
    
    def search(
        self, 
        query_embedding: List[float],
        k: int = 10,
        document_types: Optional[List[str]] = None,
        metadata_filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0
    ) -> List[Tuple[IndexedDocument, float]]:
        """
        벡터 유사도 검색
        
        Args:
            query_embedding: 쿼리 임베딩 벡터
            k: 반환할 결과 수
            document_types: 필터링할 문서 타입
            metadata_filters: 메타데이터 필터
            min_score: 최소 유사도 점수
            
        Returns:
            List[Tuple[IndexedDocument, float]]: (문서, 유사도 점수) 리스트
        """
        with self.lock:
            try:
                if not self.is_trained or self.index.ntotal == 0:
                    logger.warning("인덱스가 비어있거나 훈련되지 않음")
                    return []
                
                # 쿼리 벡터 정규화
                query_vector = np.array([query_embedding], dtype=np.float32)
                query_vector = self._normalize_embeddings(query_vector)
                
                # 검색 수행
                search_k = min(k * 3, self.index.ntotal)  # 필터링을 위해 더 많이 검색
                scores, indices = self.index.search(query_vector, search_k)
                
                # 결과 처리
                results = []
                for score, idx in zip(scores[0], indices[0]):
                    if idx == -1:  # 무효한 인덱스
                        continue
                    
                    if idx not in self.documents:
                        logger.warning(f"인덱스 불일치: {idx}")
                        continue
                    
                    doc = self.documents[idx]
                    
                    # 문서 타입 필터링
                    if document_types and doc.document_type not in document_types:
                        continue
                    
                    # 메타데이터 필터링
                    if metadata_filters and not self._match_metadata_filters(doc.metadata, metadata_filters):
                        continue
                    
                    # 점수 변환 (FAISS는 거리를 반환, 유사도로 변환)
                    if self.config.metric == "cosine":
                        similarity_score = float(score)  # IP는 이미 코사인 유사도
                    else:
                        similarity_score = 1.0 / (1.0 + float(score))  # L2 거리를 유사도로 변환
                    
                    # 최소 점수 필터링
                    if similarity_score >= min_score:
                        results.append((doc, similarity_score))
                
                # 점수 순으로 정렬하고 k개만 반환
                results.sort(key=lambda x: x[1], reverse=True)
                return results[:k]
                
            except Exception as e:
                logger.error(f"벡터 검색 실패: {str(e)}")
                return []
    
    def _match_metadata_filters(
        self, 
        metadata: Dict[str, Any], 
        filters: Dict[str, Any]
    ) -> bool:
        """
        메타데이터 필터 매칭 확인
        
        Args:
            metadata: 문서 메타데이터
            filters: 적용할 필터
            
        Returns:
            bool: 필터 매칭 여부
        """
        try:
            for key, expected_value in filters.items():
                if key not in metadata:
                    return False
                
                actual_value = metadata[key]
                
                # 리스트 필터 (OR 조건)
                if isinstance(expected_value, list):
                    if actual_value not in expected_value:
                        return False
                
                # 범위 필터
                elif isinstance(expected_value, dict):
                    if 'min' in expected_value and actual_value < expected_value['min']:
                        return False
                    if 'max' in expected_value and actual_value > expected_value['max']:
                        return False
                
                # 정확 매칭
                else:
                    if actual_value != expected_value:
                        return False
            
            return True
            
        except Exception as e:
            logger.warning(f"메타데이터 필터링 오류: {str(e)}")
            return False
    
    def update_document(self, doc_id: str, updated_doc: IndexedDocument) -> bool:
        """
        문서 업데이트
        
        Args:
            doc_id: 문서 ID
            updated_doc: 업데이트된 문서
            
        Returns:
            bool: 성공 여부
        """
        with self.lock:
            try:
                if doc_id not in self.doc_id_to_vector_id:
                    logger.warning(f"존재하지 않는 문서: {doc_id}")
                    return False
                
                vector_id = self.doc_id_to_vector_id[doc_id]
                old_doc = self.documents[vector_id]
                
                # 메타데이터와 내용 업데이트
                updated_doc.vector_id = vector_id
                updated_doc.updated_at = datetime.utcnow()
                self.documents[vector_id] = updated_doc
                
                # 문서 타입이 변경된 경우 타입 인덱스 업데이트
                if old_doc.document_type != updated_doc.document_type:
                    # 기존 타입에서 제거
                    if old_doc.document_type in self.type_indices:
                        self.type_indices[old_doc.document_type].remove(vector_id)
                    
                    # 새 타입에 추가
                    if updated_doc.document_type not in self.type_indices:
                        self.type_indices[updated_doc.document_type] = []
                    self.type_indices[updated_doc.document_type].append(vector_id)
                
                logger.info(f"문서 업데이트 완료: {doc_id}")
                return True
                
            except Exception as e:
                logger.error(f"문서 업데이트 실패: {doc_id} - {str(e)}")
                return False
    
    def delete_document(self, doc_id: str) -> bool:
        """
        문서 삭제 (논리적 삭제)
        
        Args:
            doc_id: 삭제할 문서 ID
            
        Returns:
            bool: 성공 여부
        """
        with self.lock:
            try:
                if doc_id not in self.doc_id_to_vector_id:
                    logger.warning(f"존재하지 않는 문서: {doc_id}")
                    return False
                
                vector_id = self.doc_id_to_vector_id[doc_id]
                doc = self.documents[vector_id]
                
                # 문서와 매핑 제거
                del self.documents[vector_id]
                del self.doc_id_to_vector_id[doc_id]
                
                # 타입 인덱스에서 제거
                if doc.document_type in self.type_indices:
                    if vector_id in self.type_indices[doc.document_type]:
                        self.type_indices[doc.document_type].remove(vector_id)
                
                # FAISS 인덱스에서는 물리적 삭제 불가 (재구축 필요)
                logger.info(f"문서 논리적 삭제 완료: {doc_id}")
                return True
                
            except Exception as e:
                logger.error(f"문서 삭제 실패: {doc_id} - {str(e)}")
                return False
    
    def get_document_by_id(self, doc_id: str) -> Optional[IndexedDocument]:
        """문서 ID로 문서 조회"""
        with self.lock:
            vector_id = self.doc_id_to_vector_id.get(doc_id)
            if vector_id is not None:
                return self.documents.get(vector_id)
            return None
    
    def get_documents_by_type(self, document_type: str) -> List[IndexedDocument]:
        """문서 타입별 문서 조회"""
        with self.lock:
            vector_ids = self.type_indices.get(document_type, [])
            return [self.documents[vid] for vid in vector_ids if vid in self.documents]
    
    def get_stats(self) -> Dict[str, Any]:
        """인덱스 통계 정보"""
        with self.lock:
            try:
                stats = {
                    "total_documents": len(self.documents),
                    "total_vectors": self.index.ntotal if self.index else 0,
                    "is_trained": self.is_trained,
                    "index_type": self.config.index_type,
                    "dimension": self.config.dimension,
                    "document_types": {
                        doc_type: len(vector_ids) 
                        for doc_type, vector_ids in self.type_indices.items()
                    },
                    "config": asdict(self.config),
                    "memory_usage_mb": self._estimate_memory_usage()
                }
                
                return stats
                
            except Exception as e:
                logger.error(f"통계 조회 실패: {str(e)}")
                return {"error": str(e)}
    
    def _estimate_memory_usage(self) -> float:
        """메모리 사용량 추정 (MB)"""
        try:
            # FAISS 인덱스 메모리
            index_memory = 0
            if self.index:
                index_memory = self.index.ntotal * self.config.dimension * 4  # float32
            
            # 메타데이터 메모리 (대략적 추정)
            metadata_memory = len(self.documents) * 1024  # 문서당 평균 1KB
            
            total_memory = (index_memory + metadata_memory) / (1024 * 1024)  # MB 변환
            return round(total_memory, 2)
            
        except Exception:
            return 0.0
    
    def _should_backup(self) -> bool:
        """백업 필요 여부 판단"""
        return (datetime.utcnow() - self.last_backup_time).total_seconds() > self.config.backup_interval
    
    def _backup_index(self):
        """인덱스 백업"""
        try:
            backup_dir = self.index_path / "backups"
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"index_backup_{timestamp}"
            
            self._save_index(str(backup_path))
            
            # 오래된 백업 정리 (7일 이상)
            cutoff_time = datetime.utcnow() - timedelta(days=7)
            for backup_file in backup_dir.glob("index_backup_*"):
                if backup_file.stat().st_mtime < cutoff_time.timestamp():
                    backup_file.unlink()
            
            self.last_backup_time = datetime.utcnow()
            logger.info(f"인덱스 백업 완료: {backup_path}")
            
        except Exception as e:
            logger.error(f"인덱스 백업 실패: {str(e)}")
    
    def save_index(self):
        """인덱스 저장"""
        self._save_index(str(self.index_path / "current"))
    
    def _save_index(self, base_path: str):
        """인덱스 저장 (내부용)"""
        with self.lock:
            try:
                os.makedirs(base_path, exist_ok=True)
                
                # FAISS 인덱스 저장
                if self.index:
                    faiss.write_index(self.index, f"{base_path}/faiss.index")
                
                # 메타데이터 저장
                metadata = {
                    "documents": {k: asdict(v) for k, v in self.documents.items()},
                    "doc_id_to_vector_id": self.doc_id_to_vector_id,
                    "type_indices": self.type_indices,
                    "next_vector_id": self.next_vector_id,
                    "is_trained": self.is_trained,
                    "config": asdict(self.config),
                    "saved_at": datetime.utcnow().isoformat()
                }
                
                with open(f"{base_path}/metadata.pkl", "wb") as f:
                    pickle.dump(metadata, f)
                
                logger.info(f"인덱스 저장 완료: {base_path}")
                
            except Exception as e:
                logger.error(f"인덱스 저장 실패: {str(e)}")
                raise
    
    def _load_index(self) -> bool:
        """저장된 인덱스 로드"""
        try:
            current_path = self.index_path / "current"
            
            if not (current_path / "faiss.index").exists():
                return False
            
            # FAISS 인덱스 로드
            self.index = faiss.read_index(str(current_path / "faiss.index"))
            
            # 메타데이터 로드
            with open(current_path / "metadata.pkl", "rb") as f:
                metadata = pickle.load(f)
            
            # 문서 객체 복원
            self.documents = {}
            for k, v in metadata["documents"].items():
                doc = IndexedDocument(**v)
                # datetime 객체 복원
                doc.created_at = datetime.fromisoformat(v["created_at"]) if isinstance(v["created_at"], str) else v["created_at"]
                doc.updated_at = datetime.fromisoformat(v["updated_at"]) if isinstance(v["updated_at"], str) else v["updated_at"]
                self.documents[int(k)] = doc
            
            self.doc_id_to_vector_id = metadata["doc_id_to_vector_id"]
            self.type_indices = metadata["type_indices"]
            self.next_vector_id = metadata["next_vector_id"]
            self.is_trained = metadata["is_trained"]
            
            # IVF 인덱스 설정 복원
            if self.config.index_type == "IVF" and hasattr(self.index, 'nprobe'):
                self.index.nprobe = self.config.nprobe
            
            logger.info(f"인덱스 로드 완료: {len(self.documents)}개 문서")
            return True
            
        except Exception as e:
            logger.warning(f"인덱스 로드 실패: {str(e)}")
            return False
    
    def rebuild_index(self):
        """인덱스 재구축 (삭제된 문서 물리적 제거)"""
        with self.lock:
            try:
                logger.info("인덱스 재구축 시작")
                
                if not self.documents:
                    logger.warning("재구축할 문서가 없음")
                    return
                
                # 새 인덱스 생성
                old_index = self.index
                self._create_new_index()
                
                # 모든 활성 문서의 임베딩 수집
                embeddings = []
                for doc in self.documents.values():
                    embeddings.append(doc.embedding)
                
                # 임베딩 정규화 및 추가
                embedding_matrix = np.array(embeddings, dtype=np.float32)
                embedding_matrix = self._normalize_embeddings(embedding_matrix)
                
                # 인덱스 훈련 및 벡터 추가
                if self.config.index_type != "Flat":
                    self.index.train(embedding_matrix)
                    self.is_trained = True
                
                self.index.add(embedding_matrix)
                
                logger.info(f"인덱스 재구축 완료: {len(embeddings)}개 벡터")
                
            except Exception as e:
                logger.error(f"인덱스 재구축 실패: {str(e)}")
                # 실패시 기존 인덱스 복원
                if 'old_index' in locals():
                    self.index = old_index
                raise