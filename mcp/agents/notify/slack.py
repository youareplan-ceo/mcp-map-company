import os, json
from pathlib import Path
import requests

WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "")
SUMMARY = Path("db/stocks_summary.json")

def _send(payload: dict):
    if not WEBHOOK:
        print("[slack.notify] no webhook configured, DRY mode")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    try:
        r = requests.post(WEBHOOK, json=payload, timeout=10)
        print(f"[slack.notify] status={r.status_code}")
    except Exception as e:
        print(f"[slack.notify] error: {e}")

def _line(symbol, decision, close, news_score=None, news_title=None):
    text = f"*{symbol}* → {decision} @ {close}"
    if news_score is not None and news_title:
        try:
            text += f" | 뉴스 {float(news_score):.2f}점: {news_title}"
        except Exception:
            text += f" | 뉴스 {news_score}점: {news_title}"
    return {"text": text}

def summary(symbol=None, decision=None, close=None, news_score=None, news_title=None):
    """
    플로우에서 인자 없이 호출되어도 동작:
    - 인자가 주어지면 단일 메시지 전송
    - 인자가 없으면 db/stocks_summary.json을 읽어 전체 전송
    """
    # 단일 전송 모드 (인자 제공된 경우)
    if symbol is not None and decision is not None and close is not None:
        _send(_line(symbol, decision, close, news_score, news_title))
        return

    # 배치 전송 모드 (요약 파일 기반)
    if not SUMMARY.exists():
        print("[slack.notify] no summary file, skip")
        return

    try:
        data = json.loads(SUMMARY.read_text(encoding="utf-8") or "[]")
    except Exception:
        data = []

    if not data:
        print("[slack.notify] summary empty, skip")
        return

    for row in data:
        sym = row.get("symbol")
        dec = row.get("decision")
        clo = row.get("close")
        nt  = row.get("news_top") or {}
        msg = _line(sym, dec, clo, nt.get("score"), nt.get("title"))
        _send(msg)
