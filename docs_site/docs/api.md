# API Reference

## Overview

The MCP Map Company API provides RESTful endpoints for accessing portfolio and holdings data.

## Base URL
```
http://localhost:8000
```

## Authentication
Currently using simple API key authentication (development mode).

## Endpoints

### Health Check
```
GET /health
```
Returns API health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-22T12:00:00Z"
}
```

### Holdings
```
GET /holdings
```
Retrieve portfolio holdings data.

**Query Parameters:**
- `portfolio_id` (optional): Filter by portfolio ID
- `symbol` (optional): Filter by symbol

**Response:**
```json
[
  {
    "holding_id": "P1-AAPL-2025-09-01",
    "portfolio_id": "P1",
    "symbol": "AAPL",
    "qty": 10,
    "avg_price": 175.3,
    "as_of": "2025-09-01"
  }
]
```

### Database Health
```
GET /db/health
```
Check database connectivity and table status.

## Interactive Documentation

Visit http://localhost:8000/docs for the complete interactive API documentation powered by FastAPI and Swagger UI.