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

.PHONY: db-init db-ingest db-health
db-init:
\tpython -c "import duckdb, pathlib; p=pathlib.Path('data/mcp.duckdb'); p.parent.mkdir(exist_ok=True); duckdb.connect(str(p)).close()"

db-ingest:
\tpython db/scripts/ingest_holdings.py

db-health:
\tpython -c "import duckdb; con=duckdb.connect('data/mcp.duckdb'); print(con.execute('PRAGMA database_list').fetchall()); con.close()"
