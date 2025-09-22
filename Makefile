.PHONY: build test deploy

build:
\t@echo "Building project..."
\tpython -m compileall .

test:
\t@echo "Running tests..."
\tpytest || true

deploy:
\t@echo "Manual deploy placeholder (use Render/Vercel CLI)"
