import pathlib, os
def fetch():
    raw = pathlib.Path("raw_data/news_raw.json"); raw.parent.mkdir(parents=True, exist_ok=True)
    if not raw.exists(): raw.write_text("[]", encoding="utf-8")
    print(f"[news.fetch] raw={raw} ; api_key={'set' if os.getenv('NEWSAPI_KEY') else 'missing'} (DRY)")
