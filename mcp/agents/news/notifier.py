import json
from pathlib import Path

RANKED = Path("db/news_ranked.json")

def notify(top_n: int = 5):
    try:
        ranked = json.loads(RANKED.read_text(encoding="utf-8") or "[]")
    except Exception:
        ranked = []
    top = ranked[:top_n]
    print("[news.notify] DRY: top headlines")
    for i, a in enumerate(top, 1):
        print(f"  {i}. ({a.get('symbol')}) [{a.get('score')}] {a.get('title')} - {a.get('source')}")
