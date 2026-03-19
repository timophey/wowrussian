"""
Database utility functions for safe query execution.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Select, Update, Delete, Insert
from typing import Optional, Any, List


async def safe_scalar(db: AsyncSession, statement: Select) -> Optional[Any]:
    """
    Execute a SELECT statement and return a single scalar result.
    Ensures the result cursor is properly closed to avoid connection issues.
    """
    result = await db.execute(statement)
    value = result.scalar()
    result.close()
    return value


async def safe_scalars(db: AsyncSession, statement: Select) -> List[Any]:
    """
    Execute a SELECT statement and return all scalar results as a list.
    Ensures the result cursor is properly closed.
    """
    result = await db.execute(statement)
    values = result.scalars().all()
    result.close()
    return values


async def safe_execute(db: AsyncSession, statement: Update | Delete | Insert) -> Any:
    """
    Execute an UPDATE, DELETE, or INSERT statement.
    Returns the result proxy.
    """
    result = await db.execute(statement)
    return result
