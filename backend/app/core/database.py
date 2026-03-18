from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
import os

from app.core.config import settings

# Convert SQLite URL to async version
database_url = settings.database_url.replace("sqlite://", "sqlite+aiosqlite://")

# Ensure data directory exists
os.makedirs(os.path.dirname(database_url.replace("sqlite+aiosqlite://", "")), exist_ok=True)

engine = create_async_engine(
    database_url,
    echo=settings.debug,
    future=True,
)

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
        if "sqlite" in database_url:
            await conn.execute("PRAGMA journal_mode=WAL")
        await conn.run_sync(Base.metadata.create_all)