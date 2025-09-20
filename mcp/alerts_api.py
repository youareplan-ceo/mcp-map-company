from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Dict, Any
from .db import get_conn

router = APIRouter(tags=["alerts"])

class Alert(BaseModel):
    user_id: str = "default"
    symbol: str
    level: str   # e.g. "info", "warn", "critical"
    message: str

@router.post("/alerts/add")
def add_alert(alert: Alert) -> Dict[str, Any]:
    con = get_conn()
    con.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
          user_id TEXT,
          symbol TEXT,
          level TEXT,
          message TEXT,
          created_at TIMESTAMP DEFAULT now()
        )
    """)
    con.execute("""
        INSERT INTO alerts (user_id, symbol, level, message)
        VALUES (?, ?, ?, ?)
    """, (alert.user_id, alert.symbol.upper(), alert.level, alert.message))
    con.close()
    return {"ok": True, "saved": alert.dict()}

@router.get("/alerts/list")
def list_alerts(user_id: str = Query("default")) -> Dict[str, Any]:
    con = get_conn()
    rows = con.execute("""
        SELECT user_id, symbol, level, message, created_at
        FROM alerts
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 50
    """, (user_id,)).fetchall()
    con.close()
    items = [dict(zip(["user_id","symbol","level","message","created_at"], r)) for r in rows]
    return {"ok": True, "user_id": user_id, "alerts": items}
