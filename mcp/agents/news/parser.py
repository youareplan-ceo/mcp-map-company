import json
from pathlib import Path

RAW = Path("raw_data/news_raw.json")
PARSED = Path("db/news_parsed.json"); PARSED.parent.mkdir(parents=True, exist_ok=True)

def parse():
    items = []
    if RAW.exists():
        try:
            data = json.loads(RAW.read_text(encoding="utf-8") or "[]")
            if isinstance(data, dict):
                data = [data]
            for a in data:
                items.append({
                    "title": a.get("title"),
                    "desc": a.get("description"),
                    "url": a.get("url"),
                    "source": (a.get("source") or {}).get("name"),
                    "publishedAt": a.get("publishedAt"),
                    "_sym_query": a.get("_sym_query"),
                })
        except Exception:
            pass
    PARSED.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[news.parse] in={len(items)} -> {PARSED}")
