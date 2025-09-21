import os
from fastapi import FastAPI
from datetime import datetime

app = FastAPI(title="StockPilot API", version="0.2.0")

# 헬스체크
@app.get("/api/v1/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

# 포트폴리오 손익(PnL) 샘플
@app.get("/api/v1/portfolio/pnl")
def portfolio_pnl():
    summary = {
        "total_value": 3688.64,
        "initial": 3200.00,
        "profit": 488.64,
        "profit_pct": 15.27,
        "asof": datetime.utcnow().isoformat()
    }
    holdings = [
        {"symbol": "NVDA", "shares": 10, "avg_cost": 150.0, "current": 176.67, "pnl_pct": 17.8},
        {"symbol": "AAPL", "shares": 5, "avg_cost": 220.0, "current": 245.5, "pnl_pct": 11.6},
        {"symbol": "AMZN", "shares": 3, "avg_cost": 200.0, "current": 231.48, "pnl_pct": 15.7},
    ]
    return {"summary": summary, "holdings": holdings}

# 추천 종목 샘플
@app.get("/api/v1/portfolio/reco")
def portfolio_reco():
    rec_existing = [
        {"symbol": "NVDA", "score": 3.33, "action": "hold", "reason": "중립 17.8%"}
    ]
    rec_new = [
        {"symbol": "AAPL", "score": 4.5, "action": "buy", "reason": "기술 강세"},
        {"symbol": "AMZN", "score": 4.5, "action": "buy", "reason": "매출 성장"},
    ]
    return {"meta": {"asof": datetime.utcnow().isoformat()}, "recommendations": rec_existing + rec_new}

# 루트 엔드포인트
@app.get("/")
def root():
    return {
        "name": "StockPilot API",
        "version": "0.2.0",
        "health": "/api/v1/health",
        "portfolio": {
            "pnl": "/api/v1/portfolio/pnl",
            "reco": "/api/v1/portfolio/reco"
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8099"))
    uvicorn.run(app, host="0.0.0.0", port=port)
