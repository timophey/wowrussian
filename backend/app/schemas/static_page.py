from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class StaticPageBase(BaseModel):
    """Base schema for static page."""
    url: str
    lang: str = "ru"
    title: str
    content_md: Optional[str] = None


class StaticPageCreate(StaticPageBase):
    """Schema for creating a static page."""
    pass


class StaticPageUpdate(BaseModel):
    """Schema for updating a static page."""
    title: Optional[str] = None
    content_md: Optional[str] = None


class StaticPageResponse(StaticPageBase):
    """Response schema for static page."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StaticPageListResponse(BaseModel):
    """Response schema for listing static pages."""
    pages: list[StaticPageResponse]
    total: int
