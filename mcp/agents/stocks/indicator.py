from pathlib import Path
import json, yaml
import pandas as pd
import numpy as np

RAW = Path("raw_data/stocks_prices.json")
WATCH = Path("schemas/stocks/watchlist.yaml")
OUT = Path("db/stocks_indicators.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

def rsi(series, period: int = 14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    roll_down = down.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    rs = roll_up / (roll_down.replace(0, np.nan))
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute():
    universe = []
    if WATCH.exists():
        try:
            wl = yaml.safe_load(WATCH.read_text(encoding="utf-8")) or {}
            universe = wl.get("universe", [])
        except Exception:
            pass

    rows = []
    if RAW.exists():
        try:
            data = json.loads(RAW.read_text(encoding="utf-8") or "[]")
            if isinstance(data, dict):
                for sym, arr in data.items():
                    for r in arr or []:
                        rows.append({"symbol": sym, "timestamp": r.get("timestamp"), "close": r.get("close")})
            elif isinstance(data, list):
                for r in data:
                    if "symbol" in r and "close" in r:
                        rows.append({"symbol": r["symbol"], "timestamp": r.get("timestamp"), "close": r["close"]})
        except Exception:
            pass

    if not rows:
        OUT.write_text("[]", encoding="utf-8")
        print(f"[stocks.indicator] no price rows; out={OUT} (EMPTY)")
        return

    import pandas as pd
    df = pd.DataFrame(rows)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.sort_values(["symbol","timestamp"])
    else:
        df = df.reset_index()

    results = []
    for sym, g in df.groupby("symbol"):
        g = g.copy()
        g["close"] = pd.to_numeric(g["close"], errors="coerce")
        g = g.dropna(subset=["close"])
        if g.empty:
            continue

        g["SMA_5"]  = g["close"].rolling(window=5,  min_periods=5).mean()
        g["SMA_20"] = g["close"].rolling(window=20, min_periods=20).mean()
        g["EMA_12"] = g["close"].ewm(span=12, adjust=False).mean()
        g["EMA_26"] = g["close"].ewm(span=26, adjust=False).mean()
        g["MACD"]   = g["EMA_12"] - g["EMA_26"]
        g["RSI_14"] = rsi(g["close"], period=14)

        last = g.iloc[-1]
        def val(x): 
            import pandas as pd
            return None if pd.isna(x) else float(x)
        results.append({
            "symbol": sym,
            "close": float(last["close"]),
            "SMA_5":  val(last.get("SMA_5")),
            "SMA_20": val(last.get("SMA_20")),
            "EMA_12": val(last.get("EMA_12")),
            "EMA_26": val(last.get("EMA_26")),
            "MACD":   val(last.get("MACD")),
            "RSI_14": val(last.get("RSI_14")),
        })

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[stocks.indicator] computed {len(results)} symbols -> {OUT}")

if __name__ == "__main__":
    compute()
