from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class ProjectStatus(str, enum.Enum):
    """Project status enumeration."""
    PENDING = "pending"
    CRAWLING = "crawling"
    PARSING = "parsing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


class Project(Base):
    """Project model - represents a website analysis project."""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    domain = Column(String, nullable=False, index=True)
    base_url = Column(String, nullable=False)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.PENDING, nullable=False)
    stats = Column(JSON, default=dict)  # {"total_pages": 0, "foreign_words_count": 0, ...}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="projects")
    pages = relationship("Page", back_populates="project", cascade="all, delete-orphan")
    crawl_queue = relationship("CrawlQueue", back_populates="project", cascade="all, delete-orphan")