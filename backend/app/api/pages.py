from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.project import Project
from app.models.page import Page, PageStatus
from app.models.user import User
from app.models.foreign_word import ForeignWord
from app.schemas.page import PageResponse, PageDetail
from app.services.file_storage import FileStorage
from app.core.config import settings
from app.utils.db import safe_scalar

router = APIRouter(prefix="/projects", tags=["pages"])


@router.get("/{project_id}/pages", response_model=List[PageResponse])
async def list_pages(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    status: PageStatus = None,
    current_user: User = Depends(lambda: None)
):
    """List pages for a project with optional status filter."""
    query = select(Page).where(Page.project_id == project_id)
    
    if status:
        query = query.where(Page.status == status)
    
    query = query.order_by(Page.created_at.desc())
    
    result = await db.execute(query)
    pages = result.scalars().all()
    return pages


@router.get("/{project_id}/pages/{page_id}", response_model=PageDetail)
async def get_page(
    project_id: int,
    page_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(lambda: None)
):
    """Get page details including foreign words."""
    page = await safe_scalar(db, select(Page).where(Page.id == page_id))
    if not page or page.project_id != project_id:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # Get foreign words
    result = await db.execute(
        select(ForeignWord)
        .where(ForeignWord.page_id == page_id)
        .order_by(ForeignWord.count.desc())
    )
    foreign_words = result.scalars().all()
    
    # Construct PageDetail manually to avoid lazy loading of foreign_words
    page_data = PageResponse.from_orm(page).model_dump()
    detail = PageDetail(
        **page_data,
        foreign_words=[
            {"word": fw.word, "count": fw.count, "language_guess": fw.language_guess}
            for fw in foreign_words
        ]
    )
    
    # Load HTML and text content from files
    storage = FileStorage(settings.storage_path)
    if page.html_file_path:
        try:
            detail.html_content = storage.get_file_content(page.html_file_path)
        except FileNotFoundError:
            detail.html_content = None
    
    if page.text_file_path:
        try:
            detail.text_content = storage.get_file_content(page.text_file_path)
        except FileNotFoundError:
            detail.text_content = None
    
    return detail


@router.get("/{project_id}/pages/{page_id}/html")
async def get_page_html(
    project_id: int,
    page_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(lambda: None)
):
    """Get raw HTML of a page."""
    page = await safe_scalar(db, select(Page).where(Page.id == page_id))
    if not page or page.project_id != project_id:
        raise HTTPException(status_code=404, detail="Page not found")
    
    storage = FileStorage(settings.storage_path)
    try:
        html_content = storage.get_file_content(page.html_file_path)
        return {"html": html_content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="HTML file not found")


@router.get("/{project_id}/pages/{page_id}/text")
async def get_page_text(
    project_id: int,
    page_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(lambda: None)
):
    """Get extracted text of a page."""
    page = await safe_scalar(db, select(Page).where(Page.id == page_id))
    if not page or page.project_id != project_id:
        raise HTTPException(status_code=404, detail="Page not found")
    
    storage = FileStorage(settings.storage_path)
    try:
        text_content = storage.get_file_content(page.text_file_path)
        return {"text": text_content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Text file not found")