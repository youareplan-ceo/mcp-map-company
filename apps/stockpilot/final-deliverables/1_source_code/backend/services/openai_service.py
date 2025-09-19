#!/usr/bin/env python3
"""
StockPilot AI OpenAI GPT API 연동 서비스
작성자: StockPilot Team
용도: GPT API 키 관리, 비용 모니터링, 에러 핸들링, 응답 최적화
"""

import asyncio
import json
import time
import aiohttp
import openai
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import logging
import aioredis
import os
from dataclasses import dataclass, asdict, field
from enum import Enum
import hashlib
import tiktoken
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/openai_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GPTModel(Enum):
    """GPT 모델 정의"""
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    GPT_3_5_TURBO_16K = "gpt-3.5-turbo-16k"
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-turbo-preview"
    GPT_4_32K = "gpt-4-32k"

class RequestType(Enum):
    """요청 유형 정의"""
    INVESTMENT_ANALYSIS = "investment_analysis"
    PORTFOLIO_ADVICE = "portfolio_advice"
    MARKET_SUMMARY = "market_summary"
    RISK_ASSESSMENT = "risk_assessment"
    NEWS_ANALYSIS = "news_analysis"
    GENERAL_CHAT = "general_chat"

@dataclass
class APIUsageMetrics:
    """API 사용량 메트릭"""
    timestamp: datetime
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    request_type: str
    response_time: float
    success: bool
    user_id: Optional[str] = None

@dataclass
class GPTRequest:
    """GPT 요청 데이터 클래스"""
    id: str
    user_id: str
    request_type: RequestType
    model: GPTModel
    messages: List[Dict[str, str]]
    max_tokens: Optional[int] = None
    temperature: float = 0.7
    system_prompt: Optional[str] = None
    context_data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class GPTResponse:
    """GPT 응답 데이터 클래스"""
    request_id: str
    content: str
    model: str
    usage: Dict[str, int]
    cost_usd: float
    response_time: float
    created_at: datetime = field(default_factory=datetime.now)
    finish_reason: Optional[str] = None

class OpenAIService:
    """OpenAI GPT API 서비스 클래스"""
    
    def __init__(self, config_file: str = "/app/config/openai.json"):
        self.config_file = config_file
        self.config = self._load_config()
        self.redis_client = None
        self.usage_metrics: List[APIUsageMetrics] = []
        
        # OpenAI 클라이언트 초기화
        self.api_keys = self.config.get('api_keys', [])
        self.current_key_index = 0
        self._initialize_openai_client()
        
        # 토크나이저 초기화
        self.tokenizers = {}
        self._initialize_tokenizers()
        
        # 비용 계산 테이블
        self.pricing = self._get_pricing_table()
        
        # 사용량 제한
        self.limits = self.config.get('limits', {
            'daily_cost_limit': 100.0,  # USD
            'hourly_request_limit': 1000,
            'monthly_cost_limit': 1000.0
        })
    
    def _load_config(self) -> Dict[str, Any]:
        """설정 파일 로드"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return self._get_default_config()
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        return {
            "api_keys": [
                os.getenv('OPENAI_API_KEY', ''),
                os.getenv('OPENAI_API_KEY_2', ''),
                os.getenv('OPENAI_API_KEY_3', '')
            ],
            "default_model": "gpt-3.5-turbo",
            "max_tokens": 2000,
            "temperature": 0.7,
            "limits": {
                "daily_cost_limit": 50.0,
                "hourly_request_limit": 500,
                "monthly_cost_limit": 500.0
            },
            "redis": {
                "host": os.getenv('REDIS_HOST', 'localhost'),
                "port": int(os.getenv('REDIS_PORT', 6379)),
                "password": os.getenv('REDIS_PASSWORD', '')
            },
            "monitoring": {
                "enabled": True,
                "cost_alerts": True,
                "usage_logging": True
            }
        }
    
    def _initialize_openai_client(self):
        """OpenAI 클라이언트 초기화"""
        # API 키 검증 및 설정
        valid_keys = [key for key in self.api_keys if key and key.strip()]
        
        if not valid_keys:
            logger.error("유효한 OpenAI API 키가 없습니다.")
            raise ValueError("OpenAI API 키가 필요합니다.")
        
        self.api_keys = valid_keys
        openai.api_key = self.api_keys[0]
        logger.info(f"{len(self.api_keys)}개의 API 키 로드됨")
    
    def _initialize_tokenizers(self):
        """토크나이저 초기화"""
        try:
            self.tokenizers = {
                "gpt-3.5-turbo": tiktoken.encoding_for_model("gpt-3.5-turbo"),
                "gpt-4": tiktoken.encoding_for_model("gpt-4")
            }
            logger.info("토크나이저 초기화 완료")
        except Exception as e:
            logger.error(f"토크나이저 초기화 실패: {e}")
    
    def _get_pricing_table(self) -> Dict[str, Dict[str, float]]:
        """모델별 가격표 (2024년 기준)"""
        return {
            "gpt-3.5-turbo": {
                "input": 0.0010,   # per 1K tokens
                "output": 0.0020
            },
            "gpt-3.5-turbo-16k": {
                "input": 0.0030,
                "output": 0.0040
            },
            "gpt-4": {
                "input": 0.0300,
                "output": 0.0600
            },
            "gpt-4-turbo-preview": {
                "input": 0.0100,
                "output": 0.0300
            },
            "gpt-4-32k": {
                "input": 0.0600,
                "output": 0.1200
            }
        }
    
    async def initialize(self):
        """서비스 초기화"""
        try:
            # Redis 연결
            redis_config = self.config.get('redis', {})
            redis_url = f"redis://:{redis_config.get('password')}@{redis_config.get('host', 'localhost')}:{redis_config.get('port', 6379)}/2"
            self.redis_client = await aioredis.from_url(redis_url)
            
            # API 키 유효성 검증
            await self._validate_api_keys()
            
            logger.info("OpenAI 서비스 초기화 완료")
            
        except Exception as e:
            logger.error(f"OpenAI 서비스 초기화 실패: {e}")
            raise
    
    async def _validate_api_keys(self):
        """API 키 유효성 검증"""
        valid_keys = []
        
        for i, api_key in enumerate(self.api_keys):
            try:
                # 간단한 API 호출로 키 검증
                openai.api_key = api_key
                
                response = await openai.ChatCompletion.acreate(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=5
                )
                
                valid_keys.append(api_key)
                logger.info(f"API 키 #{i+1} 검증 성공")
                
            except Exception as e:
                logger.warning(f"API 키 #{i+1} 검증 실패: {e}")
        
        if not valid_keys:
            raise ValueError("사용 가능한 API 키가 없습니다.")
        
        self.api_keys = valid_keys
        openai.api_key = self.api_keys[0]
        logger.info(f"{len(valid_keys)}개의 유효한 API 키 확인됨")
    
    def _rotate_api_key(self):
        """API 키 로테이션"""
        if len(self.api_keys) > 1:
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            openai.api_key = self.api_keys[self.current_key_index]
            logger.info(f"API 키 로테이션: #{self.current_key_index + 1}")
    
    def count_tokens(self, text: str, model: str = "gpt-3.5-turbo") -> int:
        """토큰 수 계산"""
        try:
            if model in self.tokenizers:
                tokenizer = self.tokenizers[model]
                return len(tokenizer.encode(text))
            else:
                # 대략적인 계산 (1 토큰 ≈ 4글자)
                return len(text) // 4
        except Exception as e:
            logger.error(f"토큰 계산 실패: {e}")
            return len(text) // 4
    
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        """비용 예상 계산"""
        try:
            if model in self.pricing:
                pricing = self.pricing[model]
                input_cost = (prompt_tokens / 1000) * pricing["input"]
                output_cost = (completion_tokens / 1000) * pricing["output"]
                return round(input_cost + output_cost, 6)
            else:
                # 기본값으로 gpt-3.5-turbo 가격 사용
                pricing = self.pricing["gpt-3.5-turbo"]
                input_cost = (prompt_tokens / 1000) * pricing["input"]
                output_cost = (completion_tokens / 1000) * pricing["output"]
                return round(input_cost + output_cost, 6)
        except Exception as e:
            logger.error(f"비용 계산 실패: {e}")
            return 0.0
    
    async def check_usage_limits(self, user_id: str, estimated_cost: float) -> bool:
        """사용량 제한 체크"""
        try:
            # 일일 비용 제한 체크
            daily_usage = await self._get_daily_usage(user_id)
            if daily_usage + estimated_cost > self.limits['daily_cost_limit']:
                logger.warning(f"일일 비용 제한 초과: {user_id}")
                return False
            
            # 시간당 요청 제한 체크
            hourly_requests = await self._get_hourly_requests(user_id)
            if hourly_requests >= self.limits['hourly_request_limit']:
                logger.warning(f"시간당 요청 제한 초과: {user_id}")
                return False
            
            # 월간 비용 제한 체크
            monthly_usage = await self._get_monthly_usage(user_id)
            if monthly_usage + estimated_cost > self.limits['monthly_cost_limit']:
                logger.warning(f"월간 비용 제한 초과: {user_id}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"사용량 제한 체크 실패: {e}")
            return True  # 에러 시 허용
    
    async def _get_daily_usage(self, user_id: str) -> float:
        """일일 사용량 조회"""
        try:
            if not self.redis_client:
                return 0.0
            
            today = datetime.now().strftime('%Y-%m-%d')
            key = f"usage:daily:{user_id}:{today}"
            usage = await self.redis_client.get(key)
            return float(usage) if usage else 0.0
            
        except Exception as e:
            logger.error(f"일일 사용량 조회 실패: {e}")
            return 0.0
    
    async def _get_hourly_requests(self, user_id: str) -> int:
        """시간당 요청 수 조회"""
        try:
            if not self.redis_client:
                return 0
            
            current_hour = datetime.now().strftime('%Y-%m-%d:%H')
            key = f"requests:hourly:{user_id}:{current_hour}"
            requests = await self.redis_client.get(key)
            return int(requests) if requests else 0
            
        except Exception as e:
            logger.error(f"시간당 요청 수 조회 실패: {e}")
            return 0
    
    async def _get_monthly_usage(self, user_id: str) -> float:
        """월간 사용량 조회"""
        try:
            if not self.redis_client:
                return 0.0
            
            current_month = datetime.now().strftime('%Y-%m')
            key = f"usage:monthly:{user_id}:{current_month}"
            usage = await self.redis_client.get(key)
            return float(usage) if usage else 0.0
            
        except Exception as e:
            logger.error(f"월간 사용량 조회 실패: {e}")
            return 0.0
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((openai.error.RateLimitError, openai.error.APIError))
    )
    async def _make_openai_request(self, request: GPTRequest) -> GPTResponse:
        """OpenAI API 요청 실행 (재시도 로직 포함)"""
        start_time = time.time()
        
        try:
            # 시스템 프롬프트 추가
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.extend(request.messages)
            
            # API 호출
            response = await openai.ChatCompletion.acreate(
                model=request.model.value,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                user=request.user_id
            )
            
            response_time = time.time() - start_time
            
            # 응답 처리
            choice = response.choices[0]
            usage = response.usage
            
            # 비용 계산
            cost = self.estimate_cost(
                usage.prompt_tokens,
                usage.completion_tokens,
                request.model.value
            )
            
            return GPTResponse(
                request_id=request.id,
                content=choice.message.content,
                model=response.model,
                usage=usage.to_dict(),
                cost_usd=cost,
                response_time=response_time,
                finish_reason=choice.finish_reason
            )
            
        except openai.error.RateLimitError as e:
            logger.warning(f"Rate limit 에러, API 키 로테이션: {e}")
            self._rotate_api_key()
            raise
        except openai.error.InvalidRequestError as e:
            logger.error(f"잘못된 요청: {e}")
            raise ValueError(f"잘못된 요청: {e}")
        except Exception as e:
            logger.error(f"OpenAI API 요청 실패: {e}")
            raise
    
    async def process_request(self, request: GPTRequest) -> GPTResponse:
        """GPT 요청 처리"""
        try:
            # 토큰 수 계산
            messages_text = " ".join([msg["content"] for msg in request.messages])
            if request.system_prompt:
                messages_text = request.system_prompt + " " + messages_text
            
            prompt_tokens = self.count_tokens(messages_text, request.model.value)
            estimated_tokens = request.max_tokens or 1000
            
            # 비용 예상
            estimated_cost = self.estimate_cost(prompt_tokens, estimated_tokens, request.model.value)
            
            # 사용량 제한 체크
            if not await self.check_usage_limits(request.user_id, estimated_cost):
                raise ValueError("사용량 제한 초과")
            
            # API 요청 실행
            response = await self._make_openai_request(request)
            
            # 사용량 기록
            await self._record_usage(request, response)
            
            logger.info(f"GPT 요청 처리 완료: {request.id} (비용: ${response.cost_usd:.6f})")
            return response
            
        except Exception as e:
            logger.error(f"GPT 요청 처리 실패: {request.id}: {e}")
            
            # 실패 기록
            await self._record_failure(request, str(e))
            raise
    
    async def _record_usage(self, request: GPTRequest, response: GPTResponse):
        """사용량 기록"""
        try:
            # 메트릭 생성
            usage = response.usage
            metric = APIUsageMetrics(
                timestamp=datetime.now(),
                model=response.model,
                prompt_tokens=usage['prompt_tokens'],
                completion_tokens=usage['completion_tokens'],
                total_tokens=usage['total_tokens'],
                cost_usd=response.cost_usd,
                request_type=request.request_type.value,
                response_time=response.response_time,
                success=True,
                user_id=request.user_id
            )
            
            self.usage_metrics.append(metric)
            
            if self.redis_client:
                # 일일 사용량 업데이트
                today = datetime.now().strftime('%Y-%m-%d')
                daily_key = f"usage:daily:{request.user_id}:{today}"
                await self.redis_client.incrbyfloat(daily_key, response.cost_usd)
                await self.redis_client.expire(daily_key, 86400 * 2)  # 2일 후 만료
                
                # 시간당 요청 수 업데이트
                current_hour = datetime.now().strftime('%Y-%m-%d:%H')
                hourly_key = f"requests:hourly:{request.user_id}:{current_hour}"
                await self.redis_client.incr(hourly_key)
                await self.redis_client.expire(hourly_key, 3600 * 2)  # 2시간 후 만료
                
                # 월간 사용량 업데이트
                current_month = datetime.now().strftime('%Y-%m')
                monthly_key = f"usage:monthly:{request.user_id}:{current_month}"
                await self.redis_client.incrbyfloat(monthly_key, response.cost_usd)
                
                # 상세 로그 저장
                log_data = asdict(metric)
                await self.redis_client.lpush(
                    'openai_usage_logs',
                    json.dumps(log_data, default=str)
                )
                await self.redis_client.ltrim('openai_usage_logs', 0, 9999)  # 최근 10k개 유지
            
        except Exception as e:
            logger.error(f"사용량 기록 실패: {e}")
    
    async def _record_failure(self, request: GPTRequest, error_message: str):
        """실패 기록"""
        try:
            if self.redis_client:
                failure_data = {
                    'request_id': request.id,
                    'user_id': request.user_id,
                    'model': request.model.value,
                    'request_type': request.request_type.value,
                    'error': error_message,
                    'timestamp': datetime.now().isoformat()
                }
                
                await self.redis_client.lpush(
                    'openai_failures',
                    json.dumps(failure_data)
                )
                await self.redis_client.ltrim('openai_failures', 0, 999)  # 최근 1k개 유지
        
        except Exception as e:
            logger.error(f"실패 기록 실패: {e}")
    
    def get_system_prompts(self) -> Dict[str, str]:
        """요청 유형별 시스템 프롬프트"""
        return {
            RequestType.INVESTMENT_ANALYSIS.value: """
당신은 전문적인 주식 투자 분석가입니다. 
- 객관적이고 데이터 기반의 분석을 제공합니다
- 투자 위험성을 명확히 고지합니다
- 재무 지표, 기술적 분석, 시장 동향을 종합적으로 고려합니다
- 한국어로 명확하고 이해하기 쉽게 설명합니다
- 투자 결정은 사용자의 책임임을 항상 강조합니다
            """.strip(),
            
            RequestType.PORTFOLIO_ADVICE.value: """
당신은 포트폴리오 관리 전문가입니다.
- 분산투자의 중요성을 강조합니다
- 개인의 투자 성향과 목표를 고려합니다
- 위험 관리 방법을 구체적으로 제시합니다
- 장기적 관점에서의 투자 전략을 제안합니다
- 투자는 본인의 판단과 책임 하에 이루어져야 함을 명시합니다
            """.strip(),
            
            RequestType.MARKET_SUMMARY.value: """
당신은 금융 시장 분석 전문가입니다.
- 시장의 주요 동향과 이슈를 정리합니다
- 경제 지표와 뉴스의 영향을 분석합니다
- 섹터별, 지역별 시장 상황을 종합합니다
- 중립적이고 객관적인 관점을 유지합니다
- 예측은 불확실성이 있음을 항상 언급합니다
            """.strip(),
            
            RequestType.RISK_ASSESSMENT.value: """
당신은 투자 위험 평가 전문가입니다.
- 다양한 위험 요소를 체계적으로 분석합니다
- 위험도를 명확한 기준으로 평가합니다
- 위험 완화 방안을 구체적으로 제시합니다
- 투자자의 위험 허용도를 고려합니다
- 모든 투자에는 손실 가능성이 있음을 강조합니다
            """.strip(),
            
            RequestType.NEWS_ANALYSIS.value: """
당신은 금융 뉴스 분석 전문가입니다.
- 뉴스의 시장 영향을 객관적으로 분석합니다
- 팩트와 추측을 명확히 구분합니다
- 단기 및 장기적 영향을 분석합니다
- 다양한 관점을 제시합니다
- 뉴스 해석의 한계를 인정합니다
            """.strip(),
            
            RequestType.GENERAL_CHAT.value: """
당신은 친근하고 도움이 되는 AI 투자 도우미입니다.
- 투자 관련 질문에 정확하고 유용한 답변을 제공합니다
- 복잡한 금융 개념을 쉽게 설명합니다
- 항상 정중하고 친근한 톤을 유지합니다
- 투자 결정은 개인의 책임임을 항상 상기시킵니다
- 확실하지 않은 정보는 추가 확인을 권합니다
            """.strip()
        }
    
    async def create_investment_analysis(self, user_id: str, stock_symbol: str, 
                                       market_data: Dict[str, Any], 
                                       news_data: List[Dict[str, Any]]) -> GPTResponse:
        """투자 분석 생성"""
        try:
            # 요청 데이터 준비
            context = f"""
종목: {stock_symbol}
현재가: {market_data.get('price', 'N/A')}
등락률: {market_data.get('change_percent', 'N/A')}%
거래량: {market_data.get('volume', 'N/A')}
시가총액: {market_data.get('market_cap', 'N/A')}

최근 뉴스:
"""
            for i, news in enumerate(news_data[:3], 1):
                context += f"{i}. {news.get('title', '')}\n"
            
            request = GPTRequest(
                id=f"analysis_{user_id}_{int(time.time())}",
                user_id=user_id,
                request_type=RequestType.INVESTMENT_ANALYSIS,
                model=GPTModel.GPT_3_5_TURBO,
                messages=[{
                    "role": "user",
                    "content": f"{context}\n\n위 정보를 바탕으로 {stock_symbol}에 대한 투자 분석을 해주세요."
                }],
                max_tokens=1500,
                temperature=0.7,
                system_prompt=self.get_system_prompts()[RequestType.INVESTMENT_ANALYSIS.value],
                context_data={"stock_symbol": stock_symbol, "market_data": market_data}
            )
            
            return await self.process_request(request)
            
        except Exception as e:
            logger.error(f"투자 분석 생성 실패: {e}")
            raise
    
    async def get_usage_statistics(self, user_id: Optional[str] = None, 
                                 days: int = 7) -> Dict[str, Any]:
        """사용량 통계 조회"""
        try:
            # 최근 N일간의 메트릭 필터링
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_metrics = [
                m for m in self.usage_metrics 
                if m.timestamp > cutoff_date and (not user_id or m.user_id == user_id)
            ]
            
            if not recent_metrics:
                return {"message": "사용량 데이터가 없습니다."}
            
            # 통계 계산
            total_requests = len(recent_metrics)
            total_cost = sum(m.cost_usd for m in recent_metrics)
            total_tokens = sum(m.total_tokens for m in recent_metrics)
            avg_response_time = sum(m.response_time for m in recent_metrics) / total_requests
            
            # 모델별 통계
            model_stats = {}
            for metric in recent_metrics:
                model = metric.model
                if model not in model_stats:
                    model_stats[model] = {
                        'requests': 0,
                        'cost': 0.0,
                        'tokens': 0
                    }
                model_stats[model]['requests'] += 1
                model_stats[model]['cost'] += metric.cost_usd
                model_stats[model]['tokens'] += metric.total_tokens
            
            # 요청 유형별 통계
            type_stats = {}
            for metric in recent_metrics:
                req_type = metric.request_type
                if req_type not in type_stats:
                    type_stats[req_type] = {
                        'requests': 0,
                        'cost': 0.0
                    }
                type_stats[req_type]['requests'] += 1
                type_stats[req_type]['cost'] += metric.cost_usd
            
            return {
                'period_days': days,
                'user_id': user_id,
                'summary': {
                    'total_requests': total_requests,
                    'total_cost_usd': round(total_cost, 6),
                    'total_tokens': total_tokens,
                    'avg_response_time': round(avg_response_time, 3)
                },
                'by_model': model_stats,
                'by_type': type_stats,
                'daily_breakdown': self._get_daily_breakdown(recent_metrics)
            }
            
        except Exception as e:
            logger.error(f"사용량 통계 조회 실패: {e}")
            return {"error": str(e)}
    
    def _get_daily_breakdown(self, metrics: List[APIUsageMetrics]) -> Dict[str, Dict[str, float]]:
        """일별 사용량 분석"""
        daily_stats = {}
        
        for metric in metrics:
            date_str = metric.timestamp.strftime('%Y-%m-%d')
            if date_str not in daily_stats:
                daily_stats[date_str] = {
                    'requests': 0,
                    'cost': 0.0,
                    'tokens': 0
                }
            
            daily_stats[date_str]['requests'] += 1
            daily_stats[date_str]['cost'] += metric.cost_usd
            daily_stats[date_str]['tokens'] += metric.total_tokens
        
        return daily_stats
    
    async def check_api_health(self) -> Dict[str, Any]:
        """API 상태 체크"""
        try:
            test_request = GPTRequest(
                id=f"health_check_{int(time.time())}",
                user_id="system",
                request_type=RequestType.GENERAL_CHAT,
                model=GPTModel.GPT_3_5_TURBO,
                messages=[{"role": "user", "content": "Hello, this is a health check."}],
                max_tokens=10,
                temperature=0.1
            )
            
            response = await self._make_openai_request(test_request)
            
            return {
                'status': 'healthy',
                'response_time': response.response_time,
                'model': response.model,
                'api_keys_count': len(self.api_keys),
                'current_key_index': self.current_key_index
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'api_keys_count': len(self.api_keys),
                'current_key_index': self.current_key_index
            }

async def main():
    """메인 실행 함수"""
    try:
        # 설정 디렉토리 생성
        os.makedirs('/app/config', exist_ok=True)
        os.makedirs('/app/logs', exist_ok=True)
        
        # OpenAI 서비스 초기화
        openai_service = OpenAIService()
        await openai_service.initialize()
        
        # 상태 체크
        health = await openai_service.check_api_health()
        logger.info(f"API 상태: {health}")
        
        # 테스트 투자 분석
        market_data = {
            'price': 75000,
            'change_percent': 2.5,
            'volume': 1000000,
            'market_cap': '450조원'
        }
        
        news_data = [
            {'title': '삼성전자, 3분기 실적 호조 전망'},
            {'title': 'AI 칩 시장 성장으로 반도체 업계 수혜'},
            {'title': '글로벌 메모리 시장 회복 신호'}
        ]
        
        response = await openai_service.create_investment_analysis(
            user_id="test_user",
            stock_symbol="삼성전자",
            market_data=market_data,
            news_data=news_data
        )
        
        logger.info(f"투자 분석 결과: {response.content[:200]}...")
        logger.info(f"비용: ${response.cost_usd:.6f}")
        
        # 사용량 통계
        stats = await openai_service.get_usage_statistics("test_user")
        logger.info(f"사용량 통계: {stats}")
        
    except Exception as e:
        logger.error(f"OpenAI 서비스 테스트 실패: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())