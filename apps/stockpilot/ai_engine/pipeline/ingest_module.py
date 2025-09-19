"""
데이터 수집 및 전처리 모듈
다양한 소스에서 데이터를 수집하고 AI 분석을 위한 형태로 전처리
실시간 스트리밍, 배치 처리, 데이터 검증 및 정규화 기능 포함
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union, AsyncGenerator
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import json
from pathlib import Path

from ..rag.indexer import IndexedDocument
from ..rag.embedder import TextEmbedder, EmbeddingRequest

logger = logging.getLogger(__name__)


@dataclass
class DataSource:
    """데이터 소스 정보"""
    source_id: str
    source_type: str          # 'api', 'database', 'file', 'stream'
    name: str
    description: str
    endpoint: Optional[str] = None
    credentials: Optional[Dict[str, str]] = None
    refresh_interval: int = 300  # 초 단위
    is_active: bool = True
    last_updated: Optional[datetime] = None


@dataclass
class RawDataPoint:
    """원시 데이터 포인트"""
    source_id: str
    data_type: str           # 'news', 'price', 'financial_statement', 'social_media'
    content: Dict[str, Any]
    timestamp: datetime
    metadata: Dict[str, Any]
    quality_score: float = 1.0


@dataclass
class ProcessedDocument:
    """처리된 문서"""
    doc_id: str
    title: str
    content: str
    document_type: str
    source_id: str
    processed_at: datetime
    metadata: Dict[str, Any]
    quality_metrics: Dict[str, float]
    tags: List[str] = None


class DataSourceConnector(ABC):
    """데이터 소스 연결 인터페이스"""
    
    @abstractmethod
    async def connect(self) -> bool:
        """연결 설정"""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """연결 해제"""
        pass
    
    @abstractmethod
    async def fetch_data(self, params: Dict[str, Any]) -> List[RawDataPoint]:
        """데이터 가져오기"""
        pass
    
    @abstractmethod
    async def stream_data(self) -> AsyncGenerator[RawDataPoint, None]:
        """실시간 데이터 스트림"""
        pass


class DatabaseConnector(DataSourceConnector):
    """데이터베이스 연결자"""
    
    def __init__(self, source: DataSource):
        self.source = source
        self.connection = None
    
    async def connect(self) -> bool:
        try:
            # 실제 구현시 데이터베이스 연결 코드
            logger.info(f"데이터베이스 연결: {self.source.name}")
            return True
        except Exception as e:
            logger.error(f"데이터베이스 연결 실패: {str(e)}")
            return False
    
    async def disconnect(self):
        if self.connection:
            # 연결 해제 로직
            logger.info(f"데이터베이스 연결 해제: {self.source.name}")
    
    async def fetch_data(self, params: Dict[str, Any]) -> List[RawDataPoint]:
        # 실제 구현시 SQL 쿼리 실행
        return []
    
    async def stream_data(self) -> AsyncGenerator[RawDataPoint, None]:
        # 실제 구현시 실시간 데이터 스트림
        while True:
            yield RawDataPoint(
                source_id=self.source.source_id,
                data_type="test",
                content={},
                timestamp=datetime.utcnow(),
                metadata={}
            )
            await asyncio.sleep(1)


class APIConnector(DataSourceConnector):
    """API 연결자"""
    
    def __init__(self, source: DataSource):
        self.source = source
        self.session = None
    
    async def connect(self) -> bool:
        try:
            import aiohttp
            self.session = aiohttp.ClientSession()
            logger.info(f"API 연결: {self.source.name}")
            return True
        except Exception as e:
            logger.error(f"API 연결 실패: {str(e)}")
            return False
    
    async def disconnect(self):
        if self.session:
            await self.session.close()
            logger.info(f"API 연결 해제: {self.source.name}")
    
    async def fetch_data(self, params: Dict[str, Any]) -> List[RawDataPoint]:
        if not self.session:
            return []
        
        try:
            async with self.session.get(self.source.endpoint, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    # 응답 데이터를 RawDataPoint로 변환
                    return self._parse_api_response(data)
                else:
                    logger.warning(f"API 요청 실패: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"API 데이터 가져오기 실패: {str(e)}")
            return []
    
    def _parse_api_response(self, data: Dict[str, Any]) -> List[RawDataPoint]:
        """API 응답을 RawDataPoint로 변환"""
        # 실제 구현시 API별 파싱 로직
        return []
    
    async def stream_data(self) -> AsyncGenerator[RawDataPoint, None]:
        # WebSocket 또는 Server-Sent Events 구현
        while True:
            await asyncio.sleep(1)
            yield RawDataPoint(
                source_id=self.source.source_id,
                data_type="api_stream",
                content={},
                timestamp=datetime.utcnow(),
                metadata={}
            )


class DataProcessor:
    """데이터 전처리기"""
    
    def __init__(self):
        self.text_cleaners = {
            "news": self._clean_news_text,
            "social_media": self._clean_social_media_text,
            "financial_statement": self._clean_financial_text,
            "price": self._clean_price_data
        }
        
        # 데이터 품질 체크 규칙
        self.quality_rules = {
            "min_content_length": 50,
            "max_content_length": 10000,
            "required_fields": ["title", "content", "timestamp"],
            "forbidden_words": ["스팸", "광고", "홍보"]
        }
    
    def _clean_news_text(self, content: str) -> str:
        """뉴스 텍스트 정리"""
        import re
        
        # HTML 태그 제거
        content = re.sub(r'<[^>]+>', '', content)
        
        # 특수 문자 정리
        content = re.sub(r'[^\w\s가-힣.,!?%\-()]', ' ', content)
        
        # 연속된 공백 정리
        content = re.sub(r'\s+', ' ', content)
        
        # 광고/홍보성 문구 제거
        ad_patterns = [
            r'※.*?※',
            r'\[광고\].*?\[/광고\]',
            r'▶.*?◀',
            r'기자\s*\w+@\w+\.\w+'
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content)
        
        return content.strip()
    
    def _clean_social_media_text(self, content: str) -> str:
        """소셜미디어 텍스트 정리"""
        import re
        
        # 해시태그와 멘션 처리
        content = re.sub(r'#(\w+)', r'\1', content)  # 해시태그 유지하되 # 제거
        content = re.sub(r'@\w+', '', content)       # 멘션 제거
        
        # URL 제거
        content = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', content)
        
        # 이모지 처리 (선택적 보존)
        # 실제 구현시 이모지 감성 분석 활용 가능
        
        return content.strip()
    
    def _clean_financial_text(self, content: str) -> str:
        """재무 텍스트 정리"""
        import re
        
        # 숫자 표기 통일 (천 단위 구분자)
        content = re.sub(r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', 
                        lambda m: m.group(1).replace(',', ''), content)
        
        # 화폐 단위 통일
        currency_map = {
            '억원': ' 억원',
            '만원': ' 만원',
            '조원': ' 조원'
        }
        
        for old, new in currency_map.items():
            content = content.replace(old, new)
        
        return content.strip()
    
    def _clean_price_data(self, content: str) -> str:
        """가격 데이터 정리"""
        # 가격 데이터는 주로 구조화되어 있어 최소한의 정리만 수행
        return str(content).strip()
    
    def calculate_quality_score(self, raw_data: RawDataPoint) -> float:
        """데이터 품질 점수 계산"""
        try:
            score = 1.0
            content = raw_data.content
            
            # 내용 길이 검사
            text_content = str(content.get('content', ''))
            if len(text_content) < self.quality_rules["min_content_length"]:
                score -= 0.3
            elif len(text_content) > self.quality_rules["max_content_length"]:
                score -= 0.2
            
            # 필수 필드 검사
            for field in self.quality_rules["required_fields"]:
                if field not in content or not content[field]:
                    score -= 0.2
            
            # 금지 단어 검사
            for word in self.quality_rules["forbidden_words"]:
                if word in text_content:
                    score -= 0.4
                    break
            
            # 중복 내용 검사 (간단한 휴리스틱)
            if len(set(text_content.split())) < len(text_content.split()) * 0.5:
                score -= 0.2  # 중복 단어가 너무 많음
            
            # 언어 일관성 검사
            korean_chars = sum(1 for char in text_content if '가' <= char <= '힣')
            total_chars = len(text_content)
            if total_chars > 0:
                korean_ratio = korean_chars / total_chars
                if 0.1 < korean_ratio < 0.9:  # 혼재된 언어
                    score -= 0.1
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.warning(f"품질 점수 계산 실패: {str(e)}")
            return 0.5  # 기본 점수
    
    def process_raw_data(self, raw_data: RawDataPoint) -> Optional[ProcessedDocument]:
        """원시 데이터를 처리된 문서로 변환"""
        try:
            content_dict = raw_data.content
            
            # 필수 필드 확인
            if 'content' not in content_dict:
                logger.warning(f"내용이 없는 데이터: {raw_data.source_id}")
                return None
            
            # 텍스트 정리
            cleaner = self.text_cleaners.get(raw_data.data_type, lambda x: x)
            cleaned_content = cleaner(str(content_dict['content']))
            
            if not cleaned_content or len(cleaned_content.strip()) < 10:
                logger.warning("정리된 내용이 너무 짧음")
                return None
            
            # 문서 ID 생성
            doc_id = f"{raw_data.source_id}_{raw_data.data_type}_{int(raw_data.timestamp.timestamp())}"
            
            # 제목 추출
            title = content_dict.get('title', cleaned_content[:100] + '...')
            
            # 품질 메트릭 계산
            quality_metrics = {
                'content_length': len(cleaned_content),
                'word_count': len(cleaned_content.split()),
                'readability_score': self._calculate_readability(cleaned_content),
                'information_density': self._calculate_information_density(cleaned_content)
            }
            
            # 태그 추출
            tags = self._extract_tags(cleaned_content, raw_data.data_type)
            
            # 메타데이터 보강
            enriched_metadata = raw_data.metadata.copy()
            enriched_metadata.update({
                'original_length': len(str(content_dict['content'])),
                'processing_timestamp': datetime.utcnow().isoformat(),
                'data_source': raw_data.source_id,
                'quality_score': self.calculate_quality_score(raw_data)
            })
            
            return ProcessedDocument(
                doc_id=doc_id,
                title=title,
                content=cleaned_content,
                document_type=raw_data.data_type,
                source_id=raw_data.source_id,
                processed_at=datetime.utcnow(),
                metadata=enriched_metadata,
                quality_metrics=quality_metrics,
                tags=tags
            )
            
        except Exception as e:
            logger.error(f"데이터 처리 실패: {str(e)}")
            return None
    
    def _calculate_readability(self, text: str) -> float:
        """가독성 점수 계산 (간단한 휴리스틱)"""
        try:
            sentences = text.split('.')
            words = text.split()
            
            if not sentences or not words:
                return 0.0
            
            avg_sentence_length = len(words) / len(sentences)
            
            # 평균 문장 길이 기반 점수 (10-20단어가 적정)
            if 10 <= avg_sentence_length <= 20:
                return 1.0
            elif avg_sentence_length < 10:
                return 0.8
            elif avg_sentence_length < 30:
                return 0.7
            else:
                return 0.5
                
        except Exception:
            return 0.5
    
    def _calculate_information_density(self, text: str) -> float:
        """정보 밀도 계산"""
        try:
            words = text.split()
            unique_words = set(words)
            
            if not words:
                return 0.0
            
            # 고유 단어 비율
            uniqueness = len(unique_words) / len(words)
            
            # 숫자와 전문용어 비율
            numbers = sum(1 for word in words if any(char.isdigit() for char in word))
            technical_ratio = numbers / len(words)
            
            # 종합 점수
            density_score = (uniqueness * 0.7) + (technical_ratio * 0.3)
            return min(1.0, density_score)
            
        except Exception:
            return 0.5
    
    def _extract_tags(self, content: str, data_type: str) -> List[str]:
        """내용에서 태그 추출"""
        try:
            tags = []
            
            # 데이터 타입 기본 태그
            tags.append(data_type)
            
            # 키워드 기반 태그 추출
            finance_keywords = {
                '상승': 'bullish',
                '하락': 'bearish', 
                '매수': 'buy_signal',
                '매도': 'sell_signal',
                '실적': 'earnings',
                '배당': 'dividend',
                'IPO': 'ipo',
                '인수합병': 'ma'
            }
            
            for keyword, tag in finance_keywords.items():
                if keyword in content:
                    tags.append(tag)
            
            # 중복 제거
            return list(set(tags))
            
        except Exception:
            return [data_type]


class DataIngestionPipeline:
    """데이터 수집 파이프라인 메인 클래스"""
    
    def __init__(self, embedder: TextEmbedder):
        self.embedder = embedder
        self.processor = DataProcessor()
        
        # 데이터 소스 관리
        self.data_sources: Dict[str, DataSource] = {}
        self.connectors: Dict[str, DataSourceConnector] = {}
        
        # 파이프라인 상태
        self.is_running = False
        self.batch_size = 50
        self.processing_queue = asyncio.Queue()
        
        # 통계 정보
        self.stats = {
            'processed_documents': 0,
            'failed_documents': 0,
            'start_time': None,
            'last_batch_time': None
        }
    
    def register_data_source(self, source: DataSource) -> bool:
        """데이터 소스 등록"""
        try:
            self.data_sources[source.source_id] = source
            
            # 커넥터 생성
            if source.source_type == 'database':
                connector = DatabaseConnector(source)
            elif source.source_type == 'api':
                connector = APIConnector(source)
            else:
                logger.error(f"지원하지 않는 소스 타입: {source.source_type}")
                return False
            
            self.connectors[source.source_id] = connector
            logger.info(f"데이터 소스 등록: {source.name}")
            return True
            
        except Exception as e:
            logger.error(f"데이터 소스 등록 실패: {str(e)}")
            return False
    
    async def start_pipeline(self):
        """파이프라인 시작"""
        try:
            logger.info("데이터 수집 파이프라인 시작")
            self.is_running = True
            self.stats['start_time'] = datetime.utcnow()
            
            # 모든 커넥터 연결
            for source_id, connector in self.connectors.items():
                success = await connector.connect()
                if not success:
                    logger.error(f"커넥터 연결 실패: {source_id}")
            
            # 배치 처리와 스트림 처리를 동시 실행
            tasks = [
                asyncio.create_task(self._run_batch_processing()),
                asyncio.create_task(self._run_stream_processing()),
                asyncio.create_task(self._run_document_processing())
            ]
            
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"파이프라인 시작 실패: {str(e)}")
            self.is_running = False
    
    async def stop_pipeline(self):
        """파이프라인 중지"""
        try:
            logger.info("데이터 수집 파이프라인 중지")
            self.is_running = False
            
            # 모든 커넥터 연결 해제
            for connector in self.connectors.values():
                await connector.disconnect()
                
        except Exception as e:
            logger.error(f"파이프라인 중지 실패: {str(e)}")
    
    async def _run_batch_processing(self):
        """배치 처리 실행"""
        while self.is_running:
            try:
                for source_id, source in self.data_sources.items():
                    if not source.is_active:
                        continue
                    
                    connector = self.connectors.get(source_id)
                    if not connector:
                        continue
                    
                    # 마지막 업데이트 이후 데이터 가져오기
                    params = self._build_fetch_params(source)
                    raw_data_points = await connector.fetch_data(params)
                    
                    # 처리 큐에 추가
                    for data_point in raw_data_points:
                        await self.processing_queue.put(data_point)
                    
                    # 소스 업데이트 시간 갱신
                    source.last_updated = datetime.utcnow()
                
                self.stats['last_batch_time'] = datetime.utcnow()
                
                # 배치 간격 대기
                await asyncio.sleep(60)  # 1분 간격
                
            except Exception as e:
                logger.error(f"배치 처리 오류: {str(e)}")
                await asyncio.sleep(10)  # 오류시 10초 대기
    
    async def _run_stream_processing(self):
        """스트림 처리 실행"""
        while self.is_running:
            try:
                # 스트림 지원하는 소스들의 커넥터 실행
                stream_tasks = []
                
                for source_id, source in self.data_sources.items():
                    if source.source_type in ['api', 'stream'] and source.is_active:
                        connector = self.connectors.get(source_id)
                        if connector:
                            task = asyncio.create_task(
                                self._process_stream(connector)
                            )
                            stream_tasks.append(task)
                
                if stream_tasks:
                    await asyncio.gather(*stream_tasks)
                else:
                    await asyncio.sleep(5)
                    
            except Exception as e:
                logger.error(f"스트림 처리 오류: {str(e)}")
                await asyncio.sleep(5)
    
    async def _process_stream(self, connector: DataSourceConnector):
        """개별 스트림 처리"""
        try:
            async for data_point in connector.stream_data():
                if not self.is_running:
                    break
                    
                await self.processing_queue.put(data_point)
                
        except Exception as e:
            logger.error(f"스트림 처리 오류: {str(e)}")
    
    async def _run_document_processing(self):
        """문서 처리 실행"""
        while self.is_running:
            try:
                # 배치 단위로 문서 처리
                batch = []
                
                # 큐에서 데이터 수집
                try:
                    while len(batch) < self.batch_size:
                        data_point = await asyncio.wait_for(
                            self.processing_queue.get(), 
                            timeout=5.0
                        )
                        batch.append(data_point)
                except asyncio.TimeoutError:
                    # 타임아웃시 현재 배치 처리
                    pass
                
                if not batch:
                    continue
                
                # 배치 처리
                await self._process_batch(batch)
                
            except Exception as e:
                logger.error(f"문서 처리 오류: {str(e)}")
                await asyncio.sleep(1)
    
    async def _process_batch(self, raw_data_batch: List[RawDataPoint]):
        """배치 단위 문서 처리"""
        try:
            logger.info(f"배치 처리 시작: {len(raw_data_batch)}개 데이터")
            
            # 1. 전처리
            processed_docs = []
            for raw_data in raw_data_batch:
                processed_doc = self.processor.process_raw_data(raw_data)
                if processed_doc:
                    processed_docs.append(processed_doc)
                else:
                    self.stats['failed_documents'] += 1
            
            if not processed_docs:
                logger.warning("처리된 문서가 없음")
                return
            
            # 2. 임베딩 생성
            embed_requests = []
            for doc in processed_docs:
                request = EmbeddingRequest(
                    text=f"{doc.title}\n\n{doc.content}",
                    document_type=doc.document_type,
                    metadata=doc.metadata,
                    priority=self._calculate_embedding_priority(doc)
                )
                embed_requests.append(request)
            
            # 배치 임베딩 생성
            embedding_results = await self.embedder.embed_batch(embed_requests)
            
            # 3. IndexedDocument 생성
            indexed_docs = []
            for doc, embed_result in zip(processed_docs, embedding_results):
                if embed_result:
                    indexed_doc = IndexedDocument(
                        doc_id=doc.doc_id,
                        content=doc.content,
                        embedding=embed_result.embedding,
                        document_type=doc.document_type,
                        metadata=doc.metadata,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    indexed_docs.append(indexed_doc)
            
            # 4. 인덱스 추가 (별도 함수에서 처리)
            await self._add_to_index(indexed_docs)
            
            # 통계 업데이트
            self.stats['processed_documents'] += len(indexed_docs)
            
            logger.info(f"배치 처리 완료: {len(indexed_docs)}개 문서 인덱싱")
            
        except Exception as e:
            logger.error(f"배치 처리 실패: {str(e)}")
            self.stats['failed_documents'] += len(raw_data_batch)
    
    def _build_fetch_params(self, source: DataSource) -> Dict[str, Any]:
        """데이터 가져오기 파라미터 구성"""
        params = {}
        
        # 마지막 업데이트 이후 데이터만 가져오기
        if source.last_updated:
            params['since'] = source.last_updated.isoformat()
        else:
            # 처음 실행시 최근 24시간 데이터
            since = datetime.utcnow() - timedelta(hours=24)
            params['since'] = since.isoformat()
        
        # 소스별 특별 파라미터
        if source.source_type == 'api':
            params['limit'] = 100
            
        return params
    
    def _calculate_embedding_priority(self, doc: ProcessedDocument) -> int:
        """임베딩 우선순위 계산"""
        priority = 3  # 기본 우선순위
        
        # 품질 점수 기반 조정
        quality_score = doc.metadata.get('quality_score', 0.5)
        if quality_score > 0.8:
            priority = 1  # 높은 우선순위
        elif quality_score > 0.6:
            priority = 2
        elif quality_score < 0.4:
            priority = 4  # 낮은 우선순위
        
        # 문서 타입 기반 조정
        high_priority_types = ['news', 'earnings', 'strategy']
        if doc.document_type in high_priority_types:
            priority = max(1, priority - 1)
        
        # 최신성 고려
        age_hours = (datetime.utcnow() - doc.processed_at).total_seconds() / 3600
        if age_hours < 1:  # 1시간 이내
            priority = max(1, priority - 1)
        
        return priority
    
    async def _add_to_index(self, indexed_docs: List[IndexedDocument]):
        """인덱스에 문서 추가 (외부 인덱서와 연동)"""
        try:
            # 실제 구현시 VectorIndexer와 연동
            logger.info(f"인덱스 추가 준비: {len(indexed_docs)}개 문서")
            # indexer.add_documents(indexed_docs)
            
        except Exception as e:
            logger.error(f"인덱스 추가 실패: {str(e)}")
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """파이프라인 통계 정보 반환"""
        runtime = None
        if self.stats['start_time']:
            runtime = (datetime.utcnow() - self.stats['start_time']).total_seconds()
        
        return {
            "is_running": self.is_running,
            "processed_documents": self.stats['processed_documents'],
            "failed_documents": self.stats['failed_documents'],
            "success_rate": (
                self.stats['processed_documents'] / 
                (self.stats['processed_documents'] + self.stats['failed_documents'])
                if (self.stats['processed_documents'] + self.stats['failed_documents']) > 0 else 0
            ),
            "runtime_seconds": runtime,
            "queue_size": self.processing_queue.qsize(),
            "data_sources": len(self.data_sources),
            "active_sources": sum(1 for s in self.data_sources.values() if s.is_active),
            "last_batch_time": self.stats['last_batch_time'].isoformat() if self.stats['last_batch_time'] else None
        }
    
    async def manual_ingest(
        self, 
        source_id: str, 
        data_points: List[RawDataPoint]
    ) -> Dict[str, Any]:
        """수동 데이터 수집"""
        try:
            logger.info(f"수동 데이터 수집 시작: {source_id}, {len(data_points)}개")
            
            # 배치 처리
            await self._process_batch(data_points)
            
            return {
                "success": True,
                "processed_count": len(data_points),
                "message": "수동 데이터 수집 완료"
            }
            
        except Exception as e:
            logger.error(f"수동 데이터 수집 실패: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }