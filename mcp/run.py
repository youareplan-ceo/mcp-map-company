from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import os

app = FastAPI(title="StockPilot API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

def now():
    return datetime.now(timezone.utc).isoformat()

@app.get("/api/v1/health")
def health():
    return {"ok": True, "ts": now()}

_DEFAULT_USER = "default"
PORTFOLIO = {
    _DEFAULT_USER: [
        {"symbol":"NVDA","shares":5,"avg_cost":120.0,"currency":"USD"},
        {"symbol":"AAPL","shares":5,"avg_cost":220.0,"currency":"USD"},
        {"symbol":"AMZN","shares":3,"avg_cost":200.0,"currency":"USD"},
    ]
}
PRICES = {"NVDA":176.67,"AAPL":245.50,"AMZN":231.48}

@app.get("/api/v1/portfolio/pnl")
def portfolio_pnl(user_id: str = _DEFAULT_USER):
    items = PORTFOLIO.get(user_id, [])
    total_cost = 0.0
    total_value = 0.0
    rows = []
    for it in items:
        sym = it["symbol"]
        qty = float(it["shares"])
        cost = float(it["avg_cost"])
        px = float(PRICES.get(sym, cost))
        paid = qty * cost
        value = qty * px
        pnl_amt = value - paid
        pnl_pct = (pnl_amt / paid * 100.0) if paid else 0.0
        total_cost += paid
        total_value += value
        rows.append({
            "symbol": sym,
            "qty": qty,
            "avg_cost": cost,
            "price": px,
            "value": round(value, 2),
            "pnl_pct": round(pnl_pct, 2),
            "note": f"사유: 중립 {round(pnl_pct,1)}%",
        })
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100.0) if total_cost else 0.0
    return {
        "summary": {
            "asof": now(),
            "cash": 0.0,
            "eval_value": round(total_value, 2),
            "base_cost": round(total_cost, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
        },
        "positions": rows,
    }

@app.get("/api/v1/portfolio/reco")
def portfolio_reco(user_id: str = _DEFAULT_USER):
    rec_existing = [
        {"symbol":"NVDA","action":"hold","score":3.33,"reason":"추세↑·RSI 중립·모멘텀 보통"},
    ]
    rec_new = [
        {"symbol":"AAPL","action":"buy","score":4.5,"reason":"추세 강함·RSI>50"},
        {"symbol":"AMZN","action":"buy","score":4.5,"reason":"추세 강함·RSI>50"},
    ]
    rec_signal = [
        {"symbol":"NVDA","action":"trim","score":3.1,"reason":"목표가 근접 · 일부 차익"},
    ]
    return {"meta":{"asof": now()}, "recommendations": rec_existing + rec_new + rec_signal}

@app.get("/")
def root():
    return {
        "name":"StockPilot API","version":"0.2.0",
        "health":"/api/v1/health",
        "portfolio":{"pnl":"/api/v1/portfolio/pnl","reco":"/api/v1/portfolio/reco"}
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT","8099"))
    uvicorn.run(app, host="0.0.0.0", port=port)
