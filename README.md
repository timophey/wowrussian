# WowRussian Analyzer

A web application for analyzing websites to detect foreign words and anglicisms.

## Features

- Analyze any website by entering its URL
- Crawl all pages within the same domain
- Extract text content from HTML
- Detect foreign words using **168fz microservice** or local dictionaries (law №168-FZ compliant)
- Real-time updates via WebSocket
- View detailed statistics and word frequency
- Multi-user support with isolated storage
- **Graceful degradation** - falls back to local analysis if 168fz is unavailable

## Tech Stack

**Backend:**
- Python 3.11
- FastAPI
- SQLAlchemy 2.0 (Supports SQLite, PostgreSQL, MySQL)
- Celery + Redis
- BeautifulSoup4

**Frontend:**
- React 18
- Material-UI
- Axios
- WebSocket API

**Infrastructure:**
- Docker & Docker Compose
- Nginx
- Redis

## Database Options

The application supports three database backends:

| Database | Driver | Use Case | Connection URL Format |
|----------|--------|----------|----------------------|
| SQLite | aiosqlite | Development, small deployments | `sqlite+aiosqlite:///./data/app.db` |
| PostgreSQL | asyncpg | Production (recommended) | `postgresql+asyncpg://user:password@host:port/dbname` |
| MySQL/MariaDB | aiomysql | Production (alternative) | `mysql+aiomysql://user:password@host:port/dbname` |

**Recommendation:** Use PostgreSQL for production as it offers better JSON support, concurrency, and advanced features.

### Switching Databases

1. Install the appropriate driver in `backend/requirements.txt` (already included)
2. Set `DATABASE_URL` environment variable to your chosen database
3. For Docker deployments, uncomment the database service in `docker-compose.yml`
4. **Migrations run automatically on startup** - no manual step required

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for frontend development)

### Using PostgreSQL (Production)

1. Copy environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and set your database configuration:
```env
DATABASE_URL=postgresql+asyncpg://wowrussian:wowrussian_password@postgres:5432/wowrussian
```

3. Start all services with PostgreSQL:
```bash
# Uncomment postgres service in docker-compose.yml or use:
# docker-compose --profile postgres up -d
docker-compose up -d
```

4. Access the application:
   - Frontend: http://localhost:3000 (configurable via `FRONTEND_PORT` in `.env`)
   - Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

### Using MySQL (Alternative)

1. Edit `.env`:
```env
DATABASE_URL=mysql+aiomysql://wowrussian:wowrussian_password@mysql:3306/wowrussian
```

2. Uncomment the `mysql` service in `docker-compose.yml` and comment out SQLite volumes

3. Start services:
```bash
docker-compose up -d
```

### Using SQLite (Default - Development)

1. Start all services (SQLite is configured by default):
```bash
docker-compose up -d
```

2. Access the application at http://localhost:3000 (or the port set in `FRONTEND_PORT`)

### Production Deployment

1. Clone the repository:
```bash
git clone <repository-url>
cd wowrussian
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Edit `.env` and set your `SECRET_KEY`:
```env
SECRET_KEY=your-secret-key-here
DEBUG=False
```

4. Start all services:
```bash
docker-compose up -d
```

5. Access the application:
   - Frontend: http://localhost:3000 (configurable via `FRONTEND_PORT`)
   - Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

### Development Setup

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start development server (migrations run automatically)
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm start
```

## Project Structure

```
wowrussian/
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── core/         # Config, database
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   └── tasks/        # Celery tasks
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── pages/
│   │   ├── services/
│   │   └── hooks/
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── alembic.ini
├── .env.example
└── storage/              # File storage (created at runtime)
```

## API Documentation

API documentation is available at `/docs` (Swagger UI) when the backend is running.

### Key Endpoints

- `POST /api/projects` - Create new analysis project
- `GET /api/projects` - List user's projects
- `GET /api/projects/{id}` - Get project details
- `DELETE /api/projects/{id}` - Delete project
- `POST /api/projects/{id}/stop` - Stop analysis
- `GET /api/projects/{project_id}/pages` - List pages
- `GET /api/projects/{project_id}/pages/{page_id}` - Get page details
- `GET /api/stats/{project_id}` - Get statistics

### WebSocket

Connect to `/ws/projects/{project_id}` for real-time updates.

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `True` |
| `SECRET_KEY` | JWT secret key | (required) |
| `DATABASE_URL` | Database connection URL (supports SQLite, PostgreSQL, MySQL) | `sqlite+aiosqlite:///./data/app.db` |
| `REDIS_URL` | Redis connection URL | `redis://redis:6379/0` |
| `STORAGE_PATH` | File storage path | `/app/storage` |
| `DICTIONARY_PATH` | Path to Russian words dictionary file | `/app/dictionaries/russian_words.txt` |
| `DICTIONARY_URL` | URL to download dictionary from | `https://raw.githubusercontent.com/danakt/russian-words/master/russian.txt` |
| `AUTO_DOWNLOAD_DICTIONARY` | Auto-download dictionary if not found | `True` |
| **168fz Integration** |||
| `USE_FZ168` | Enable 168fz microservice for enhanced detection | `True` |
| `FZ168_URL` | URL of 168fz service | `http://fz168:8000` |
| `FZ168_TIMEOUT` | Request timeout in seconds | `10` |
| `FZ168_RETRY_ATTEMPTS` | Number of retry attempts | `3` |
| `CRAWLER_DELAY` | Delay between requests (seconds) | `1` |
| `CRAWLER_USER_AGENT` | User-Agent for crawler | `WowRussianBot/1.0` |

### Database Connection URL Examples

**SQLite:**
```env
DATABASE_URL=sqlite+aiosqlite:///./data/app.db
```

**PostgreSQL:**
```env
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/database_name
```

**MySQL:**
```env
DATABASE_URL=mysql+aiomysql://username:password@localhost:3306/database_name
```

## 168fz Integration

This project can integrate with the [168fz](https://github.com/timophey/168fz) microservice for enhanced foreign word detection compliant with Federal Law №168-FZ.

### Features

- **Advanced classification**: Detects prohibited words, foreign words with/without Russian alternatives
- **Multiple dictionaries**: Uses official normative dictionaries and custom user dictionaries
- **Risk assessment**: Provides risk level (low/medium/high) for each text
- **Language detection**: Identifies language of foreign words

### Configuration

1. **Enable 168fz** in `.env`:
   ```env
   USE_FZ168=True
   FZ168_URL=http://fz168:8000  # or your external server URL
   ```

2. **Deploy 168fz service**:
   - **Option A (Docker Compose)**: Uncomment the `fz168` service in `docker-compose.yml`
   - **Option B (External)**: Deploy 168fz separately and set `FZ168_URL` to its address

3. **Run migrations** (automatic on startup) - new `source` field added to `foreign_words` table

### Fallback Behavior

If 168fz is unavailable (timeout, connection error, etc.), the system automatically falls back to the local dictionary-based analyzer. All operations continue without interruption.

### Data Source Tracking

The `source` field in `foreign_words` table indicates which analyzer detected the word:
- `fz168` - detected by 168fz service
- `dictionary` - from main Russian dictionary (local fallback)
- `fallback` - from built-in minimal dictionary (local fallback)

### Disabling 168fz

To use only the local analyzer:
```env
USE_FZ168=False
```

## Deployment on CloudPanel

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed instructions.

## Development

### Running Tests

```bash
cd backend
pytest
```

### Database Migrations

**Note:** Migrations run automatically on application startup.

To manually run migrations (e.g., for debugging or special cases):

```bash
cd backend
alembic upgrade head
```

To create a new migration after changing models:

```bash
cd backend
alembic revision --autogenerate -m "Description of changes"
```

### Adding New Features

1. Create a new branch: `git checkout -b feature/feature-name`
2. Make your changes
3. Commit with clear message: `git commit -m "Add: feature description"`
4. Push and create PR

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.