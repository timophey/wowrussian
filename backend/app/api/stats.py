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
    
    # Check if we have pages with fz168_raw_response to use fz168 data
    fz168_page_count = await safe_scalar(
        db,
        select(func.count()).select_from(Page).where(
            Page.project_id == project_id,
            Page.fz168_raw_response.isnot(None)
        )
    )
    
    if fz168_page_count and fz168_page_count > 0:
        # Use fz168_raw_response data for pages that have it
        result = await db.execute(
            select(Page).where(
                Page.project_id == project_id,
                Page.fz168_raw_response.isnot(None)
            )
        )
        pages = result.scalars().all()
        
        total_pages = len(pages)
        
        # Status distribution (only for fz168 pages)
        status_dist = {}
        for page in pages:
            status_val = page.status.value if hasattr(page.status, 'value') else str(page.status)
            status_dist[status_val] = status_dist.get(status_val, 0) + 1
        
        # Aggregate fz168 data
        total_words = 0
        total_foreign_words = 0
        foreign_word_freq = {}
        
        # Risk level distribution and violation statistics
        risk_level_distribution = {"high": 0, "medium": 0, "low": 0}
        total_violations = 0
        
        foreign_statuses = {"foreign", "foreign_with_alternative", "prohibited"}
        
        for page in pages:
            fz168_raw = page.fz168_raw_response
            if not fz168_raw or not isinstance(fz168_raw, dict):
                continue
            data = fz168_raw.get('data', {})
            all_words = data.get('all_words', [])
            summary = data.get('summary', {})
            
            # Aggregate risk level and violations from summary
            if summary:
                risk_level = summary.get('risk_level', 'low')
                if risk_level in risk_level_distribution:
                    risk_level_distribution[risk_level] += 1
                total_violations += summary.get('violation_count', 0)
            
            if not all_words:
                continue
            total_words += len(all_words)
            for word_data in all_words:
                status = word_data.get('status', '')
                if status in foreign_statuses:
                    word = word_data.get('word', '').lower()
                    total_foreign_words += 1
                    foreign_word_freq[word] = foreign_word_freq.get(word, 0) + 1
        
        unique_foreign_words = len(foreign_word_freq)
        foreign_percentage = (total_foreign_words / total_words * 100) if total_words > 0 else 0
        avg_words = total_words / total_pages if total_pages > 0 else 0
        avg_foreign = total_foreign_words / total_pages if total_pages > 0 else 0
        
        # Top foreign words
        top_foreign_words = [
            {"word": word, "count": count}
            for word, count in sorted(foreign_word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
        ]
    else:
        # Fallback to original method (all pages, using DB aggregates)
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
        top_foreign_words = [
            {"word": word, "count": count}
            for word, count in top_words_result.all()
        ]
        
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
        "top_foreign_words": top_foreign_words,
        "risk_level_distribution": risk_level_distribution if fz168_page_count and fz168_page_count > 0 else {"high": 0, "medium": 0, "low": 0},
        "total_violations": total_violations if fz168_page_count and fz168_page_count > 0 else 0
    }


@router.get("/{project_id}/unique-foreign-words")
async def get_unique_foreign_words(
    project_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    guest_session_token: Optional[str] = Query(None, description="Guest session token for unauthenticated access")
) -> Dict[str, Any]:
    """Get unique foreign words with the pages they appear on."""
    # Verify project access (same logic as get_project_stats)
    token = None
    from fastapi.security import OAuth2PasswordBearer
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
    try:
        token = await oauth2_scheme(request)
    except:
        pass

    user = await get_optional_user(token, db) if token else None

    if user:
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
        if guest_session_token:
            result = await db.execute(
                select(GuestSession).where(GuestSession.session_token == guest_session_token)
            )
            guest_session = result.scalar_one_or_none()
            if guest_session:
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
                await db.execute(
                    update(GuestSession)
                    .where(GuestSession.id == guest_session.id)
                    .values(last_activity=func.now())
                )
                await db.commit()
            else:
                raise HTTPException(status_code=401, detail="Invalid guest session")
        else:
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

    # Check if we have pages with fz168_raw_response
    fz168_page_count = await safe_scalar(
        db,
        select(func.count()).select_from(Page).where(
            Page.project_id == project_id,
            Page.fz168_raw_response.isnot(None)
        )
    )

    foreign_statuses = {"foreign", "foreign_with_alternative", "prohibited"}
    unique_words_data = {}

    if fz168_page_count and fz168_page_count > 0:
        # Use fz168_raw_response data
        result = await db.execute(
            select(Page).where(
                Page.project_id == project_id,
                Page.fz168_raw_response.isnot(None)
            )
        )
        pages = result.scalars().all()

        for page in pages:
            fz168_raw = page.fz168_raw_response
            if not fz168_raw or not isinstance(fz168_raw, dict):
                continue
            data = fz168_raw.get('data', {})
            all_words = data.get('all_words', [])

            for word_data in all_words:
                status = word_data.get('status', '')
                if status in foreign_statuses:
                    word = word_data.get('word', '')
                    word_lower = word.lower()
                    if word_lower not in unique_words_data:
                        unique_words_data[word_lower] = {
                            "word": word,
                            "total_count": 0,
                            "status": status,
                            "pages": []
                        }
                    unique_words_data[word_lower]["total_count"] += 1
                    # Add page if not already added
                    page_info = {"id": page.id, "url": page.url}
                    if not any(p["id"] == page.id for p in unique_words_data[word_lower]["pages"]):
                        unique_words_data[word_lower]["pages"].append(page_info)
    else:
        # Fallback to original ForeignWord table
        result = await db.execute(
            select(ForeignWord, Page.url, Page.id)
            .join(Page)
            .where(Page.project_id == project_id)
        )
        rows = result.all()

        for fw, page_url, page_id in rows:
            word_lower = fw.word.lower()
            if word_lower not in unique_words_data:
                unique_words_data[word_lower] = {
                    "word": fw.word,
                    "total_count": 0,
                    "status": "foreign",
                    "pages": []
                }
            unique_words_data[word_lower]["total_count"] += fw.count
            page_info = {"id": page_id, "url": page_url}
            if not any(p["id"] == page_id for p in unique_words_data[word_lower]["pages"]):
                unique_words_data[word_lower]["pages"].append(page_info)

    # Sort by total_count descending
    sorted_words = sorted(unique_words_data.values(), key=lambda x: x["total_count"], reverse=True)

    return {
        "project_id": project_id,
        "total_unique_words": len(sorted_words),
        "words": sorted_words
    }