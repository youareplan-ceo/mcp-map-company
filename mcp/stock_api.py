from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 내부 라우터
from . import recommend_api
from . import market_api
from . import portfolio_api

app = FastAPI(title="StockPilot API", version="0.3.0")

# ──────────────────────────────────────
# CORS (필요 시 Vercel 도메인으로 제한)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────
# 기본 Health 엔드포인트
@app.get("/api/v1/health")
def health():
    return {"ok": True, "msg": "StockPilot API alive"}

# ──────────────────────────────────────
# 라우터 등록 (모두 /api/v1 prefix 적용)
app.include_router(recommend_api.router, prefix="/api/v1/stock")
app.include_router(market_api.router,    prefix="/api/v1/stock")
app.include_router(portfolio_api.router, prefix="/api/v1")
