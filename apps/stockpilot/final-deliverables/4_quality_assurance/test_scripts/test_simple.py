"""
간단한 FastAPI 서버 - 의존성 최소화
기본 API 연동 테스트용
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="StockPilot AI API",
    version="1.0.0",
    description="AI 기반 투자 코파일럿 서비스"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "StockPilot AI API", "version": "1.0.0", "status": "running"}

@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "StockPilot AI API",
        "version": "1.0.0"
    }

@app.get("/api/v1/status")
async def service_status():
    return {
        "overall_status": "operational",
        "services": {
            "api": "online",
            "database": "unknown"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)