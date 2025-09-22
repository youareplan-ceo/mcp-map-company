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

.PHONY: api-run api-test api-docker
api-run:
	uvicorn api.main:app --reload --port 8099

api-test:
	pytest -q

api-docker:
	docker build -t mcp-api:local .
	docker run --rm -p 8099:8099 mcp-api:local
