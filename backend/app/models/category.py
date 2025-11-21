from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    slug = Column(String, nullable=False)
    description = Column(String, nullable=True)  # Description for LLM classification
    display_order = Column(Integer, default=0)
    is_deleted = Column(Boolean, default=False, index=True)  # Soft delete flag
    deleted_at = Column(DateTime, nullable=True)  # When category was deleted
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="categories")
    articles = relationship("Article", back_populates="category")
