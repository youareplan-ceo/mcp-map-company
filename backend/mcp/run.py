from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.mcp.routes import portfolio_store  # 기존 라우터 임포트 그대로 사용

app = FastAPI(title="StockPilot API", version="0.2.0")

# Vercel/로컬에서 접근 허용 (필요시 팀 도메인 추가)
ALLOWED_ORIGINS = [
    "https://mcp-map-company.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio_store.router, prefix="/api/v1/portfolio")

@app.get("/api/v1/health")
def health():
    return {"ok": True}
