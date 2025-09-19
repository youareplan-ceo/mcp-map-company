import json, datetime as dt
from pathlib import Path
import duckdb

IND = Path("db/stocks_indicators.json")
SIG = Path("db/stocks_signals.json")

def _load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8") or "[]")
    except Exception:
        return []

def persist():
    ind = _load_json(IND)
    sig = _load_json(SIG)
    con = duckdb.connect("duckdb/stocks.db")
    con.execute("BEGIN")

    if ind:
        con.execute("CREATE TABLE IF NOT EXISTS indicators (symbol TEXT, ts TIMESTAMP, sma5 DOUBLE, sma20 DOUBLE, macd DOUBLE)")
        rows = []
        for a in ind:
            rows.append((
                a.get("symbol"),
                dt.datetime.utcnow(),
                float(a.get("sma5") or 0),
                float(a.get("sma20") or 0),
                float(a.get("macd") or 0),
            ))
        con.executemany("INSERT INTO indicators VALUES (?, ?, ?, ?, ?)", rows)

    if sig:
        con.execute("CREATE TABLE IF NOT EXISTS signals (symbol TEXT, ts TIMESTAMP, decision TEXT, rationale TEXT, close DOUBLE)")
        rows = []
        for a in sig:
            rows.append((
                a.get("symbol"),
                dt.datetime.utcnow(),
                a.get("decision"),
                a.get("rationale"),
                float(a.get("close") or 0),
            ))
        con.executemany("INSERT INTO signals VALUES (?, ?, ?, ?, ?)", rows)

    con.execute("COMMIT")
    con.close()
    print(f"[stocks.store] inserted {len(ind)} indicators, {len(sig)} signals into duckdb")
