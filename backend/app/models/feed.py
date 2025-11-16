from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Feed(Base):
    __tablename__ = "feeds"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    url = Column(String, nullable=False, index=True)
    title = Column(String)
    source_title = Column(String)  # User-friendly source name for display
    description = Column(String)
    is_active = Column(Boolean, default=True)
    last_fetched = Column(DateTime, nullable=True)
    fetch_interval = Column(Integer, default=60)  # minutes
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="feeds")
    articles = relationship(
        "Article", back_populates="feed", cascade="all, delete-orphan"
    )
