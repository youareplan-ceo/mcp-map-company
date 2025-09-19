from typing import Dict, Any, List, Optional
import math

def _to_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        if isinstance(v, str):
            t = v.strip()
            if t == "":
                return None
            v = float(t)
        else:
            v = float(v)
        if math.isnan(v):
            return None
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
        out.append(sum(win)/n if len(win) == n else None)
    return out

def run(action: str, payload: Dict[str, Any]):
    payload = payload or {}
    if action == "sma_cross":
        closes = payload.get("close", [])
        fast_n = int(payload.get("fast", 5))
        slow_n = int(payload.get("slow", 20))

        closes_f = [_to_float(x) for x in closes]
        if len([x for x in closes_f if x is not None]) < slow_n + 1:
            return {"error": "not enough data"}

        sma_f = _sma(closes_f, fast_n)
        sma_s = _sma(closes_f, slow_n)
        last  = len(closes_f) - 1

        fast_last = sma_f[last]
        slow_last = sma_s[last]
        fast_prev = sma_f[last-1] if last-1 >= 0 else None
        slow_prev = sma_s[last-1] if last-1 >= 0 else None

        signal = "neutral"
        crossed = None
        if (fast_prev is not None and slow_prev is not None and
            fast_last is not None and slow_last is not None):
            if fast_prev <= slow_prev and fast_last > slow_last:
                signal, crossed = "golden_cross", "up"
            elif fast_prev >= slow_prev and fast_last < slow_last:
                signal, crossed = "death_cross", "down"

        return {
            "signal": signal,
            "fast": fast_n,
            "slow": slow_n,
            "fast_ma": fast_last,
            "slow_ma": slow_last,
            "crossed": crossed,
            "last_close": closes_f[last],
        }
    return {"error":"unknown action"}
