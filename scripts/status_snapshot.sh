#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

echo "=== GIT ==="
git rev-parse --abbrev-ref HEAD
git log --oneline -3

echo "=== API ==="
curl -sS "http://127.0.0.1:8099/health" || true

echo "=== PRICES SAMPLE ==="
curl -sS "http://127.0.0.1:8099/api/v1/stock/prices/latest?symbols=NVDA,AAPL,AMZN" || true

echo "=== PORTFOLIO PnL ==="
curl -sS "http://127.0.0.1:8099/portfolio/pnl"  | jq '.summary' || true

echo "=== PORTFOLIO Reco ==="
curl -sS "http://127.0.0.1:8099/portfolio/reco" | jq '.recommendations' || true

echo "=== DB COUNTS ==="
python - <<'PY'
from mcp.db import get_conn
con=get_conn()
print("rows_in_prices =", con.execute("SELECT COUNT(*) FROM prices").fetchone()[0])
print("last_ts =", con.execute("SELECT max(ts) FROM prices").fetchone()[0])
con.close()
PY
