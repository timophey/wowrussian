from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class PageStatus(str, enum.Enum):
    """Page status enumeration."""
    QUEUED = "queued"
    CRAWLING = "crawling"
    PARSED = "parsed"
    ANALYZED = "analyzed"
    FAILED = "failed"


class Page(Base):
    """Page model - represents a single crawled page."""

    __tablename__ = "pages"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    url = Column(String, nullable=False, index=True)
    html_file_path = Column(String, nullable=True)  # Relative path to stored HTML file
    text_file_path = Column(String, nullable=True)  # Relative path to extracted text file
    status = Column(SQLEnum(PageStatus), default=PageStatus.QUEUED, nullable=False)
    words_count = Column(Integer, default=0)
    foreign_words_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="pages")
    foreign_words = relationship("ForeignWord", back_populates="page", cascade="all, delete-orphan")