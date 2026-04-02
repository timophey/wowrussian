from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ProjectStatus(str, Enum):
    PENDING = "pending"
    CRAWLING = "crawling"
    PARSING = "parsing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


class ExportJobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProjectBase(BaseModel):
    url: HttpUrl


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    status: Optional[ProjectStatus] = None
    stats: Optional[Dict[str, Any]] = None


class ProjectResponse(BaseModel):
    id: int
    user_id: int
    domain: str
    base_url: str
    status: ProjectStatus
    stats: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectDetail(ProjectResponse):
    pages_count: int = 0
    queue_count: int = 0
    processing_count: int = 0
    completed_count: int = 0
    total_foreign_words: int = 0
    unique_foreign_words: int = 0


class ExportJobResponse(BaseModel):
    id: int
    project_id: int
    user_id: int
    status: ExportJobStatus
    language: str
    progress: int
    total_words: Optional[int] = None
    processed_words: Optional[int] = None
    file_size: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExportJobDetail(ExportJobResponse):
    file_path: Optional[str] = None


# Alias for compatibility with __init__.py imports
Project = ProjectResponse
