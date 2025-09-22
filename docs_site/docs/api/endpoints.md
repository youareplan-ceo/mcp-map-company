# API Endpoints

Complete reference for MCP Map Company REST API.

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://api.mcp-map-company.com`

## Authentication

Currently, the API uses basic authentication. Include credentials in headers:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.mcp-map-company.com/api/v1/status
```

## Core Endpoints

### Health Check

#### `GET /health`
Check API server status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-22T12:00:00Z",
  "version": "1.0.0"
}
```

### Data Operations

#### `GET /api/v1/data`
Retrieve data records.

**Parameters:**
- `limit` (int): Maximum records to return (default: 100)
- `offset` (int): Record offset for pagination (default: 0)
- `format` (str): Response format (`json`, `csv`) (default: json)

**Response:**
```json
{
  "data": [...],
  "total": 1500,
  "limit": 100,
  "offset": 0
}
```

#### `POST /api/v1/data`
Add new data records.

**Request Body:**
```json
{
  "records": [
    {
      "id": "unique_id",
      "name": "Record Name",
      "value": 123.45,
      "timestamp": "2025-09-22T12:00:00Z"
    }
  ]
}
```

### Analytics

#### `GET /api/v1/analytics/summary`
Get analytics summary.

**Response:**
```json
{
  "total_records": 1500,
  "last_updated": "2025-09-22T12:00:00Z",
  "metrics": {
    "avg_value": 98.7,
    "max_value": 250.0,
    "min_value": 0.1
  }
}
```

## Error Handling

All endpoints return consistent error responses:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid parameter: limit must be between 1 and 1000",
    "details": {...}
  }
}
```

### Status Codes

- `200` - Success
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `500` - Internal Server Error

## Rate Limiting

- **Development**: No limits
- **Production**: 1000 requests/hour per API key

## SDKs & Examples

### Python
```python
import requests

response = requests.get('http://localhost:8000/api/v1/data')
data = response.json()
```

### curl
```bash
curl -X GET "http://localhost:8000/api/v1/data?limit=50" \
     -H "Content-Type: application/json"
```

## Interactive Documentation

Visit `/docs` for Swagger UI or `/redoc` for ReDoc interface.