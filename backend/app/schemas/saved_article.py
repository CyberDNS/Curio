from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, List
from .article import Article


class TagBase(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and normalize tag name."""
        # Strip whitespace and convert to lowercase for consistency
        v = v.strip().lower()
        if not v:
            raise ValueError("Tag name cannot be empty")
        if len(v) > 50:
            raise ValueError("Tag name cannot exceed 50 characters")
        return v


class TagCreate(TagBase):
    pass


class Tag(TagBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class SavedArticleBase(BaseModel):
    article_id: int


class SavedArticleCreate(SavedArticleBase):
    tag_names: Optional[List[str]] = []  # List of tag names to associate


class SavedArticleUpdateTags(BaseModel):
    tag_names: List[str]  # Replace all tags with this list


class SavedArticle(SavedArticleBase):
    id: int
    user_id: int
    saved_at: datetime
    tags: List[Tag] = []

    class Config:
        from_attributes = True


class SavedArticleWithArticle(SavedArticle):
    """SavedArticle with full article details included."""

    article: Article

    class Config:
        from_attributes = True
