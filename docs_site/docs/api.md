# API Reference

FastAPI server providing RESTful endpoints.

## Base URL

- **Development**: `http://localhost:8000`
- **Interactive Docs**: `http://localhost:8000/docs`

## Core Endpoints

### Health Check
```
GET /health
```
Returns server status and health information.

### Data Endpoints
```
GET /api/v1/data
POST /api/v1/data
```
Retrieve and manage data records.

**Parameters**:
- `limit`: Maximum records (default: 100)
- `offset`: Pagination offset (default: 0)
- `format`: Response format (`json`, `csv`)

### Analytics
```
GET /api/v1/analytics/summary
```
Get analytics summary and metrics.

## Error Responses

All endpoints return consistent error format:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Description",
    "details": {}
  }
}
```

## Authentication

Currently uses basic authentication. Include headers:
```bash
curl -H "Authorization: Bearer TOKEN" \
     http://localhost:8000/api/v1/data
```

## Rate Limiting

- Development: No limits
- Production: 1000 requests/hour