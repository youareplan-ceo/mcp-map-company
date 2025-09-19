from typing import Dict, Any, List, Optional
import yfinance as yf
import pandas as pd
import math
from pathlib import Path

def _to_float(v) -> Optional[float]:
    if v is None: return None
    try:
        if isinstance(v, str):
            t = v.strip()
            if t == "": return None
            v = float(t)
        else:
            v = float(v)
        if math.isnan(v): return None
        return v
    except Exception:
        return None

def _sma(vals: List[Optional[float]], n: int) -> List[Optional[float]]:
    out: List[Optional[float]] = []
    buf: List[Optional[float]] = []
    for v in vals:
        fv = _to_float(v)
        buf.append(fv)
        win = [x for x in buf[-n:] if x is not None]
        out.append(sum(win)/n if len(win)==n else None)
    return out

def _read_tickers_csv(path: str) -> List[str]:
    p = Path(path)
    if not p.exists():
        return []
    df = pd.read_csv(p)
    col = df.columns[0]
    vals = [str(x).strip() for x in df[col].tolist() if str(x).strip()]
    vals = [v for v in vals if not v.startswith("#")]
    return list(dict.fromkeys(vals))

def _fetch_ohlcv(ticker: str, period="3mo", interval="1d"):
    t = yf.Ticker(ticker)
    df = t.history(period=period, interval=interval, auto_adjust=False)
    if df.empty:
        return None
    df = df.reset_index()
    df.rename(columns=str.lower, inplace=True)
    opens  = [_to_float(x) for x in df["open"].tolist()]
    highs  = [_to_float(x) for x in df["high"].tolist()]
    lows   = [_to_float(x) for x in df["low"].tolist()]
    closes = [_to_float(x) for x in df["close"].tolist()]
    vols   = [None if pd.isna(x) else int(x) for x in df["volume"].fillna(0).tolist()]
    last_close = closes[-1]
    # 20일 평균 거래량
    window = [x for x in vols[-20:] if x is not None]
    avg_vol20 = int(sum(window)/len(window)) if window else 0
    return {
        "rows": len(df),
        "opens": opens,
        "highs": highs,
        "lows": lows,
        "closes": closes,
        "vols": vols,
        "last_close": last_close,
        "avg_vol20": avg_vol20,
    }

def _sma_cross(closes: List[Optional[float]], fast=5, slow=20):
    if not closes or len([x for x in closes if x is not None]) < slow+1:
        return {"signal":"neutral", "fast_ma":None, "slow_ma":None, "crossed":None}
    sma_f = _sma(closes, fast)
    sma_s = _sma(closes, slow)
    last = len(closes)-1
    fast_last, slow_last = sma_f[last], sma_s[last]
    fast_prev = sma_f[last-1] if last-1 >= 0 else None
    slow_prev = sma_s[last-1] if last-1 >= 0 else None

    signal, crossed = "neutral", None
    if (fast_prev is not None and slow_prev is not None and
        fast_last is not None and slow_last is not None):
        if fast_prev <= slow_prev and fast_last > slow_last:
            signal, crossed = "golden_cross", "up"
        elif fast_prev >= slow_prev and fast_last < slow_last:
            signal, crossed = "death_cross", "down"
    return {
        "signal": signal,
        "fast_ma": fast_last,
        "slow_ma": slow_last,
        "crossed": crossed,
    }

def _rsi14(closes: List[Optional[float]], n: int = 14) -> Optional[float]:
    vals = [x for x in closes]
    if len([x for x in vals if x is not None]) < n+1:
        return None
    # Wilder 방식
    deltas = []
    for i in range(1, len(vals)):
        if vals[i] is None or vals[i-1] is None:
            deltas.append(None)
        else:
            deltas.append(vals[i] - vals[i-1])
    gains = [max(d,0) if d is not None else None for d in deltas]
    losses = [abs(min(d,0)) if d is not None else None for d in deltas]

    # 초기 평균
    g_init = [x for x in gains[:n] if x is not None]
    l_init = [x for x in losses[:n] if x is not None]
    if len(g_init) < n or len(l_init) < n:
        return None
    avg_gain = sum(g_init)/n
    avg_loss = sum(l_init)/n

    # 이후 smoothed
    for i in range(n, len(deltas)):
        g = gains[i] if gains[i] is not None else 0.0
        l = losses[i] if losses[i] is not None else 0.0
        avg_gain = (avg_gain*(n-1) + g) / n
        avg_loss = (avg_loss*(n-1) + l) / n

    if avg_loss == 0:
        return 100.0
    rs = avg_gain/avg_loss
    return 100.0 - (100.0/(1.0+rs))

def _atr14(highs: List[Optional[float]], lows: List[Optional[float]], closes: List[Optional[float]], n: int = 14) -> Optional[float]:
    if not highs or not lows or not closes:
        return None
    if len(highs) != len(lows) or len(highs) != len(closes):
        return None
    if len([x for x in closes if x is not None]) < n+1:
        return None
    TRs: List[Optional[float]] = []
    prev_close = None
    for i in range(len(highs)):
        h, l, c = highs[i], lows[i], closes[i]
        if h is None or l is None or c is None:
            TRs.append(None)
        else:
            if prev_close is None:
                tr = h - l
            else:
                tr = max(h - l, abs(h - prev_close), abs(l - prev_close))
            TRs.append(tr)
        prev_close = c
    # 마지막 n개가 유효해야 평균 계산
    window = [x for x in TRs[-n:] if x is not None]
    if len(window) < n:
        return None
    return sum(window)/n

def run(action: str, payload: Dict[str, Any]):
    payload = payload or {}
    if action != "batch_sma":
        return {"error":"unknown action"}

    tickers: List[str] = (payload.get("tickers") or [])[:]
    csv_path = payload.get("csv_path")
    if csv_path:
        tickers += _read_tickers_csv(csv_path)
    tickers = [t for t in tickers if t]
    if not tickers:
        return {"error":"no tickers"}

    period   = payload.get("period", "3mo")
    interval = payload.get("interval", "1d")
    fast     = int(payload.get("fast", 5))
    slow     = int(payload.get("slow", 20))

    # 필터 (옵션)
    min_last_close  = _to_float(payload.get("min_last_close"))
    min_avg_vol20   = payload.get("min_avg_vol20")
    min_avg_vol20   = int(min_avg_vol20) if min_avg_vol20 not in (None, "",) else None
    min_rsi         = _to_float(payload.get("min_rsi"))   # 예: 40
    max_rsi         = _to_float(payload.get("max_rsi"))   # 예: 80
    min_atr_pct     = _to_float(payload.get("min_atr_pct")) # 예: 0.5 (%)
    max_atr_pct     = _to_float(payload.get("max_atr_pct")) # 예: 5.0

    results: List[Dict[str, Any]] = []
    for tk in tickers:
        data = _fetch_ohlcv(tk, period=period, interval=interval)
        if not data:
            results.append({"ticker": tk, "error": "no_data"})
            continue

        # 보조지표
        rsi14 = _rsi14(data["closes"], 14)
        atr14 = _atr14(data["highs"], data["lows"], data["closes"], 14)
        atr_pct = (atr14 / data["last_close"] * 100.0) if (atr14 is not None and data["last_close"]) else None

        # 조건 필터링
        if min_last_close is not None and (data["last_close"] is None or data["last_close"] < min_last_close):
            results.append({"ticker": tk, "filtered": "price", "last_close": data["last_close"]})
            continue
        if (min_avg_vol20 is not None) and (data["avg_vol20"] < min_avg_vol20):
            results.append({"ticker": tk, "filtered": "volume", "avg_vol20": data["avg_vol20"], "last_close": data["last_close"]})
            continue
        if min_rsi is not None and (rsi14 is None or rsi14 < min_rsi):
            results.append({"ticker": tk, "filtered": "rsi_min", "rsi14": rsi14, "last_close": data["last_close"]})
            continue
        if max_rsi is not None and (rsi14 is None or rsi14 > max_rsi):
            results.append({"ticker": tk, "filtered": "rsi_max", "rsi14": rsi14, "last_close": data["last_close"]})
            continue
        if min_atr_pct is not None and (atr_pct is None or atr_pct < min_atr_pct):
            results.append({"ticker": tk, "filtered": "atr_min", "atr_pct": atr_pct, "last_close": data["last_close"]})
            continue
        if max_atr_pct is not None and (atr_pct is None or atr_pct > max_atr_pct):
            results.append({"ticker": tk, "filtered": "atr_max", "atr_pct": atr_pct, "last_close": data["last_close"]})
            continue

        sig = _sma_cross(data["closes"], fast=fast, slow=slow)
        results.append({
            "ticker": tk,
            "period": period,
            "interval": interval,
            "last_close": data["last_close"],
            "avg_vol20": data["avg_vol20"],
            "fast": fast,
            "slow": slow,
            "rsi14": rsi14,
            "atr14": atr14,
            "atr_pct": atr_pct,
            **sig,
        })

    # 정렬: 골든크로스 우선 → RSI 내림차순 → 종가 내림차순
    order = {"golden_cross":0, "neutral":1, "death_cross":2}
    results.sort(key=lambda x: (
        order.get(x.get("signal","neutral"), 1),
        -(x.get("rsi14") or 0),
        -(x.get("last_close") or 0)
    ))
    return {"results": results, "count": len(results)}
