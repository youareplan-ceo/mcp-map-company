"""
비용 가드레일 미들웨어
OpenAI API 호출 전후에 비용 한도 체크 및 제한
"""

import time
from typing import Callable
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

from app.middleware.usage_tracker import get_usage_tracker
from app.config import get_settings

settings = get_settings()


class CostGuardMiddleware(BaseHTTPMiddleware):
    """비용 한도 체크 미들웨어"""
    
    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/usage/stats",
            "/usage/cost-check"
        ]
        self.usage_tracker = None
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """요청 처리 전후에 비용 체크"""
        
        # 제외 경로 체크
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # 사용량 추적기 초기화
        if not self.usage_tracker:
            try:
                self.usage_tracker = await get_usage_tracker()
            except Exception as e:
                logger.warning(f"사용량 추적기 초기화 실패: {e}")
                return await call_next(request)
        
        # AI 분석 관련 엔드포인트만 비용 체크
        ai_endpoints = ["/stocks/", "/signals/", "/analysis"]
        is_ai_endpoint = any(endpoint in request.url.path for endpoint in ai_endpoints)
        
        if is_ai_endpoint and request.method in ["POST", "PUT"]:
            # API 호출 전 비용 한도 체크
            try:
                can_proceed, limit_msg = await self.usage_tracker.check_cost_limits()
                
                if not can_proceed:
                    logger.warning(f"비용 한도 초과로 요청 차단: {request.url.path}")
                    return JSONResponse(
                        status_code=429,  # Too Many Requests
                        content={
                            "error": "Cost limit exceeded",
                            "message": limit_msg,
                            "code": "COST_LIMIT_EXCEEDED",
                            "retry_after": 3600  # 1시간 후 재시도 권장
                        }
                    )
                
                # 알림 임계치 체크 및 경고 헤더 추가
                stats = await self.usage_tracker.get_usage_stats(days=1)
                daily_usage = list(stats['daily_usage'].values())[0] if stats['daily_usage'] else {}
                current_cost = daily_usage.get('total_cost', 0.0)
                
                warning_threshold = settings.daily_cost_limit * settings.cost_alert_threshold
                
                response = await call_next(request)
                
                # 경고 헤더 추가
                if current_cost >= warning_threshold:
                    response.headers["X-Cost-Warning"] = f"Approaching daily limit: ${current_cost:.2f}/${settings.daily_cost_limit}"
                    response.headers["X-Cost-Percentage"] = f"{(current_cost/settings.daily_cost_limit)*100:.1f}%"
                
                return response
                
            except Exception as e:
                logger.error(f"비용 체크 중 오류: {e}")
                # 비용 체크 실패 시에도 요청은 계속 처리
                return await call_next(request)
        
        return await call_next(request)


class OpenAIRateLimiter:
    """OpenAI API 호출 속도 제한"""
    
    def __init__(self, max_calls_per_minute: int = 60):
        self.max_calls_per_minute = max_calls_per_minute
        self.calls = []
        self.lock = False
    
    async def check_rate_limit(self) -> bool:
        """호출 속도 제한 체크"""
        current_time = time.time()
        
        # 1분 이전 호출 기록 제거
        self.calls = [call_time for call_time in self.calls if current_time - call_time < 60]
        
        if len(self.calls) >= self.max_calls_per_minute:
            return False
        
        self.calls.append(current_time)
        return True
    
    async def get_wait_time(self) -> float:
        """대기 시간 계산"""
        if not self.calls:
            return 0.0
        
        oldest_call = min(self.calls)
        wait_time = 60 - (time.time() - oldest_call)
        return max(0, wait_time)


# 전역 인스턴스
openai_rate_limiter = OpenAIRateLimiter()


async def enforce_openai_limits() -> bool:
    """OpenAI API 호출 전 제한 사항 체크"""
    
    # 속도 제한 체크
    if not await openai_rate_limiter.check_rate_limit():
        wait_time = await openai_rate_limiter.get_wait_time()
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": f"Too many OpenAI API calls. Wait {wait_time:.1f} seconds",
                "retry_after": int(wait_time) + 1
            }
        )
    
    # 비용 한도 체크
    usage_tracker = await get_usage_tracker()
    can_proceed, limit_msg = await usage_tracker.check_cost_limits()
    
    if not can_proceed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Cost limit exceeded", 
                "message": limit_msg,
                "code": "COST_LIMIT_EXCEEDED"
            }
        )
    
    return True