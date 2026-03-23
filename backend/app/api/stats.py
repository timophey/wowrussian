from typing import Annotated, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.project import Project, ProjectStatus
from app.models.page import Page, PageStatus
from app.models.foreign_word import ForeignWord
from app.models.user import User
from app.models.guest_session import GuestSession
from app.utils.db import safe_scalar
from app.api.auth import get_optional_user
from sqlalchemy import update

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/{project_id}")
async def get_project_stats(
    project_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    guest_session_token: Optional[str] = Query(None, description="Guest session token for unauthenticated access")
) -> Dict[str, Any]:
    """Get detailed statistics for a project."""
    # Verify project access
    # Try to get authenticated user first
    token = None
    # We need to extract token from request manually since we're not using Depends
    from fastapi.security import OAuth2PasswordBearer
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
    try:
        token = await oauth2_scheme(request)
    except:
        pass

    user = await get_optional_user(token, db) if token else None

    if user:
        # Authenticated user: check if project belongs to them
        project = await safe_scalar(
            db,
            select(Project).where(
                Project.id == project_id,
                Project.user_id == user.id
            )
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
    else:
        # No authenticated user, check guest session
        if guest_session_token:
            result = await db.execute(
                select(GuestSession).where(GuestSession.session_token == guest_session_token)
            )
            guest_session = result.scalar_one_or_none()
            if guest_session:
                # Check if project belongs to this guest session
                project = await safe_scalar(
                    db,
                    select(Project).where(
                        Project.id == project_id,
                        Project.user_id == 1,
                        Project.guest_session_id == guest_session.id
                    )
                )
                if not project:
                    raise HTTPException(status_code=404, detail="Project not found")
                # Update guest session activity
                await db.execute(
                    update(GuestSession)
                    .where(GuestSession.id == guest_session.id)
                    .values(last_activity=func.now())
                )
                await db.commit()
            else:
                # Invalid guest token
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid guest session"
                )
        else:
            # No credentials at all - only allow access to default user's public projects
            project = await safe_scalar(
                db,
                select(Project).where(
                    Project.id == project_id,
                    Project.user_id == 1,
                    Project.guest_session_id.is_(None)
                )
            )
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
    total_words = await safe_scalar(
        db,
        select(func.sum(Page.words_count)).where(Page.project_id == project_id)
    ) or 0
    
    # Total foreign words
    total_foreign_words = await safe_scalar(
        db,
        select(func.sum(Page.foreign_words_count)).where(Page.project_id == project_id)
    ) or 0
    
    # Unique foreign words
    unique_foreign_words = await safe_scalar(
        db,
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