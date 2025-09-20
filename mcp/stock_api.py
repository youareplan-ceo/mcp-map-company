from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 내부 라우터
from . import recommend_api
from . import market_api

app = FastAPI(title="StockPilot API", version="0.1.0")

# ───────────────────────────────────────────────
# CORS (필요 시 Vercel 도메인으로 제한)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ───────────────────────────────────────────────
# 라우터 등록 (여기가 핵심)
app.include_router(recommend_api.router, prefix="/api/v1/stock")
app.include_router(market_api.router,    prefix="/api/v1/stock")

# ───────────────────────────────────────────────
# 헬스체크
@app.get("/health")
def health():
    return {"ok": True, "service": "stockpilot", "status": "alive"}

# ───────────────────────────────────────────────
# 프론트 호환 브리지: /api/v1/ai/signals → recommend_api의 get_ai_signals
@app.get("/api/v1/ai/signals")
def _ai_signals_bridge(user_id: str = "default"):
    from .recommend_api import get_ai_signals
    return get_ai_signals(user_id)
