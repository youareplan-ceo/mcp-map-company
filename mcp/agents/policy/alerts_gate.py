import json
from pathlib import Path

SIG = Path("db/stocks_signals.json")
NEWS = Path("db/news_ranked.json")
OUT  = Path("db/alerts_candidates.json")

def _load(p):
    try:
        return json.loads(p.read_text(encoding="utf-8") or "[]")
    except Exception:
        return []

def enforce(min_news_score: float = 3.0, allow_actions=("SELL",)):
    # 입력 로드
    sigs = _load(SIG)
    news = _load(NEWS)

    # 심볼별 최고 점수 뉴스 맵
    best = {}
    for a in news:
        sym = a.get("symbol")
        if not sym: 
            continue
        if sym not in best or (a.get("score",0) > best[sym].get("score",0)):
            best[sym] = a

    # 규칙 적용
    out = []
    for s in sigs:
        sym = s.get("symbol")
        act = (s.get("decision") or "").upper()
        if act not in allow_actions:
            continue
        top = best.get(sym)
        if not top or float(top.get("score") or 0) < float(min_news_score):
            continue
        out.append({
            "symbol": sym,
            "decision": act,
            "close": s.get("close"),
            "rationale": s.get("rationale"),
            "news": {
                "score": top.get("score"),
                "title": top.get("title"),
                "source": top.get("source"),
                "url": top.get("url"),
                "publishedAt": top.get("publishedAt"),
            }
        })

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[policy.alerts] keep={len(out)} -> {OUT}")
    for r in out:
        print(f" - {r['symbol']} [{r['decision']}] @ {r['close']} | 뉴스 {r['news']['score']}점: {r['news']['title']}")
