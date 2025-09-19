from pathlib import Path
import json

IND = Path("db/stocks_indicators.json")
OUT = Path("db/stocks_signals.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

def generate():
    if not IND.exists():
        OUT.write_text("[]", encoding="utf-8")
        print(f"[stocks.signal] indicators not found; out={OUT} (EMPTY)")
        return

    try:
        indicators = json.loads(IND.read_text(encoding="utf-8") or "[]")
    except Exception:
        indicators = []

    signals = []
    for row in indicators:
        sym = row.get("symbol")
        sma5 = row.get("SMA_5")
        sma20 = row.get("SMA_20")
        rsi14 = row.get("RSI_14")
        macd = row.get("MACD")
        close = row.get("close")

        decision = "HOLD"
        notes = []

        if (sma5 is not None) and (sma20 is not None):
            if sma5 > sma20:
                decision = "BUY"
                notes.append("SMA5>SMA20 (momentum up)")
            elif sma5 < sma20:
                decision = "SELL"
                notes.append("SMA5<SMA20 (momentum down)")

        if isinstance(rsi14, (int, float)):
            if rsi14 < 30:
                notes.append("RSI<30 (oversold)")
                if decision == "BUY": decision = "BUY+"
                elif decision == "SELL": decision = "HOLD"
            elif rsi14 > 70:
                notes.append("RSI>70 (overbought)")
                if decision == "SELL": decision = "SELL+"
                elif decision == "BUY": decision = "HOLD"

        if isinstance(macd, (int, float)):
            if macd > 0 and decision.startswith("BUY"):
                notes.append("MACD>0 (bullish confirm)")
            if macd < 0 and decision.startswith("SELL"):
                notes.append("MACD<0 (bearish confirm)")

        signals.append({
            "symbol": sym,
            "close": close,
            "decision": decision,
            "rationale": " | ".join(notes)
        })

    OUT.write_text(json.dumps(signals, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[stocks.signal] generated {len(signals)} signals -> {OUT}")

if __name__ == "__main__":
    generate()
