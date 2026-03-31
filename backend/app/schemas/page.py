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
    # 168fz metadata (optional, may be null for pages not analyzed with 168-fz)
    fz168_summary: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class PageDetail(PageResponse):
    html_content: Optional[str] = None
    text_content: Optional[str] = None
    foreign_words: List[Dict[str, Any]] = []  # [{"word": "test", "count": 5, "language_guess": "en"}, ...]
    russian_words: List[Dict[str, Any]] = []  # [{"word": "привет", "count": 3, "source": "dictionary"}, ...]
    # 168fz metadata
    fz168_statistics: Optional[Dict[str, Any]] = None  # statistics from 168fz
    fz168_summary: Optional[Dict[str, Any]] = None  # summary from 168fz
    fz168_checks: Optional[Dict[str, Any]] = None  # checks (foreign_words, prohibited_words, etc.)
    fz168_dictionaries: Optional[List[Dict[str, Any]]] = None  # list of dictionaries used
    fz168_raw_response: Optional[Dict[str, Any]] = None  # complete raw response from 168fz API

# Alias for compatibility with __init__.py imports
Page = PageResponse