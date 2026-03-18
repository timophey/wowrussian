from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import redis.asyncio as redis

from app.core.database import get_db
from app.core.config import settings
from app.models.project import Project, ProjectStatus
from app.models.page import Page, PageStatus
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectDetail
from app.schemas.page import PageResponse
from app.services.file_storage import FileStorage
from app.tasks import crawl_project

router = APIRouter(prefix="/projects", tags=["projects"])


async def get_redis():
    """Get Redis connection."""
    return redis.from_url(settings.redis_url)


@router.post("", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(lambda: None)  # TODO: Implement proper auth
):
    """Create a new project from URL."""
    from urllib.parse import urlparse
    
    # Parse URL to get domain
    parsed = urlparse(str(project.url))
    domain = parsed.netloc
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    # Create project
    new_project = Project(
        user_id=1,  # TODO: Use current_user.id
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
    
    # Trigger async crawl task
    crawl_project.delay(new_project.id)
    
    return new_project


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(lambda: None)
):
    """List all projects for current user."""
    result = await db.execute(
        select(Project).where(Project.user_id == 1).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()
    return projects


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(lambda: None)
):
    """Get project details with statistics."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get counts
    total_pages = await db.scalar(
        select(func.count()).select_from(Page).where(Page.project_id == project_id)
    )
    queue_count = await db.scalar(
        select(func.count()).select_from(Project.crawl_queue).where(
            Project.crawl_queue.c.project_id == project_id,
            Project.crawl_queue.c.status == QueueStatus.PENDING
        )
    )
    processing_count = await db.scalar(
        select(func.count()).select_from(Page).where(
            Page.project_id == project_id,
            Page.status.in_([PageStatus.QUEUED, PageStatus.CRAWLING, PageStatus.PARSED])
        )
    )
    completed_count = await db.scalar(
        select(func.count()).select_from(Page).where(
            Page.project_id == project_id,
            Page.status == PageStatus.ANALYZED
        )
    )
    total_foreign_words = await db.scalar(
        select(func.sum(Page.foreign_words_count)).where(Page.project_id == project_id)
    )
    unique_foreign_words = await db.scalar(
        select(func.count()).select_from(Page.foreign_words).distinct(Page.foreign_words.c.word)
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
    current_user: User = Depends(lambda: None)
):
    """Delete project and all associated data."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Delete files
    storage = FileStorage(settings.storage_path)
    storage.delete_project_files(1, project_id)  # TODO: Use current_user.id
    
    # Delete project (cascade will handle related records)
    await db.delete(project)
    await db.commit()
    
    return {"message": "Project deleted"}


@router.post("/{project_id}/stop")
async def stop_project(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(lambda: None)
):
    """Stop project scanning."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.status = ProjectStatus.STOPPED
    await db.commit()
    
    # TODO: Send stop signal to Celery task
    
    return {"message": "Project stopped"}