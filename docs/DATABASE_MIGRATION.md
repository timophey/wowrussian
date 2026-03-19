# Database Migration Guide

This guide explains how to switch between different database backends (SQLite, PostgreSQL, MySQL) in the WowRussian Analyzer project.

## Supported Databases

| Database | Driver | Pros | Cons |
|----------|--------|------|------|
| **SQLite** | aiosqlite | Zero configuration, file-based, great for development | Limited concurrency, not ideal for high-traffic production |
| **PostgreSQL** | asyncpg | Full ACID compliance, excellent JSON support, best for production | Requires separate database server |
| **MySQL/MariaDB** | aiomysql | Mature, widely used, good performance | Slightly less feature-rich than PostgreSQL |

**Recommendation:** Use PostgreSQL for production deployments.

## Switching Databases

### 1. Install Required Dependencies

The project already includes all database drivers in `requirements.txt`. To use a specific database, ensure the corresponding driver is not commented out:

```txt
# For PostgreSQL:
asyncpg==0.29.0

# For MySQL:
aiomysql==0.2.0

# For SQLite:
aiosqlite==0.19.0
```

Install the driver:
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment Variable

Set the `DATABASE_URL` environment variable in your `.env` file:

**SQLite (default):**
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

### 3. Docker Deployment

If using Docker Compose:

1. Uncomment the database service (`postgres` or `mysql`) in `docker-compose.yml`
2. Uncomment the database dependency in `backend` and `celery-worker` services
3. Set the appropriate `DATABASE_URL` in your `.env` file
4. Start services: `docker-compose up -d`

Example for PostgreSQL:
```yaml
# In docker-compose.yml, uncomment:
# - postgres
# in backend and celery-worker depends_on sections

# In .env:
DATABASE_URL=postgresql+asyncpg://wowrussian:wowrussian_password@postgres:5432/wowrussian
```

## Migrating Existing Data from SQLite

If you have existing data in SQLite and want to migrate to PostgreSQL or MySQL:

### Option 1: Export/Import via JSON (Recommended)

1. **Export data from SQLite:**
   ```python
   # Create a script to export all data to JSON
   import json
   from sqlalchemy import select
   from app.core.database import AsyncSessionLocal
   from app.models import User, Project, Page, ForeignWord, CrawlQueue
   
   async def export_data():
       async with AsyncSessionLocal() as session:
           # Export each table
           users = (await session.execute(select(User))).scalars().all()
           projects = (await session.execute(select(Project))).scalars().all()
           # ... export all tables
           
           with open('export.json', 'w') as f:
               json.dump({
                   'users': users,
                   'projects': projects,
                   # ...
               }, f, default=str)
   ```

2. **Switch to new database** (update `DATABASE_URL`)

3. **Run migrations:**
   ```bash
   alembic upgrade head
   ```

4. **Import data to new database:**
   ```python
   async def import_data():
       async with AsyncSessionLocal() as session:
           # Load and insert data
           with open('export.json', 'r') as f:
               data = json.load(f)
           # Insert records
   ```

### Option 2: Use Database Tools

Use native database tools:

**SQLite to PostgreSQL:**
```bash
# Export SQLite to SQL
sqlite3 app.db .dump > dump.sql

# Clean up the SQL for PostgreSQL compatibility
# Then import:
psql -U username -d database_name -f dump.sql
```

**SQLite to MySQL:**
```bash
# Use conversion tools or manual SQL adaptation
```

## Important Notes

### Enum Types

The application uses SQLAlchemy `Enum` types which are handled differently across databases:

- **PostgreSQL:** Creates native ENUM types
- **MySQL:** Creates native ENUM types  
- **SQLite:** Emulates ENUM with CHECK constraints

The migration file (`001_initial.py`) handles this automatically.

### JSON Columns

The `projects.stats` column uses JSON type:

- **PostgreSQL:** Uses `JSONB` (binary, indexed, best performance)
- **MySQL:** Uses `JSON` (since MySQL 5.7+)
- **SQLite:** Stores as TEXT with JSON serialization

### DateTime Handling

All DateTime fields use UTC. No timezone conversion is needed between databases.

### Auto-increment IDs

All tables use `Integer` primary keys with auto-increment:

- **PostgreSQL:** Uses `SERIAL`/`BIGSERIAL`
- **MySQL:** Uses `AUTO_INCREMENT`
- **SQLite:** Uses `INTEGER PRIMARY KEY AUTOINCREMENT`

## Troubleshooting

### "No module named 'asyncpg'" or "No module named 'aiomysql'"

Install the required driver:
```bash
pip install asyncpg  # for PostgreSQL
# or
pip install aiomysql  # for MySQL
```

### Migration fails with enum errors

The migration uses standard `sa.Enum()` which should work across all databases. If you encounter issues, ensure you're using the latest version of the migration file.

### Connection refused (PostgreSQL/MySQL)

Ensure the database container is running and healthy:
```bash
docker-compose ps
```

Check logs:
```bash
docker-compose logs postgres
# or
docker-compose logs mysql
```

### "database does not exist" error

Create the database manually:
```bash
# PostgreSQL
docker-compose exec postgres psql -U wowrussian -c "CREATE DATABASE wowrussian;"

# MySQL
docker-compose exec mysql mysql -u root -p -e "CREATE DATABASE wowrussian;"
```

## Performance Considerations

### PostgreSQL (Recommended)

- Enable connection pooling (pgbouncer) for production
- Use connection pool settings in `database.py` (already configured)
- Consider adding indexes for frequently queried columns
- JSONB columns support indexing for better query performance

### MySQL

- Use InnoDB engine (default in modern MySQL)
- Configure appropriate buffer pool size
- JSON columns are supported but less feature-rich than PostgreSQL

### SQLite

- Enable WAL mode (already enabled in `database.py`)
- Use connection pooling carefully (SQLite has limited concurrency)
- Not recommended for production with multiple workers

## Rollback

To rollback to SQLite from another database:

1. Stop the application
2. Change `DATABASE_URL` back to SQLite
3. Export data from current database (see migration options above)
4. Drop the SQLite database file if exists
5. Run migrations: `alembic upgrade head`
6. Import data to SQLite

**Note:** Some PostgreSQL/MySQL-specific features may not translate perfectly to SQLite. Test thoroughly.

## Additional Resources

- [SQLAlchemy Database Migration](https://docs.sqlalchemy.org/en/20/orm/migrations.html)
- [Alembic Documentation](https://alembic.sqlalchemy.org/en/latest/)
- [PostgreSQL vs MySQL Comparison](https://www.postgresql.org/docs/current/external-interfaces.html)
