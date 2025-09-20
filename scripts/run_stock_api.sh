#!/bin/bash
exec /Users/youareplan/Desktop/mcp-map-company/.venv/bin/python3 -m uvicorn mcp.stock_api:app --host 127.0.0.1 --port 8099 --log-level info
