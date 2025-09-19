import json, datetime as dt
from pathlib import Path
import duckdb

RANKED = Path("db/news_ranked.json")

def persist():
    try:
        ranked = json.loads(RANKED.read_text(encoding="utf-8") or "[]")
    except Exception:
        ranked = []
    con = duckdb.connect("duckdb/stocks.db")
    rows = []
    for a in ranked:
        rows.append((
            a.get("symbol"),
            dt.datetime.fromisoformat((a.get("publishedAt") or "1970-01-01T00:00:00").replace("Z","+00:00")),
            a.get("title"),
            a.get("url"),
            a.get("source"),
            float(a.get("score") or 0.0),
        ))
    con.execute("BEGIN")
    con.execute("CREATE TABLE IF NOT EXISTS news (symbol TEXT, ts TIMESTAMP, title TEXT, url TEXT, source TEXT, score DOUBLE)")
    if rows:
        con.executemany("INSERT INTO news VALUES (?, ?, ?, ?, ?, ?)", rows)
    con.execute("COMMIT")
    con.close()
    print(f"[news.store] inserted {len(rows)} rows into duckdb/stocks.db.news")
