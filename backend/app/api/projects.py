from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, asc, desc
import redis.asyncio as redis
import logging
from pathlib import Path

from app.core.database import get_db
from app.core.config import settings
from app.models.project import Project, ProjectStatus
from app.models.page import Page, PageStatus
from app.models.user import User
from app.models.crawl_queue import CrawlQueue, QueueStatus
from app.models.foreign_word import ForeignWord
from app.models.guest_session import GuestSession
from app.models.export_job import ExportJob, ExportJobStatus
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectDetail, ExportJobResponse, ExportJobDetail
from app.schemas.page import PageResponse
from app.services.file_storage import FileStorage
from app.services.excel_exporter import ExcelExporter
from app.tasks import crawl_project
from app.utils.db import safe_scalar
from app.api.auth import get_current_user, get_optional_user

logger = logging.getLogger(__name__)

# Optional auth: doesn't raise error if token is missing
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

router = APIRouter(prefix="/projects", tags=["projects"])

async def get_redis():
    """Get Redis connection."""
    return redis.from_url(settings.redis_url)


@router.post("", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    token: str | None = Depends(oauth2_scheme_optional),
    guest_session_token: Optional[str] = Query(None, description="Guest session token for unauthenticated users")
):
    """Create a new project from URL.
    If user is authenticated, project belongs to them.
    If guest_session_token is provided, project belongs to that guest session.
    If neither, project belongs to default user (ID=1)."""
    from urllib.parse import urlparse

    user_id = 1  # default user
    guest_session_id = None

    # Try to get authenticated user first
    if token:
        try:
            current_user = await get_current_user(token, db)
            user_id = current_user.id
        except HTTPException:
            # Invalid token, fall back to guest session or default
            pass

    # If no authenticated user, check for guest session
    if user_id == 1 and guest_session_token:
        result = await db.execute(
            select(GuestSession).where(GuestSession.session_token == guest_session_token)
        )
        guest_session = result.scalar_one_or_none()
        if guest_session:
            guest_session_id = guest_session.id
            # Update last activity
            from sqlalchemy import update
            await db.execute(
                update(GuestSession)
                .where(GuestSession.id == guest_session_id)
                .values(last_activity=func.now())
            )
        else:
            # Invalid guest session token, create new one
            guest_session = GuestSession()
            db.add(guest_session)
            await db.commit()
            await db.refresh(guest_session)
            guest_session_id = guest_session.id

    # Ensure default user exists
    if user_id == 1:
        existing_user = await safe_scalar(db, select(User).where(User.id == 1))
        if not existing_user:
            default_user = User(
                id=1,
                email="default@example.com",
                password_hash="dummy_hash_for_testing"
            )
            db.add(default_user)
            await db.commit()

    # Parse URL to get domain
    parsed = urlparse(str(project.url))
    domain = parsed.netloc
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    # Create project
    new_project = Project(
        user_id=user_id,
        guest_session_id=guest_session_id,
        domain=domain,
        base_url=base_url,
        status=ProjectStatus.PENDING,
        stats={"total_pages": 0, "foreign_words_count": 0}
    )
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)

    # Add initial URL to crawl queue
    from app.models.crawl_queue import CrawlQueue, QueueStatus
    queue_item = CrawlQueue(
        project_id=new_project.id,
        url=base_url,
        status=QueueStatus.PENDING
    )
    db.add(queue_item)
    await db.commit()

    return new_project


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    token: str | None = Depends(oauth2_scheme_optional),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    user_id: Optional[int] = Query(None, description="Filter projects by user ID (admin only)"),
    guest_session_token: Optional[str] = Query(None, description="Guest session token for unauthenticated access")
):
    """List all projects for current user, guest session, or default user (for guests).
    Admins can filter by specific user_id using admin authentication."""
    from app.api.admin import verify_admin_access

    # Check if user_id filter is requested - requires admin access
    if user_id is not None:
        if not await verify_admin_access(request):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required to filter by user"
            )
        final_user_id = user_id
        final_guest_session_id = None
    else:
        # Try to get authenticated user first
        user = await get_optional_user(token, db)
        if user:
            final_user_id = user.id
            final_guest_session_id = None
        else:
            # No authenticated user, check for guest session
            if guest_session_token:
                result = await db.execute(
                    select(GuestSession).where(GuestSession.session_token == guest_session_token)
                )
                guest_session = result.scalar_one_or_none()
                if guest_session:
                    final_user_id = 1  # Default user for guest projects
                    final_guest_session_id = guest_session.id
                    # Update last activity
                    from sqlalchemy import update
                    await db.execute(
                        update(GuestSession)
                        .where(GuestSession.id == guest_session.id)
                        .values(last_activity=func.now())
                    )
                    await db.commit()
                else:
                    # Invalid guest token, fall back to default public projects
                    final_user_id = 1
                    final_guest_session_id = None
            else:
                # No guest token, show default user's public projects only
                final_user_id = 1
                final_guest_session_id = None
    
    # Validate sort_by parameter
    allowed_sort_fields = {
        "domain": Project.domain,
        "status": Project.status,
        "created_at": Project.created_at
    }
    
    if sort_by not in allowed_sort_fields:
        sort_by = "created_at"
    
    # Validate sort_order
    order_func = asc if sort_order.lower() == "asc" else desc

    # Build query with dynamic ordering - filter by user and/or guest session
    if final_guest_session_id is not None:
        query = select(Project).where(
            Project.user_id == final_user_id,
            Project.guest_session_id == final_guest_session_id
        )
    else:
        query = select(Project).where(Project.user_id == final_user_id)
    query = query.order_by(order_func(allowed_sort_fields[sort_by]))
    
    result = await db.execute(query)
    projects = result.scalars().all()
    
    # Calculate actual statistics for all projects in batch
    if projects:
        project_ids = [p.id for p in projects]
        
        # Get page counts per project
        page_counts_result = await db.execute(
            select(Page.project_id, func.count(Page.id))
            .where(Page.project_id.in_(project_ids))
            .group_by(Page.project_id)
        )
        page_counts = {pid: count for pid, count in page_counts_result.all()}
        
        # Get foreign words counts per project (sum of foreign_words_count from pages)
        foreign_words_result = await db.execute(
            select(Page.project_id, func.sum(Page.foreign_words_count))
            .where(Page.project_id.in_(project_ids))
            .group_by(Page.project_id)
        )
        foreign_words_counts = {pid: count for pid, count in foreign_words_result.all()}
        
        # Update each project's stats with calculated values
        for project in projects:
            project.stats = {
                "total_pages": page_counts.get(project.id, 0),
                "foreign_words_count": foreign_words_counts.get(project.id, 0) or 0
            }
    
    return projects


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    token: str | None = Depends(oauth2_scheme_optional),
    guest_session_token: Optional[str] = Query(None, description="Guest session token for unauthenticated access")
):
    """Get project details with statistics.
    Allows access to projects belonging to the authenticated user,
    or to projects associated with a valid guest_session_token,
    or to projects belonging to the default user (ID=1) without authentication."""

    # Try to get authenticated user first
    user = await get_optional_user(token, db)

    guest_session = None
    if user:
        # Authenticated user: filter by user_id
        user_id = user.id
        guest_session_id = None
    else:
        # No authenticated user, check for guest session
        if guest_session_token:
            result = await db.execute(
                select(GuestSession).where(GuestSession.session_token == guest_session_token)
            )
            guest_session = result.scalar_one_or_none()
            if guest_session:
                user_id = 1  # Default user for guest projects
                guest_session_id = guest_session.id
                # Update last activity
                from sqlalchemy import update
                await db.execute(
                    update(GuestSession)
                    .where(GuestSession.id == guest_session.id)
                    .values(last_activity=func.now())
                )
                await db.commit()
            else:
                # Invalid guest token, fall back to default public projects
                user_id = 1
                guest_session_id = None
        else:
            # No guest token, show default user's public projects only
            user_id = 1
            guest_session_id = None

    # Build query to find project
    if guest_session_id is not None:
        # Filter by both user_id and guest_session_id
        project = await safe_scalar(
            db,
            select(Project).where(
                Project.id == project_id,
                Project.user_id == user_id,
                Project.guest_session_id == guest_session_id
            )
        )
    else:
        # Filter by user_id only (includes default user's public projects)
        project = await safe_scalar(
            db,
            select(Project).where(
                Project.id == project_id,
                Project.user_id == user_id
            )
        )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get counts
    total_pages = await safe_scalar(
        db,
        select(func.count()).select_from(Page).where(Page.project_id == project_id)
    )
    queue_count = await safe_scalar(
        db,
        select(func.count()).select_from(CrawlQueue).where(
            CrawlQueue.project_id == project_id,
            CrawlQueue.status == QueueStatus.PENDING
        )
    )
    processing_count = await safe_scalar(
        db,
        select(func.count()).select_from(Page).where(
            Page.project_id == project_id,
            Page.status.in_([PageStatus.QUEUED, PageStatus.CRAWLING, PageStatus.PARSED])
        )
    )
    completed_count = await safe_scalar(
        db,
        select(func.count()).select_from(Page).where(
            Page.project_id == project_id,
            Page.status == PageStatus.ANALYZED
        )
    )
    total_foreign_words = await safe_scalar(
        db,
        select(func.sum(Page.foreign_words_count)).where(Page.project_id == project_id)
    )
    unique_foreign_words = await safe_scalar(
        db,
        select(func.count(func.distinct(ForeignWord.word)))
        .join(Page, ForeignWord.page_id == Page.id)
        .where(Page.project_id == project_id)
    )
    
    detail = ProjectDetail.from_orm(project)
    detail.pages_count = total_pages or 0
    detail.queue_count = queue_count or 0
    detail.processing_count = processing_count or 0
    detail.completed_count = completed_count or 0
    detail.total_foreign_words = total_foreign_words or 0
    detail.unique_foreign_words = unique_foreign_words or 0
    
    return detail


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
    token: str | None = Depends(oauth2_scheme_optional),
    guest_session_token: Optional[str] = Query(None, description="Guest session token for unauthenticated access")
):
    """Delete project and all associated data.
    Allows deletion of projects by authenticated users,
    or by guest sessions that own the project."""
    from fastapi.security import OAuth2PasswordBearer
    oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
    
    # Try to get authenticated user first
    if token is None:
        token = await oauth2_scheme_optional(request)
    user = await get_optional_user(token, db) if token else None
    
    guest_session = None
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
                        Project.user_id == 1,  # Default user
                        Project.guest_session_id == guest_session.id
                    )
                )
                if not project:
                    raise HTTPException(status_code=404, detail="Project not found")
                # Update guest session activity
                from sqlalchemy import update
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
            # No credentials - try default user's public projects only
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
    
    # Delete files
    storage = FileStorage(settings.storage_path)
    storage.delete_project_files(project.user_id, project_id)
    
    # Delete project (cascade will handle related records)
    await db.delete(project)
    await db.commit()
    
    return {"message": "Project deleted"}


@router.delete("/{project_id}/pages")
async def clear_project_pages(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
    token: str | None = Depends(oauth2_scheme_optional),
    guest_session_token: Optional[str] = Query(None, description="Guest session token for unauthenticated access")
):
    """Clear all pages and crawl queue for a project.
    Allows clearing of projects by authenticated users,
    or by guest sessions that own the project."""
    from fastapi.security import OAuth2PasswordBearer
    oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
    
    # Try to get authenticated user first
    if token is None:
        token = await oauth2_scheme_optional(request)
    user = await get_optional_user(token, db) if token else None
    
    guest_session = None
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
                        Project.user_id == 1,  # Default user
                        Project.guest_session_id == guest_session.id
                    )
                )
                if not project:
                    raise HTTPException(status_code=404, detail="Project not found")
                # Update guest session activity
                from sqlalchemy import update
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
            # No credentials - try default user's public projects only
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
    
    # Delete all project files (HTML and text)
    storage = FileStorage(settings.storage_path)
    storage.delete_project_files(project.user_id, project_id)
    
    # Delete all pages (cascade deletes foreign words)
    await db.execute(
        delete(Page).where(Page.project_id == project_id)
    )
    
    # Delete all queue items
    await db.execute(
        delete(CrawlQueue).where(CrawlQueue.project_id == project_id)
    )
    
    # Reset project stats
    project.stats = {"total_pages": 0, "foreign_words_count": 0}
    project.status = ProjectStatus.PENDING
    await db.commit()
    
    return {"message": "Pages cleared successfully"}


@router.post("/{project_id}/stop")
async def stop_project(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
    token: str | None = Depends(oauth2_scheme_optional),
    guest_session_token: Optional[str] = Query(None, description="Guest session token for unauthenticated access")
):
    """Stop project scanning.
    Allows stopping of projects by authenticated users,
    or by guest sessions that own the project."""
    from fastapi.security import OAuth2PasswordBearer
    oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
    
    # Try to get authenticated user first
    if token is None:
        token = await oauth2_scheme_optional(request)
    user = await get_optional_user(token, db) if token else None
    
    guest_session = None
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
                        Project.user_id == 1,  # Default user
                        Project.guest_session_id == guest_session.id
                    )
                )
                if not project:
                    raise HTTPException(status_code=404, detail="Project not found")
                # Update guest session activity
                from sqlalchemy import update
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
            # No credentials - try default user's public projects only
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
    
    project.status = ProjectStatus.STOPPED
    await db.commit()
    
    # TODO: Send stop signal to Celery task
    
    return {"message": "Project stopped"}
@router.post("/{project_id}/start")
async def start_project(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
    token: str | None = Depends(oauth2_scheme_optional),
    guest_session_token: Optional[str] = Query(None, description="Guest session token for unauthenticated access")
):
    """Manually start project crawling.
    Allows starting of projects by authenticated users,
    or by guest sessions that own the project."""
    from fastapi.security import OAuth2PasswordBearer
    oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
    
    # Try to get authenticated user first
    if token is None:
        token = await oauth2_scheme_optional(request)
    user = await get_optional_user(token, db) if token else None
    
    guest_session = None
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
                        Project.user_id == 1,  # Default user
                        Project.guest_session_id == guest_session.id
                    )
                )
                if not project:
                    raise HTTPException(status_code=404, detail="Project not found")
                # Update guest session activity
                from sqlalchemy import update
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
            # No credentials - try default user's public projects only
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
    
    # Check if project is already running
    if project.status in [ProjectStatus.CRAWLING, ProjectStatus.PARSING, ProjectStatus.ANALYZING]:
        raise HTTPException(status_code=400, detail="Project is already running")
    
    # Clear existing pages and queue to avoid duplicates
    storage = FileStorage(settings.storage_path)
    storage.delete_project_files(project.user_id, project_id)
    
    # Delete all pages (cascade deletes foreign words)
    await db.execute(
        delete(Page).where(Page.project_id == project_id)
    )
    
    # Delete all queue items
    await db.execute(
        delete(CrawlQueue).where(CrawlQueue.project_id == project_id)
    )
    
    # Reset project stats
    project.stats = {"total_pages": 0, "foreign_words_count": 0}
    project.status = ProjectStatus.PENDING
    await db.commit()
    
    # Add base URL to queue
    queue_item = CrawlQueue(
        project_id=project_id,
        url=project.base_url,
        status=QueueStatus.PENDING
    )
    db.add(queue_item)
    await db.commit()
    
    # Trigger async crawl task
    crawl_project.delay(project_id)


@router.get("/{project_id}/export-xlsx")
async def export_project_xlsx(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request = None,
    token: str | None = Depends(oauth2_scheme_optional),
    guest_session_token: Optional[str] = Query(None, description="Guest session token for unauthenticated access"),
    language: Optional[str] = Query("ru", description="Language code for headers (ru or en)")
):
    """Export aggregated analysis results for all pages in a project to XLSX.
    
    Aggregates all words from all analyzed pages in the project.
    Each word row includes its originating page URL.
    """
    logger.info(f"Export endpoint called: project_id={project_id}, language={language}")
    # Verify project access (similar to other project endpoints)
    user = await get_optional_user(token, db) if token else None
    guest_session = None
    
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
                        Project.user_id == 1,  # Default user
                        Project.guest_session_id == guest_session.id
                    )
                )
                if not project:
                    raise HTTPException(status_code=404, detail="Project not found")
                # Update guest session activity
                from sqlalchemy import update
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
            # No credentials - try default user's public projects only
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
    
    try:
        # Fetch all pages with fz168_raw_response for this project
        result = await db.execute(
            select(Page).where(
                Page.project_id == project_id,
                Page.fz168_raw_response.isnot(None)
            )
        )
        pages = result.scalars().all()
        logger.info(f"Export endpoint: project_id={project_id}, found {len(pages)} pages with raw_response")
        
        if not pages:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No analyzed pages found for this project"
            )
        
        # Aggregate all words from all pages, adding page_url to each word
        all_words_aggregated = []
        for idx, page in enumerate(pages):
            page_data = page.fz168_raw_response
            # The raw_response could be the full response or just the data part
            if isinstance(page_data, dict):
                # If it's the full response with 'data' key
                analysis_data = page_data.get('data', page_data)
            else:
                analysis_data = page_data
            
            words = analysis_data.get('all_words', [])
            for word in words:
                all_words_aggregated.append({
                    **word,
                    'page_url': page.url
                })
        
        analysis_data = {
            'all_words': all_words_aggregated
        }
        
        # Use ExcelExporter - each word has its own page_url
        excel_bytes = ExcelExporter.export_analysis(
            analysis_data=analysis_data,
            selected_statuses=None,  # All statuses
            page_url=None,  # Will use per-word page_url
            language=language or "ru"
        )
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"project_{project_id}_export_{timestamp}.xlsx"
        
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        import traceback, sys
        exc_type, exc_value, exc_tb = sys.exc_info()
        print("EXCEPTION CAUGHT:", type(e).__name__, e, file=sys.stderr, flush=True)
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        # logger.error(f"Error generating project XLSX export: {type(e).__name__}: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate export: {type(e).__name__}: {str(e)}"
        )


@router.post("/{project_id}/export-xlsx/async")
async def start_async_export(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request = None,
    token: str | None = Depends(oauth2_scheme_optional),
    guest_session_token: Optional[str] = Query(None, description="Guest session token for unauthenticated access"),
    language: Optional[str] = Query("ru", description="Language code for headers (ru or en)")
):
    """Start asynchronous XLSX export for a project.

    Returns an export job ID that can be used to check progress and download the file.
    For large projects with many pages, this async approach prevents timeouts.
    """
    # Verify project access
    user = await get_optional_user(token, db) if token else None
    guest_session = None

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
        user_id = user.id
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
                        Project.user_id == 1,  # Default user
                        Project.guest_session_id == guest_session.id
                    )
                )
                if not project:
                    raise HTTPException(status_code=404, detail="Project not found")
                user_id = 1
                # Update guest session activity
                from sqlalchemy import update
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
            # No credentials - try default user's public projects only
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
            user_id = 1

    # Check if project has analyzed pages
    page_count = await safe_scalar(
        db,
        select(func.count()).select_from(Page).where(
            Page.project_id == project_id,
            Page.fz168_raw_response.isnot(None)
        )
    )
    if not page_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No analyzed pages found for this project. Please analyze the project first."
        )

    # Create export job
    from app.schemas.project import ExportJobResponse
    job = ExportJob(
        project_id=project_id,
        user_id=user_id,
        status=ExportJobStatus.PENDING,
        language=language or "ru"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Start Celery task
    from app.tasks.export_tasks import export_project_xlsx
    task = export_project_xlsx.apply_async(args=[job.id])
    job.celery_task_id = task.id
    await db.commit()

    logger.info(f"Started async export job {job.id} for project {project_id}")

    return {
        "job_id": job.id,
        "status": "pending",
        "message": "Export job started. Use the job_id to check progress and download the file."
    }


@router.get("/export-jobs/{job_id}", response_model=ExportJobResponse)
async def get_export_job_status(
    job_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    token: str | None = Depends(oauth2_scheme_optional),
    guest_session_token: Optional[str] = Query(None, description="Guest session token for unauthenticated access")
):
    """Get status and progress of an export job."""
    # Verify access to the job's project
    job = await safe_scalar(db, select(ExportJob).where(ExportJob.id == job_id))
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")

    # Check if user has access to this project
    user = await get_optional_user(token, db) if token else None
    if user:
        # Check project ownership
        project = await safe_scalar(
            db,
            select(Project).where(
                Project.id == job.project_id,
                Project.user_id == user.id
            )
        )
        if not project:
            raise HTTPException(status_code=403, detail="Access denied")
    else:
        # Check guest session
        if guest_session_token:
            result = await db.execute(
                select(GuestSession).where(GuestSession.session_token == guest_session_token)
            )
            guest_session = result.scalar_one_or_none()
            if guest_session:
                project = await safe_scalar(
                    db,
                    select(Project).where(
                        Project.id == job.project_id,
                        Project.user_id == 1,
                        Project.guest_session_id == guest_session.id
                    )
                )
                if not project:
                    raise HTTPException(status_code=403, detail="Access denied")
            else:
                raise HTTPException(status_code=401, detail="Invalid guest session")
        else:
            # No credentials - check default user's public project
            project = await safe_scalar(
                db,
                select(Project).where(
                    Project.id == job.project_id,
                    Project.user_id == 1,
                    Project.guest_session_id.is_(None)
                )
            )
            if not project:
                raise HTTPException(status_code=403, detail="Access denied")

    return job


@router.get("/export-jobs/{job_id}/download")
async def download_export_file(
    job_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    token: str | None = Depends(oauth2_scheme_optional),
    guest_session_token: Optional[str] = Query(None, description="Guest session token for unauthenticated access")
):
    """Download the generated XLSX file for a completed export job."""
    # Verify access (same as get_export_job_status)
    job = await safe_scalar(db, select(ExportJob).where(ExportJob.id == job_id))
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")

    # Check access (similar to get_export_job_status)
    user = await get_optional_user(token, db) if token else None
    if user:
        project = await safe_scalar(
            db,
            select(Project).where(
                Project.id == job.project_id,
                Project.user_id == user.id
            )
        )
        if not project:
            raise HTTPException(status_code=403, detail="Access denied")
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
                        Project.id == job.project_id,
                        Project.user_id == 1,
                        Project.guest_session_id == guest_session.id
                    )
                )
                if not project:
                    raise HTTPException(status_code=403, detail="Access denied")
            else:
                raise HTTPException(status_code=401, detail="Invalid guest session")
        else:
            project = await safe_scalar(
                db,
                select(Project).where(
                    Project.id == job.project_id,
                    Project.user_id == 1,
                    Project.guest_session_id.is_(None)
                )
            )
            if not project:
                raise HTTPException(status_code=403, detail="Access denied")

    # Check if job is completed
    if job.status != ExportJobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Export job is not completed. Current status: {job.status}"
        )

    if not job.file_path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Export job marked as completed but no file found"
        )

    # Read file bytes
    try:
        file_path = Path(job.file_path)
        # If the stored path is relative, resolve it relative to storage path
        if not file_path.is_absolute():
            storage_base = Path(settings.storage_path).resolve()
            file_path = storage_base / file_path
        # Normalize the path
        file_path = file_path.resolve()
        # Security check: ensure the file is within the storage base directory
        storage_base = Path(settings.storage_path).resolve()
        if not file_path.is_relative_to(storage_base):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid file path"
            )
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export file not found on server"
            )
        file_bytes = file_path.read_bytes()
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export file not found on server"
        )

    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"project_{job.project_id}_export_{timestamp}.xlsx"

    # Return raw bytes as Response
    return Response(
        content=file_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/export-jobs/{job_id}/cancel")
async def cancel_export_job(
    job_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    token: str | None = Depends(oauth2_scheme_optional),
    guest_session_token: Optional[str] = Query(None, description="Guest session token for unauthenticated access")
):
    """Cancel a running export job."""
    from celery.result import AsyncResult
    from app.tasks.celery_app import celery_app

    # Verify access to the job's project (same as get_export_job_status)
    job = await safe_scalar(db, select(ExportJob).where(ExportJob.id == job_id))
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")

    # Check if user has access to this project
    user = await get_optional_user(token, db) if token else None
    if user:
        project = await safe_scalar(
            db,
            select(Project).where(
                Project.id == job.project_id,
                Project.user_id == user.id
            )
        )
        if not project:
            raise HTTPException(status_code=403, detail="Access denied")
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
                        Project.id == job.project_id,
                        Project.user_id == 1,
                        Project.guest_session_id == guest_session.id
                    )
                )
                if not project:
                    raise HTTPException(status_code=403, detail="Access denied")
            else:
                raise HTTPException(status_code=401, detail="Invalid guest session")
        else:
            project = await safe_scalar(
                db,
                select(Project).where(
                    Project.id == job.project_id,
                    Project.user_id == 1,
                    Project.guest_session_id.is_(None)
                )
            )
            if not project:
                raise HTTPException(status_code=403, detail="Access denied")

    # Check if job can be cancelled
    if job.status not in [ExportJobStatus.PENDING, ExportJobStatus.PROCESSING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Export job cannot be cancelled. Current status: {job.status}"
        )

    # Set cancellation flag in database
    job.cancelled = 1
    await db.commit()

    # Also try to revoke the Celery task if it has a task ID
    if job.celery_task_id:
        try:
            celery_app.control.revoke(job.celery_task_id, terminate=True)
            logger.info(f"Cancelled Celery task {job.celery_task_id} for export job {job_id}")
        except Exception as e:
            logger.error(f"Failed to revoke Celery task {job.celery_task_id}: {e}")

    # Publish cancellation event
    await publish_export_update(job_id, "cancelled", {"message": "Export job was cancelled by user"})

    return {"message": "Export job cancellation requested"}
