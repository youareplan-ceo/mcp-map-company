# MCP Map Company

Welcome to the MCP Map Company documentation portal.

## Overview

MCP Map Company is a comprehensive platform providing:

- **API Services**: RESTful APIs for data access
- **Dashboard**: Real-time monitoring with Streamlit
- **Database**: DuckDB analytics engine
- **CI/CD**: Automated GitHub Actions workflows

## Quick Start

1. **Installation**: `pip install -r requirements.txt`
2. **Database**: `make db-init && make db-ingest`
3. **Dashboard**: `make dash-run` (port 8098)
4. **API**: `python -m api.main` (port 8000)

## Key Features

- **Modern Stack**: FastAPI + Streamlit + DuckDB
- **Analytics**: Real-time metrics and monitoring
- **Testing**: Comprehensive test coverage
- **Deployment**: Docker + GitHub Actions

## Links

- [GitHub Repository](https://github.com/youareplan-ceo/mcp-map-company)
- [API Documentation](http://localhost:8000/docs)
- [Dashboard](http://localhost:8098)