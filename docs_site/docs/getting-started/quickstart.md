# Quick Start

Get up and running with MCP Map Company in under 5 minutes.

## 1. Installation

First, follow the [installation guide](installation.md) to set up your environment.

## 2. Start the Services

### Dashboard
```bash
make dash-run
```
Access at: http://localhost:8098

### API Server
```bash
python -m api.main
```
Access at: http://localhost:8000

## 3. Basic Usage

### View Dashboard
1. Open http://localhost:8098
2. Navigate through the panels:
   - **Overview**: System status and metrics
   - **Metrics**: Performance analytics
   - **Logs**: System activity

### API Exploration
1. Open http://localhost:8000/docs
2. Try the interactive API documentation
3. Test endpoints with sample data

### Database Operations
```bash
# Check database health
make db-health

# Run data ingestion
make db-ingest
```

## 4. Example Workflows

### Adding New Data
```bash
# Add your data files to data/
# Run ingestion
make db-ingest

# Verify in dashboard
make dash-run
```

### Running Tests
```bash
# Full test suite
make test

# Specific tests
pytest tests/test_api.py
```

## 5. Common Tasks

| Task | Command |
|------|---------|
| Start dashboard | `make dash-run` |
| Run tests | `make test` |
| Build project | `make build` |
| Check DB health | `make db-health` |
| Deploy (manual) | `make deploy` |

## Next Steps

- [Architecture Overview](../architecture/overview.md)
- [Development Guide](../development/setup.md)
- [API Reference](../api/endpoints.md)