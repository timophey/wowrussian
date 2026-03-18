# API Documentation

## Base URL

```
http://localhost:8000/api
```

## Authentication

Currently, authentication is not fully implemented. All endpoints are accessible without authentication in development.

In production, JWT tokens will be required via `Authorization: Bearer <token>` header.

## Endpoints

### Projects

#### Create Project

Creates a new website analysis project.

```http
POST /projects
Content-Type: application/json

{
  "url": "https://example.com"
}
```

**Response:**
```json
{
  "id": 1,
  "user_id": 1,
  "domain": "example.com",
  "base_url": "https://example.com",
  "status": "pending",
  "stats": {},
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

#### List Projects

Returns all projects for the current user.

```http
GET /projects
```

**Response:**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "domain": "example.com",
    "base_url": "https://example.com",
    "status": "completed",
    "stats": {
      "total_pages": 50,
      "foreign_words_count": 150
    },
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

#### Get Project

Returns detailed information about a project including statistics.

```http
GET /projects/{project_id}
```

**Response:**
```json
{
  "id": 1,
  "user_id": 1,
  "domain": "example.com",
  "base_url": "https://example.com",
  "status": "completed",
  "stats": {},
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00",
  "pages_count": 50,
  "queue_count": 0,
  "processing_count": 0,
  "completed_count": 50,
  "total_foreign_words": 150,
  "unique_foreign_words": 75
}
```

#### Delete Project

Deletes a project and all associated data.

```http
DELETE /projects/{project_id}
```

**Response:**
```json
{
  "message": "Project deleted"
}
```

#### Stop Project

Stops an ongoing analysis.

```http
POST /projects/{project_id}/stop
```

**Response:**
```json
{
  "message": "Project stopped"
}
```

### Pages

#### List Pages

Returns all pages for a project.

```http
GET /projects/{project_id}/pages
```

**Query Parameters:**
- `status` (optional): Filter by page status (`queued`, `crawling`, `parsed`, `analyzed`, `failed`)

**Response:**
```json
[
  {
    "id": 1,
    "project_id": 1,
    "url": "https://example.com/page1",
    "status": "analyzed",
    "words_count": 500,
    "foreign_words_count": 15,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

#### Get Page Details

Returns detailed information about a page including foreign words.

```http
GET /projects/{project_id}/pages/{page_id}
```

**Response:**
```json
{
  "id": 1,
  "project_id": 1,
  "url": "https://example.com/page1",
  "status": "analyzed",
  "words_count": 500,
  "foreign_words_count": 15,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00",
  "html_content": "<!DOCTYPE html>...",
  "text_content": "Extracted text...",
  "foreign_words": [
    {"word": "online", "count": 3},
    {"word": "meeting", "count": 2}
  ]
}
```

#### Get Page HTML

Returns raw HTML content of a page.

```http
GET /projects/{project_id}/pages/{page_id}/html
```

**Response:**
```json
{
  "html": "<!DOCTYPE html>..."
}
```

#### Get Page Text

Returns extracted text content of a page.

```http
GET /projects/{project_id}/pages/{page_id}/text
```

**Response:**
```json
{
  "text": "Extracted text content..."
}
```

### Statistics

#### Get Project Statistics

Returns detailed statistics for a project.

```http
GET /stats/{project_id}
```

**Response:**
```json
{
  "project_id": 1,
  "total_pages": 50,
  "status_distribution": {
    "queued": 0,
    "crawling": 0,
    "parsed": 0,
    "analyzed": 50,
    "failed": 0
  },
  "total_words": 25000,
  "total_foreign_words": 150,
  "unique_foreign_words": 75,
  "foreign_percentage": 0.6,
  "average_words_per_page": 500.0,
  "average_foreign_per_page": 3.0,
  "top_foreign_words": [
    {"word": "online", "count": 25},
    {"word": "meeting", "count": 18}
  ]
}
```

### Authentication

#### Register

```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "created_at": "2024-01-01T00:00:00"
}
```

#### Login

```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=securepassword123
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

## WebSocket

Connect to receive real-time updates about project progress.

### Connection URL

```
ws://localhost:8000/ws/projects/{project_id}
```

### Message Format

All messages are JSON objects with an `event` and `data` field.

#### Events

**page_crawled**
```json
{
  "event": "page_crawled",
  "data": {
    "page_id": 1,
    "url": "https://example.com/page1"
  }
}
```

**page_analyzed**
```json
{
  "event": "page_analyzed",
  "data": {
    "page_id": 1,
    "url": "https://example.com/page1",
    "words_count": 500,
    "foreign_words_count": 15
  }
}
```

**project_completed**
```json
{
  "event": "project_completed",
  "data": {
    "status": "completed"
  }
}
```

**error**
```json
{
  "event": "error",
  "data": {
    "message": "Error description"
  }
}
```

## Status Codes

| Code | Description |
|------|-------------|
| 200 | OK |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 404 | Not Found |
| 500 | Internal Server Error |

## Error Response Format

```json
{
  "detail": "Error description"
}
```

## Rate Limiting

Currently, no rate limiting is implemented. In production, consider adding:
- Per-IP rate limiting
- Per-user rate limiting
- Crawl delay between requests (configurable)

## Pagination

Not implemented yet. Will be added in future versions.

## Sorting and Filtering

Not implemented yet. Will be added in future versions.