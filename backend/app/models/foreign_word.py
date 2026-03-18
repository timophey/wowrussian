from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.core.database import Base


class ForeignWord(Base):
    """Foreign word model - stores detected foreign words from pages."""

    __tablename__ = "foreign_words"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(Integer, ForeignKey("pages.id", ondelete="CASCADE"), nullable=False)
    word = Column(String, nullable=False, index=True)
    count = Column(Integer, default=1, nullable=False)
    language_guess = Column(String, nullable=True)  # e.g., "en", "de", etc.

    # Composite index for faster queries
    __table_args__ = (
        Index('idx_page_word', 'page_id', 'word', unique=True),
    )

    # Relationships
    page = relationship("Page", back_populates="foreign_words")