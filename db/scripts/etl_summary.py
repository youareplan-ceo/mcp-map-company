import json, datetime, duckdb, pathlib
root = pathlib.Path(__file__).resolve().parents[2]
db = root/"data"/"mcp.duckdb"
con = duckdb.connect(str(db))
summary = {
  "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S KST"),
  "tables": [r[0] for r in con.execute("SHOW TABLES").fetchall()],
  "holdings_rows": con.execute("SELECT COUNT(*) FROM holdings").fetchone()[0]
}
con.close()
outdir = root/"data"/"etl"; outdir.mkdir(parents=True, exist_ok=True)
(outdir/"last_run.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
print("✅ wrote", outdir/"last_run.json")
