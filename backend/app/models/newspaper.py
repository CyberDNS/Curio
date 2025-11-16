from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Newspaper(Base):
    __tablename__ = "newspapers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)  # The date this newspaper is for

    # Structure contains the curated newspaper content
    # Format: {
    #   "today": [article_id_1, article_id_2, ...],
    #   "categories": {
    #     "category_slug_1": [article_id_3, article_id_4, ...],
    #     "category_slug_2": [article_id_5, article_id_6, ...]
    #   }
    # }
    structure = Column(JSON, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="newspapers")
