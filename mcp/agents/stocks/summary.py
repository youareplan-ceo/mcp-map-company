import json
from pathlib import Path

SIG = Path("db/stocks_signals.json")
NEWS = Path("db/news_ranked.json")
OUT = Path("db/stocks_summary.json")

def _load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8") or "[]")
    except Exception:
        return []

def build():
    signals = _load_json(SIG)
    news = _load_json(NEWS)
    # 심볼별 최고 점수 뉴스만 매핑
    best_news = {}
    for a in news:
        sym = a.get("symbol")
        if not sym: 
            continue
        if sym not in best_news or (a.get("score", 0) > best_news[sym].get("score", 0)):
            best_news[sym] = a

    summary = []
    for s in signals:
        sym = s.get("symbol")
        bn = best_news.get(sym)
        row = {
            "symbol": sym,
            "decision": s.get("decision"),
            "close": s.get("close"),
            "rationale": s.get("rationale"),
            "news_top": {
                "score": bn.get("score") if bn else None,
                "title": bn.get("title") if bn else None,
                "source": bn.get("source") if bn else None,
                "url": bn.get("url") if bn else None,
                "publishedAt": bn.get("publishedAt") if bn else None,
            } if bn else None
        }
        summary.append(row)

    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[stocks.summary] wrote {len(summary)} rows -> {OUT}")
    # 콘솔 요약 출력
    for r in summary:
        nt = r.get("news_top") or {}
        print(f" - {r['symbol']} [{r['decision']}] @ {r.get('close')} | "
              f"{(r.get('rationale') or '')} | "
              f"뉴스Top: {nt.get('score')}점 {nt.get('source')} - {nt.get('title')}")

if __name__ == "__main__":
    build()
