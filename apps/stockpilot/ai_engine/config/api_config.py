"""
OpenAI API 설정 및 클라이언트 관리
한국 시장 분석을 위한 API 설정 최적화
"""

import os
import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import openai
from openai import AsyncOpenAI
import backoff
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class APIProvider(Enum):
    """API 제공업체"""
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    OPENAI_COMPATIBLE = "openai_compatible"

@dataclass
class APIConfiguration:
    """API 설정 클래스"""
    provider: APIProvider = APIProvider.OPENAI
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    organization: Optional[str] = None
    project: Optional[str] = None
    
    # Azure OpenAI 전용 설정
    azure_endpoint: Optional[str] = None
    api_version: str = "2024-02-01"
    
    # 요청 제한 설정
    max_retries: int = 3
    timeout: float = 60.0
    rate_limit_rpm: int = 3500  # 분당 요청 수
    rate_limit_tpm: int = 40000  # 분당 토큰 수
    
    # 한국어 처리 최적화 설정
    default_temperature: float = 0.3  # 한국어 분석의 일관성을 위해 낮게 설정
    default_max_tokens: int = 2000
    korean_model_preference: Dict[str, str] = field(default_factory=lambda: {
        "embedding": "text-embedding-3-large",  # 한국어 임베딩 최적
        "chat": "gpt-4-turbo-preview",          # 한국어 이해도 높음
        "analysis": "gpt-4",                    # 복잡한 분석용
        "translation": "gpt-3.5-turbo"         # 번역 및 간단한 작업
    })

class OpenAIClientManager:
    """OpenAI 클라이언트 매니저 - 한국 시장 특화"""
    
    def __init__(self, config: APIConfiguration):
        self.config = config
        self.client: Optional[AsyncOpenAI] = None
        self.sync_client: Optional[openai.OpenAI] = None
        
        # 요청 추적을 위한 변수들
        self.request_count = 0
        self.token_usage = 0
        self.last_request_time = datetime.now()
        self.rate_limit_window = timedelta(minutes=1)
        
        # 한국어 처리 관련 설정
        self.korean_system_prompts = {
            "stock_analysis": """당신은 한국 주식시장 전문 분석가입니다. 
코스피, 코스닥 시장에 대한 깊은 이해를 바탕으로 정확하고 신뢰할 수 있는 분석을 제공합니다.
모든 답변은 한국어로 제공하되, 전문 용어는 적절히 설명해주세요.""",
            
            "news_sentiment": """당신은 한국 경제뉴스 감정분석 전문가입니다.
한국어 뉴스 기사의 감정과 시장 영향도를 정확히 분석합니다.
긍정적, 부정적, 중립적 감정을 수치화하여 제공합니다.""",
            
            "market_insights": """당신은 한국 금융시장 인사이트 전문가입니다.
복잡한 시장 데이터를 쉽게 이해할 수 있도록 설명하며,
투자자 관점에서 실용적인 정보를 제공합니다."""
        }
    
    async def initialize(self):
        """클라이언트 초기화"""
        try:
            # 환경 변수에서 설정 로드
            await self._load_config_from_env()
            
            # OpenAI 클라이언트 생성
            client_kwargs = {
                "api_key": self.config.api_key,
                "timeout": self.config.timeout,
                "max_retries": self.config.max_retries
            }
            
            if self.config.base_url:
                client_kwargs["base_url"] = self.config.base_url
            
            if self.config.organization:
                client_kwargs["organization"] = self.config.organization
                
            if self.config.project:
                client_kwargs["project"] = self.config.project
            
            # 비동기 클라이언트
            self.client = AsyncOpenAI(**client_kwargs)
            
            # 동기 클라이언트 (필요시)
            self.sync_client = openai.OpenAI(**client_kwargs)
            
            # 연결 테스트
            await self._test_connection()
            
            logger.info("OpenAI 클라이언트가 성공적으로 초기화되었습니다.")
            
        except Exception as e:
            logger.error(f"OpenAI 클라이언트 초기화 실패: {e}")
            raise
    
    async def _load_config_from_env(self):
        """환경 변수에서 설정 로드"""
        self.config.api_key = os.getenv("OPENAI_API_KEY")
        if not self.config.api_key:
            raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        # 선택적 설정들
        if base_url := os.getenv("OPENAI_BASE_URL"):
            self.config.base_url = base_url
            
        if organization := os.getenv("OPENAI_ORGANIZATION"):
            self.config.organization = organization
            
        if project := os.getenv("OPENAI_PROJECT"):
            self.config.project = project
        
        # Azure OpenAI 설정
        if azure_endpoint := os.getenv("AZURE_OPENAI_ENDPOINT"):
            self.config.azure_endpoint = azure_endpoint
            self.config.provider = APIProvider.AZURE_OPENAI
            
        if api_version := os.getenv("AZURE_OPENAI_API_VERSION"):
            self.config.api_version = api_version
    
    async def _test_connection(self):
        """API 연결 테스트"""
        try:
            # 간단한 임베딩 요청으로 연결 테스트
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",  # 테스트용 작은 모델
                input="연결 테스트"
            )
            
            if response and response.data:
                logger.info("OpenAI API 연결 테스트 성공")
            else:
                raise Exception("API 응답이 비어있습니다.")
                
        except Exception as e:
            logger.error(f"OpenAI API 연결 테스트 실패: {e}")
            raise
    
    @backoff.on_exception(
        backoff.expo,
        (openai.RateLimitError, openai.APITimeoutError, openai.InternalServerError),
        max_tries=3,
        max_time=60
    )
    async def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt_type: str = "stock_analysis",
        **kwargs
    ) -> Dict[str, Any]:
        """채팅 완성 API 호출 (한국어 최적화)"""
        
        # 요청 전 rate limit 체크
        await self._check_rate_limit()
        
        # 기본값 설정
        if model is None:
            model = self.config.korean_model_preference["chat"]
        if temperature is None:
            temperature = self.config.default_temperature
        if max_tokens is None:
            max_tokens = self.config.default_max_tokens
        
        # 한국어 시스템 프롬프트 추가
        if messages and messages[0].get("role") != "system":
            system_prompt = self.korean_system_prompts.get(
                system_prompt_type, 
                self.korean_system_prompts["stock_analysis"]
            )
            messages = [{"role": "system", "content": system_prompt}] + messages
        
        try:
            start_time = time.time()
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            # 응답 시간 및 사용량 추적
            response_time = time.time() - start_time
            usage = response.usage
            
            # 사용량 업데이트
            self.request_count += 1
            if usage:
                self.token_usage += usage.total_tokens
            
            logger.debug(f"Chat completion 완료: {response_time:.2f}초, "
                        f"토큰 사용: {usage.total_tokens if usage else 0}")
            
            return {
                "response": response,
                "usage": usage.__dict__ if usage else {},
                "response_time": response_time,
                "model": model
            }
            
        except openai.RateLimitError as e:
            logger.warning(f"Rate limit 도달: {e}")
            # 잠시 대기 후 재시도는 backoff 데코레이터가 처리
            raise
            
        except openai.APIError as e:
            logger.error(f"OpenAI API 오류: {e}")
            raise
            
        except Exception as e:
            logger.error(f"예상치 못한 오류: {e}")
            raise
    
    @backoff.on_exception(
        backoff.expo,
        (openai.RateLimitError, openai.APITimeoutError),
        max_tries=3
    )
    async def create_embedding(
        self,
        text: Union[str, List[str]],
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """임베딩 생성 API 호출 (한국어 최적화)"""
        
        await self._check_rate_limit()
        
        if model is None:
            model = self.config.korean_model_preference["embedding"]
        
        try:
            start_time = time.time()
            
            # 한국어 텍스트 전처리 (필요시)
            if isinstance(text, str):
                text = self._preprocess_korean_text(text)
            elif isinstance(text, list):
                text = [self._preprocess_korean_text(t) for t in text]
            
            response = await self.client.embeddings.create(
                model=model,
                input=text,
                **kwargs
            )
            
            response_time = time.time() - start_time
            usage = response.usage
            
            self.request_count += 1
            if usage:
                self.token_usage += usage.total_tokens
            
            logger.debug(f"Embedding 생성 완료: {response_time:.2f}초, "
                        f"토큰 사용: {usage.total_tokens if usage else 0}")
            
            return {
                "response": response,
                "usage": usage.__dict__ if usage else {},
                "response_time": response_time,
                "model": model
            }
            
        except Exception as e:
            logger.error(f"Embedding 생성 실패: {e}")
            raise
    
    def _preprocess_korean_text(self, text: str) -> str:
        """한국어 텍스트 전처리"""
        if not text or not isinstance(text, str):
            return text
        
        # 기본 정리
        text = text.strip()
        
        # 연속된 공백 제거
        import re
        text = re.sub(r'\s+', ' ', text)
        
        # 불필요한 특수문자 정리 (한국어 특성 고려)
        # 한글, 영문, 숫자, 기본 문장부호만 유지
        text = re.sub(r'[^\w\s가-힣.,!?;:()\-\[\]{}"\'/]', ' ', text)
        
        # 다시 공백 정리
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    async def _check_rate_limit(self):
        """Rate limit 체크 및 대기"""
        current_time = datetime.now()
        
        # 1분 window에서의 요청 수 체크
        if (current_time - self.last_request_time) < self.rate_limit_window:
            if self.request_count >= self.config.rate_limit_rpm:
                sleep_time = (self.rate_limit_window - 
                            (current_time - self.last_request_time)).total_seconds()
                logger.warning(f"Rate limit 도달. {sleep_time:.1f}초 대기...")
                await asyncio.sleep(sleep_time)
                self.request_count = 0
                self.token_usage = 0
                self.last_request_time = datetime.now()
        else:
            # 새로운 1분 window 시작
            self.request_count = 0
            self.token_usage = 0
            self.last_request_time = current_time
    
    async def get_available_models(self) -> List[str]:
        """사용 가능한 모델 목록 조회"""
        try:
            models = await self.client.models.list()
            return [model.id for model in models.data]
        except Exception as e:
            logger.error(f"모델 목록 조회 실패: {e}")
            return []
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """API 사용 통계 반환"""
        return {
            "request_count": self.request_count,
            "token_usage": self.token_usage,
            "last_request_time": self.last_request_time.isoformat(),
            "rate_limit_rpm": self.config.rate_limit_rpm,
            "rate_limit_tpm": self.config.rate_limit_tpm
        }
    
    async def validate_api_key(self) -> bool:
        """API 키 유효성 검증"""
        try:
            await self._test_connection()
            return True
        except Exception as e:
            logger.error(f"API 키 검증 실패: {e}")
            return False
    
    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """요청 비용 추정 (USD 기준)"""
        # 2024년 1월 기준 OpenAI 가격 (참고용)
        pricing = {
            "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},  # per 1K tokens
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},
            "text-embedding-3-large": {"input": 0.00013, "output": 0},
            "text-embedding-3-small": {"input": 0.00002, "output": 0}
        }
        
        if model not in pricing:
            logger.warning(f"모델 {model}의 가격 정보가 없습니다. 기본값 사용.")
            return (input_tokens + output_tokens) * 0.001 / 1000
        
        model_pricing = pricing[model]
        input_cost = (input_tokens / 1000) * model_pricing["input"]
        output_cost = (output_tokens / 1000) * model_pricing["output"]
        
        return input_cost + output_cost
    
    async def shutdown(self):
        """클라이언트 정리"""
        if self.client:
            await self.client.close()
        
        logger.info("OpenAI 클라이언트가 종료되었습니다.")

# 글로벌 클라이언트 인스턴스
_openai_client_manager: Optional[OpenAIClientManager] = None

async def get_openai_client() -> OpenAIClientManager:
    """OpenAI 클라이언트 매니저 반환"""
    global _openai_client_manager
    
    if _openai_client_manager is None:
        config = APIConfiguration()
        _openai_client_manager = OpenAIClientManager(config)
        await _openai_client_manager.initialize()
    
    return _openai_client_manager

async def initialize_openai_client(config: Optional[APIConfiguration] = None) -> OpenAIClientManager:
    """OpenAI 클라이언트 초기화"""
    global _openai_client_manager
    
    if config is None:
        config = APIConfiguration()
    
    _openai_client_manager = OpenAIClientManager(config)
    await _openai_client_manager.initialize()
    
    return _openai_client_manager

# 편의 함수들
async def create_korean_chat_completion(
    messages: List[Dict[str, str]],
    model: str = "gpt-4-turbo-preview",
    temperature: float = 0.3
) -> str:
    """한국어 채팅 완성 간편 함수"""
    client = await get_openai_client()
    result = await client.create_chat_completion(
        messages=messages,
        model=model,
        temperature=temperature,
        system_prompt_type="stock_analysis"
    )
    
    return result["response"].choices[0].message.content

async def create_korean_embedding(text: str) -> List[float]:
    """한국어 임베딩 생성 간편 함수"""
    client = await get_openai_client()
    result = await client.create_embedding(text)
    
    return result["response"].data[0].embedding

# 사용 예시
async def example_usage():
    """사용 예시"""
    try:
        # 클라이언트 초기화
        client = await initialize_openai_client()
        
        # 한국어 주식 분석 요청
        messages = [
            {"role": "user", "content": "삼성전자의 최근 실적에 대해 분석해주세요."}
        ]
        
        result = await client.create_chat_completion(
            messages=messages,
            system_prompt_type="stock_analysis"
        )
        
        print(f"분석 결과: {result['response'].choices[0].message.content}")
        print(f"사용 토큰: {result['usage']['total_tokens']}")
        print(f"응답 시간: {result['response_time']:.2f}초")
        
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    # 테스트 실행
    asyncio.run(example_usage())