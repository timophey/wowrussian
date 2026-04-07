from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.static_page import StaticPage
from app.schemas.static_page import (
    StaticPageCreate,
    StaticPageUpdate,
    StaticPageResponse,
    StaticPageListResponse,
)
from app.api.admin import get_admin_or_role_admin
from app.models.user import User

router = APIRouter(prefix="/static-pages", tags=["static-pages"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


@router.get("/{url}", response_model=StaticPageResponse)
async def get_static_page(
    url: str,
    lang: str = Query(default="ru", description="Language code"),
    db: AsyncSession = Depends(get_db),
):
    """Get a static page by URL and language."""
    result = await db.execute(
        select(StaticPage).where(StaticPage.url == url, StaticPage.lang == lang)
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page '{url}' not found for language '{lang}'",
        )
    return page


@router.get("/", response_model=StaticPageListResponse)
async def list_static_pages(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """List all static pages."""
    # Get total count
    count_result = await db.execute(select(func.count(StaticPage.id)))
    total = count_result.scalar_one()

    # Get pages
    result = await db.execute(
        select(StaticPage).order_by(StaticPage.url, StaticPage.lang).offset(skip).limit(limit)
    )
    pages = result.scalars().all()

    return StaticPageListResponse(pages=pages, total=total)


@router.post("/", response_model=StaticPageResponse, status_code=status.HTTP_201_CREATED)
async def create_static_page(
    page_data: StaticPageCreate,
    current_user: Annotated[User, Depends(get_admin_or_role_admin)],
    db: AsyncSession = Depends(get_db),
):
    """Create a new static page (admin only)."""
    # Check if page already exists
    existing = await db.execute(
        select(StaticPage).where(StaticPage.url == page_data.url, StaticPage.lang == page_data.lang)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Page '{page_data.url}' already exists for language '{page_data.lang}'",
        )

    new_page = StaticPage(
        url=page_data.url,
        lang=page_data.lang,
        title=page_data.title,
        content_md=page_data.content_md,
    )
    db.add(new_page)
    await db.commit()
    await db.refresh(new_page)
    return new_page


@router.put("/{page_id}", response_model=StaticPageResponse)
async def update_static_page(
    page_id: int,
    page_data: StaticPageUpdate,
    current_user: Annotated[User, Depends(get_admin_or_role_admin)],
    db: AsyncSession = Depends(get_db),
):
    """Update a static page (admin only)."""
    result = await db.execute(select(StaticPage).where(StaticPage.id == page_id))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page with id {page_id} not found",
        )

    # Update fields
    if page_data.title is not None:
        page.title = page_data.title
    if page_data.content_md is not None:
        page.content_md = page_data.content_md

    await db.commit()
    await db.refresh(page)
    return page


@router.delete("/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_static_page(
    page_id: int,
    current_user: Annotated[User, Depends(get_admin_or_role_admin)],
    db: AsyncSession = Depends(get_db),
):
    """Delete a static page (admin only)."""
    result = await db.execute(select(StaticPage).where(StaticPage.id == page_id))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page with id {page_id} not found",
        )

    await db.delete(page)
    await db.commit()
    return None
