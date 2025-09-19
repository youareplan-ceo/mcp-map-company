"""
StockPilot AI 백엔드 메인 애플리케이션
FastAPI를 사용한 RESTful API 서버
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from core.config import settings
from core.database import init_db
from api.routes import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    앱 시작/종료 시 실행되는 생명주기 관리자
    """
    # 시작시 실행
    await init_db()
    yield
    # 종료시 실행 (필요시 추가)


def create_application() -> FastAPI:
    """
    FastAPI 애플리케이션 생성 및 설정
    """
    application = FastAPI(
        title="StockPilot AI API",
        description="AI 기반 투자 코파일럿 서비스",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )

    # CORS 미들웨어 설정
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 라우터 등록
    application.include_router(api_router, prefix="/api/v1")

    return application


# FastAPI 앱 인스턴스 생성
app = create_application()


@app.get("/")
async def root():
    """
    헬스체크 엔드포인트
    """
    return {"message": "StockPilot AI API가 정상 작동 중입니다"}


@app.get("/health")
async def health_check():
    """
    상세 헬스체크 엔드포인트
    """
    return {
        "status": "healthy",
        "service": "StockPilot AI Backend",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level="info"
    )