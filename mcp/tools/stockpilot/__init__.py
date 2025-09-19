import duckdb, json, sys, os

DB = os.getenv("SP_DB_PATH", "data/stock_signals.duckdb")

def handle(action: str, payload: dict):
    if action != "signals.latest":
        return {"error":"unknown action"}
    limit = int(payload.get("limit") or 100)
    con = duckdb.connect(DB, read_only=True)
    row = con.execute("SELECT run_id FROM runs ORDER BY ts_epoch DESC LIMIT 1").fetchone()
    if not row:
        return {"run_id": None, "signals": []}
    run_id = row[0]
    rows = con.execute("""
      SELECT ticker, last_close, rsi14, atr_pct, signal, crossed, fast, slow, avg_vol20
      FROM signals WHERE run_id=? ORDER BY signal, rsi14 DESC, last_close DESC LIMIT ?
    """, [run_id, limit]).fetchall()
    con.close()
    return {"run_id": run_id, "signals":[
      {"ticker":r[0], "last_close":r[1], "rsi14":r[2], "atr_pct":r[3],
       "signal":r[4], "crossed":r[5], "fast":r[6], "slow":r[7], "avg_vol20":r[8]}
      for r in rows
    ]}

if __name__ == "__main__":
    # CLI: python -m mcp.tools.stockpilot signals.latest '{"limit":20}'
    action = sys.argv[1]
    payload = json.loads(sys.argv[2]) if len(sys.argv)>2 else {}
    print(json.dumps(handle(action, payload), ensure_ascii=False))
