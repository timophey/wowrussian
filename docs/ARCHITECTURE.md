# Architecture Documentation

## System Overview

WowRussian Analyzer is a distributed web application for crawling websites and analyzing text content for foreign words. The system uses asynchronous processing with Celery workers to handle long-running crawl and analysis tasks.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         User Browser                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              React Frontend (Material-UI)            │  │
│  │  - Home page with URL input                          │  │
│  │  - Project dashboard with real-time updates         │  │
│  │  - Page details with foreign words list             │  │
│  └──────────────────────────┬──────────────────────────┘  │
│                             │ HTTP API + WebSocket         │
└─────────────────────────────┼─────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────┐
│                    Nginx (Reverse Proxy)                  │
│  - Serves static React files                            │
│  - Proxies /api to FastAPI backend                      │
│  - Proxies /ws to WebSocket                             │
└─────────────────────────────┬─────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────┐
│                    FastAPI Application                    │
│  ┌──────────────────────────────────────────────────────┐│
│  │  API Endpoints:                                      ││
│  │  - /api/projects (CRUD)                              ││
│  │  - /api/pages (list, get)                            ││
│  │  - /api/stats (statistics)                           ││
│  │  - /ws/projects/{id} (WebSocket)                     ││
│  └──────────────────────────┬───────────────────────────┘│
│                             │                              │
│  ┌──────────────────────────▼───────────────────────────┐│
│  │  SQLite Database                                     ││
│  │  - users                                             ││
│  │  - projects                                          ││
│  │  - pages                                             ││
│  │  - foreign_words                                     ││
│  │  - crawl_queue                                       ││
│  └──────────────────────────────────────────────────────┘│
└───────────────────────────────────────────────────────────┘
                              │
                              │ Redis Pub/Sub
                              │
┌─────────────────────────────▼─────────────────────────────┐
│                    Celery Workers                         │
│  ┌──────────────────────────────────────────────────────┐│
│  │  Task: crawl_project                                ││
│  │  - Fetch robots.txt                                 ││
│  │  - Crawl pages respecting domain boundary          ││
│  │  - Extract links and queue for processing          ││
│  └──────────────────────────────────────────────────────┘│
│  ┌──────────────────────────────────────────────────────┐│
│  │  Task: parse_and_analyze_page                       ││
│  │  - Parse HTML with BeautifulSoup                    ││
│  │  - Extract clean text                               ││
│  │  - Analyze for foreign words                        ││
│  │  - Save results to DB and files                     ││
│  └──────────────────────────────────────────────────────┘│
└───────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────┐
│                  File Storage (Local)                     │
│  storage/                                                 │
│  ├── {user_id}/                                          │
│  │   ├── {project_id}/                                  │
│  │   │   ├── html/{page_id}.html                        │
│  │   │   └── text/{page_id}.txt                         │
└───────────────────────────────────────────────────────────┘
```

## Components

### Frontend (React)

**Responsibilities:**
- User interface for URL input and project management
- Display real-time updates via WebSocket
- Show statistics and foreign word lists
- View HTML and extracted text

**Key Files:**
- `src/App.js` - Main router
- `src/pages/HomePage.js` - URL input form
- `src/pages/ProjectPage.js` - Project dashboard
- `src/pages/PageDetailPage.js` - Page analysis details
- `src/services/api.js` - API client
- `src/hooks/useWebSocket.js` - WebSocket hook

### Backend (FastAPI)

**Responsibilities:**
- REST API for CRUD operations
- WebSocket endpoint for real-time updates
- Request validation with Pydantic
- Database session management

**Key Files:**
- `app/main.py` - FastAPI application setup
- `app/api/` - API endpoint routers
- `app/core/` - Configuration and database
- `app/models/` - SQLAlchemy ORM models
- `app/schemas/` - Pydantic request/response schemas

### Word Analyzer

**Responsibilities:**
- Load Russian language dictionary from file or download automatically
- Tokenize and analyze text for foreign words
- Detect language of foreign words using langdetect
- Comply with law №168-FZ requirements using normative dictionaries

**Key Features:**
- **Dictionary Management**: Automatically downloads dictionary if not present (configurable)
- **Multiple Sources**: Supports loading from local file or downloading from URL
- **Language Detection**: Uses `langdetect` library to identify foreign language (en, fr, de, etc.)
- **Fallback Dictionary**: Minimal built-in dictionary for basic functionality when external dictionary is unavailable

**Configuration:**
- `DICTIONARY_PATH`: Path to Russian words dictionary file
- `DICTIONARY_URL`: URL to download dictionary from
- `AUTO_DOWNLOAD_DICTIONARY`: Enable/disable automatic download

**Dictionary Format:**
- One word per line
- UTF-8 encoding
- Comments starting with `#` are ignored
- Only Cyrillic words are used; non-alphabetic characters are stripped

**Algorithm:**
1. Tokenize text (lowercase, remove punctuation)
2. For each word:
   - If in Russian dictionary → mark as Russian
   - Else if contains Latin characters → mark as foreign, detect language
   - Else (Cyrillic but not in dictionary) → mark as Russian (conservative)
3. Aggregate statistics (total, foreign, unique foreign words, frequency)

### Database (SQLite)

**Schema:**

```sql
users (
  id INTEGER PK,
  email VARCHAR UNIQUE,
  password_hash VARCHAR,
  created_at DATETIME
)

projects (
  id INTEGER PK,
  user_id INTEGER FK,
  domain VARCHAR,
  base_url VARCHAR,
  status ENUM,
  stats JSON,
  created_at DATETIME,
  updated_at DATETIME
)

pages (
  id INTEGER PK,
  project_id INTEGER FK,
  url VARCHAR,
  html_file_path VARCHAR,
  text_file_path VARCHAR,
  status ENUM,
  words_count INTEGER,
  foreign_words_count INTEGER,
  created_at DATETIME,
  updated_at DATETIME
)

foreign_words (
  id INTEGER PK,
  page_id INTEGER FK,
  word VARCHAR,
  count INTEGER,
  language_guess VARCHAR,
  UNIQUE(page_id, word)
)

crawl_queue (
  id INTEGER PK,
  project_id INTEGER FK,
  url VARCHAR,
  status ENUM,
  attempts INTEGER,
  last_attempt_at DATETIME,
  created_at DATETIME
)
```

### Celery Workers

**Responsibilities:**
- Asynchronous crawling and analysis
- Task retry and error handling
- Progress tracking

**Tasks:**

1. **crawl_project** - Main orchestration task
   - Fetches URLs from crawl queue
   - Invokes crawler for each URL
   - Creates page records
   - Triggers parse_and_analyze_page

2. **parse_and_analyze_page** - Single page processing
   - Reads HTML from file storage
   - Extracts text with BeautifulSoup
   - Analyzes text for foreign words
   - Saves results to database

### File Storage

Files are stored in a structured directory hierarchy:

```
storage/
├── 1/                    # user_id
│   └── 1/                # project_id
│       ├── html/
│       │   └── 1.html    # page_id.html
│       └── text/
│           └── 1.txt     # page_id.txt
```

This structure provides:
- User isolation
- Easy cleanup (delete user directory)
- No database bloat from large text/HTML content

### WebSocket & Real-time Updates

**Flow:**
1. Frontend connects to `/ws/projects/{project_id}`
2. Backend WebSocket endpoint subscribes to Redis channel `project:{project_id}:updates`
3. Celery tasks publish events to Redis during processing
4. WebSocket forwards events to connected clients

**Events:**
- `page_crawled` - Page HTML fetched
- `page_analyzed` - Analysis complete
- `project_completed` - All pages processed
- `error` - Error occurred

## Data Flow

### Project Creation Flow

```
1. User enters URL → Frontend POST /api/projects
2. Backend:
   - Extracts domain from URL
   - Creates Project record (status: pending)
   - Creates CrawlQueue record with base_url
   - Returns project ID
3. Frontend redirects to /project/{id}
4. Backend triggers Celery task: crawl_project.delay(project_id)
```

### Crawl & Analysis Flow

```
1. Celery task: crawl_project
   - Gets pending URLs from crawl_queue
   - For each URL:
     a. Fetch HTML (respecting robots.txt)
     b. Create Page record (status: crawling)
     c. Save HTML to file
     d. Update Page status: parsed
     e. Trigger parse_and_analyze_page.delay(page_id)
     f. Update crawl_queue item to completed
   - Check completion, update project status

2. Celery task: parse_and_analyze_page
   - Load HTML from file
   - Extract text with HTMLParser
   - Save text to file
   - Analyze with WordAnalyzer
   - Create ForeignWord records
   - Update Page status: analyzed
   - Publish WebSocket event
```

## Security Considerations

### Current Implementation (Development)

- No authentication (all endpoints open)
- Plain text password storage (TODO: hash with bcrypt)
- No rate limiting
- Basic URL validation

### Production Requirements

1. **Authentication**: Implement JWT with proper verification
2. **Password Hashing**: Use passlib with bcrypt
3. **Rate Limiting**: Add per-IP and per-user limits
4. **URL Validation**: Strict validation to prevent SSRF
5. **CORS**: Configure allowed origins properly
6. **Secrets**: Use strong SECRET_KEY, rotate regularly
7. **HTTPS**: Enforce HTTPS in production
8. **File Access**: Ensure storage directory is not web-accessible

## Scalability Considerations

### Current Design

- Single Redis instance
- Multiple Celery workers (concurrency configurable)
- SQLite for simplicity (file-based, no separate server)

### Scaling to Production

1. **Database**: Switch to PostgreSQL for better concurrency
2. **Redis**: Use managed Redis with persistence
3. **Celery**: Add monitoring with Flower
4. **Storage**: Use S3 or similar for distributed file storage
5. **Load Balancing**: Multiple backend instances behind nginx
6. **Caching**: Add Redis caching for frequent queries

## Performance Optimizations

1. **SQLite WAL Mode**: Enabled for better concurrent access
2. **Database Indexes**: Added on frequently queried columns
3. **Async Operations**: All I/O operations are async (aiohttp, async SQLAlchemy)
4. **File Storage**: Offloads large content from database
5. **Connection Pooling**: SQLAlchemy connection pool

## Error Handling

- Network errors during crawling are caught and logged
- Failed pages are marked with status `failed`
- Project continues even if individual pages fail
- Errors are broadcast via WebSocket to frontend
- Celery task retries can be configured

## Monitoring

**Health Check:**
```
GET /health
```

**Logs:**
- Backend: stdout (captured by Docker)
- Celery: stdout with loglevel=info
- Frontend: Browser console

**Metrics to Monitor:**
- Queue length (Redis)
- Active Celery workers
- Disk usage (storage)
- Database size
- Request latency

## Future Improvements

1. **Authentication & Authorization**: Full user management
2. **Crawl Configuration**: Depth limit, page limit, include/exclude patterns
3. **Export**: CSV/JSON export of results
4. **Comparison**: Compare different crawls of same site
5. **API Keys**: For external integrations
6. **Content Checker Integration**: Integration with https://content-checker.ru/ for official compliance verification
7. **Normative Dictionaries Support**: Direct integration with RAS normative dictionaries (Orthoepic, Foreign Words, Explanatory)
8. **Custom Dictionaries**: Per-user custom word lists
9. **GraphQL API**: Alternative to REST
10. **Microservices**: Split crawler, analyzer into separate services
11. **Message Queue**: RabbitMQ as alternative to Redis