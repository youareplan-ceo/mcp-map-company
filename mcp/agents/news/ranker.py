import json, datetime as dt
from pathlib import Path

LINKED = Path("db/news_by_symbol.json")
RANKED = Path("db/news_ranked.json"); RANKED.parent.mkdir(parents=True, exist_ok=True)

TRUST_SCORES = { "연합뉴스": 2.0, "Reuters": 2.0, "Bloomberg": 2.5, "WSJ": 2.0, "CNBC": 1.5 }

def _recency_boost(publishedAt):
    try:
        ts = dt.datetime.fromisoformat((publishedAt or "").replace('Z','+00:00'))
        hours = max(1, (dt.datetime.now(dt.timezone.utc) - ts.astimezone(dt.timezone.utc)).total_seconds()/3600.0)
        return max(0.1, 1.5 / (hours**0.5))
    except Exception:
        return 0.1

def rank():
    try:
        linked = json.loads(LINKED.read_text(encoding="utf-8") or "[]")
    except Exception:
        linked = []

    ranked = []
    for a in linked:
        score = 0.0
        score += float(a.get("hits") or 0) * 1.0
        score += float(TRUST_SCORES.get(a.get("source") or "", 0.0))
        score += _recency_boost(a.get("publishedAt") or "")
        ranked.append({
            "symbol": a.get("symbol"),
            "score": round(score, 3),
            "title": a.get("title"),
            "url": a.get("url"),
            "source": a.get("source"),
            "publishedAt": a.get("publishedAt"),
        })

    ranked.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    RANKED.write_text(json.dumps(ranked, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[news.rank] ranked={len(ranked)} -> {RANKED}")
