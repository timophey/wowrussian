from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class GuestSession(Base):
    """Guest session model - tracks unauthenticated users."""

    __tablename__ = "guest_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_token = Column(String, unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    # Relationships
    projects = relationship("Project", back_populates="guest_session", cascade="all, delete-orphan")
