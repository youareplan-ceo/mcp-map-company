from mcp.collector import ensure_table, load_watchlist, fetch_prices, insert_prices
def main():
    ensure_table()
    syms = load_watchlist() or ["NVDA","AAPL","AMZN","MSFT","TSLA"]
    rows = fetch_prices(syms)
    insert_prices(rows)
    ok = sum(1 for r in rows if r.get("ok"))
    print({"fetched": len(rows), "inserted": ok, "failed": len(rows)-ok})
if __name__ == "__main__":
    main()
