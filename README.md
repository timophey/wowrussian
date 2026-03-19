# WowRussian Analyzer

A web application for analyzing websites to detect foreign words and anglicisms.

## Features

- Analyze any website by entering its URL
- Crawl all pages within the same domain
- Extract text content from HTML
- Detect foreign words using normative RAS dictionaries (law №168-FZ compliant)
- Real-time updates via WebSocket
- View detailed statistics and word frequency
- Multi-user support with isolated storage

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
4. Run migrations: `alembic upgrade head`

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
- Frontend: http://localhost:3000
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

2. Access the application at http://localhost:3000

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
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

### Development Setup

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start development server
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

## Deployment on CloudPanel

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed instructions.

## Development

### Running Tests

```bash
cd backend
pytest
```

### Database Migrations

```bash
cd backend
alembic upgrade head
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