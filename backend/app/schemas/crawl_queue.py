from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class QueueStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class CrawlQueueBase(BaseModel):
    url: str


class CrawlQueueCreate(CrawlQueueBase):
    pass


class CrawlQueueResponse(BaseModel):
    id: int
    project_id: int
    url: str
    status: QueueStatus
    attempts: int
    last_attempt_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Alias for compatibility with __init__.py imports
CrawlQueue = CrawlQueueResponse