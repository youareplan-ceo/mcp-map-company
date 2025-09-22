# Development Setup

Complete guide for setting up a development environment.

## Prerequisites

Ensure you have the following installed:

- **Python 3.9+**: `python --version`
- **Git**: `git --version`
- **Make**: `make --version`
- **Docker** (optional): `docker --version`

## Environment Setup

### 1. Clone and Navigate
```bash
git clone https://github.com/youareplan-ceo/mcp-map-company.git
cd mcp-map-company
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

### 4. Environment Variables
Copy and configure environment files:
```bash
cp .env.example .env
# Edit .env with your configuration
```

Required variables:
```bash
# Database
DATABASE_URL=data/mcp.duckdb

# API
API_HOST=localhost
API_PORT=8000

# Dashboard
DASH_HOST=localhost
DASH_PORT=8098
```

## Database Setup

### Initialize Database
```bash
make db-init
```

### Seed with Sample Data
```bash
make db-ingest
```

### Verify Database Health
```bash
make db-health
```

## Development Workflow

### Start Services

#### Dashboard (Streamlit)
```bash
make dash-run
# Available at: http://localhost:8098
```

#### API Server (FastAPI)
```bash
python -m api.main
# Available at: http://localhost:8000
# Docs at: http://localhost:8000/docs
```

### Testing

#### Run All Tests
```bash
make test
```

#### Run Specific Tests
```bash
pytest tests/test_api.py -v
pytest tests/test_dashboard.py -v
```

#### Test Coverage
```bash
pytest --cov=api --cov=dashboard tests/
```

### Code Quality

#### Linting
```bash
flake8 api/ dashboard/
black api/ dashboard/
```

#### Type Checking
```bash
mypy api/ dashboard/
```

## Docker Development

### Build Container
```bash
docker build -t mcp-map-company:dev .
```

### Run Container
```bash
docker run -p 8000:8000 -p 8098:8098 mcp-map-company:dev
```

### Docker Compose
```bash
docker-compose up -d
```

## Common Development Tasks

| Task | Command |
|------|---------|
| Start dashboard | `make dash-run` |
| Start API | `python -m api.main` |
| Run tests | `make test` |
| Reset database | `make db-init && make db-ingest` |
| Format code | `black .` |
| Lint code | `flake8 .` |

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 8098
lsof -ti:8098
# Kill the process
kill -9 $(lsof -ti:8098)
```

### Database Issues
```bash
# Reset database
rm data/mcp.duckdb
make db-init
make db-ingest
```

### Dependencies Issues
```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt
```

## IDE Configuration

### VSCode Settings
`.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black"
}
```

### Pre-commit Hooks
```bash
pip install pre-commit
pre-commit install
```

## Next Steps

- [Testing Guide](testing.md)
- [Contributing Guidelines](contributing.md)
- [API Reference](../api/endpoints.md)