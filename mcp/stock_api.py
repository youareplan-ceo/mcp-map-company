from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 내부 라우터
from . import recommend_api
from . import market_api
from . import portfolio_api   # ★ 추가

app = FastAPI(title="StockPilot API", version="0.1.0")

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
# 라우터 등록
app.include_router(recommend_api.router)
app.include_router(market_api.router)
app.include_router(portfolio_api.router)  # ★ 추가
