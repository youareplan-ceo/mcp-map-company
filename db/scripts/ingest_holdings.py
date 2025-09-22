import duckdb, pandas as pd, sys, pathlib
root = pathlib.Path(__file__).resolve().parents[2]
db_path = root / "data" / "mcp.duckdb"
csv_path = root / "data" / "samples" / "holdings_sample.csv"
schema_sql = root / "db" / "sql" / "schema.sql"

con = duckdb.connect(str(db_path))
con.execute(schema_sql.read_text())

df = pd.read_csv(csv_path)
# 간단한 pk 생성
df["holding_id"] = df.apply(lambda r: f"{r['portfolio_id']}-{r['symbol']}-{r['as_of']}", axis=1)
con.execute("CREATE TABLE IF NOT EXISTS holdings AS SELECT * FROM df LIMIT 0;")  # 보강용
con.register("df", df)
con.execute("""
INSERT OR REPLACE INTO holdings (holding_id, portfolio_id, symbol, qty, avg_price, as_of)
SELECT holding_id, portfolio_id, symbol, qty, avg_price, CAST(as_of AS DATE) FROM df
""")
print(f"✅ Ingested {len(df)} rows into {db_path}")
