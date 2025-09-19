#!/usr/bin/env python3
"""
StockPilot 토큰 발급 및 인증 API 서버
- POST /auth/token (client_id, scope) → JWT 반환
- PyJWT 사용, TTL 10-30분
- 완전 자동화된 토큰 관리 시스템
"""

import os
import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 인증 시스템 임포트
from utils.websocket_auth import get_auth_manager, UserRole

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="StockPilot 인증 API 서버",
    version="2.0.0",
    description="토큰 발급 및 검증 전용 API"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 인증 관리자 초기화
jwt_secret = os.getenv('JWT_SECRET_KEY', 'stockpilot-prod-secret-2024')
auth_manager = get_auth_manager(jwt_secret)

# Pydantic 모델들
class TokenRequest(BaseModel):
    """토큰 요청 모델"""
    client_id: str
    scope: List[str] = ["basic"]  # basic, premium, admin
    expires_in_minutes: Optional[int] = 20  # 10-30분 TTL

class TokenResponse(BaseModel):
    """토큰 응답 모델"""
    token: str
    client_id: str
    role: str
    scope: List[str]
    expires_in_minutes: int
    available_channels: List[str]
    issued_at: str
    usage: str

class TokenVerifyRequest(BaseModel):
    """토큰 검증 요청 모델"""
    token: str

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "StockPilot 인증 API",
        "version": "2.0.0",
        "status": "online",
        "endpoints": {
            "token_issue": "POST /auth/token",
            "token_verify": "POST /auth/verify",
            "stats": "GET /auth/stats"
        }
    }

@app.post("/auth/token", response_model=TokenResponse)
async def generate_auth_token(request: TokenRequest):
    """토큰 발급 REST 엔드포인트 (자동 승인)"""
    try:
        # 자동 검증 및 승인
        if not request.client_id or len(request.client_id.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail={"error": "client_id가 필수입니다", "code": "INVALID_CLIENT_ID"}
            )
        
        if not (10 <= request.expires_in_minutes <= 30):
            raise HTTPException(
                status_code=400,
                detail={"error": "expires_in_minutes는 10-30 범위여야 합니다", "code": "INVALID_TTL"}
            )
        
        # 스코프에서 역할 결정 (최고 스코프 자동 승인)
        role_mapping = {
            "basic": UserRole.BASIC,
            "premium": UserRole.PREMIUM, 
            "admin": UserRole.ADMIN
        }
        
        user_role = UserRole.GUEST
        for scope in request.scope:
            if scope in role_mapping:
                candidate_role = role_mapping[scope]
                if candidate_role == UserRole.ADMIN:
                    user_role = UserRole.ADMIN
                    break
                elif candidate_role == UserRole.PREMIUM and user_role != UserRole.ADMIN:
                    user_role = UserRole.PREMIUM
                elif candidate_role == UserRole.BASIC and user_role not in [UserRole.ADMIN, UserRole.PREMIUM]:
                    user_role = UserRole.BASIC
        
        # 토큰 생성 (자동 승인)
        token = auth_manager.generate_token(
            user_id=request.client_id,
            role=user_role,
            expires_in_minutes=request.expires_in_minutes
        )
        
        # 이용 가능한 채널 조회
        available_channels = _get_available_channels_for_role(user_role)
        
        logger.info(f"🎫 토큰 자동 발급: client_id={request.client_id}, role={user_role.value}, ttl={request.expires_in_minutes}분")
        
        return TokenResponse(
            token=token,
            client_id=request.client_id,
            role=user_role.value,
            scope=request.scope,
            expires_in_minutes=request.expires_in_minutes,
            available_channels=available_channels,
            issued_at=datetime.now(timezone.utc).isoformat(),
            usage=f"wss://localhost:8000/ws?token={token[:20]}..."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"토큰 발급 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "토큰 발급 실패", "code": "TOKEN_GENERATION_FAILED"}
        )

@app.post("/auth/verify")
async def verify_auth_token(request: TokenVerifyRequest):
    """토큰 검증 엔드포인트"""
    try:
        if not request.token:
            raise HTTPException(
                status_code=400,
                detail={"error": "token이 필수입니다", "valid": False}
            )
        
        is_valid, payload = auth_manager.verify_token(request.token)
        
        if is_valid:
            return {
                "valid": True,
                "user_id": payload["user_id"],
                "role": payload["role"].value,
                "expires_at": payload["exp"].isoformat() if hasattr(payload["exp"], 'isoformat') else str(payload["exp"]),
                "issued_at": payload["iat"].isoformat() if hasattr(payload["iat"], 'isoformat') else str(payload["iat"])
            }
        else:
            return {"valid": False, "error": "토큰이 유효하지 않습니다"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"토큰 검증 오류: {e}")
        return {"valid": False, "error": "토큰 검증 실패"}

@app.get("/auth/stats")
async def auth_stats():
    """인증 시스템 통계"""
    stats = auth_manager.get_connection_stats()
    stats["token_settings"] = {
        "default_ttl_minutes": auth_manager.TOKEN_EXPIRY_MINUTES,
        "supported_scopes": ["basic", "premium", "admin"],
        "supported_roles": [role.value for role in UserRole]
    }
    return stats

def _get_available_channels_for_role(role: UserRole) -> List[str]:
    """역할에 따른 이용 가능 채널 리스트 반환"""
    channels = []
    
    # 모든 역할이 접근 가능한 채널
    channels.extend(["us_stocks", "market_status"])
    
    # BASIC 이상 배경
    if role in [UserRole.BASIC, UserRole.PREMIUM, UserRole.ADMIN]:
        channels.extend(["us_indices", "exchange_rates"])
    
    # PREMIUM 이상 배경
    if role in [UserRole.PREMIUM, UserRole.ADMIN]:
        channels.append("us_news")
    
    # ADMIN만 접근 가능
    if role == UserRole.ADMIN:
        channels.append("ai_signals")
    
    return channels

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 StockPilot 인증 API 서버 시작...")
    uvicorn.run(app, host="0.0.0.0", port=8001)