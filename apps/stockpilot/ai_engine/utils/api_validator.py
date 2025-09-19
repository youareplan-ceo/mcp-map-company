"""
API 응답 검증 및 오류 처리 유틸리티
OpenAI API 응답의 유효성 검증 및 한국어 특화 오류 처리
"""

import logging
import json
import re
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import asyncio
from functools import wraps

import openai
from openai import APIError, RateLimitError, APITimeoutError, AuthenticationError

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """검증 수준"""
    STRICT = "strict"      # 엄격한 검증
    STANDARD = "standard"  # 표준 검증
    LENIENT = "lenient"    # 관대한 검증

class ErrorSeverity(Enum):
    """오류 심각도"""
    CRITICAL = "critical"  # 치명적 오류
    HIGH = "high"         # 높은 심각도
    MEDIUM = "medium"     # 중간 심각도
    LOW = "low"          # 낮은 심각도

@dataclass
class ValidationResult:
    """검증 결과"""
    is_valid: bool
    confidence_score: float  # 0.0 - 1.0
    issues: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]
    korean_content_score: float  # 한국어 컨텐츠 품질 점수

@dataclass
class APIError:
    """API 오류 정보"""
    error_type: str
    error_code: Optional[str]
    message: str
    korean_message: str  # 한국어 오류 메시지
    severity: ErrorSeverity
    retry_after: Optional[int]  # 재시도 권장 시간(초)
    suggested_actions: List[str]
    timestamp: datetime

class KoreanContentValidator:
    """한국어 컨텐츠 검증기"""
    
    def __init__(self):
        # 한국어 품질 체크 패턴
        self.quality_patterns = {
            "korean_chars": r'[가-힣]',
            "complete_sentences": r'[.!?]$',
            "financial_terms": r'(매출|영업이익|주가|투자|분석|전망|실적|성장|수익)',
            "proper_spacing": r'[가-힣]\s[가-힣]',
            "no_truncation": r'\.{3,}$|…$',  # 말줄임표로 끝나지 않음
        }
        
        # 문제가 되는 패턴들
        self.problematic_patterns = {
            "repetitive": r'(.{10,})\1{2,}',  # 반복되는 패턴
            "incomplete": r'[가-힣][a-zA-Z]$|[a-zA-Z][가-힣]$',  # 불완전한 단어
            "encoding_issues": r'\\u[0-9a-fA-F]{4}',  # 유니코드 인코딩 문제
            "mixed_lang_confusion": r'[가-힣][A-Z]{2,}[가-힣]',  # 언어 혼재 문제
        }
    
    def validate_korean_content(
        self, 
        content: str, 
        validation_level: ValidationLevel = ValidationLevel.STANDARD
    ) -> ValidationResult:
        """한국어 컨텐츠 검증"""
        if not content:
            return ValidationResult(
                is_valid=False,
                confidence_score=0.0,
                issues=["빈 응답"],
                warnings=[],
                metadata={},
                korean_content_score=0.0
            )
        
        issues = []
        warnings = []
        metadata = {}
        
        # 1. 기본 한국어 컨텐츠 검사
        korean_char_count = len(re.findall(self.quality_patterns["korean_chars"], content))
        total_char_count = len(content)
        korean_ratio = korean_char_count / total_char_count if total_char_count > 0 else 0
        
        metadata["korean_ratio"] = korean_ratio
        metadata["korean_char_count"] = korean_char_count
        metadata["total_char_count"] = total_char_count
        
        # 2. 한국어 비율 검증
        if validation_level == ValidationLevel.STRICT:
            min_korean_ratio = 0.4
        elif validation_level == ValidationLevel.STANDARD:
            min_korean_ratio = 0.3
        else:  # LENIENT
            min_korean_ratio = 0.2
        
        if korean_ratio < min_korean_ratio:
            issues.append(f"한국어 비율이 낮습니다 ({korean_ratio:.1%} < {min_korean_ratio:.1%})")
        
        # 3. 문장 완성도 검사
        sentences = re.split(r'[.!?]\s*', content)
        complete_sentences = [s for s in sentences if len(s.strip()) > 0]
        
        if len(complete_sentences) == 0:
            issues.append("완성된 문장이 없습니다")
        
        # 4. 금융 용어 적절성 검사 (금융 관련 응답인 경우)
        financial_terms = re.findall(self.quality_patterns["financial_terms"], content, re.IGNORECASE)
        metadata["financial_terms_count"] = len(financial_terms)
        
        # 5. 문제 패턴 검사
        for pattern_name, pattern in self.problematic_patterns.items():
            if re.search(pattern, content):
                if pattern_name == "repetitive":
                    issues.append("반복되는 내용이 감지되었습니다")
                elif pattern_name == "incomplete":
                    warnings.append("불완전한 단어 조합이 있습니다")
                elif pattern_name == "encoding_issues":
                    issues.append("인코딩 문제가 감지되었습니다")
                elif pattern_name == "mixed_lang_confusion":
                    warnings.append("언어 혼재로 인한 가독성 문제가 있을 수 있습니다")
        
        # 6. 응답 길이 적절성
        if validation_level != ValidationLevel.LENIENT:
            if len(content.strip()) < 10:
                issues.append("응답이 너무 짧습니다")
            elif len(content) > 5000:  # 토큰 제한 고려
                warnings.append("응답이 매우 깁니다")
        
        # 7. 트렁케이션 검사
        if re.search(self.quality_patterns["no_truncation"], content):
            issues.append("응답이 중간에 잘린 것으로 보입니다")
        
        # 8. 종합 품질 점수 계산
        quality_factors = {
            "korean_ratio": korean_ratio,
            "completeness": 1.0 if not re.search(self.quality_patterns["no_truncation"], content) else 0.5,
            "sentence_structure": min(1.0, len(complete_sentences) / 3.0),  # 3문장 이상이면 만점
            "no_problems": 1.0 if len(issues) == 0 else (0.5 if len(issues) == 1 else 0.0)
        }
        
        korean_content_score = (
            quality_factors["korean_ratio"] * 0.3 +
            quality_factors["completeness"] * 0.3 +
            quality_factors["sentence_structure"] * 0.2 +
            quality_factors["no_problems"] * 0.2
        )
        
        # 9. 전체 유효성 판단
        is_valid = len(issues) == 0 and korean_content_score >= 0.5
        confidence_score = korean_content_score
        
        return ValidationResult(
            is_valid=is_valid,
            confidence_score=confidence_score,
            issues=issues,
            warnings=warnings,
            metadata=metadata,
            korean_content_score=korean_content_score
        )

class OpenAIResponseValidator:
    """OpenAI 응답 검증기"""
    
    def __init__(self):
        self.korean_validator = KoreanContentValidator()
    
    def validate_chat_response(
        self, 
        response: Any, 
        validation_level: ValidationLevel = ValidationLevel.STANDARD
    ) -> ValidationResult:
        """채팅 응답 검증"""
        issues = []
        warnings = []
        metadata = {}
        
        try:
            # 1. 기본 구조 검증
            if not hasattr(response, 'choices') or not response.choices:
                issues.append("응답에 choices가 없습니다")
                return ValidationResult(
                    is_valid=False, confidence_score=0.0, issues=issues,
                    warnings=warnings, metadata=metadata, korean_content_score=0.0
                )
            
            # 2. 첫 번째 선택지 검증
            first_choice = response.choices[0]
            if not hasattr(first_choice, 'message') or not first_choice.message:
                issues.append("메시지가 없습니다")
                return ValidationResult(
                    is_valid=False, confidence_score=0.0, issues=issues,
                    warnings=warnings, metadata=metadata, korean_content_score=0.0
                )
            
            # 3. 메시지 내용 검증
            message_content = first_choice.message.content
            if not message_content:
                issues.append("메시지 내용이 비어있습니다")
                return ValidationResult(
                    is_valid=False, confidence_score=0.0, issues=issues,
                    warnings=warnings, metadata=metadata, korean_content_score=0.0
                )
            
            # 4. finish_reason 검증
            if hasattr(first_choice, 'finish_reason'):
                if first_choice.finish_reason == 'length':
                    warnings.append("토큰 한도로 인해 응답이 잘렸을 수 있습니다")
                elif first_choice.finish_reason == 'content_filter':
                    issues.append("컨텐츠 필터에 의해 응답이 차단되었습니다")
                elif first_choice.finish_reason not in ['stop', 'length']:
                    warnings.append(f"예상치 못한 종료 이유: {first_choice.finish_reason}")
            
            # 5. 사용량 정보 검증
            if hasattr(response, 'usage') and response.usage:
                metadata["input_tokens"] = response.usage.prompt_tokens
                metadata["output_tokens"] = response.usage.completion_tokens
                metadata["total_tokens"] = response.usage.total_tokens
                
                # 토큰 사용량 이상 검사
                if response.usage.total_tokens == 0:
                    warnings.append("토큰 사용량이 0입니다")
                elif response.usage.total_tokens > 10000:  # 높은 사용량
                    warnings.append("매우 높은 토큰 사용량")
            
            # 6. 한국어 컨텐츠 검증
            korean_validation = self.korean_validator.validate_korean_content(
                message_content, validation_level
            )
            
            issues.extend(korean_validation.issues)
            warnings.extend(korean_validation.warnings)
            metadata.update(korean_validation.metadata)
            
            # 7. 종합 점수 계산
            structure_score = 1.0 if len(issues) == 0 else 0.5
            content_score = korean_validation.korean_content_score
            overall_score = (structure_score + content_score) / 2
            
            return ValidationResult(
                is_valid=len(issues) == 0,
                confidence_score=overall_score,
                issues=issues,
                warnings=warnings,
                metadata=metadata,
                korean_content_score=korean_validation.korean_content_score
            )
            
        except Exception as e:
            logger.error(f"응답 검증 중 오류 발생: {e}")
            return ValidationResult(
                is_valid=False,
                confidence_score=0.0,
                issues=[f"검증 중 오류: {str(e)}"],
                warnings=[],
                metadata={},
                korean_content_score=0.0
            )
    
    def validate_embedding_response(self, response: Any) -> ValidationResult:
        """임베딩 응답 검증"""
        issues = []
        warnings = []
        metadata = {}
        
        try:
            # 1. 기본 구조 검증
            if not hasattr(response, 'data') or not response.data:
                issues.append("응답에 data가 없습니다")
                return ValidationResult(
                    is_valid=False, confidence_score=0.0, issues=issues,
                    warnings=warnings, metadata=metadata, korean_content_score=1.0
                )
            
            # 2. 임베딩 데이터 검증
            first_embedding = response.data[0]
            if not hasattr(first_embedding, 'embedding') or not first_embedding.embedding:
                issues.append("임베딩 벡터가 없습니다")
                return ValidationResult(
                    is_valid=False, confidence_score=0.0, issues=issues,
                    warnings=warnings, metadata=metadata, korean_content_score=1.0
                )
            
            # 3. 벡터 차원 검증
            embedding_vector = first_embedding.embedding
            vector_dimension = len(embedding_vector)
            metadata["vector_dimension"] = vector_dimension
            
            # 일반적인 OpenAI 임베딩 차원
            expected_dimensions = {
                "text-embedding-3-small": 1536,
                "text-embedding-3-large": 3072,
                "text-embedding-ada-002": 1536
            }
            
            # 차원 적절성 검사 (모델을 알 수 없으면 일반적인 범위로 검사)
            if vector_dimension < 300:
                warnings.append(f"임베딩 차원이 낮습니다: {vector_dimension}")
            elif vector_dimension > 5000:
                warnings.append(f"임베딩 차원이 매우 높습니다: {vector_dimension}")
            
            # 4. 벡터 값 검증
            vector_values = list(embedding_vector)
            if not all(isinstance(v, (int, float)) for v in vector_values):
                issues.append("임베딩 벡터에 숫자가 아닌 값이 포함되어 있습니다")
            
            # 벡터 정규화 검사 (일반적으로 정규화된 벡터 사용)
            import math
            vector_magnitude = math.sqrt(sum(v**2 for v in vector_values))
            metadata["vector_magnitude"] = vector_magnitude
            
            if abs(vector_magnitude - 1.0) > 0.1:  # 정규화 허용 오차
                warnings.append(f"벡터가 정규화되지 않았을 수 있습니다: 크기 {vector_magnitude:.3f}")
            
            # 5. 사용량 정보 검증
            if hasattr(response, 'usage') and response.usage:
                metadata["total_tokens"] = response.usage.total_tokens
            
            confidence_score = 1.0 if len(issues) == 0 else 0.5
            
            return ValidationResult(
                is_valid=len(issues) == 0,
                confidence_score=confidence_score,
                issues=issues,
                warnings=warnings,
                metadata=metadata,
                korean_content_score=1.0  # 임베딩은 언어 무관
            )
            
        except Exception as e:
            logger.error(f"임베딩 응답 검증 중 오류 발생: {e}")
            return ValidationResult(
                is_valid=False,
                confidence_score=0.0,
                issues=[f"검증 중 오류: {str(e)}"],
                warnings=[],
                metadata={},
                korean_content_score=0.0
            )

class APIErrorHandler:
    """API 오류 처리기"""
    
    def __init__(self):
        # 한국어 오류 메시지 매핑
        self.korean_error_messages = {
            "rate_limit_exceeded": "API 호출 한도를 초과했습니다",
            "insufficient_quota": "API 사용량 할당량이 부족합니다",
            "invalid_api_key": "API 키가 유효하지 않습니다",
            "model_not_found": "요청한 모델을 찾을 수 없습니다",
            "invalid_request": "요청 형식이 올바르지 않습니다",
            "server_error": "서버에서 오류가 발생했습니다",
            "timeout": "요청 시간이 초과되었습니다",
            "context_length_exceeded": "입력 텍스트가 너무 깁니다",
            "content_filter": "내용이 안전 정책에 위반됩니다",
            "network_error": "네트워크 연결에 문제가 있습니다"
        }
        
        # 오류별 권장 액션
        self.error_actions = {
            "rate_limit_exceeded": [
                "잠시 후 다시 시도하세요",
                "요청 빈도를 줄이세요",
                "더 높은 등급의 API 플랜을 고려하세요"
            ],
            "insufficient_quota": [
                "API 사용량을 확인하고 결제하세요",
                "사용량 알림을 설정하세요",
                "더 효율적인 프롬프트를 사용하세요"
            ],
            "invalid_api_key": [
                "API 키를 다시 확인하세요",
                "새로운 API 키를 생성하세요",
                "환경 변수 설정을 확인하세요"
            ],
            "model_not_found": [
                "지원되는 모델 목록을 확인하세요",
                "모델명 철자를 확인하세요",
                "계정에 해당 모델 접근 권한이 있는지 확인하세요"
            ],
            "invalid_request": [
                "요청 파라미터를 확인하세요",
                "API 문서를 참조하세요",
                "입력 데이터 형식을 확인하세요"
            ],
            "server_error": [
                "잠시 후 다시 시도하세요",
                "지속적인 문제 발생 시 지원팀에 문의하세요"
            ],
            "timeout": [
                "네트워크 연결을 확인하세요",
                "타임아웃 설정을 늘리세요",
                "입력 텍스트 길이를 줄이세요"
            ],
            "context_length_exceeded": [
                "입력 텍스트를 요약하거나 분할하세요",
                "더 긴 컨텍스트를 지원하는 모델을 사용하세요",
                "불필요한 내용을 제거하세요"
            ],
            "content_filter": [
                "내용을 수정하여 재시도하세요",
                "안전 정책을 확인하세요",
                "중립적인 표현으로 바꾸세요"
            ],
            "network_error": [
                "인터넷 연결을 확인하세요",
                "VPN 사용 시 연결을 확인하세요",
                "잠시 후 다시 시도하세요"
            ]
        }
    
    def handle_openai_error(self, error: Exception) -> APIError:
        """OpenAI 오류 처리"""
        try:
            error_info = self._classify_openai_error(error)
            
            return APIError(
                error_type=error_info["type"],
                error_code=error_info.get("code"),
                message=str(error),
                korean_message=error_info["korean_message"],
                severity=error_info["severity"],
                retry_after=error_info.get("retry_after"),
                suggested_actions=error_info["actions"],
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"오류 처리 중 예외 발생: {e}")
            return APIError(
                error_type="unknown_error",
                error_code=None,
                message=str(error),
                korean_message="알 수 없는 오류가 발생했습니다",
                severity=ErrorSeverity.HIGH,
                retry_after=None,
                suggested_actions=["잠시 후 다시 시도하세요"],
                timestamp=datetime.now()
            )
    
    def _classify_openai_error(self, error: Exception) -> Dict[str, Any]:
        """OpenAI 오류 분류"""
        if isinstance(error, RateLimitError):
            return {
                "type": "rate_limit_exceeded",
                "severity": ErrorSeverity.MEDIUM,
                "korean_message": self.korean_error_messages["rate_limit_exceeded"],
                "actions": self.error_actions["rate_limit_exceeded"],
                "retry_after": 60  # 기본 1분 후 재시도
            }
        
        elif isinstance(error, AuthenticationError):
            return {
                "type": "invalid_api_key",
                "severity": ErrorSeverity.HIGH,
                "korean_message": self.korean_error_messages["invalid_api_key"],
                "actions": self.error_actions["invalid_api_key"]
            }
        
        elif isinstance(error, APITimeoutError):
            return {
                "type": "timeout",
                "severity": ErrorSeverity.MEDIUM,
                "korean_message": self.korean_error_messages["timeout"],
                "actions": self.error_actions["timeout"],
                "retry_after": 30
            }
        
        elif isinstance(error, APIError):
            # 일반적인 API 오류 처리
            error_message = str(error).lower()
            
            if "quota" in error_message or "billing" in error_message:
                return {
                    "type": "insufficient_quota",
                    "severity": ErrorSeverity.HIGH,
                    "korean_message": self.korean_error_messages["insufficient_quota"],
                    "actions": self.error_actions["insufficient_quota"]
                }
            
            elif "model" in error_message and "not found" in error_message:
                return {
                    "type": "model_not_found",
                    "severity": ErrorSeverity.MEDIUM,
                    "korean_message": self.korean_error_messages["model_not_found"],
                    "actions": self.error_actions["model_not_found"]
                }
            
            elif "context_length" in error_message or "too long" in error_message:
                return {
                    "type": "context_length_exceeded",
                    "severity": ErrorSeverity.MEDIUM,
                    "korean_message": self.korean_error_messages["context_length_exceeded"],
                    "actions": self.error_actions["context_length_exceeded"]
                }
            
            elif "content policy" in error_message or "safety" in error_message:
                return {
                    "type": "content_filter",
                    "severity": ErrorSeverity.MEDIUM,
                    "korean_message": self.korean_error_messages["content_filter"],
                    "actions": self.error_actions["content_filter"]
                }
            
            elif "server" in error_message or "internal" in error_message:
                return {
                    "type": "server_error",
                    "severity": ErrorSeverity.MEDIUM,
                    "korean_message": self.korean_error_messages["server_error"],
                    "actions": self.error_actions["server_error"],
                    "retry_after": 30
                }
            
            else:
                return {
                    "type": "invalid_request",
                    "severity": ErrorSeverity.MEDIUM,
                    "korean_message": self.korean_error_messages["invalid_request"],
                    "actions": self.error_actions["invalid_request"]
                }
        
        else:
            # 네트워크 오류 등 기타 오류
            return {
                "type": "network_error",
                "severity": ErrorSeverity.MEDIUM,
                "korean_message": self.korean_error_messages["network_error"],
                "actions": self.error_actions["network_error"],
                "retry_after": 15
            }

# 데코레이터 함수들
def validate_response(validation_level: ValidationLevel = ValidationLevel.STANDARD):
    """응답 검증 데코레이터"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                
                # 응답 검증
                validator = OpenAIResponseValidator()
                if hasattr(result.get("response", {}), "choices"):
                    validation = validator.validate_chat_response(
                        result["response"], validation_level
                    )
                elif hasattr(result.get("response", {}), "data"):
                    validation = validator.validate_embedding_response(
                        result["response"]
                    )
                else:
                    validation = ValidationResult(
                        is_valid=True, confidence_score=1.0, issues=[], 
                        warnings=[], metadata={}, korean_content_score=1.0
                    )
                
                # 검증 결과를 응답에 추가
                result["validation"] = {
                    "is_valid": validation.is_valid,
                    "confidence_score": validation.confidence_score,
                    "issues": validation.issues,
                    "warnings": validation.warnings,
                    "korean_content_score": validation.korean_content_score
                }
                
                return result
                
            except Exception as e:
                logger.error(f"응답 검증 데코레이터에서 오류 발생: {e}")
                return result  # 검증 실패 시에도 원래 결과 반환
        
        return wrapper
    return decorator

def handle_api_errors(func):
    """API 오류 처리 데코레이터"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        error_handler = APIErrorHandler()
        
        try:
            return await func(*args, **kwargs)
            
        except Exception as e:
            # 오류 처리 및 로깅
            api_error = error_handler.handle_openai_error(e)
            
            logger.error(f"API 오류 발생: {api_error.korean_message}")
            logger.error(f"오류 상세: {api_error.message}")
            logger.error(f"권장 조치: {', '.join(api_error.suggested_actions)}")
            
            # 오류 정보를 포함한 응답 반환
            return {
                "error": True,
                "error_info": {
                    "type": api_error.error_type,
                    "message": api_error.korean_message,
                    "suggested_actions": api_error.suggested_actions,
                    "retry_after": api_error.retry_after,
                    "severity": api_error.severity.value
                },
                "original_error": str(e)
            }
    
    return wrapper

# 글로벌 인스턴스들
response_validator = OpenAIResponseValidator()
error_handler = APIErrorHandler()

# 편의 함수들
def validate_chat_completion(response: Any, level: ValidationLevel = ValidationLevel.STANDARD) -> ValidationResult:
    """채팅 완성 응답 검증"""
    return response_validator.validate_chat_response(response, level)

def validate_embedding(response: Any) -> ValidationResult:
    """임베딩 응답 검증"""
    return response_validator.validate_embedding_response(response)

def get_korean_error_message(error: Exception) -> str:
    """한국어 오류 메시지 반환"""
    api_error = error_handler.handle_openai_error(error)
    return api_error.korean_message

def get_error_suggestions(error: Exception) -> List[str]:
    """오류 해결 제안 반환"""
    api_error = error_handler.handle_openai_error(error)
    return api_error.suggested_actions

# 사용 예시
if __name__ == "__main__":
    # 테스트용 Mock 응답
    class MockResponse:
        def __init__(self):
            self.choices = [MockChoice()]
            self.usage = MockUsage()
    
    class MockChoice:
        def __init__(self):
            self.message = MockMessage()
            self.finish_reason = "stop"
    
    class MockMessage:
        def __init__(self):
            self.content = "삼성전자는 한국의 대표적인 기술 기업입니다. 반도체와 전자제품 분야에서 글로벌 리더십을 보여주고 있습니다."
    
    class MockUsage:
        def __init__(self):
            self.prompt_tokens = 20
            self.completion_tokens = 30
            self.total_tokens = 50
    
    # 검증 테스트
    print("=== API 응답 검증 테스트 ===")
    
    mock_response = MockResponse()
    validation = validate_chat_completion(mock_response, ValidationLevel.STANDARD)
    
    print(f"검증 결과: {'통과' if validation.is_valid else '실패'}")
    print(f"신뢰도 점수: {validation.confidence_score:.2f}")
    print(f"한국어 컨텐츠 점수: {validation.korean_content_score:.2f}")
    
    if validation.issues:
        print(f"문제점: {', '.join(validation.issues)}")
    
    if validation.warnings:
        print(f"경고: {', '.join(validation.warnings)}")
    
    print(f"메타데이터: {validation.metadata}")
    
    # 오류 처리 테스트
    print("\n=== 오류 처리 테스트 ===")
    
    test_error = RateLimitError("Rate limit exceeded")
    korean_message = get_korean_error_message(test_error)
    suggestions = get_error_suggestions(test_error)
    
    print(f"한국어 오류 메시지: {korean_message}")
    print(f"해결 제안: {', '.join(suggestions)}")