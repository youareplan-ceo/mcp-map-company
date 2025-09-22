# Development Guide

Development setup and contribution guidelines.

## Environment Setup

### 1. Clone and Install
```bash
git clone https://github.com/youareplan-ceo/mcp-map-company.git
cd mcp-map-company
pip install -r requirements.txt
```

### 2. Database Setup
```bash
make db-init    # Initialize DuckDB
make db-ingest  # Load sample data
make db-health  # Verify setup
```

### 3. Start Services
```bash
# Terminal 1: Dashboard
make dash-run

# Terminal 2: API Server
python -m api.main
```

## Testing

### Run Tests
```bash
make test                    # All tests
pytest tests/test_api.py     # Specific tests
pytest --cov=. tests/        # With coverage
```

### Test Structure
```
tests/
├── test_api.py         # API endpoint tests
├── test_dashboard.py   # Dashboard tests
└── test_database.py    # Database tests
```

## Code Quality

### Linting
```bash
flake8 api/ dashboard/
black api/ dashboard/
```

### Type Checking
```bash
mypy api/ dashboard/
```

## Database Development

### Schema Management
```bash
# View schema
cat db/sql/schema.sql

# Reset database
rm data/mcp.duckdb
make db-init
```

### Data Operations
```bash
make db-ingest     # Ingest data
make etl-summary   # ETL summary
make etl-all       # Full ETL pipeline
```

## Documentation

### Local Development
```bash
make docs-serve    # Serve at http://localhost:8097
make docs-build    # Build static site
```

### Deployment
```bash
make docs-deploy   # Deploy to GitHub Pages
```

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/name`
3. Make changes and test: `make test`
4. Commit changes: `git commit -m "feat: description"`
5. Push branch: `git push origin feature/name`
6. Create Pull Request

## Project Structure

```
mcp-map-company/
├── api/              # FastAPI server
├── dashboard/        # Streamlit app
├── db/              # Database scripts
├── data/            # Data files
├── tests/           # Test suites
├── docs_site/       # Documentation
└── .github/         # CI/CD workflows
```