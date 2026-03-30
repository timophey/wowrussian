from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, asc, desc, func

from app.core.database import get_db
from app.models.project import Project
from app.models.page import Page, PageStatus
from app.models.user import User
from app.models.foreign_word import ForeignWord
from app.models.russian_word import RussianWord
from app.models.guest_session import GuestSession
from app.schemas.page import PageResponse, PageDetail
from app.services.file_storage import FileStorage
from app.core.config import settings
from app.utils.db import safe_scalar
from app.api.auth import get_optional_user
from app.api.admin import verify_admin_access

router = APIRouter(prefix="/projects", tags=["pages"])


async def verify_project_access(
    request: Request,
    project_id: int,
    db: AsyncSession,
    token: str | None = None,
    guest_session_token: Optional[str] = None
) -> Project:
    """Verify that the requester has access to the project.
    Supports authenticated users and guest sessions."""
    from fastapi.security import OAuth2PasswordBearer
    oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

    # Try to get authenticated user first
    if token is None:
        token = await oauth2_scheme_optional(request)
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
        return project

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
            return project
        else:
            # Invalid guest token
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid guest session"
            )

    # No credentials at all - only allow access to default user's public projects (no guest_session_id)
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
    return project


@router.get("/{project_id}/pages", response_model=List[PageResponse])
async def list_pages(
    project_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    status: PageStatus = None,
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    guest_session_token: Optional[str] = Query(None, description="Guest session token for unauthenticated access")
):
    """List pages for a project with optional status filter and sorting."""
    # Verify project access
    await verify_project_access(request, project_id, db, None, guest_session_token)

    query = select(Page).where(Page.project_id == project_id)
    
    if status:
        query = query.where(Page.status == status)
    
    # Validate sort_by parameter
    allowed_sort_fields = {
        "url": Page.url,
        "status": Page.status,
        "foreign_words_count": Page.foreign_words_count,
        "words_count": Page.words_count,
        "created_at": Page.created_at
    }
    
    if sort_by not in allowed_sort_fields:
        sort_by = "created_at"
    
    # Validate sort_order
    order_func = asc if sort_order.lower() == "asc" else desc
    
    # Apply ordering
    query = query.order_by(order_func(allowed_sort_fields[sort_by]))
    
    result = await db.execute(query)
    pages = result.scalars().all()
    return pages


@router.get("/{project_id}/pages/{page_id}", response_model=PageDetail)
async def get_page(
    project_id: int,
    page_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    guest_session_token: Optional[str] = Query(None, description="Guest session token for unauthenticated access")
):
    """Get page details including foreign and Russian words."""
    # Verify project access
    await verify_project_access(request, project_id, db, None, guest_session_token)

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
    
    # Get russian words
    result = await db.execute(
        select(RussianWord)
        .where(RussianWord.page_id == page_id)
        .order_by(RussianWord.count.desc())
    )
    russian_words = result.scalars().all()
    
    # Construct PageDetail manually to avoid lazy loading
    page_data = PageResponse.from_orm(page).model_dump()
    detail = PageDetail(
        **page_data,
        foreign_words=[
            {"word": fw.word, "count": fw.count, "language_guess": fw.language_guess}
            for fw in foreign_words
        ],
        russian_words=[
            {"word": rw.word, "count": rw.count, "source": rw.source}
            for rw in russian_words
        ],
        # Include 168fz metadata if available
        fz168_statistics=page.fz168_statistics,
        fz168_summary=page.fz168_summary,
        fz168_checks=page.fz168_checks,
        fz168_dictionaries=page.fz168_dictionaries
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
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    guest_session_token: Optional[str] = Query(None, description="Guest session token for unauthenticated access")
):
    """Get raw HTML of a page."""
    # Verify project access
    await verify_project_access(request, project_id, db, None, guest_session_token)

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
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    guest_session_token: Optional[str] = Query(None, description="Guest session token for unauthenticated access")
):
    """Get extracted text of a page."""
    # Verify project access
    await verify_project_access(request, project_id, db, None, guest_session_token)

    page = await safe_scalar(db, select(Page).where(Page.id == page_id))
    if not page or page.project_id != project_id:
        raise HTTPException(status_code=404, detail="Page not found")
    
    storage = FileStorage(settings.storage_path)
    try:
        text_content = storage.get_file_content(page.text_file_path)
        return {"text": text_content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Text file not found")