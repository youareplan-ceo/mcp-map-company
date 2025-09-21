# StockPilot — Quick Runbook (2025-09-21, Asia/Seoul)

- API: FastAPI @ `mcp/stock_api.py`
- 로컬 포트: **8099**
- 수집: launchd(collect_once, StartInterval=60s) → DuckDB `data/stockpilot.duckdb`
- 주요 엔드포인트:
  - GET /health
  - GET /api/v1/stock/prices/latest?symbols=NVDA,AAPL,AMZN
  - GET /portfolio/pnl
  - GET /portfolio/reco
- 프로세스:
  - com.stockpilot.api / com.stockpilot.collector (launchd)
- 브랜치: `feat/reco-api-skeleton` (포트폴리오 PnL/Reco 포함)
