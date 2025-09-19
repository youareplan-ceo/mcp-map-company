"""
RAG 컨텍스트 구성 모듈
검색된 문서들을 바탕으로 AI 모델이 사용할 최적화된 컨텍스트를 구성
토큰 관리, 컨텍스트 압축, 시간순 정렬, 메타데이터 첨부 등의 기능 포함
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
import tiktoken
from collections import defaultdict
import json

from .retriever import SearchResult
from .indexer import IndexedDocument
from ..config.model_policy import ModelTier, model_policy

logger = logging.getLogger(__name__)


@dataclass
class ContextChunk:
    """컨텍스트 청크 정보"""
    content: str
    source_document: IndexedDocument
    relevance_score: float
    token_count: int
    chunk_type: str  # 'summary', 'detail', 'metadata'
    priority: int    # 1(높음) ~ 5(낮음)


@dataclass
class BuiltContext:
    """구성된 컨텍스트"""
    formatted_context: str
    total_tokens: int
    source_documents: List[IndexedDocument]
    chunk_summary: Dict[str, Any]
    metadata: Dict[str, Any]
    truncated: bool = False


class ContextBuilder:
    """
    RAG용 컨텍스트 구성 및 최적화 클래스
    토큰 제한, 관련성 기반 우선순위, 압축 등을 지원
    """
    
    def __init__(self, model_name: str = "gpt-4"):
        """
        초기화
        
        Args:
            model_name: 토큰 계산에 사용할 모델명
        """
        self.model_name = model_name
        
        try:
            self.tokenizer = tiktoken.encoding_for_model(model_name)
        except KeyError:
            # 지원하지 않는 모델의 경우 기본 인코딩 사용
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
            logger.warning(f"모델 '{model_name}' 토크나이저 미지원, 기본 인코딩 사용")
        
        # 문서 타입별 템플릿
        self.document_templates = {
            "news": """📰 **뉴스**: {title}
📅 **날짜**: {date}
📈 **감성**: {sentiment}
📝 **내용**: {content}
🔗 **출처**: {source}
---""",
            
            "price_data": """📊 **주가 데이터**: {symbol}
📅 **날짜**: {date}  
💰 **종가**: {close_price}
📈 **변동률**: {change_percent}%
📊 **거래량**: {volume}
---""",
            
            "technical_analysis": """📈 **기술적 분석**: {symbol}
📅 **분석일**: {date}
🎯 **신호**: {signal}
📊 **지표**: {indicators}
📝 **분석**: {content}
---""",
            
            "strategy": """🎯 **투자 전략**: {title}
📅 **생성일**: {date}
⭐ **등급**: {rating}
📝 **전략**: {content}
🎯 **목표**: {target}
---""",
            
            "general": """📄 **문서**: {title}
📅 **날짜**: {date}
📝 **내용**: {content}
---"""
        }
        
        # 압축 설정
        self.compression_ratios = {
            "summary": 0.3,    # 요약으로 30% 압축
            "bullet_points": 0.5,  # 불릿 포인트로 50% 압축
            "key_facts": 0.2   # 핵심 사실만 20% 압축
        }
    
    def count_tokens(self, text: str) -> int:
        """
        텍스트의 토큰 수 계산
        
        Args:
            text: 입력 텍스트
            
        Returns:
            int: 토큰 수
        """
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            logger.warning(f"토큰 계산 실패: {str(e)}")
            # 대략적 추정 (영어 기준)
            return len(text.split()) * 1.3
    
    def build_context(
        self,
        search_results: List[SearchResult],
        query: str,
        model_tier: ModelTier,
        max_tokens: Optional[int] = None,
        include_metadata: bool = True,
        compression_level: str = "none"  # none, summary, bullet_points, key_facts
    ) -> BuiltContext:
        """
        검색 결과를 바탕으로 컨텍스트 구성
        
        Args:
            search_results: 검색 결과 리스트
            query: 원본 쿼리
            model_tier: 사용할 모델 티어
            max_tokens: 최대 토큰 수 (None이면 모델 기본값 사용)
            include_metadata: 메타데이터 포함 여부
            compression_level: 압축 수준
            
        Returns:
            BuiltContext: 구성된 컨텍스트
        """
        try:
            logger.info(f"컨텍스트 구성 시작: {len(search_results)}개 문서")
            
            # 토큰 제한 설정
            if max_tokens is None:
                policy = model_policy.get_policy(model_tier)
                max_tokens = int(policy.max_tokens * 0.7)  # 출력 토큰 여유분 확보
            
            # 문서들을 청크로 변환
            chunks = self._create_chunks(
                search_results, 
                compression_level,
                include_metadata
            )
            
            # 우선순위 기반 청크 선택
            selected_chunks = self._select_chunks(chunks, max_tokens)
            
            # 컨텍스트 포맷팅
            formatted_context = self._format_context(
                selected_chunks, 
                query,
                include_metadata
            )
            
            # 결과 생성
            total_tokens = self.count_tokens(formatted_context)
            source_documents = [chunk.source_document for chunk in selected_chunks]
            
            # 청크 요약 정보
            chunk_summary = self._create_chunk_summary(selected_chunks)
            
            # 메타데이터 생성
            metadata = {
                "query": query,
                "model_tier": model_tier.value,
                "max_tokens": max_tokens,
                "compression_level": compression_level,
                "total_documents": len(search_results),
                "selected_documents": len(selected_chunks),
                "truncated": len(selected_chunks) < len(chunks),
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = BuiltContext(
                formatted_context=formatted_context,
                total_tokens=total_tokens,
                source_documents=source_documents,
                chunk_summary=chunk_summary,
                metadata=metadata,
                truncated=len(selected_chunks) < len(chunks)
            )
            
            logger.info(f"컨텍스트 구성 완료: {total_tokens} 토큰, "
                       f"{len(selected_chunks)}/{len(chunks)} 청크 선택")
            
            return result
            
        except Exception as e:
            logger.error(f"컨텍스트 구성 실패: {str(e)}")
            raise
    
    def _create_chunks(
        self,
        search_results: List[SearchResult],
        compression_level: str,
        include_metadata: bool
    ) -> List[ContextChunk]:
        """
        검색 결과를 컨텍스트 청크로 변환
        
        Args:
            search_results: 검색 결과
            compression_level: 압축 수준
            include_metadata: 메타데이터 포함 여부
            
        Returns:
            List[ContextChunk]: 컨텍스트 청크 리스트
        """
        chunks = []
        
        for result in search_results:
            doc = result.document
            
            # 내용 처리 (압축 적용)
            if compression_level != "none":
                content = self._compress_content(doc.content, compression_level)
            else:
                content = doc.content
            
            # 문서 타입에 따른 포맷팅
            formatted_content = self._format_document(doc, content)
            
            # 토큰 수 계산
            token_count = self.count_tokens(formatted_content)
            
            # 우선순위 계산 (관련성 점수 기반)
            priority = self._calculate_priority(result)
            
            chunk = ContextChunk(
                content=formatted_content,
                source_document=doc,
                relevance_score=result.final_score,
                token_count=token_count,
                chunk_type="content",
                priority=priority
            )
            
            chunks.append(chunk)
            
            # 메타데이터 청크 추가 (선택적)
            if include_metadata and doc.metadata:
                metadata_content = self._format_metadata(doc.metadata)
                if metadata_content:
                    metadata_chunk = ContextChunk(
                        content=metadata_content,
                        source_document=doc,
                        relevance_score=result.final_score * 0.5,  # 메타데이터는 낮은 관련성
                        token_count=self.count_tokens(metadata_content),
                        chunk_type="metadata",
                        priority=priority + 1  # 낮은 우선순위
                    )
                    chunks.append(metadata_chunk)
        
        # 우선순위와 관련성으로 정렬
        chunks.sort(key=lambda x: (x.priority, -x.relevance_score))
        
        return chunks
    
    def _compress_content(self, content: str, compression_level: str) -> str:
        """
        내용 압축
        
        Args:
            content: 원본 내용
            compression_level: 압축 수준
            
        Returns:
            str: 압축된 내용
        """
        try:
            if compression_level == "summary":
                # 첫 문장 + 중요 문장들
                sentences = content.split('.')
                if len(sentences) <= 3:
                    return content
                
                # 첫 문장과 마지막 문장, 그리고 가장 긴 문장 몇 개 선택
                first_sentence = sentences[0] + '.'
                last_sentence = sentences[-1] if sentences[-1].strip() else sentences[-2] + '.'
                
                # 중간 문장들을 길이순 정렬해서 상위 몇 개 선택
                middle_sentences = sentences[1:-1]
                middle_sentences.sort(key=len, reverse=True)
                selected_middle = middle_sentences[:2]
                
                return f"{first_sentence} {' '.join(selected_middle)} {last_sentence}"
                
            elif compression_level == "bullet_points":
                # 불릿 포인트 형식으로 압축
                sentences = [s.strip() for s in content.split('.') if s.strip()]
                if len(sentences) <= 3:
                    return content
                
                bullet_points = []
                for sentence in sentences[:5]:  # 최대 5개 포인트
                    if len(sentence) > 10:  # 너무 짧은 문장 제외
                        bullet_points.append(f"• {sentence}")
                
                return '\n'.join(bullet_points)
                
            elif compression_level == "key_facts":
                # 핵심 키워드만 추출
                sentences = content.split('.')
                key_info = []
                
                keywords = ['상승', '하락', '매수', '매도', '목표', '전망', '분석', '예상']
                
                for sentence in sentences:
                    if any(keyword in sentence for keyword in keywords):
                        key_info.append(sentence.strip())
                
                if not key_info:
                    # 키워드가 없으면 첫 문장
                    key_info = [sentences[0]]
                
                return '. '.join(key_info[:3])  # 최대 3개 사실
                
            else:
                return content
                
        except Exception as e:
            logger.warning(f"내용 압축 실패: {str(e)}")
            return content
    
    def _format_document(self, doc: IndexedDocument, content: str) -> str:
        """
        문서 타입에 따른 포맷팅
        
        Args:
            doc: 문서 객체
            content: 문서 내용
            
        Returns:
            str: 포맷팅된 내용
        """
        try:
            template = self.document_templates.get(
                doc.document_type, 
                self.document_templates["general"]
            )
            
            # 메타데이터에서 정보 추출
            metadata = doc.metadata or {}
            
            format_params = {
                "title": metadata.get("title", "제목 없음"),
                "date": doc.created_at.strftime("%Y-%m-%d %H:%M"),
                "content": content,
                "source": metadata.get("source", "알 수 없음")
            }
            
            # 문서 타입별 특별 처리
            if doc.document_type == "news":
                sentiment_score = metadata.get("sentiment_score", 0)
                if sentiment_score > 0.1:
                    sentiment = "긍정적"
                elif sentiment_score < -0.1:
                    sentiment = "부정적"
                else:
                    sentiment = "중립적"
                
                format_params.update({
                    "sentiment": sentiment,
                    "title": metadata.get("title", content[:50] + "...")
                })
                
            elif doc.document_type == "price_data":
                format_params.update({
                    "symbol": metadata.get("symbol", "N/A"),
                    "close_price": metadata.get("close_price", "N/A"),
                    "change_percent": metadata.get("change_percent", "N/A"),
                    "volume": metadata.get("volume", "N/A")
                })
                
            elif doc.document_type == "technical_analysis":
                format_params.update({
                    "symbol": metadata.get("symbol", "N/A"),
                    "signal": metadata.get("signal", "중립"),
                    "indicators": metadata.get("indicators", "N/A")
                })
                
            elif doc.document_type == "strategy":
                format_params.update({
                    "rating": metadata.get("rating", "등급 없음"),
                    "target": metadata.get("target", "목표 없음")
                })
            
            return template.format(**format_params)
            
        except Exception as e:
            logger.warning(f"문서 포맷팅 실패: {str(e)}")
            return f"📄 **문서**: {content}"
    
    def _format_metadata(self, metadata: Dict[str, Any]) -> str:
        """
        메타데이터 포맷팅
        
        Args:
            metadata: 메타데이터 딕셔너리
            
        Returns:
            str: 포맷팅된 메타데이터
        """
        try:
            important_fields = [
                "symbol", "sector", "market_cap", "pe_ratio", 
                "dividend_yield", "52_week_high", "52_week_low"
            ]
            
            formatted_items = []
            for field in important_fields:
                if field in metadata:
                    value = metadata[field]
                    formatted_items.append(f"**{field.replace('_', ' ').title()}**: {value}")
            
            if formatted_items:
                return "🏷️ **메타데이터**:\n" + "\n".join(formatted_items) + "\n---"
            
            return ""
            
        except Exception as e:
            logger.warning(f"메타데이터 포맷팅 실패: {str(e)}")
            return ""
    
    def _calculate_priority(self, search_result: SearchResult) -> int:
        """
        검색 결과의 우선순위 계산
        
        Args:
            search_result: 검색 결과
            
        Returns:
            int: 우선순위 (1이 가장 높음)
        """
        try:
            score = search_result.final_score
            doc_type = search_result.document.document_type
            
            # 문서 타입별 기본 우선순위
            type_priorities = {
                "strategy": 1,
                "technical_analysis": 2, 
                "news": 3,
                "price_data": 4,
                "general": 5
            }
            
            base_priority = type_priorities.get(doc_type, 5)
            
            # 점수에 따른 조정
            if score > 0.8:
                base_priority = max(1, base_priority - 1)
            elif score < 0.6:
                base_priority = min(5, base_priority + 1)
            
            return base_priority
            
        except Exception as e:
            logger.warning(f"우선순위 계산 실패: {str(e)}")
            return 5
    
    def _select_chunks(
        self, 
        chunks: List[ContextChunk], 
        max_tokens: int
    ) -> List[ContextChunk]:
        """
        토큰 제한 내에서 최적의 청크 선택
        
        Args:
            chunks: 청크 리스트
            max_tokens: 최대 토큰 수
            
        Returns:
            List[ContextChunk]: 선택된 청크들
        """
        selected_chunks = []
        total_tokens = 0
        
        # 기본 프롬프트 토큰 예약 (약 200토큰)
        reserved_tokens = 200
        available_tokens = max_tokens - reserved_tokens
        
        for chunk in chunks:
            if total_tokens + chunk.token_count <= available_tokens:
                selected_chunks.append(chunk)
                total_tokens += chunk.token_count
            else:
                # 토큰 초과시 중요도가 높은 청크라면 일부만 포함
                if chunk.priority <= 2:  # 높은 우선순위
                    remaining_tokens = available_tokens - total_tokens
                    if remaining_tokens > 50:  # 최소한의 의미있는 내용
                        # 청크 내용 일부 포함
                        truncated_content = self._truncate_chunk(
                            chunk, 
                            remaining_tokens
                        )
                        if truncated_content:
                            selected_chunks.append(truncated_content)
                            total_tokens = available_tokens
                break
        
        return selected_chunks
    
    def _truncate_chunk(
        self, 
        chunk: ContextChunk, 
        max_tokens: int
    ) -> Optional[ContextChunk]:
        """
        청크 내용을 토큰 제한에 맞게 잘라내기
        
        Args:
            chunk: 원본 청크
            max_tokens: 최대 토큰 수
            
        Returns:
            Optional[ContextChunk]: 잘라낸 청크 (또는 None)
        """
        try:
            content_lines = chunk.content.split('\n')
            truncated_lines = []
            current_tokens = 0
            
            for line in content_lines:
                line_tokens = self.count_tokens(line + '\n')
                if current_tokens + line_tokens <= max_tokens:
                    truncated_lines.append(line)
                    current_tokens += line_tokens
                else:
                    break
            
            if truncated_lines:
                truncated_content = '\n'.join(truncated_lines)
                if len(truncated_lines) < len(content_lines):
                    truncated_content += "\n... (내용 생략)"
                
                return ContextChunk(
                    content=truncated_content,
                    source_document=chunk.source_document,
                    relevance_score=chunk.relevance_score,
                    token_count=current_tokens,
                    chunk_type=chunk.chunk_type + "_truncated",
                    priority=chunk.priority
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"청크 자르기 실패: {str(e)}")
            return None
    
    def _format_context(
        self,
        chunks: List[ContextChunk],
        query: str,
        include_metadata: bool
    ) -> str:
        """
        최종 컨텍스트 포맷팅
        
        Args:
            chunks: 선택된 청크들
            query: 원본 쿼리
            include_metadata: 메타데이터 포함 여부
            
        Returns:
            str: 포맷팅된 컨텍스트
        """
        try:
            context_parts = []
            
            # 헤더
            context_parts.append("# 📊 StockPilot AI - 컨텍스트 정보")
            context_parts.append(f"**질문**: {query}")
            context_parts.append(f"**분석 시각**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} (UTC)")
            context_parts.append("")
            
            # 문서들을 타입별로 그룹화
            chunks_by_type = defaultdict(list)
            for chunk in chunks:
                if chunk.chunk_type != "metadata":  # 메타데이터는 별도 처리
                    chunks_by_type[chunk.source_document.document_type].append(chunk)
            
            # 문서 타입별 섹션
            type_headers = {
                "strategy": "## 🎯 투자 전략",
                "technical_analysis": "## 📈 기술적 분석", 
                "news": "## 📰 관련 뉴스",
                "price_data": "## 💰 주가 데이터",
                "general": "## 📄 일반 문서"
            }
            
            for doc_type in ["strategy", "technical_analysis", "news", "price_data", "general"]:
                type_chunks = chunks_by_type.get(doc_type, [])
                if type_chunks:
                    context_parts.append(type_headers.get(doc_type, f"## {doc_type}"))
                    context_parts.append("")
                    
                    for chunk in type_chunks:
                        context_parts.append(chunk.content)
                        context_parts.append("")
            
            # 메타데이터 섹션 (선택적)
            if include_metadata:
                metadata_chunks = [c for c in chunks if c.chunk_type == "metadata"]
                if metadata_chunks:
                    context_parts.append("## 🏷️ 추가 정보")
                    context_parts.append("")
                    for chunk in metadata_chunks:
                        context_parts.append(chunk.content)
                        context_parts.append("")
            
            # 푸터
            context_parts.append("---")
            context_parts.append("💡 **참고**: 위 정보는 실시간 데이터 분석을 바탕으로 구성되었습니다.")
            context_parts.append("투자 결정시 반드시 추가적인 검토와 전문가 상담을 받으시기 바랍니다.")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"컨텍스트 포맷팅 실패: {str(e)}")
            # 간단한 폴백 포맷
            simple_context = f"질문: {query}\n\n"
            for chunk in chunks:
                simple_context += chunk.content + "\n\n"
            return simple_context
    
    def _create_chunk_summary(self, chunks: List[ContextChunk]) -> Dict[str, Any]:
        """
        청크 요약 정보 생성
        
        Args:
            chunks: 청크 리스트
            
        Returns:
            Dict[str, Any]: 요약 정보
        """
        try:
            summary = {
                "total_chunks": len(chunks),
                "total_tokens": sum(c.token_count for c in chunks),
                "chunk_types": {},
                "document_types": {},
                "priority_distribution": {},
                "relevance_stats": {
                    "max": max(c.relevance_score for c in chunks) if chunks else 0,
                    "min": min(c.relevance_score for c in chunks) if chunks else 0,
                    "avg": sum(c.relevance_score for c in chunks) / len(chunks) if chunks else 0
                }
            }
            
            # 타입별 통계
            for chunk in chunks:
                chunk_type = chunk.chunk_type
                doc_type = chunk.source_document.document_type
                priority = chunk.priority
                
                summary["chunk_types"][chunk_type] = summary["chunk_types"].get(chunk_type, 0) + 1
                summary["document_types"][doc_type] = summary["document_types"].get(doc_type, 0) + 1
                summary["priority_distribution"][priority] = summary["priority_distribution"].get(priority, 0) + 1
            
            return summary
            
        except Exception as e:
            logger.warning(f"청크 요약 생성 실패: {str(e)}")
            return {"total_chunks": len(chunks), "error": str(e)}
    
    def optimize_context_for_model(
        self,
        context: BuiltContext,
        target_model: ModelTier
    ) -> BuiltContext:
        """
        특정 모델에 맞게 컨텍스트 최적화
        
        Args:
            context: 원본 컨텍스트
            target_model: 대상 모델
            
        Returns:
            BuiltContext: 최적화된 컨텍스트
        """
        try:
            policy = model_policy.get_policy(target_model)
            max_tokens = int(policy.max_tokens * 0.7)
            
            # 이미 토큰 제한 내라면 그대로 반환
            if context.total_tokens <= max_tokens:
                return context
            
            logger.info(f"컨텍스트 최적화 시작: {context.total_tokens} -> {max_tokens} 토큰")
            
            # 문서들을 다시 청크로 변환
            search_results = []
            for doc in context.source_documents:
                # 가상의 검색 결과 생성 (점수는 문서 순서 기반)
                from ..rag.retriever import SearchResult
                result = SearchResult(
                    document=doc,
                    relevance_score=0.8,  # 기본 점수
                    time_score=0.5,
                    final_score=0.7,
                    rank=len(search_results) + 1,
                    retrieval_reason="context_optimization",
                    matched_keywords=[]
                )
                search_results.append(result)
            
            # 더 강한 압축으로 재구성
            compression_level = "summary" if context.metadata.get("compression_level") == "none" else "key_facts"
            
            optimized_context = self.build_context(
                search_results=search_results,
                query=context.metadata.get("query", ""),
                model_tier=target_model,
                max_tokens=max_tokens,
                include_metadata=False,  # 메타데이터 제외로 토큰 절약
                compression_level=compression_level
            )
            
            logger.info(f"컨텍스트 최적화 완료: {optimized_context.total_tokens} 토큰")
            return optimized_context
            
        except Exception as e:
            logger.error(f"컨텍스트 최적화 실패: {str(e)}")
            return context  # 실패시 원본 반환