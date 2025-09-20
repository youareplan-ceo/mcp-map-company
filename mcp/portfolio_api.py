from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from typing import Dict, Any
from .db import get_conn

router = APIRouter(tags=["portfolio"])  # ✅ prefix 제거

class UpsertHolding(BaseModel):
    user_id: str = Field(default="default")
    symbol: str
    shares: float
    avg_cost: float
    currency: str = "USD"

@router.post("/upsert")
def upsert_holding(req: UpsertHolding) -> Dict[str, Any]:
    con = get_conn()
    con.execute("INSERT INTO holdings (user_id, symbol, shares, avg_cost, currency, updated_at) VALUES (?, ?, ?, ?, ?, now())",
               (req.user_id, req.symbol.upper(), float(req.shares), float(req.avg_cost), req.currency.upper()))
    con.close()
    return {"ok": True, "symbol": req.symbol.upper(), "shares": req.shares, "avg_cost": req.avg_cost, "currency": req.currency.upper()}

@router.get("/holdings")
def list_holdings(user_id: str = Query("default")) -> Dict[str, Any]:
    con = get_conn()
    rows = con.execute("SELECT user_id, symbol, shares, avg_cost, currency, updated_at FROM holdings_latest WHERE user_id = ? ORDER BY symbol", (user_id,)).fetchall()
    con.close()
    return {"ok": True, "user_id": user_id,
            "items": [dict(zip(["user_id","symbol","shares","avg_cost","currency","updated_at"], r)) for r in rows]}
