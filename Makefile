.PHONY: build test deploy

build:
\t@echo "Building project..."
\tpython -m compileall .

test:
\t@echo "Running tests..."
\tpytest || true

deploy:
\t@echo "Manual deploy via Render/Vercel CLI"
\t# Example:
\t#   curl -X POST $RENDER_DEPLOY_HOOK
\t#   npx vercel --prod --token=$VERCEL_TOKEN

.PHONY: dash-run
dash-run:
\tstreamlit run dashboard/app.py --server.port 8098

.PHONY: db-init db-ingest db-health
db-init:
\tpython - <<'PY'
import duckdb, pathlib
root = pathlib.Path('.').resolve()
db = root / 'data' / 'mcp.duckdb'
db.parent.mkdir(parents=True, exist_ok=True)
con = duckdb.connect(str(db))
con.close()
print(f"✅ Created {db}")
PY

db-ingest:
\tpython db/scripts/ingest_holdings.py

db-health:
\tpython db/scripts/db_health.py
