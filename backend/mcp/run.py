from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.mcp.api import portfolio_store  # ← 실제 위치: backend/mcp/api/portfolio_store.py

app = FastAPI(title="StockPilot API", version="0.2.0")

ALLOWED_ORIGINS = [
    "https://mcp-map-company.vercel.app",       # 기존 Vercel 기본
    "https://stockpilot-customer.vercel.app",   # 고객용
    "https://stockpilot-admin.vercel.app",      # 운영자용
    "https://stockpilot-dev.vercel.app",        # 개발자용
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",                    # 로컬 개발용
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio_store.router, prefix="/api/v1/portfolio", tags=["portfolio"])

@app.get("/api/v1/health")
def health():
    return {"ok": True}
