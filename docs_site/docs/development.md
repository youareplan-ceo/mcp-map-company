# Development Guide

## Architecture

The MCP Map Company platform follows a modern microservices architecture:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Dashboard     │    │   API Server    │    │   Database      │
│   (Streamlit)   │    │   (FastAPI)     │    │   (DuckDB)      │
│   Port 8098     │    │   Port 8000     │    │   File-based    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Project Structure

```
mcp-map-company/
├── api/                 # FastAPI application
├── dashboard/           # Streamlit dashboard
├── db/                  # Database scripts and schema
├── docs_site/           # MkDocs documentation
├── data/               # Data files and database
├── scripts/            # Utility scripts
├── tests/              # Test suite
└── .github/workflows/  # CI/CD pipelines
```

## Local Development

### Environment Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Database Development
```bash
# Initialize database
make db-init

# Ingest sample data
make db-ingest

# Check database health
make db-health

# Run ETL pipeline
make etl-all
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=api --cov=dashboard

# Run specific test file
pytest tests/test_health.py
```

### Documentation
```bash
# Sync incident documentation
make docs-sync

# Serve documentation locally
make docs-serve

# Build static documentation
make docs-build
```

## CI/CD

The project uses GitHub Actions for continuous integration and deployment:

- **API CI**: Builds and tests the FastAPI application
- **Documentation**: Automatically deploys to GitHub Pages
- **Weekly Monitoring**: Automated health checks and reporting

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request