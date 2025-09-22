import duckdb, pandas as pd, pathlib, datetime
root = pathlib.Path(__file__).resolve().parents[1]
db = root / "data" / "mcp.duckdb"
db.parent.mkdir(parents=True, exist_ok=True)
df = pd.DataFrame({"ts":[datetime.datetime.now(datetime.timezone.utc)]})
con = duckdb.connect(str(db))
con.execute("CREATE TABLE IF NOT EXISTS etl_runs(ts TIMESTAMP)")
con.execute("INSERT INTO etl_runs VALUES (?)", [df.ts[0]])
con.close()
print(f"✅ ETL run recorded at {df.ts[0]}")