# Getting Started

Quick setup guide for MCP Map Company development.

## Prerequisites

- Python 3.9+
- Git
- Make

## Installation

```bash
# Clone repository
git clone https://github.com/youareplan-ceo/mcp-map-company.git
cd mcp-map-company

# Install dependencies
pip install -r requirements.txt

# Initialize database
make db-init
make db-ingest
```

## Running Services

### Dashboard
```bash
make dash-run
# Access: http://localhost:8098
```

### API Server
```bash
python -m api.main
# Access: http://localhost:8000
# Docs: http://localhost:8000/docs
```

## Verification

```bash
# Run tests
make test

# Check database
make db-health

# Check services
curl http://localhost:8000/health
```

## Common Commands

| Command | Purpose |
|---------|---------|
| `make dash-run` | Start dashboard |
| `make db-health` | Check database |
| `make test` | Run tests |
| `make docs-serve` | Serve documentation |