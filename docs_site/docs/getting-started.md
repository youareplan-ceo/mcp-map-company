# Getting Started

## Prerequisites

- Python 3.11+
- Git
- Docker (optional)

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/youareplan-ceo/mcp-map-company.git
   cd mcp-map-company
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize database:**
   ```bash
   make db-init
   make db-ingest
   ```

## Running Services

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

### Documentation
```bash
make docs-serve
```
Access at: http://localhost:8097

## Development Workflow

1. **Database Health Check:**
   ```bash
   make db-health
   ```

2. **ETL Pipeline:**
   ```bash
   make etl-all
   ```

3. **Testing:**
   ```bash
   pytest
   ```