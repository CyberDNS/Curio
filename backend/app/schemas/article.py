from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict


class ArticleBase(BaseModel):
    title: str
    link: str
    description: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    image_url: Optional[str] = None
    image_urls: Optional[List[str]] = None


class ArticleCreate(ArticleBase):
    feed_id: int
    category_id: Optional[int] = None


class ArticleUpdate(BaseModel):
    is_read: Optional[bool] = None


class Article(ArticleBase):
    id: int
    feed_id: Optional[int] = None
    category_id: Optional[int] = None
    image_url: Optional[str] = None

    # LLM-enhanced fields
    llm_title: Optional[str] = None
    llm_subtitle: Optional[str] = None
    llm_summary: Optional[str] = None
    llm_category_suggestion: Optional[str] = None
    image_urls: Optional[List[str]] = None

    # Analysis fields
    summary: Optional[str] = None
    relevance_score: float = 0.0  # >= 0.6 means "recommended"
    tags: Optional[List[str]] = None

    # User feedback and score adjustment
    user_vote: int = 0  # 0 = neutral, -1 = downvote
    vote_updated_at: Optional[datetime] = None
    adjusted_relevance_score: Optional[float] = (
        None  # Final score after downvote adjustment
    )
    score_adjustment_reason: Optional[str] = None  # Brief explanation for UI

    # Newspaper tracking
    newspaper_appearances: Optional[Dict[str, str]] = {}  # {date: section}

    # Feed source information
    feed_source_title: Optional[str] = None  # From feed.source_title

    # Duplicate detection
    is_duplicate: bool = False
    duplicate_of_id: Optional[int] = None
    title_embedding: Optional[str] = None  # JSON string of embedding vector

    # Metadata
    is_read: bool = False  # False = "NEW" article, True = read
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
