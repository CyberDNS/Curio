from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Float,
    JSON,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    feed_id = Column(Integer, ForeignKey("feeds.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    # Original article data from RSS
    title = Column(String, nullable=False)
    link = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text)
    content = Column(Text)
    author = Column(String)
    published_date = Column(DateTime)

    # LLM enhanced data
    llm_title = Column(String)  # LLM-generated improved title
    llm_subtitle = Column(String)  # LLM-generated subtitle/tagline
    llm_summary = Column(Text)  # LLM-generated summary
    llm_category_suggestion = Column(String)  # LLM-suggested category name
    image_urls = Column(JSON)  # List of image URLs extracted by LLM

    # LLM analysis
    summary = Column(Text)  # Kept for backward compatibility
    relevance_score = Column(Float, default=0.0)  # >= 0.6 means "recommended"

    # Duplicate detection
    is_duplicate = Column(Boolean, default=False)  # True if article is a duplicate
    duplicate_of_id = Column(
        Integer, ForeignKey("articles.id"), nullable=True
    )  # Points to the best/original article
    # Store embeddings as JSON text - compatible with all PostgreSQL installations
    title_embedding = Column(
        Text, nullable=True
    )  # OpenAI embedding for similarity (JSON array)

    # Newspaper tracking
    # Format: {"2025-01-15": "today", "2025-01-16": "technology"}
    # Tracks which newspaper edition (date) and which section the article appeared in
    newspaper_appearances = Column(JSON, default=dict)

    # Metadata
    is_read = Column(Boolean, default=False)  # False = "NEW" article, True = read
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="articles")
    feed = relationship("Feed", back_populates="articles")
    category = relationship("Category", back_populates="articles")
    duplicate_of = relationship(
        "Article", remote_side=[id], foreign_keys=[duplicate_of_id]
    )

    @property
    def feed_source_title(self):
        """Dynamic property to get feed source title from relationship."""
        return self.feed.source_title if self.feed else None
