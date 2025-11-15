# API Documentation

## Authentication

All API requests require authentication using an API key.

### Request Headers

```
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

## Endpoints

### GET /api/v1/users

Retrieve a list of users.

**Parameters:**
- `limit` (optional): Number of results (default: 10, max: 100)
- `offset` (optional): Pagination offset (default: 0)

**Response:**
```json
{
  "users": [
    {
      "id": 1,
      "name": "John Doe",
      "email": "john@example.com"
    }
  ],
  "total": 42
}
```

### POST /api/v1/users

Create a new user.

**Request Body:**
```json
{
  "name": "Jane Smith",
  "email": "jane@example.com",
  "role": "developer"
}
```

**Response:**
```json
{
  "id": 2,
  "name": "Jane Smith",
  "email": "jane@example.com",
  "role": "developer",
  "created_at": "2025-01-15T10:30:00Z"
}
```

## Error Responses

### 400 Bad Request
Invalid request parameters or body.

### 401 Unauthorized
Missing or invalid API key.

### 404 Not Found
Resource not found.

### 500 Internal Server Error
Server error occurred.

## Rate Limiting

- 100 requests per minute per API key
- 1000 requests per hour per API key

Exceeding limits returns HTTP 429 (Too Many Requests).
