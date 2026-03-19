from pydantic import BaseModel, Field, AnyHttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PageStatus(str, Enum):
    QUEUED = "queued"
    CRAWLING = "crawling"
    PARSED = "parsed"
    ANALYZED = "analyzed"
    FAILED = "failed"


class PageBase(BaseModel):
    url: AnyHttpUrl


class PageCreate(PageBase):
    pass


class PageResponse(BaseModel):
    id: int
    project_id: int
    url: str
    status: PageStatus
    words_count: int
    foreign_words_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PageDetail(PageResponse):
    html_content: Optional[str] = None
    text_content: Optional[str] = None
    foreign_words: List[Dict[str, Any]] = []  # [{"word": "test", "count": 5, "language_guess": "en"}, ...]
    russian_words: List[Dict[str, Any]] = []  # [{"word": "привет", "count": 3, "source": "dictionary"}, ...]

# Alias for compatibility with __init__.py imports
Page = PageResponse