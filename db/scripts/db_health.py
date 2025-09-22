import duckdb, pathlib
root = pathlib.Path(__file__).resolve().parents[2]
db_path = root / "data" / "mcp.duckdb"
con = duckdb.connect(str(db_path))
tables = con.execute("SHOW TABLES").fetchall()
print("Tables:", tables)
cnt = con.execute("SELECT COUNT(*) FROM holdings").fetchone()[0]
print("holdings rows:", cnt)
print("✅ DB health OK")
