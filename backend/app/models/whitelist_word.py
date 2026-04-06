from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class WhitelistWord(Base):
    """Whitelist word model - stores words that should be excluded from violations."""

    __tablename__ = "whitelist_words"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    word = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="whitelist_words")

    # Unique constraint: each word can only appear once per project
    __table_args__ = (
        UniqueConstraint('project_id', 'word', name='uq_project_word'),
    )
