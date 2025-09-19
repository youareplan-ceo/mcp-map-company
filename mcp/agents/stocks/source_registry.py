from pathlib import Path
import yaml, json

WATCH = Path("schemas/stocks/watchlist.yaml")
def register_sources():
    # 기본 워치리스트가 없으면 예시 생성
    if not WATCH.exists():
        WATCH.parent.mkdir(parents=True, exist_ok=True)
        data = {"universe": ["005930.KS","000660.KS","035420.KS"]}
        WATCH.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        print(f"[stocks.sources] created {WATCH} (example)")
    else:
        print(f"[stocks.sources] using {WATCH}")
