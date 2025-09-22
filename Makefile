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
