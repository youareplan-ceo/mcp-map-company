import os
from fastapi import APIRouter, Query
from typing import Dict, Any, List
from .db import get_conn
from .indicators import fetch_indicators, score_from_indicators, get_weights

router = APIRouter(tags=["recommend"])

# 임계치 (환경변수에서 주입 가능)
RECOMMEND_THRESHOLD = float(os.getenv("RECOMMEND_THRESHOLD", 2.5))
ADD_MORE_THRESHOLD  = float(os.getenv("ADD_MORE_THRESHOLD", 3.0))
WARN_THRESHOLD      = float(os.getenv("WARN_THRESHOLD", -2.5))

def _save_alert(user_id: str, symbol: str, level: str, message: str) -> None:
    con = get_conn()
    con.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
          user_id   TEXT,
          symbol    TEXT,
          level     TEXT,
          message   TEXT,
          created_at TIMESTAMP DEFAULT now()
        )
    """)
    exists = con.execute("""
        SELECT 1 FROM alerts
        WHERE user_id = ? AND symbol = ? AND level = ? AND message = ?
        ORDER BY created_at DESC
        LIMIT 1
    """, (user_id, symbol.upper(), level, message)).fetchone()
    if exists:
        con.close()
        return
    con.execute("INSERT INTO alerts (user_id, symbol, level, message) VALUES (?, ?, ?, ?)",
                (user_id, symbol.upper(), level, message))
    con.close()

@router.get("/recommendations")
def get_recommendations(user_id: str = Query("default")) -> Dict[str, Any]:
    # 1) 보유 종목
    con = get_conn()
    rows = con.execute("""
        SELECT symbol, shares, avg_cost
        FROM holdings_latest
        WHERE user_id = ?
        ORDER BY symbol
    """, (user_id,)).fetchall()
    con.close()
    holdings = [dict(zip(["symbol","shares","avg_cost"], r)) for r in rows]
    owned = {h["symbol"] for h in holdings}

    # 2) 후보군 (회장님 관심 종목 워치리스트)
    watchlist = {
        "GOOGL",   # Alphabet A
        "APLD",    # Applied Digital
        "NVDA",    # NVIDIA
        "ORCL",    # Oracle
        "TSLA",    # Tesla
        "PLTR",    # Palantir
        "SAND",    # Sandstorm Gold
        "NVTS",    # Navitas Semiconductor
        "STRC",    # Sarcos Robotics (확인필요)
        "RXRX",    # Recursion Pharma
        "TER",     # Teradyne
        "VRT",     # Vertiv Holdings
        "QQQM",    # Invesco ETF
        "ARM",     # ARM Holdings ADR
        "LEU",     # Centrus Energy
        "AAPL",    # Apple
        "AMZN",    # Amazon
        "SERV",    # Serve Robotics
        "NBIS",    # Nebius Group
        "CRWV"     # CoreWeave
    }
    candidates = sorted(owned.union(watchlist))

    # 3) 각 심볼에 대해 지표/점수 계산
    raw_reco: List[Dict[str, Any]] = []
    for sym in candidates:
        ind = fetch_indicators(sym)
        if not ind.get("ok"):
            raw_reco.append({
                "symbol": sym,
                "score": 0.0,
                "why": [f"데이터오류:{ind.get('error','unknown')}"],
                "currentPrice": None
            })
            continue
        sc = score_from_indicators(ind)
        raw_reco.append({
            "symbol": sym,
            "score": sc["score"],
            "why": sc["why"],
            "currentPrice": ind["price"],
            "asof": ind["asof"]
        })

    # 4) 보유/신규로 분리 + 임계치에 따라 액션/알림
    existing, new = [], []
    for r in raw_reco:
        sym, score = r["symbol"], float(r["score"])
        if sym in owned:
            if score >= ADD_MORE_THRESHOLD:
                _save_alert(user_id, sym, "info", f"{sym}: 추가 매수 제안(점수 {score:.2f})")
                r["action"] = "add_more"
            elif score <= WARN_THRESHOLD:
                _save_alert(user_id, sym, "warn", f"{sym}: 보유 주의(점수 {score:.2f})")
                r["action"] = "watch"
            else:
                r["action"] = "hold"
            existing.append(r)
        else:
            if score >= RECOMMEND_THRESHOLD:
                _save_alert(user_id, sym, "info", f"{sym}: 신규 매수 제안(점수 {score:.2f})")
                r["action"] = "buy"
            else:
                r["action"] = "skip"
            new.append(r)

    return {
        "ok": True,
        "user_id": user_id,
        "holdings": holdings,
        "recommendations": {"existing": existing, "new": new},
        "meta": {
            "recommend_threshold": RECOMMEND_THRESHOLD,
            "add_more_threshold": ADD_MORE_THRESHOLD,
            "warn_threshold": WARN_THRESHOLD,
            "scoring": "RSI/SMA/momentum (6mo daily, yfinance)",
            "weights": {
                "trend": get_weights()[0],
                "rsi": get_weights()[1],
                "mom": get_weights()[2]
            }
        }
    }

@router.get("/ai/signals")
def get_ai_signals(user_id: str = Query("default")) -> Dict[str, Any]:
    base = get_recommendations(user_id)
    rec = base.get("recommendations", {}) or {}
    existing = rec.get("existing", [])
    new = rec.get("new", [])
    signals = []
    def pick(items):
        for r in items:
            act = r.get("action")
            if act in ("buy","add_more","watch"):
                signals.append({
                    "symbol": r["symbol"],
                    "action": "buy" if act in ("buy","add_more") else "hold",
                    "message": f"{act}",
                    "description": "AI 점수 기반 신호",
                    "price": r.get("currentPrice"),
                    "quantity": 1
                })
    pick(existing); pick(new)
    rec_cards = []
    def to_card(items):
        for r in items:
            typ = {"hold":"hold","add_more":"add","buy":"new"}.get(r.get("action","hold"), "hold")
            rec_cards.append({
                "type": typ,
                "symbol": r["symbol"],
                "reason": " / ".join((r.get("why") or [])[:2]),
                "currentPrice": r.get("currentPrice"),
                "targetPrice": None,
                "action": {"hold":"보유 지속","add":"추가 분석","new":"신규 분석"}.get(typ,"보유 지속")
            })
    to_card(existing); to_card(new)
    holdings = base.get("holdings", [])
    portfolio = {
        "totalValue": None, "profit": None, "profitPercentage": None,
        "stockCount": len(holdings), "cashRatio": None, "monthlyReturn": None,
        "riskLevel": "중간"
    }
    return {"ok": True, "portfolio": portfolio, "signals": signals,
            "recommendations": rec_cards, "meta": base.get("meta", {})}

