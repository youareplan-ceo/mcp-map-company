import os
import datetime as dt
from typing import Dict, Any
import pandas as pd

def get_weights():
    """
    환경변수로 가중치 제어
    RECO_W_TREND, RECO_W_RSI, RECO_W_MOM (기본 1.0)
    """
    try:
        w_trend = float(os.getenv("RECO_W_TREND", 1.0))
        w_rsi   = float(os.getenv("RECO_W_RSI",   1.0))
        w_mom   = float(os.getenv("RECO_W_MOM",   1.0))
    except Exception:
        w_trend, w_rsi, w_mom = 1.0, 1.0, 1.0
    return w_trend, w_rsi, w_mom

def _rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / (avg_loss.replace(0, 1e-9))
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1])

def _sma(series: pd.Series, n: int) -> float:
    return float(series.rolling(n).mean().iloc[-1])

def fetch_indicators(symbol: str) -> Dict[str, Any]:
    """yfinance로 6개월 일봉을 가져와 RSI/SMA/모멘텀 계산"""
    try:
        import yfinance as yf
        sym = symbol.upper().strip()
        tkr = yf.Ticker(sym)
        hist = tkr.history(period="6mo", interval="1d", auto_adjust=True)
        if hist.empty:
            return {"ok": False, "error": "empty history", "symbol": sym}
        close = hist["Close"].dropna()
        price = float(close.iloc[-1])
        sma20 = _sma(close, 20)
        sma50 = _sma(close, 50)
        sma200 = _sma(close, 200) if len(close) >= 200 else None
        rsi14 = _rsi(close, 14)

        # SMA20 모멘텀: 최근 5일 기울기(증가면 +)
        sma20_series = close.rolling(20).mean().dropna()
        mom = None
        if len(sma20_series) >= 6:
            mom = float(sma20_series.iloc[-1] - sma20_series.iloc[-6])

        return {
            "ok": True,
            "symbol": sym,
            "price": price,
            "rsi14": rsi14,
            "sma20": sma20,
            "sma50": sma50,
            "sma200": sma200,
            "momentum20_5d": mom,
            "asof": dt.datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "symbol": symbol}

def score_from_indicators(ind: Dict[str, Any]) -> Dict[str, Any]:
    """
    컴포넌트별 점수(0~1)를 가중 평균 → 최종 0~5로 스케일
    - trend: 가격과 SMA 관계
    - rsi: 14일 RSI 구간
    - mom: 20일 SMA의 5일 변화량(+이면 우상향)
    """
    if not ind.get("ok"):
        return {"score": 0.0, "why": [f"데이터오류: {ind.get('error','unknown')}"]}

    price = ind["price"]
    sma50 = ind["sma50"]
    sma200 = ind.get("sma200")
    rsi = ind["rsi14"]
    mom = ind.get("momentum20_5d")

    # 1) Trend component (0~1)
    if sma200:
        if price > sma50 > sma200:
            trend_comp = 1.0
            trend_note = "P>SMA50>SMA200"
        elif price > sma50:
            trend_comp = 0.7
            trend_note = "P>SMA50"
        else:
            trend_comp = 0.2
            trend_note = "P<=SMA50"
    else:
        if price > sma50:
            trend_comp = 0.7
            trend_note = "P>SMA50"
        else:
            trend_comp = 0.2
            trend_note = "P<=SMA50"

    # 2) RSI component (0~1)
    if 50 <= rsi <= 70:
        rsi_comp = 1.0; rsi_note = "RSI 50~70"
    elif 40 <= rsi < 50:
        rsi_comp = 0.6; rsi_note = "RSI 40~50"
    elif rsi > 70:
        rsi_comp = 0.3; rsi_note = "RSI >70 과열"
    elif rsi < 30:
        rsi_comp = 0.5; rsi_note = "RSI <30 과매도"
    else:
        rsi_comp = 0.4; rsi_note = "RSI 중립"

    # 3) Momentum component (0~1)
    if mom is not None and mom > 0:
        mom_comp = 1.0; mom_note = "SMA20 상승"
    else:
        mom_comp = 0.3; mom_note = "SMA20 정체/하락"

    # 가중 평균 → 0~5 스케일
    w_trend, w_rsi, w_mom = get_weights()
    w_sum = max(1e-9, w_trend + w_rsi + w_mom)
    weighted = (trend_comp*w_trend + rsi_comp*w_rsi + mom_comp*w_mom) / w_sum
    score = float(max(0.0, min(5.0, 5.0 * weighted)))

    why = [
        f"추세:{trend_comp:.2f}({trend_note})×{w_trend}",
        f"RSI:{rsi_comp:.2f}({rsi_note})×{w_rsi}",
        f"모멘텀:{mom_comp:.2f}({mom_note})×{w_mom}",
        f"합산:{score:.2f}"
    ]
    return {"score": score, "why": why}
