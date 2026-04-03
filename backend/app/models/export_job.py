from datetime import datetime
import enum
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


def _export_job_status_values(x):
    """Convert ExportJobStatus enum to its value for database operations.
    Works for both DDL (when x is the enum class) and binding (when x is an enum member).
    """
    if isinstance(x, type):
        # DDL: x is the enum class, return list of values
        return [member.value for member in x]
    # Binding: x is an enum member, return its value
    return x.value


class ExportJobStatus(str, enum.Enum):
    """Export job status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExportJob(Base):
    """ExportJob model - tracks asynchronous Excel export jobs."""

    __tablename__ = "export_jobs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(SQLEnum(ExportJobStatus, name='exportjobstatus', values_callable=_export_job_status_values), default=ExportJobStatus.PENDING, nullable=False)
    language = Column(String, default="ru", nullable=False)
    timezone = Column(String, default="UTC", nullable=False)  # Client's timezone (e.g., "Asia/Yekaterinburg")
    progress = Column(Integer, default=0)  # 0-100 percentage
    total_words = Column(Integer, default=0)
    processed_words = Column(Integer, default=0)
    file_path = Column(String, nullable=True)  # Path to generated file
    file_size = Column(Integer, nullable=True)  # File size in bytes
    error_message = Column(String, nullable=True)
    celery_task_id = Column(String, nullable=True)
    cancelled = Column(Integer, default=0, nullable=False)  # 0 = not cancelled, 1 = cancelled
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="export_jobs")
    owner = relationship("User", back_populates="export_jobs")
