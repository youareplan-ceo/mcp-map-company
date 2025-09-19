from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import duckdb, os

DB = os.getenv("SP_DB_PATH","data/stock_signals.duckdb")

app = FastAPI(title="MCP ControlTower API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    try:
        con = duckdb.connect(DB, read_only=True)
        con.execute("select 1")
        con.close()
        return {"ok": True, "db": DB}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/signals/latest")
def latest(
    limit: int = Query(100, ge=1, le=500),
    min_rsi: float | None = None,
    max_rsi: float | None = None,
    min_atr: float | None = None,
    max_atr: float | None = None,
    signal: list[str] | None = Query(default=None)  # ex) ?signal=BUY&signal=WATCH
):
    con = duckdb.connect(DB, read_only=True)
    row = con.execute("SELECT run_id FROM runs ORDER BY ts_epoch DESC LIMIT 1").fetchone()
    if not row:
        con.close()
        return {"run_id": None, "signals": []}
    run_id = row[0]

    # 동적 WHERE 구성
    where = ["run_id = ?"]
    args = [run_id]
    if min_rsi is not None:
        where.append("rsi14 >= ?"); args.append(min_rsi)
    if max_rsi is not None:
        where.append("rsi14 <= ?"); args.append(max_rsi)
    if min_atr is not None:
        where.append("atr_pct >= ?"); args.append(min_atr)
    if max_atr is not None:
        where.append("atr_pct <= ?"); args.append(max_atr)
    if signal:
        qs = ",".join(["?"]*len(signal))
        where.append(f"signal IN ({qs})"); args.extend(signal)

    sql = f"""
      SELECT ticker, last_close, rsi14, atr_pct, signal, crossed, fast, slow, avg_vol20
      FROM signals
      WHERE {" AND ".join(where)}
      ORDER BY signal, rsi14 DESC, last_close DESC
      LIMIT ?
    """
    args.append(limit)
    rows = con.execute(sql, args).fetchall()
    con.close()

    return JSONResponse({
      "run_id": run_id,
      "signals": [
        {"ticker":r[0], "last_close":r[1], "rsi14":r[2], "atr_pct":r[3],
         "signal":r[4], "crossed":bool(r[5]), "fast":r[6], "slow":r[7], "avg_vol20":r[8]}
        for r in rows
      ]
    })
