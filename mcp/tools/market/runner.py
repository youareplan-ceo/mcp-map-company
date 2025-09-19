from typing import Dict, Any, List
import yfinance as yf
import pandas as pd

def _to_list(series: pd.Series) -> List[float]:
    return [None if pd.isna(x) else float(x) for x in series.tolist()]

def run(action: str, payload: Dict[str, Any]):
    payload = payload or {}
    if action == "fetch_ohlcv":
        ticker   = payload.get("ticker", "AAPL")
        period   = payload.get("period", "3mo")
        interval = payload.get("interval", "1d")
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval=interval, auto_adjust=False)
        if df.empty:
            return {"error": f"no data for {ticker} {period} {interval}"}
        df = df.reset_index()
        df.rename(columns=str.lower, inplace=True)
        ts = [int(pd.Timestamp(x).timestamp()) for x in df["date"]]
        return {
            "ticker": ticker,
            "period": period,
            "interval": interval,
            "timestamp": ts,
            "open":  _to_list(df["open"]),
            "high":  _to_list(df["high"]),
            "low":   _to_list(df["low"]),
            "close": _to_list(df["close"]),
            "volume": [None if pd.isna(x) else int(x) for x in df["volume"].fillna(0)],
            "last_close": float(df["close"].iloc[-1]),
            "rows": len(df),
        }
    return {"error":"unknown action"}
