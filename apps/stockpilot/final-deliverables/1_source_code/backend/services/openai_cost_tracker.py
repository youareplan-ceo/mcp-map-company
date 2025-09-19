#!/usr/bin/env python3
"""
OpenAI API 비용 추적 통합 모듈
모든 OpenAI API 호출에 대한 자동 비용 추적 및 최적화
"""

import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from functools import wraps
import openai
from openai import AsyncOpenAI

from services.cost_dashboard import track_openai_cost

# 로깅 설정
logger = logging.getLogger(__name__)

# OpenAI 모델별 비용 정보 (USD per 1K tokens)
OPENAI_PRICING = {
    "gpt-4": {
        "input": 0.03,
        "output": 0.06
    },
    "gpt-4-turbo": {
        "input": 0.01,
        "output": 0.03
    },
    "gpt-4-turbo-preview": {
        "input": 0.01,
        "output": 0.03
    },
    "gpt-4o": {
        "input": 0.005,
        "output": 0.015
    },
    "gpt-4o-mini": {
        "input": 0.00015,
        "output": 0.0006
    },
    "gpt-3.5-turbo": {
        "input": 0.0015,
        "output": 0.002
    },
    "gpt-3.5-turbo-instruct": {
        "input": 0.0015,
        "output": 0.002
    },
    "text-embedding-ada-002": {
        "input": 0.0001,
        "output": 0.0001
    },
    "text-embedding-3-small": {
        "input": 0.00002,
        "output": 0.00002
    },
    "text-embedding-3-large": {
        "input": 0.00013,
        "output": 0.00013
    },
    "whisper-1": {
        "input": 0.006,  # per minute
        "output": 0.006
    },
    "tts-1": {
        "input": 0.015,  # per 1K characters
        "output": 0.015
    },
    "tts-1-hd": {
        "input": 0.03,  # per 1K characters
        "output": 0.03
    },
    "dall-e-2": {
        "1024x1024": 0.020,
        "512x512": 0.018,
        "256x256": 0.016
    },
    "dall-e-3": {
        "standard_1024x1024": 0.040,
        "standard_1792x1024": 0.080,
        "hd_1024x1024": 0.080,
        "hd_1792x1024": 0.120
    }
}

class OpenAICostTracker:
    """OpenAI API 비용 추적기"""
    
    def __init__(self, channel: str = "default", country: str = "KR"):
        self.channel = channel
        self.country = country
        self.session_stats = {
            "total_calls": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "start_time": datetime.now()
        }

    def calculate_cost(self, model: str, usage: Dict[str, Any], request_type: str = "chat") -> float:
        """모델과 사용량을 기반으로 비용 계산"""
        try:
            # 모델명 정규화
            normalized_model = self._normalize_model_name(model)
            
            if normalized_model not in OPENAI_PRICING:
                logger.warning(f"알 수 없는 모델: {model}, 기본 비용 적용")
                return 0.001  # 기본 비용
            
            pricing = OPENAI_PRICING[normalized_model]
            total_cost = 0.0
            
            if request_type == "chat" or request_type == "completion":
                # 텍스트 생성 API 비용 계산
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                
                total_cost += (input_tokens / 1000) * pricing["input"]
                total_cost += (output_tokens / 1000) * pricing["output"]
                
            elif request_type == "embedding":
                # 임베딩 API 비용 계산
                total_tokens = usage.get("total_tokens", 0)
                total_cost += (total_tokens / 1000) * pricing["input"]
                
            elif request_type == "audio":
                # 오디오 API 비용 계산 (분 단위)
                duration = usage.get("duration", 0)  # 초 단위
                minutes = duration / 60
                total_cost += minutes * pricing["input"]
                
            elif request_type == "image":
                # 이미지 생성 API 비용 계산
                size = usage.get("size", "1024x1024")
                quality = usage.get("quality", "standard")
                
                cost_key = f"{quality}_{size}" if quality in ["hd"] else size
                if cost_key in pricing:
                    total_cost += pricing[cost_key]
                else:
                    total_cost += pricing.get("1024x1024", 0.02)
            
            return round(total_cost, 6)
            
        except Exception as e:
            logger.error(f"비용 계산 오류: {e}")
            return 0.001

    def _normalize_model_name(self, model: str) -> str:
        """모델명 정규화"""
        # 모델명에서 날짜나 버전 정보 제거
        model_lower = model.lower()
        
        if "gpt-4o-mini" in model_lower:
            return "gpt-4o-mini"
        elif "gpt-4o" in model_lower:
            return "gpt-4o"
        elif "gpt-4-turbo" in model_lower:
            return "gpt-4-turbo"
        elif "gpt-4" in model_lower:
            return "gpt-4"
        elif "gpt-3.5-turbo-instruct" in model_lower:
            return "gpt-3.5-turbo-instruct"
        elif "gpt-3.5-turbo" in model_lower:
            return "gpt-3.5-turbo"
        elif "text-embedding-3-large" in model_lower:
            return "text-embedding-3-large"
        elif "text-embedding-3-small" in model_lower:
            return "text-embedding-3-small"
        elif "text-embedding-ada-002" in model_lower:
            return "text-embedding-ada-002"
        elif "whisper" in model_lower:
            return "whisper-1"
        elif "tts-1-hd" in model_lower:
            return "tts-1-hd"
        elif "tts-1" in model_lower:
            return "tts-1"
        elif "dall-e-3" in model_lower:
            return "dall-e-3"
        elif "dall-e-2" in model_lower:
            return "dall-e-2"
        else:
            return model

    async def track_api_call(self, model: str, usage: Dict[str, Any], 
                           response_time_ms: int, request_type: str = "chat",
                           user_id: Optional[str] = None, session_id: Optional[str] = None):
        """API 호출 추적"""
        try:
            # 비용 계산
            cost = self.calculate_cost(model, usage, request_type)
            
            # 토큰 수 집계
            if request_type in ["chat", "completion"]:
                token_count = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
            elif request_type == "embedding":
                token_count = usage.get("total_tokens", 0)
            else:
                token_count = 0
            
            # 세션 통계 업데이트
            self.session_stats["total_calls"] += 1
            self.session_stats["total_tokens"] += token_count
            self.session_stats["total_cost"] += cost
            
            # 비용 추적 시스템에 전송
            alerts = await track_openai_cost(
                model=model,
                channel=self.channel,
                country=self.country,
                call_count=1,
                token_count=token_count,
                cost_usd=cost,
                response_time_ms=response_time_ms,
                user_id=user_id,
                session_id=session_id
            )
            
            # 경고가 있으면 로깅
            if alerts:
                for alert in alerts:
                    logger.warning(f"비용 알림: {alert.level.value.upper()} - {alert.message}")
            
            logger.info(f"OpenAI API 호출 추적: {model} | 비용: ${cost:.6f} | 토큰: {token_count}")
            
        except Exception as e:
            logger.error(f"API 호출 추적 오류: {e}")

    def get_session_stats(self) -> Dict[str, Any]:
        """세션 통계 조회"""
        duration = datetime.now() - self.session_stats["start_time"]
        
        return {
            **self.session_stats,
            "session_duration_minutes": duration.total_seconds() / 60,
            "average_cost_per_call": self.session_stats["total_cost"] / max(self.session_stats["total_calls"], 1),
            "average_cost_per_token": self.session_stats["total_cost"] / max(self.session_stats["total_tokens"], 1)
        }

# 전역 비용 추적기 인스턴스
_cost_tracker_instances = {}

def get_cost_tracker(channel: str = "default", country: str = "KR") -> OpenAICostTracker:
    """비용 추적기 인스턴스 가져오기"""
    key = f"{channel}_{country}"
    if key not in _cost_tracker_instances:
        _cost_tracker_instances[key] = OpenAICostTracker(channel, country)
    return _cost_tracker_instances[key]

def track_openai_call(channel: str = "default", country: str = "KR", 
                     user_id: Optional[str] = None, session_id: Optional[str] = None):
    """OpenAI API 호출 추적 데코레이터"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            tracker = get_cost_tracker(channel, country)
            
            try:
                # API 호출 실행
                result = await func(*args, **kwargs)
                
                # 응답 시간 계산
                response_time_ms = int((time.time() - start_time) * 1000)
                
                # 결과에서 모델과 사용량 정보 추출
                model = getattr(result, 'model', kwargs.get('model', 'unknown'))
                usage = getattr(result, 'usage', {})
                
                if hasattr(usage, 'model_dump'):
                    usage = usage.model_dump()
                elif hasattr(usage, '__dict__'):
                    usage = usage.__dict__
                
                # 요청 타입 추측
                request_type = "chat"
                if "embedding" in func.__name__.lower():
                    request_type = "embedding"
                elif "audio" in func.__name__.lower() or "speech" in func.__name__.lower():
                    request_type = "audio"
                elif "image" in func.__name__.lower():
                    request_type = "image"
                
                # 비용 추적
                await tracker.track_api_call(
                    model=model,
                    usage=usage,
                    response_time_ms=response_time_ms,
                    request_type=request_type,
                    user_id=user_id,
                    session_id=session_id
                )
                
                return result
                
            except Exception as e:
                # 에러가 발생해도 응답 시간은 기록
                response_time_ms = int((time.time() - start_time) * 1000)
                logger.error(f"OpenAI API 호출 실패: {e}")
                
                # 실패한 호출도 추적 (비용은 0)
                await tracker.track_api_call(
                    model=kwargs.get('model', 'unknown'),
                    usage={"prompt_tokens": 0, "completion_tokens": 0},
                    response_time_ms=response_time_ms,
                    request_type="chat",
                    user_id=user_id,
                    session_id=session_id
                )
                
                raise
        
        return wrapper
    return decorator

class TrackedOpenAI:
    """비용 추적이 통합된 OpenAI 클라이언트"""
    
    def __init__(self, api_key: str, channel: str = "default", country: str = "KR"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.tracker = get_cost_tracker(channel, country)
        self.channel = channel
        self.country = country

    async def chat_completion(self, **kwargs) -> Any:
        """채팅 완성 API (추적 포함)"""
        start_time = time.time()
        
        try:
            response = await self.client.chat.completions.create(**kwargs)
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # 비용 추적
            await self.tracker.track_api_call(
                model=response.model,
                usage=response.usage.model_dump() if response.usage else {},
                response_time_ms=response_time_ms,
                request_type="chat",
                user_id=kwargs.get('user'),
                session_id=kwargs.get('session_id')
            )
            
            return response
            
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"채팅 완성 API 호출 실패: {e}")
            
            # 실패한 호출도 추적
            await self.tracker.track_api_call(
                model=kwargs.get('model', 'unknown'),
                usage={"prompt_tokens": 0, "completion_tokens": 0},
                response_time_ms=response_time_ms,
                request_type="chat"
            )
            
            raise

    async def embedding(self, **kwargs) -> Any:
        """임베딩 API (추적 포함)"""
        start_time = time.time()
        
        try:
            response = await self.client.embeddings.create(**kwargs)
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # 비용 추적
            await self.tracker.track_api_call(
                model=response.model,
                usage=response.usage.model_dump() if response.usage else {},
                response_time_ms=response_time_ms,
                request_type="embedding",
                user_id=kwargs.get('user'),
                session_id=kwargs.get('session_id')
            )
            
            return response
            
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"임베딩 API 호출 실패: {e}")
            
            await self.tracker.track_api_call(
                model=kwargs.get('model', 'unknown'),
                usage={"total_tokens": 0},
                response_time_ms=response_time_ms,
                request_type="embedding"
            )
            
            raise

    async def speech_to_text(self, **kwargs) -> Any:
        """음성-텍스트 변환 API (추적 포함)"""
        start_time = time.time()
        
        try:
            response = await self.client.audio.transcriptions.create(**kwargs)
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # 오디오 파일 길이 추정 (실제로는 파일에서 추출해야 함)
            duration = kwargs.get('duration', 60)  # 기본 60초
            
            await self.tracker.track_api_call(
                model=kwargs.get('model', 'whisper-1'),
                usage={"duration": duration},
                response_time_ms=response_time_ms,
                request_type="audio",
                user_id=kwargs.get('user'),
                session_id=kwargs.get('session_id')
            )
            
            return response
            
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"음성-텍스트 API 호출 실패: {e}")
            
            await self.tracker.track_api_call(
                model=kwargs.get('model', 'whisper-1'),
                usage={"duration": 0},
                response_time_ms=response_time_ms,
                request_type="audio"
            )
            
            raise

    def get_session_stats(self) -> Dict[str, Any]:
        """세션 통계 조회"""
        return self.tracker.get_session_stats()

# 편의 함수들
async def create_tracked_chat_completion(api_key: str, channel: str = "korean", 
                                       country: str = "KR", **kwargs) -> Any:
    """추적이 포함된 채팅 완성 API 호출"""
    client = TrackedOpenAI(api_key, channel, country)
    return await client.chat_completion(**kwargs)

async def create_tracked_embedding(api_key: str, channel: str = "korean", 
                                 country: str = "KR", **kwargs) -> Any:
    """추적이 포함된 임베딩 API 호출"""
    client = TrackedOpenAI(api_key, channel, country)
    return await client.embedding(**kwargs)

# 사용 예시 및 테스트
async def test_cost_tracking():
    """비용 추적 테스트"""
    import os
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY 환경변수가 설정되지 않음")
        return
    
    # 추적이 포함된 클라이언트 생성
    client = TrackedOpenAI(api_key, channel="test", country="KR")
    
    try:
        # 테스트 채팅 완성
        response = await client.chat_completion(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "한국 주식시장에 대해 간단히 설명해줘"}
            ],
            max_tokens=100,
            user="test_user",
            session_id="test_session"
        )
        
        print("응답:", response.choices[0].message.content[:100] + "...")
        
        # 세션 통계 출력
        stats = client.get_session_stats()
        print("세션 통계:", stats)
        
    except Exception as e:
        logger.error(f"테스트 실패: {e}")

if __name__ == "__main__":
    asyncio.run(test_cost_tracking())