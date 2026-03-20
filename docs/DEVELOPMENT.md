# Development Guide

This guide covers setting up the development environment and contributing to the project.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Redis (for Celery)
- SQLite (included with Python)

## Quick Start

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate it
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp ../.env.example ../.env
# Edit .env file with your settings

# Initialize database
alembic upgrade head

# Start Redis (in separate terminal)
redis-server

# Start Celery worker (in separate terminal)
celery -A app.tasks worker --loglevel=info

# Start FastAPI (in main terminal)
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

The app will be available at:
- Frontend: http://localhost:3000 (configurable via `FRONTEND_PORT` in `.env`)
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

## Project Structure

```
wowrussian/
├── backend/
│   ├── app/
│   │   ├── api/          # REST API endpoints
│   │   │   ├── auth.py
│   │   │   ├── projects.py
│   │   │   ├── pages.py
│   │   │   ├── stats.py
│   │   │   └── websocket.py
│   │   ├── core/         # Core configuration
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   │   ├── crawler.py
│   │   │   ├── parser.py
│   │   │   ├── analyzer.py
│   │   │   └── file_storage.py
│   │   ├── tasks/        # Celery tasks
│   │   │   ├── celery_app.py
│   │   │   └── crawl_tasks.py
│   │   └── main.py       # FastAPI app entry
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── pages/        # React pages
│   │   ├── services/     # API client
│   │   └── hooks/        # Custom hooks
│   ├── package.json
│   └── Dockerfile
├── docs/
├── alembic/
├── docker-compose.yml
├── .env.example
└── README.md
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Follow the existing code style:
- Use type hints
- Add docstrings
- Write tests for new functionality

### 3. Run Tests

```bash
cd backend
pytest
```

### 4. Format Code

```bash
# Backend
black backend/
isort backend/

# Frontend
cd frontend
npm run format  # if configured, or use Prettier extension
```

### 5. Commit Changes

```bash
git add .
git commit -m "Add: description of changes"
```

### 6. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then open a Pull Request on GitHub.

## Database Migrations

### Create a New Migration

```bash
cd backend
alembic revision --autogenerate -m "Description of changes"
```

### Apply Migrations

```bash
alembic upgrade head
```

### Rollback Migration

```bash
alembic downgrade -1
```

## Adding New Features

### Backend - New API Endpoint

1. Add route to appropriate file in `app/api/`
2. Create Pydantic schemas in `app/schemas/`
3. Add business logic to `app/services/` if needed
4. Update `app/main.py` to include router

Example:

```python
# app/api/example.py
from fastapi import APIRouter, Depends
from app.schemas.example import ExampleCreate, ExampleResponse

router = APIRouter(prefix="/examples", tags=["examples"])

@router.post("", response_model=ExampleResponse)
async def create_example(example: ExampleCreate, db: AsyncSession = Depends(get_db)):
    # Implementation
    pass
```

### Frontend - New Page

1. Create component in `frontend/src/pages/`
2. Add route in `frontend/src/App.js`
3. Create API service functions if needed in `frontend/src/services/api.js`
4. Add navigation links

### Adding a New Celery Task

1. Define task in `app/tasks/crawl_tasks.py`:

```python
@celery_app.task(bind=True, name="my_task")
def my_task(self, param1, param2):
    asyncio.run(_my_task_async(param1, param2))

async def _my_task_async(param1, param2):
    # Implementation
    pass
```

2. Call from anywhere:

```python
from app.tasks.crawl_tasks import my_task
my_task.delay(arg1, arg2)
```

## Debugging

### Backend

FastAPI provides automatic API documentation at `/docs` and `/redoc`.

Check logs:
```bash
# If using docker-compose
docker-compose logs -f backend

# If running directly
# Check terminal where uvicorn is running
```

### Frontend

Open browser DevTools (F12):
- Console: JavaScript errors
- Network: API requests
- React DevTools: Component inspection

### Celery

Check worker logs:
```bash
docker-compose logs -f celery
```

Monitor tasks:
```bash
# Install flower for monitoring
pip install flower
celery -A app.tasks flower
# Visit http://localhost:5555
```

### Database

Inspect SQLite database:
```bash
cd backend
sqlite3 data/app.db

# Inside sqlite3
.tables
SELECT * FROM projects;
.exit
```

## Testing

### Run All Tests

```bash
cd backend
pytest
```

### Run Specific Test

```bash
pytest tests/test_crawler.py::test_crawl_url
```

### With Coverage

```bash
pytest --cov=app --cov-report=html
# Open htmlcov/index.html
```

### Writing Tests

Create `tests/` directory in backend:

```python
# tests/test_example.py
import pytest
from app.services.example import ExampleService

@pytest.mark.asyncio
async def test_example_function():
    result = await ExampleService.some_method()
    assert result is not None
```

## Environment Variables

See `.env.example` for all available options. Important ones:

- `DEBUG` - Enable debug mode (development only)
- `SECRET_KEY` - JWT secret (change in production!)
- `DATABASE_URL` - Database connection string
- `REDIS_URL` - Redis connection
- `CRAWLER_MAX_PAGES` - Max pages to crawl (default 1000)
- `CRAWLER_DELAY` - Seconds between requests (default 1)

## Common Tasks

### Reset Database

```bash
cd backend
rm -rf ../data/*  # WARNING: deletes all data
alembic upgrade head
```

### Clear Storage

```bash
rm -rf storage/*
```

### Rebuild Docker Images

```bash
docker-compose build --no-cache
docker-compose up -d
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f celery
```

### Access Database in Docker

```bash
docker-compose exec backend bash
# Inside container
sqlite3 /app/data/app.db
```

### Run Shell in Container

```bash
docker-compose exec backend bash
```

## Code Style

- Follow PEP 8 for Python
- Use Black for formatting: `black backend/`
- Use isort for imports: `isort backend/`
- Use ESLint for JavaScript: `npm run lint`

## Performance Tips

1. **Database Queries**: Use indexes, avoid N+1 queries
2. **Async Operations**: Always use async/await for I/O
3. **File Storage**: Don't store large blobs in database
4. **Crawling**: Respect `CRAWLER_DELAY` to avoid rate limits

## Troubleshooting

### "Database is locked" error

SQLite has file locking issues with multiple writers. Solutions:
- Enable WAL mode (already done in code)
- Reduce concurrent writes
- Consider PostgreSQL for production

### Celery tasks not executing

1. Check Redis is running: `redis-cli ping`
2. Check Celery worker logs
3. Restart worker: `docker-compose restart celery`

### WebSocket not connecting

1. Check nginx proxy config for `/ws/`
2. Verify backend WebSocket endpoint is running
3. Check browser console for errors

### Port already in use

```bash
# Find process using port
lsof -i :8000
# Kill it
kill -9 <PID>
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Ensure all tests pass
6. Submit a Pull Request

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [React Documentation](https://reactjs.org/docs)
- [Material-UI Documentation](https://mui.com/)