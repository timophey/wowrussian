from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, asc, desc
import redis.asyncio as redis

from app.core.database import get_db
from app.core.config import settings
from app.models.project import Project, ProjectStatus
from app.models.page import Page, PageStatus
from app.models.user import User
from app.models.crawl_queue import CrawlQueue, QueueStatus
from app.models.foreign_word import ForeignWord
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectDetail
from app.schemas.page import PageResponse
from app.services.file_storage import FileStorage
from app.tasks import crawl_project
from app.utils.db import safe_scalar
from app.api.auth import get_current_user

async def get_optional_user(
    token: str | None,
    db: AsyncSession
) -> User | None:
    """Get current user if token is valid, otherwise return None."""
    if not token:
        return None
    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None

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
    token: str | None = Depends(oauth2_scheme_optional)
):
    """Create a new project from URL.
    If user is authenticated, project belongs to them.
    If not, project belongs to default user (ID=1)."""
    from urllib.parse import urlparse
    
    # Get user from token if provided
    user_id = 1  # default user
    if token:
        try:
            current_user = await get_current_user(token, db)
            user_id = current_user.id
        except HTTPException:
            # Invalid token, use default user
            user_id = 1
    
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
    db: Annotated[AsyncSession, Depends(get_db)],
    token: str | None = Depends(oauth2_scheme_optional),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order: asc or desc")
):
    """List all projects for current user or default user (for guests)."""
    user = await get_optional_user(token, db)
    
    # Determine user_id to filter by
    user_id = user.id if user else 1  # Use authenticated user or default user
    
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
    
    # Build query with dynamic ordering - filter by user
    query = select(Project).where(Project.user_id == user_id)
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
    token: str | None = Depends(oauth2_scheme_optional)
):
    """Get project details with statistics.
    Allows access to projects belonging to the default user (ID=1) without authentication,
    or to authenticated users' own projects."""
    user = await get_optional_user(token, db)
    
    # Determine user_id to filter by
    if user:
        user_id = user.id
    else:
        user_id = 1  # For guests, only allow access to default user's projects
    
    # Ensure project belongs to the appropriate user
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
    token: str | None = Depends(oauth2_scheme_optional)
):
    """Delete project and all associated data.
    Allows deletion of default user's projects without authentication,
    or authenticated users' own projects."""
    user = await get_optional_user(token, db)
    
    # Determine user_id to filter by
    user_id = user.id if user else 1
    
    # Ensure project belongs to the appropriate user
    project = await safe_scalar(
        db,
        select(Project).where(
            Project.id == project_id,
            Project.user_id == user_id
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
    token: str | None = Depends(oauth2_scheme_optional)
):
    """Clear all pages and crawl queue for a project.
    Allows clearing of default user's projects without authentication,
    or authenticated users' own projects."""
    user = await get_optional_user(token, db)
    
    # Determine user_id to filter by
    user_id = user.id if user else 1
    
    # Ensure project belongs to the appropriate user
    project = await safe_scalar(
        db,
        select(Project).where(
            Project.id == project_id,
            Project.user_id == user_id
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
    token: str | None = Depends(oauth2_scheme_optional)
):
    """Stop project scanning.
    Allows stopping of default user's projects without authentication,
    or authenticated users' own projects."""
    user = await get_optional_user(token, db)
    
    # Determine user_id to filter by
    user_id = user.id if user else 1
    
    # Ensure project belongs to the appropriate user
    project = await safe_scalar(
        db,
        select(Project).where(
            Project.id == project_id,
            Project.user_id == user_id
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
    token: str | None = Depends(oauth2_scheme_optional)
):
    """Manually start project crawling.
    Allows starting of default user's projects without authentication,
    or authenticated users' own projects."""
    user = await get_optional_user(token, db)
    
    # Determine user_id to filter by
    user_id = user.id if user else 1
    
    # Ensure project belongs to the appropriate user
    project = await safe_scalar(
        db,
        select(Project).where(
            Project.id == project_id,
            Project.user_id == user_id
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
    
    return {"message": "Project started"}