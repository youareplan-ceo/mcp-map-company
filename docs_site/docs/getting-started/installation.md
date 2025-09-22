# Installation

This guide will help you set up the MCP Map Company development environment.

## Prerequisites

- Python 3.9+
- Git
- Docker (optional)

## Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/youareplan-ceo/mcp-map-company.git
cd mcp-map-company
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Initialize Database

```bash
make db-init
make db-ingest
```

### 4. Run the Dashboard

```bash
make dash-run
```

The dashboard will be available at `http://localhost:8098`.

## Docker Setup

### Build and Run

```bash
docker build -t mcp-map-company .
docker run -p 8000:8000 mcp-map-company
```

## Verification

Check that everything is working:

```bash
make test
make db-health
```

## Next Steps

- [Quick Start Guide](quickstart.md)
- [Development Setup](../development/setup.md)
- [API Documentation](../api/endpoints.md)