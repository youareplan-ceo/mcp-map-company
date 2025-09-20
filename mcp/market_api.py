from fastapi import APIRouter, Query
from typing import Dict, Any, List
import datetime as dt

router = APIRouter(tags=["market"])

# 단건/배치 실가격 (yfinance) - 이미 구현돼 있다면 유지
def _fetch_price(symbol: str) -> Dict[str, Any]:
    try:
        import yfinance as yf
    except Exception as e:
        return {"symbol": symbol, "ok": False, "error": f"yfinance not available: {e}"}
    sym = symbol.upper().strip()
    tkr = yf.Ticker(sym)
    price, source = None, None
    try:
        fi = getattr(tkr, "fast_info", None)
        if fi and "lastPrice" in fi and fi["lastPrice"]:
            price = float(fi["lastPrice"]); source = "fast_info.lastPrice"
    except Exception:
        pass
    if price is None:
        try:
            hist = tkr.history(period="1d", interval="1d", auto_adjust=True)
            if not hist.empty:
                price = float(hist["Close"].iloc[-1]); source = "history.Close[-1]"
        except Exception:
            pass
    if price is None:
        return {"symbol": sym, "ok": False, "error": "no price from yfinance"}
    return {"symbol": sym, "ok": True, "price": price, "source": source, "asof": dt.datetime.utcnow().isoformat() + "Z"}

@router.get("/price")
def get_price(symbol: str = Query(...)) -> Dict[str, Any]:
    return _fetch_price(symbol)

@router.get("/batch_prices")
def get_batch_prices(symbols: str = Query(...)) -> Dict[str, Any]:
    syms = [s.strip() for s in symbols.split(",") if s.strip()]
    return {"ok": True, "items": [_fetch_price(s) for s in syms]}

# ▼▼ DB 최신가 조회 (collector가 쌓아둔 prices 테이블에서 최근 1건)
from .db import get_conn
@router.get("/prices/latest")
def latest_prices(symbols: str = Query(..., description="쉼표구분: NVDA,MSFT,AAPL")):
    syms = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    con = get_conn()
    items = []
    for s in syms:
        row = con.execute("""
            SELECT symbol, price, source, ts
            FROM prices
            WHERE symbol = ?
            ORDER BY ts DESC
            LIMIT 1
        """, (s,)).fetchone()
        if row:
            items.append({"symbol": row[0], "price": float(row[1]),
                          "source": row[2], "asof": row[3]})
        else:
            items.append({"symbol": s, "error": "no data"})
    con.close()
    return {"ok": True, "items": items}
