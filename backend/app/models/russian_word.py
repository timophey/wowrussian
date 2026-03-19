from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.core.database import Base


class RussianWord(Base):
    """Russian word model - stores detected Russian words from pages with source information."""

    __tablename__ = "russian_words"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(Integer, ForeignKey("pages.id", ondelete="CASCADE"), nullable=False)
    word = Column(String, nullable=False, index=True)
    count = Column(Integer, default=1, nullable=False)
    source = Column(String, nullable=True)  # 'dictionary', 'fallback', or None

    # Composite index for faster queries
    __table_args__ = (
        Index('idx_page_russian_word', 'page_id', 'word', unique=True),
    )

    # Relationships
    page = relationship("Page", back_populates="russian_words")
