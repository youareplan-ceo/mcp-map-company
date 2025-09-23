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

# ──────────────────────────────────────
# NEW: UI 호환 단순 엔드포인트
from typing import List
from .db import get_conn

@app.get("/api/v1/recommend")
def get_simple_recommendations(tickers: str = None):
    """UI 호환 간단 추천 엔드포인트"""
    if tickers:
        # 쿼리 파라미터로 종목 지정
        symbols = [s.strip().upper() for s in tickers.split(",") if s.strip()]
    else:
        # 포트폴리오에서 보유 종목 가져오기
        try:
            con = get_conn()
            rows = con.execute("SELECT DISTINCT symbol FROM portfolio").fetchall()
            con.close()
            symbols = [row[0] for row in rows] if rows else ["AAPL", "GOOGL", "MSFT"]
        except:
            symbols = ["AAPL", "GOOGL", "MSFT"]  # 기본값

    recommendations = []
    for symbol in symbols:
        # 간단한 규칙 기반 추천 (목업)
        try:
            con = get_conn()
            # 보유 정보 확인
            portfolio_row = con.execute(
                "SELECT buy_price, quantity FROM portfolio WHERE symbol = ?",
                (symbol,)
            ).fetchone()
            con.close()

            if portfolio_row:
                buy_price = portfolio_row[0]
                # 간단한 규칙: 매수가 대비 5% 이하면 BUY, 10% 이상이면 SELL 추천
                current_price = buy_price * 1.02  # 목업 현재가 (매수가 대비 +2%)

                if current_price < buy_price * 0.95:
                    action = "BUY"
                    buy_below = buy_price * 0.95
                    sell_above = None
                    score = 8.5
                elif current_price > buy_price * 1.10:
                    action = "HOLD"  # UI에서 SELL로 매핑 가능
                    buy_below = None
                    sell_above = buy_price * 1.15
                    score = 3.2
                else:
                    action = "WATCH"
                    buy_below = buy_price * 0.98
                    sell_above = buy_price * 1.12
                    score = 6.1
            else:
                # 신규 종목
                action = "WATCH"
                buy_below = 150.0  # 목업 매수 추천가
                sell_above = None
                score = 7.0

            recommendations.append({
                "symbol": symbol,
                "action": action,
                "buy_below": buy_below,
                "sell_above": sell_above,
                "score": score
            })

        except Exception:
            # 에러 시 기본값
            recommendations.append({
                "symbol": symbol,
                "action": "WATCH",
                "buy_below": None,
                "sell_above": None,
                "score": 5.0
            })

    return recommendations

@app.get("/api/v1/quote")
def get_quotes(tickers: str):
    """UI 호환 시세 조회 엔드포인트"""
    symbols = [s.strip().upper() for s in tickers.split(",") if s.strip()]
    quotes = []

    for symbol in symbols:
        try:
            # 먼저 기존 시세 소스 사용 시도 (market_api 활용)
            from .market_api import _fetch_price
            price_data = _fetch_price(symbol)

            if price_data.get("ok"):
                quotes.append({
                    "symbol": symbol,
                    "price": price_data["price"],
                    "currency": "USD"
                })
            else:
                # 실패 시 임시 고정값 사용
                fallback_prices = {
                    "AAPL": 185.0,
                    "GOOGL": 140.0,
                    "MSFT": 380.0,
                    "NVDA": 950.0,
                    "TSLA": 250.0
                }
                price = fallback_prices.get(symbol, 100.0)
                quotes.append({
                    "symbol": symbol,
                    "price": price,
                    "currency": "USD"
                })

        except Exception:
            # 에러 시 기본값
            quotes.append({
                "symbol": symbol,
                "price": 100.0,
                "currency": "USD"
            })

    return quotes
