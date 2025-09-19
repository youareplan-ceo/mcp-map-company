import yaml, pathlib
def fetch():
    wl = yaml.safe_load(pathlib.Path("schemas/stocks/watchlist.yaml").read_text(encoding="utf-8")).get("universe", [])
    raw = pathlib.Path("raw_data/stocks_prices.json")
    raw.parent.mkdir(parents=True, exist_ok=True)
    if not raw.exists():
        raw.write_text("[]", encoding="utf-8")
    print(f"[stocks.fetch] symbols={len(wl)} ; raw={raw} (DRY)")
