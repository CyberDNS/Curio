from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional


class FeedBase(BaseModel):
    url: str
    title: Optional[str] = None
    source_title: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True
    fetch_interval: int = 60


class FeedCreate(FeedBase):
    pass


class FeedUpdate(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None
    source_title: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    fetch_interval: Optional[int] = None


class Feed(FeedBase):
    id: int
    source_title: Optional[str] = None
    last_fetched: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
