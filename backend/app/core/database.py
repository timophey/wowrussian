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
    """Initialize database tables."""
    async with engine.begin() as conn:
        # Enable WAL mode for SQLite for better concurrency
        if database_url.startswith("sqlite+aiosqlite://"):
            await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.run_sync(Base.metadata.create_all)