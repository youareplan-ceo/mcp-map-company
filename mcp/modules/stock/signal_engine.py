import os, time, re, concurrent.futures
import numpy as np
import pandas as pd
from .schema import Signal

def _mode():
    return os.getenv("STOCK_SIGNAL_MODE", "MOCK").upper()

# ---------- 튜닝 파라미터(환경변수) ----------
def _f(name, default):
    try: return float(os.getenv(name, str(default)))
    except: return float(default)

def _i(name, default):
    try: return int(os.getenv(name, str(default)))
    except: return int(default)

# 데이터 받기
YF_TIMEOUT  = _f("STOCK_SIGNAL_YF_TIMEOUT", 5.0)
YF_PERIOD   = os.getenv("STOCK_SIGNAL_YF_PERIOD", "2y")
YF_INTERVAL = os.getenv("STOCK_SIGNAL_YF_INTERVAL", "1d")

# 동시성/캐시
MAX_WORKERS = _i("STOCK_SIGNAL_MAX_WORKERS", 12)
CACHE_TTL   = _f("STOCK_SIGNAL_CACHE_TTL", 60.0)

# ----- 규칙 임계값(튜닝용) -----
RSI_OVERBOUGHT = _f("SP_RSI_OVERBOUGHT", 70.0)  # 70→75로 올리면 더 보수적
RSI_OVERSOLD   = _f("SP_RSI_OVERSOLD", 30.0)    # 30→25로 내리면 더 공격적
GAP_UP_PCT     = _f("SP_GAP_BREAKOUT_PCT", 0.03) # 0.03=+3%
GAP_DN_PCT     = _f("SP_GAP_BREAKDOWN_PCT", 0.03)# 0.03=-3%
VOL_SURGE_X    = _f("SP_VOLUME_SURGE_MULT", 1.8) # 1.8배 이상 급증

RISK_BELOW200  = _f("SP_RISK_BELOW_200MA_PCT", 0.03) # 200MA보다 3% 밑이면 리스크

# ----- 가중치(룰의 영향력) -----
W_MA    = _f("SP_WEIGHT_MA",    1.0)
W_VOL   = _f("SP_WEIGHT_VOL",   1.0)
W_GAP   = _f("SP_WEIGHT_GAP",   1.0)
W_RSI   = _f("SP_WEIGHT_RSI",   1.0)
W_RISK  = _f("SP_WEIGHT_RISK",  1.0)

# ----- 액션 임계점(총점→BUY/SELL) -----
SCORE_BUY_TH   = _f("SP_SCORE_BUY_THRESHOLD", 2.0)   # 2 이상이면 BUY
SCORE_SELL_TH  = _f("SP_SCORE_SELL_THRESHOLD", -2.0) # -2 이하 SELL

# ----- 신뢰도 계산 계수 -----
CONF_BASE  = _f("SP_CONF_BASE", 0.5)
CONF_SLOPE = _f("SP_CONF_SLOPE", 0.15)

_SPAC_SUFFIX = ("-U","-W","-R","-S")
_NUM6       = re.compile(r'^\d{6}$')
_SPAC_TAIL  = re.compile(r'^[A-Z0-9]{1,5}[UWRS]$')  # AACIU/AACIW/AACBR 등

def _chunked(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i+size]

def _rsi(series, window=14):
    diff = series.diff().dropna()
    up = diff.clip(lower=0); down = -diff.clip(upper=0)
    rs = (up.rolling(window).mean()) / (down.rolling(window).mean().replace(0, np.nan))
    return 100 - (100 / (1 + rs))

def _mk(ticker, score, reasons, horizon="D"):
    if score >= SCORE_BUY_TH: action = "BUY"
    elif score <= SCORE_SELL_TH: action = "SELL"
    else: action = "HOLD"
    conf = min(0.9, CONF_BASE + CONF_SLOPE*abs(score))
    return Signal(ticker=ticker, action=action, confidence=round(conf,2),
                  horizon=horizon, reasons=(reasons[:6] if reasons else ["neutral: no rule hit"]))

def _signals_mock(tickers, horizon="D"):
    out=[]
    for sym,_,_ in tickers:
        h=sum(ord(c) for c in sym)%10; score=0; reasons=[]
        if h in (0,1,2): score+=2; reasons.append("mock: momentum strong")
        if h in (3,4): score-=2; reasons.append("mock: momentum weak")
        if h in (5,6): score+=1; reasons.append("mock: volume uptick")
        if h in (7,):  score-=1; reasons.append("mock: mean-revert risk")
        out.append(_mk(sym,score,reasons,horizon))
    return out

def _yf_candidates(sym_raw: str):
    s = sym_raw.upper().replace(".","-")
    if s.endswith(_SPAC_SUFFIX) or _SPAC_TAIL.match(s):
        return []
    if _NUM6.match(s):
        return [f"{s}.KS", f"{s}.KQ"]
    return [s]

def _dl_prices_yf(sym_raw):
    import yfinance as yf
    cands = _yf_candidates(sym_raw)
    if not cands:
        raise RuntimeError("skip_spac_tail")
    last_err = None
    for sy in cands:
        try:
            start=time.time()
            df = yf.download(sy, period=YF_PERIOD, interval=YF_INTERVAL,
                             progress=False, auto_adjust=False, threads=False)
            if df is not None and not df.empty:
                return df
            last_err = RuntimeError("no_data")
        except Exception as e:
            last_err = e
        if (time.time() - start) > YF_TIMEOUT:
            last_err = TimeoutError("yf_timeout")
    if last_err: raise last_err
    raise RuntimeError("no_data")

_CACHE = {}  # sym_raw -> (ts, df)
def _dl_prices_cached(sym_raw):
    now=time.time()
    rec=_CACHE.get(sym_raw)
    if rec and (now-rec[0])<CACHE_TTL:
        return rec[1]
    df=_dl_prices_yf(sym_raw)
    _CACHE[sym_raw]=(now, df)
    return df

def _flatten_for(sym, df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        try:
            if df.columns.nlevels>=2 and sym in df.columns.get_level_values(-1):
                df = df.xs(sym, axis=1, level=-1)
            else:
                df.columns = [str(c[0]) if isinstance(c, tuple) else str(c) for c in df.columns]
        except Exception:
            df.columns = [str(c[0]) if isinstance(c, tuple) else str(c) for c in df.columns]
    return df

def _one_live(sym, horizon="D"):
    try:
        df = _dl_prices_cached(sym)
        df = _flatten_for(sym.upper().replace(".","-"), df)
    except Exception as e:
        kind = type(e).__name__; msg = (e.args[0] if getattr(e,"args",None) else "")
        return _mk(sym, 0, [f"live: fetch_fail:{msg or kind}"], horizon)

    cols={str(c).lower():c for c in df.columns}
    pick=lambda k: df[cols[k]] if k in cols else None
    close=pick("close"); open_=pick("open"); high=pick("high"); low=pick("low"); vol=pick("volume")
    if close is None or vol is None or len(close.dropna())<60:
        return _mk(sym, 0, ["live: short_or_missing"], horizon)

    close=close.dropna(); vol=vol.dropna()
    sma50=close.rolling(50).mean(); sma200=close.rolling(200).mean()
    rsi14=_rsi(close,14); vavg20=vol.rolling(20).mean()

    score=0; reasons=[]

    # 1) 추세(이평)
    if not np.isnan(sma50.iloc[-1]) and not np.isnan(sma200.iloc[-1]):
        if sma50.iloc[-1]>sma200.iloc[-1] and close.iloc[-1]>sma50.iloc[-1]:
            score+=W_MA; reasons.append("ma: uptrend (50>200 & px>50)")
        if sma50.iloc[-1]<sma200.iloc[-1] and close.iloc[-1]<sma200.iloc[-1]:
            score-=W_MA; reasons.append("ma: downtrend (50<200 & px<200)")

    # 2) 거래량 급증
    if not np.isnan(vavg20.iloc[-1]) and vavg20.iloc[-1]>0:
        if vol.iloc[-1] > VOL_SURGE_X * vavg20.iloc[-1]:
            score+=W_VOL; reasons.append(f"volume: surge>{VOL_SURGE_X:.1f}x 20d")

    # 3) 갭
    if open_ is not None and high is not None and low is not None and len(open_)>=2 and len(high)>=2 and len(low)>=2:
        prev_high=float(high.iloc[-2]); prev_low=float(low.iloc[-2])
        if float(open_.iloc[-1]) >= (1.0 + GAP_UP_PCT) * prev_high:
            score+=W_GAP; reasons.append(f"gap: breakout >={int(GAP_UP_PCT*100)}%")
        elif float(open_.iloc[-1]) <= (1.0 - GAP_DN_PCT) * prev_low:
            score-=W_GAP; reasons.append(f"gap: breakdown <={int(GAP_DN_PCT*100)}%")

    # 4) RSI
    if not np.isnan(rsi14.iloc[-1]):
        if rsi14.iloc[-1] < RSI_OVERSOLD:
            score+=W_RSI; reasons.append(f"rsi: oversold {rsi14.iloc[-1]:.1f}<{RSI_OVERSOLD:.0f}")
        elif rsi14.iloc[-1] > RSI_OVERBOUGHT:
            score-=W_RSI; reasons.append(f"rsi: overbought {rsi14.iloc[-1]:.1f}>{RSI_OVERBOUGHT:.0f}")

    # 5) 200MA 리스크
    if not np.isnan(sma200.iloc[-1]) and close.iloc[-1] < (1.0 - RISK_BELOW200) * sma200.iloc[-1]:
        score-=W_RISK; reasons.append(f"risk: below 200MA by >={int(RISK_BELOW200*100)}%")

    return _mk(sym, score, reasons, horizon)

def make_signals(tickers, horizon="D"):
    if _mode()=="LIVE":
        return [_one_live(t[0], horizon=horizon) for t in tickers]
    return _signals_mock(tickers, horizon=horizon)

def make_signals_chunked(tickers, horizon="D", batch_size=500):
    out=[]
    for batch in _chunked(tickers, max(1,batch_size)):
        if _mode()=="LIVE":
            with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,MAX_WORKERS)) as ex:
                futs=[ex.submit(_one_live, t[0], horizon) for t in batch]
                for f in futs:
                    try:
                        out.append(f.result())
                    except Exception as e:
                        out.append(_mk("UNKNOWN", 0, [f"live: worker_fail:{type(e).__name__}"], horizon))
        else:
            out.extend(_signals_mock(batch, horizon=horizon))
    return out
