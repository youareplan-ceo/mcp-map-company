"""
StockPilot AI FastAPI 메인 애플리케이션
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from loguru import logger

from app.config import get_settings
from app.api.v1.api import api_router
from app.websocket.handlers import get_websocket_handler, get_data_updater
from app.middleware.cost_guard import CostGuardMiddleware
from app.jobs.jobs import register_all_jobs
from app.jobs.job_scheduler import get_job_scheduler

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 StockPilot AI 백엔드 시작")
    
    # WebSocket 데이터 업데이터 시작
    data_updater = get_data_updater()
    await data_updater.start_updates()
    
    # 배치 작업 시스템 초기화
    try:
        register_all_jobs()
        job_scheduler = get_job_scheduler()
        job_scheduler.setup_default_schedule()
        job_scheduler.start()
        logger.info("✅ 배치 시스템 초기화 완료")
    except Exception as e:
        logger.error(f"❌ 배치 시스템 초기화 실패: {str(e)}")
    
    yield
    
    # 종료 시 정리
    await data_updater.stop_updates()
    
    # 배치 스케줄러 중단
    try:
        job_scheduler = get_job_scheduler()
        job_scheduler.stop()
        logger.info("✅ 배치 시스템 종료 완료")
    except Exception as e:
        logger.error(f"❌ 배치 시스템 종료 실패: {str(e)}")
    
    logger.info("🛑 StockPilot AI 백엔드 종료")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=settings.allowed_methods,
    allow_headers=settings.allowed_headers,
)

# 비용 가드레일 미들웨어 추가
app.add_middleware(CostGuardMiddleware)

app.include_router(api_router, prefix="/api/v1")

websocket_handler = get_websocket_handler()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_handler.handle_client_connection(websocket)


@app.get("/")
async def root():
    return {"message": "StockPilot AI API", "version": settings.app_version}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.reload)