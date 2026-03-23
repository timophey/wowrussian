import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects import registry as dialect_registry
from sqlalchemy import text

from app.core.config import settings

# Register async dialects based on the database type
database_url = settings.database_url

# Auto-convert sync URLs to async if needed
url_mappings = {
    'sqlite://': 'sqlite+aiosqlite://',
    'postgresql://': 'postgresql+asyncpg://',
    'postgres://': 'postgresql+asyncpg://',
    'mysql://': 'mysql+aiomysql://',
    'mysql+pymysql://': 'mysql+aiomysql://',
}

for sync_prefix, async_prefix in url_mappings.items():
    if database_url.startswith(sync_prefix) and '+' not in database_url.split('://')[1].split('/')[0]:
        database_url = database_url.replace(sync_prefix, async_prefix, 1)
        break

# Register dialects if needed
try:
    if database_url.startswith("sqlite+aiosqlite://"):
        import aiosqlite
        dialect_registry.register("sqlite.aiosqlite", "aiosqlite.dialect:AsyncAdapt_sqlite_aiosqlite")
    elif database_url.startswith("postgresql+asyncpg://"):
        import asyncpg
    elif database_url.startswith("mysql+aiomysql://"):
        import aiomysql
except ImportError as e:
    print(f"Warning: Database driver import failed: {e}")
    print("Make sure to install the appropriate driver:")
    print("  - SQLite: aiosqlite")
    print("  - PostgreSQL: asyncpg")
    print("  - MySQL: aiomysql")

# For SQLite, ensure the data directory exists
if database_url.startswith("sqlite+aiosqlite://"):
    db_path = database_url.replace("sqlite+aiosqlite://", "")
    if not db_path.startswith(':'):  # Not in-memory
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

# Create engine with appropriate settings
engine_kwargs = {
    'echo': settings.debug,
    'future': True,
}

# Add pool settings for PostgreSQL/MySQL
if database_url.startswith(('postgresql+asyncpg://', 'mysql+aiomysql://')):
    engine_kwargs['pool_size'] = 10
    engine_kwargs['max_overflow'] = 20

engine = create_async_engine(database_url, **engine_kwargs)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


def create_session_factory():
    """
    Create a new session factory with a fresh engine.
    This ensures the engine is created in the same event loop where it will be used,
    avoiding 'Future attached to a different loop' errors.
    """
    local_engine = create_async_engine(database_url, **engine_kwargs)
    return sessionmaker(
        local_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db() -> AsyncSession:
    """Dependency for getting database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database by running Alembic migrations."""
    from alembic.config import Config
    from alembic import command
    from sqlalchemy import create_engine, inspect
    
    # Ensure data directory exists for SQLite
    if database_url.startswith("sqlite+aiosqlite://"):
        db_path = database_url.replace("sqlite+aiosqlite://", "")
        if not db_path.startswith(':'):  # Not in-memory
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Enable WAL mode for SQLite for better concurrency (before migrations)
    if database_url.startswith("sqlite+aiosqlite://"):
        sync_url = database_url.replace('+aiosqlite', '')
        sync_engine = create_engine(sync_url)
        with sync_engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.commit()
        sync_engine.dispose()
    
    # Prepare Alembic configuration
    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), '..', '..', 'alembic.ini'))
    sync_url = database_url.replace('+asyncpg', '').replace('+aiomysql', '').replace('+aiosqlite', '')
    alembic_cfg.set_main_option('sqlalchemy.url', sync_url)
    
    # Check if database is already initialized with schema but missing alembic_version
    sync_engine = create_engine(sync_url)
    inspector = inspect(sync_engine)
    existing_tables = inspector.get_table_names()
    sync_engine.dispose()
    
    # If main tables exist but alembic_version doesn't, stamp current version
    main_tables = ['users', 'projects', 'pages', 'foreign_words', 'russian_words', 'crawl_queue']
    has_main_tables = any(table in existing_tables for table in main_tables)
    has_alembic_version = 'alembic_version' in existing_tables
    
    if has_main_tables and not has_alembic_version:
        print("Database schema exists but alembic_version not found. Stamping current version...")
        command.stamp(alembic_cfg, 'head')
        return
    
    # Run Alembic migrations normally
    try:
        command.upgrade(alembic_cfg, 'head')
    except Exception as e:
        print(f"Migration error: {e}")
        raise