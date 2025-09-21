from fastapi import APIRouter, Query
from typing import Dict, Any, List, Optional
import os
import math
import datetime as dt

from mcp.db import get_conn

router = APIRouter(tags=["portfolio"])

# ─────────────────────────────────────────
# 테이블 생성
def ensure_portfolio_table():
    con = get_conn()
    con.execute("""
    CREATE TABLE IF NOT EXISTS portfolio (
        symbol TEXT,
        buy_price DOUBLE,
        quantity DOUBLE
    )
    """)
    con.close()

# ─────────────────────────────────────────
# CRUD
@router.post("/portfolio/add")
def add_portfolio(symbol: str, buy_price: float, quantity: float):
    ensure_portfolio_table()
    con = get_conn()
    con.execute("INSERT INTO portfolio VALUES (?, ?, ?)", (symbol.upper().strip(), buy_price, quantity))
    con.close()
    return {"ok": True, "msg": f"{symbol} 추가 완료"}

@router.post("/portfolio/upsert")
def upsert_portfolio(symbol: str, buy_price: float, quantity: float):
    ensure_portfolio_table()
    sym = symbol.upper().strip()
    con = get_conn()
    con.execute("DELETE FROM portfolio WHERE symbol = ?", (sym,))
    con.execute("INSERT INTO portfolio VALUES (?, ?, ?)", (sym, buy_price, quantity))
    con.close()
    return {"ok": True, "msg": f"{sym} 업서트 완료"}

@router.post("/portfolio/delete")
def delete_portfolio(symbol: str):
    ensure_portfolio_table()
    sym = symbol.upper().strip()
    con = get_conn()
    con.execute("DELETE FROM portfolio WHERE symbol = ?", (sym,))
    con.close()
    return {"ok": True, "msg": f"{sym} 삭제 완료"}

@router.get("/portfolio/list")
def list_portfolio():
    ensure_portfolio_table()
    con = get_conn()
    rows = con.execute("SELECT symbol, buy_price, quantity FROM portfolio").fetchall()
    con.close()
    items = [dict(zip(["symbol","buy_price","quantity"], r)) for r in rows]
    return {"ok": True, "items": items}

# ─────────────────────────────────────────
# 유틸
def _nan_to_none(x):
    try:
        return None if (isinstance(x, float) and math.isnan(x)) else x
    except Exception:
        return x

def _latest_price_for(symbol: str) -> Dict[str, Any]:
    """prices 테이블에서 최신 1건"""
    con = get_conn()
    row = con.execute("""
        SELECT price, source, ts
        FROM prices
        WHERE symbol = ?
        ORDER BY ts DESC
        LIMIT 1
    """, (symbol,)).fetchone()
    con.close()
    if not row:
        return {"price": None, "source": None, "asof": None}
    price = _nan_to_none(float(row[0]) if row[0] is not None else None)
    # ts가 파이썬 datetime이면 isoformat, 아니면 문자열 변환
    ts = row[2]
    if hasattr(ts, "isoformat"):
        asof = ts.isoformat() + "Z" if not str(ts).endswith("Z") else ts.isoformat()
    else:
        asof = str(ts)
    return {"price": price, "source": row[1], "asof": asof}

# ─────────────────────────────────────────
# PnL 계산
@router.get("/portfolio/pnl")
def portfolio_pnl() -> Dict[str, Any]:
    ensure_portfolio_table()
    con = get_conn()
    rows = con.execute("SELECT symbol, buy_price, quantity FROM portfolio").fetchall()
    con.close()

    items: List[Dict[str, Any]] = []
    total_cost = 0.0
    total_value = 0.0

    for sym, buy_price, qty in rows:
        sym_u = sym.upper().strip()
        latest = _latest_price_for(sym_u)
        cur = latest["price"]
        cost = (buy_price or 0.0) * (qty or 0.0)
        value = (cur * qty) if (cur is not None and qty is not None) else None
        profit = (value - cost) if (value is not None) else None
        profit_pct = ((profit / cost) * 100.0) if (profit is not None and cost and cost != 0.0) else None

        # 총계 집계 (None 방지)
        total_cost += cost or 0.0
        total_value += (value or 0.0)

        items.append({
            "symbol": sym_u,
            "buy_price": buy_price,
            "quantity": qty,
            "last_price": cur,
            "asof": latest["asof"],
            "value": None if value is None else float(value),
            "cost": float(cost),
            "profit": None if profit is None else float(profit),
            "profit_pct": None if profit_pct is None else float(profit_pct),
        })

    total_profit = total_value - total_cost
    total_profit_pct = (total_profit / total_cost * 100.0) if total_cost else None

    return {
        "ok": True,
        "items": items,
        "summary": {
            "total_cost": float(total_cost),
            "total_value": float(total_value),
            "total_profit": float(total_profit),
            "total_profit_pct": None if total_profit_pct is None else float(total_profit_pct),
            "asof": dt.datetime.now(dt.timezone.utc).isoformat()
        }
    }

# ─────────────────────────────────────────
# 단순 추천 룰 (초기 뼈대)
@router.get("/portfolio/reco")
def portfolio_reco() -> Dict[str, Any]:
    pnl = portfolio_pnl()
    if not pnl.get("ok"):
        return {"ok": False, "error": "pnl failed"}

    take_profit = float(os.getenv("RECO_TAKE_PROFIT_PCT", "20"))   # +20% 이상
    stop_loss   = float(os.getenv("RECO_STOP_LOSS_PCT", "-10"))    # -10% 이하
    add_on_dip  = float(os.getenv("RECO_ADD_ON_DIP_PCT", "-5"))    # -5%~-10% 사이 추가매수 관심

    recs: List[Dict[str, Any]] = []
    for it in pnl["items"]:
        sym = it["symbol"]
        pp  = it.get("profit_pct")
        lp  = it.get("last_price")
        if pp is None or lp is None:
            recs.append({
                "symbol": sym, "action": "watch",
                "reason": "가격/손익 불충분", "note": "데이터 누락",
            })
            continue

        # 규칙 적용
        if pp >= take_profit:
            recs.append({
                "symbol": sym, "action": "trim",
                "reason": f"수익 {pp:.1f}% ≥ 익절 기준 {take_profit:.0f}%",
                "suggestion": "부분익절 고려",
            })
        elif stop_loss <= pp < 0:
            if pp <= float(add_on_dip):
                recs.append({
                    "symbol": sym, "action": "add",
                    "reason": f"조정 {pp:.1f}% ≤ 추가매수 관심 {add_on_dip:.0f}%",
                    "suggestion": "분할매수 관심",
                })
            else:
                recs.append({
                    "symbol": sym, "action": "hold",
                    "reason": f"소폭 하락 {pp:.1f}%",
                    "suggestion": "관망",
                })
        elif pp < stop_loss:
            recs.append({
                "symbol": sym, "action": "cut",
                "reason": f"손실 {pp:.1f}% ≤ 손절 기준 {stop_loss:.0f}%",
                "suggestion": "리스크 관리",
            })
        else:
            recs.append({
                "symbol": sym, "action": "hold",
                "reason": f"중립 {pp:.1f}%",
                "suggestion": "보유",
            })

    return {
        "ok": True,
        "rules": {
            "take_profit_pct": take_profit,
            "stop_loss_pct": stop_loss,
            "add_on_dip_pct": add_on_dip,
        },
        "recommendations": recs,
        "pnl": pnl["summary"]
    }
