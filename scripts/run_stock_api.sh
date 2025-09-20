#!/bin/zsh
set -euo pipefail
cd /Users/youareplan/Desktop/mcp-map-company
# venv 있으면 활성화(없어도 무시)
if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
fi
exec /opt/homebrew/bin/python3 -m uvicorn mcp.stock_api:app --host 127.0.0.1 --port 8099 --log-level info
