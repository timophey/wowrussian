from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.core.database import Base


class QueueStatus(str, enum.Enum):
    """Queue status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class CrawlQueue(Base):
    """Crawl queue model - manages URLs to be crawled."""

    __tablename__ = "crawl_queue"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    url = Column(String, nullable=False)
    status = Column(SQLEnum(QueueStatus), default=QueueStatus.PENDING, nullable=False)
    attempts = Column(Integer, default=0)
    last_attempt_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="crawl_queue")

    # Index for efficient querying
    __table_args__ = (
        Index('idx_project_status', 'project_id', 'status'),
    )