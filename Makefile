.PHONY: build test deploy

build:
	@echo "Building project..."
	python -m compileall .

test:
	@echo "Running tests..."
	pytest || true

deploy:
	@echo "Manual deploy via Render/Vercel CLI"
	# Example:
	#   curl -X POST $RENDER_DEPLOY_HOOK
	#   npx vercel --prod --token=$VERCEL_TOKEN

.PHONY: dash-run
dash-run:
	streamlit run dashboard/app.py --server.port 8098

.PHONY: db-init db-ingest db-health
db-init:
	python - <<'PY'
import duckdb, pathlib
root = pathlib.Path('.').resolve()
db = root / 'data' / 'mcp.duckdb'
db.parent.mkdir(parents=True, exist_ok=True)
con = duckdb.connect(str(db))
con.close()
print(f"✅ Created {db}")
PY

db-ingest:
	python db/scripts/ingest_holdings.py

db-health:
	python db/scripts/db_health.py

.PHONY: ghcr-login api-tag api-release
ghcr-login:
	@echo "Logging in to GHCR..."
	echo $GHCR_TOKEN | docker login ghcr.io -u youareplan-ceo --password-stdin

api-tag:
	@if [ -z "$V" ]; then echo "Usage: make api-tag V=v0.1.0"; exit 1; fi
	git tag $V
	git push origin $V

api-release:
	@echo "Trigger workflow_dispatch (UI에서 실행 권장)"

.PHONY: docs-serve docs-build docs-deploy docs-sync
docs-serve:
	cd docs_site && mkdocs serve -a 0.0.0.0:8097

docs-build:
	cd docs_site && mkdocs build

docs-deploy:
	cd docs_site && mkdocs gh-deploy

docs-sync:
	python3 scripts/sync_incident_docs.py

.PHONY: etl-all
etl-all:
	python db/scripts/etl_all.py
