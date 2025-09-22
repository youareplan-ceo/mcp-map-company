# Testing Guide

Comprehensive testing strategy for MCP Map Company.

## Test Structure

```
tests/
├── conftest.py          # Pytest configuration
├── test_api.py          # API endpoint tests
├── test_dashboard.py    # Dashboard tests
├── test_database.py     # Database tests
└── integration/         # Integration tests
```

## Running Tests

### All Tests
```bash
make test
```

### Specific Test Files
```bash
pytest tests/test_api.py -v
pytest tests/test_dashboard.py -v
pytest tests/test_database.py -v
```

### Test Categories
```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Smoke tests
pytest -m smoke
```

## Test Configuration

### pytest.ini
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    unit: Unit tests
    integration: Integration tests
    smoke: Smoke tests
    slow: Slow tests
```

### Coverage
```bash
# Run with coverage
pytest --cov=api --cov=dashboard tests/

# Generate HTML report
pytest --cov=api --cov=dashboard --cov-report=html tests/
```

## API Testing

### Example Test
```python
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_data_endpoint():
    response = client.get("/api/v1/data?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) <= 10
```

### Testing with Database
```python
import pytest
import duckdb
from api.database import get_db

@pytest.fixture
def test_db():
    # Create test database
    conn = duckdb.connect(":memory:")
    # Setup test schema
    conn.execute("CREATE TABLE test_table (...)")
    yield conn
    conn.close()

def test_database_query(test_db):
    result = test_db.execute("SELECT COUNT(*) FROM test_table").fetchone()
    assert result[0] >= 0
```

## Dashboard Testing

### Streamlit Testing
```python
import pytest
from streamlit.testing.v1 import AppTest

def test_dashboard_loads():
    at = AppTest.from_file("dashboard/app.py")
    at.run()
    assert not at.exception

def test_dashboard_navigation():
    at = AppTest.from_file("dashboard/app.py")
    at.run()

    # Test page navigation
    at.selectbox("page_selector").select("Metrics").run()
    assert "Metrics" in at.get("title").value
```

## Database Testing

### DuckDB Tests
```python
import pytest
import duckdb
from db.scripts.ingest_holdings import ingest_data

@pytest.fixture
def memory_db():
    conn = duckdb.connect(":memory:")
    # Create test schema
    conn.execute("""
        CREATE TABLE holdings (
            id INTEGER,
            name VARCHAR,
            value DECIMAL(10,2)
        )
    """)
    yield conn
    conn.close()

def test_data_ingestion(memory_db):
    # Test data ingestion
    test_data = [
        {"id": 1, "name": "Test", "value": 100.0}
    ]

    # Insert test data
    memory_db.execute(
        "INSERT INTO holdings VALUES (?, ?, ?)",
        (test_data[0]["id"], test_data[0]["name"], test_data[0]["value"])
    )

    # Verify
    result = memory_db.execute("SELECT COUNT(*) FROM holdings").fetchone()
    assert result[0] == 1
```

## Integration Testing

### End-to-End Tests
```python
import pytest
import requests
import subprocess
import time

@pytest.fixture(scope="session")
def running_services():
    # Start services for testing
    api_process = subprocess.Popen(["python", "-m", "api.main"])
    time.sleep(2)  # Wait for startup

    yield

    # Cleanup
    api_process.terminate()

def test_full_workflow(running_services):
    # Test complete workflow

    # 1. Check API health
    response = requests.get("http://localhost:8000/health")
    assert response.status_code == 200

    # 2. Add data via API
    data = {"records": [{"id": "test1", "name": "Test", "value": 123.45}]}
    response = requests.post("http://localhost:8000/api/v1/data", json=data)
    assert response.status_code == 201

    # 3. Retrieve data
    response = requests.get("http://localhost:8000/api/v1/data")
    assert response.status_code == 200
    assert len(response.json()["data"]) > 0
```

## Test Data Management

### Fixtures
```python
@pytest.fixture
def sample_data():
    return {
        "holdings": [
            {"id": 1, "name": "Asset 1", "value": 1000.0},
            {"id": 2, "name": "Asset 2", "value": 2000.0},
        ]
    }

@pytest.fixture
def clean_database():
    # Setup clean database
    conn = duckdb.connect("test.duckdb")
    yield conn
    # Cleanup
    conn.close()
    os.remove("test.duckdb")
```

### Test Data Files
```
tests/data/
├── sample_holdings.csv
├── test_config.json
└── mock_responses.json
```

## Performance Testing

### Load Testing
```python
import pytest
import time
from concurrent.futures import ThreadPoolExecutor
import requests

def test_api_performance():
    def make_request():
        response = requests.get("http://localhost:8000/api/v1/data")
        return response.status_code == 200

    # Test with multiple concurrent requests
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request) for _ in range(100)]
        results = [future.result() for future in futures]

    # All requests should succeed
    assert all(results)
```

## Continuous Integration

### GitHub Actions
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: pip install -r requirements-dev.txt
      - run: make test
      - run: pytest --cov=. --cov-report=xml
      - uses: codecov/codecov-action@v1
```

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Clear Names**: Use descriptive test function names
3. **AAA Pattern**: Arrange, Act, Assert
4. **Mock External Services**: Don't test external dependencies
5. **Test Edge Cases**: Include boundary conditions
6. **Fast Feedback**: Keep unit tests fast

## Debugging Tests

### Verbose Output
```bash
pytest -v -s tests/test_api.py::test_specific_function
```

### PDB Debugging
```bash
pytest --pdb tests/test_api.py
```

### Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```