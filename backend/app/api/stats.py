from typing import Annotated, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.project import Project, ProjectStatus
from app.models.page import Page, PageStatus
from app.models.foreign_word import ForeignWord
from app.models.user import User

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/{project_id}")
async def get_project_stats(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(lambda: None)
) -> Dict[str, Any]:
    """Get detailed statistics for a project."""
    # Check project exists
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Page status distribution
    status_counts = await db.execute(
        select(Page.status, func.count(Page.id))
        .where(Page.project_id == project_id)
        .group_by(Page.status)
    )
    status_dist = {status.value: count for status, count in status_counts.all()}
    
    # Total pages
    total_pages = sum(status_dist.values())
    
    # Total words
    total_words = await db.scalar(
        select(func.sum(Page.words_count)).where(Page.project_id == project_id)
    ) or 0
    
    # Total foreign words
    total_foreign_words = await db.scalar(
        select(func.sum(Page.foreign_words_count)).where(Page.project_id == project_id)
    ) or 0
    
    # Unique foreign words
    unique_foreign_words = await db.scalar(
        select(func.count(func.distinct(ForeignWord.word)))
        .select_from(ForeignWord)
        .join(Page)
        .where(Page.project_id == project_id)
    ) or 0
    
    # Top foreign words
    top_words_result = await db.execute(
        select(ForeignWord.word, func.sum(ForeignWord.count).label("total_count"))
        .join(Page)
        .where(Page.project_id == project_id)
        .group_by(ForeignWord.word)
        .order_by(func.sum(ForeignWord.count).desc())
        .limit(20)
    )
    top_words = [
        {"word": word, "count": count}
        for word, count in top_words_result.all()
    ]
    
    # Average words per page
    avg_words = total_words / total_pages if total_pages > 0 else 0
    avg_foreign = total_foreign_words / total_pages if total_pages > 0 else 0
    
    return {
        "project_id": project_id,
        "total_pages": total_pages,
        "status_distribution": status_dist,
        "total_words": total_words,
        "total_foreign_words": total_foreign_words,
        "unique_foreign_words": unique_foreign_words,
        "foreign_percentage": (total_foreign_words / total_words * 100) if total_words > 0 else 0,
        "average_words_per_page": round(avg_words, 2),
        "average_foreign_per_page": round(avg_foreign, 2),
        "top_foreign_words": top_words
    }