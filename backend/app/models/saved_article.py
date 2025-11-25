from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


# Many-to-many association table for saved articles and tags
saved_article_tags = Table(
    "saved_article_tags",
    Base.metadata,
    Column(
        "saved_article_id",
        Integer,
        ForeignKey("saved_articles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    ),
)


class SavedArticle(Base):
    __tablename__ = "saved_articles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    article_id = Column(
        Integer,
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    saved_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="saved_articles")
    article = relationship("Article")
    tags = relationship(
        "Tag", secondary=saved_article_tags, back_populates="saved_articles"
    )


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="tags")
    saved_articles = relationship(
        "SavedArticle", secondary=saved_article_tags, back_populates="tags"
    )

    # Ensure unique tag names per user
    __table_args__ = ({"sqlite_autoincrement": True},)
