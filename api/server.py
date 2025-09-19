from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import duckdb, json

DB = Path("duckdb/stocks.db")
SUMMARY_JSON = Path("db/stocks_summary.json")
ALERTS = Path("db/alerts_candidates.json")

app = FastAPI(title="MCP Map API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _con():
    if not DB.exists():
        return None
    try:
        return duckdb.connect(str(DB), read_only=True)
    except Exception:
        return None

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/api/stockpilot/signals")
def signals(limit: int = 200):
    con = _con()
    if not con:
        return []
    q = f"""
      SELECT symbol, ts, decision, close, rationale
      FROM signals
      ORDER BY ts DESC
      LIMIT {int(limit)}
    """
    return con.execute(q).df().to_dict(orient="records")

@app.get("/api/stockpilot/news")
def news(limit: int = 200):
    con = _con()
    if not con:
        return []
    q = f"""
    WITH ranked AS (
      SELECT
        symbol, ts, score, source, title, url,
        ROW_NUMBER() OVER (PARTITION BY symbol, title ORDER BY ts DESC) AS rn
      FROM news
    )
    SELECT symbol, ts, score, source, title, url
    FROM ranked
    WHERE rn = 1
    ORDER BY ts DESC
    LIMIT {int(limit)}
    """
    return con.execute(q).df().to_dict(orient="records")

@app.get("/api/stockpilot/summary")
def summary():
    if SUMMARY_JSON.exists():
        try:
            return json.loads(SUMMARY_JSON.read_text(encoding="utf-8") or "[]")
        except Exception:
            pass
    return []

@app.get("/api/stockpilot/alerts")
def alerts():
    if not ALERTS.exists():
        return []
    try:
        return json.loads(ALERTS.read_text(encoding="utf-8") or "[]")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
