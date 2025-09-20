import time, datetime as dt
from typing import Iterable, List, Dict, Any
from .db import get_conn

def load_watchlist() -> List[str]:
    # recommend_api의 워치리스트를 그대로 재사용
    try:
        from .recommend_api import get_recommendations
        base = get_recommendations(user_id="default")
        rec = base.get("recommendations", {}) or {}
        # 보유 + 신규 후보의 심볼을 모두 워치리스트로 사용
        syms = {*(h["symbol"] for h in base.get("holdings", [])),
                *(r["symbol"] for r in rec.get("existing", [])),
                *(r["symbol"] for r in rec.get("new", []))}
        return sorted(syms)
    except Exception:
        # 실패 시 기본값 (필요시 환경변수/파일로 교체 가능)
        return ["NVDA","AAPL","AMZN","GOOGL","ORCL","PLTR"]

def fetch_prices(symbols: Iterable[str]) -> List[Dict[str, Any]]:
    out = []
    try:
        import yfinance as yf
    except Exception as e:
        return [{"symbol": s, "ok": False, "error": f"yfinance missing: {e}"} for s in symbols]

    for s in symbols:
        sym = s.strip().upper()
        price, source = None, None
        try:
            t = yf.Ticker(sym)
            fi = getattr(t, "fast_info", None)
            if fi and "lastPrice" in fi and fi["lastPrice"]:
                price = float(fi["lastPrice"]); source = "fast_info.lastPrice"
            if price is None:
                hist = t.history(period="1d", interval="1d", auto_adjust=True)
                if not hist.empty:
                    price = float(hist["Close"].iloc[-1]); source = "history.Close[-1]"
        except Exception as e:
            out.append({"symbol": sym, "ok": False, "error": str(e)})
            continue
        if price is not None:
            out.append({"symbol": sym, "ok": True, "price": price, "source": source})
        else:
            out.append({"symbol": sym, "ok": False, "error": "no price"})
    return out

def ensure_table():
    con = get_conn()
    con.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            ts TIMESTAMP,
            symbol TEXT,
            price DOUBLE,
            source TEXT
        )
    """)
    con.close()

def insert_prices(rows: List[Dict[str, Any]]):
    con = get_conn()
    now = dt.datetime.utcnow()
    for r in rows:
        if r.get("ok"):
            con.execute("INSERT INTO prices (ts,symbol,price,source) VALUES (?,?,?,?)",
                        (now, r["symbol"], float(r["price"]), r.get("source") or "unknown"))
    con.close()

def collect_once():
    ensure_table()
    syms = load_watchlist()
    rows = fetch_prices(syms)
    insert_prices(rows)
    ok = sum(1 for r in rows if r.get("ok"))
    fail = len(rows) - ok
    return {"ok": True, "fetched": len(rows), "inserted": ok, "failed": fail, "symbols": syms}

if __name__ == "__main__":
    # 기본: 60초 주기 수집 루프
    interval = int(__import__("os").environ.get("COLLECT_INTERVAL_SEC", "60"))
    print(f"[collector] start interval={interval}s")
    ensure_table()
    while True:
        res = collect_once()
        print("[collector]", res)
        time.sleep(interval)
