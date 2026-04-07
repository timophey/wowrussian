from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint
from app.core.database import Base


class StaticPage(Base):
    """Static page model for storing markdown content with multilingual support."""

    __tablename__ = "static_pages"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False, index=True)  # e.g., "legal-info", "privacy-policy"
    lang = Column(String, nullable=False, default="ru", index=True)  # e.g., "ru", "en"
    title = Column(String, nullable=False)
    content_md = Column(Text, nullable=True)  # Markdown content
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Unique constraint: each URL can have one page per language
    __table_args__ = (
        UniqueConstraint("url", "lang", name="uq_static_page_url_lang"),
    )

    def __repr__(self):
        return f"<StaticPage url='{self.url}' lang='{self.lang}' title='{self.title}'>"
