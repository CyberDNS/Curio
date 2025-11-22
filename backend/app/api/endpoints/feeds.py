from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.feed import Feed
from app.models.user import User
from app.schemas.feed import Feed as FeedSchema, FeedCreate, FeedUpdate

router = APIRouter()


@router.get("/", response_model=List[FeedSchema])
def get_feeds(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all RSS feeds for the current user."""
    feeds = (
        db.query(Feed)
        .filter(Feed.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return feeds


@router.post("/", response_model=FeedSchema)
def create_feed(
    feed: FeedCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new RSS feed for the current user."""
    # Check if feed already exists for this user
    existing = (
        db.query(Feed)
        .filter(Feed.url == feed.url, Feed.user_id == current_user.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Feed already exists")

    db_feed = Feed(**feed.model_dump(), user_id=current_user.id)
    db.add(db_feed)
    db.commit()
    db.refresh(db_feed)
    return db_feed


@router.get("/{feed_id}", response_model=FeedSchema)
def get_feed(
    feed_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific feed by ID for the current user."""
    feed = (
        db.query(Feed)
        .filter(Feed.id == feed_id, Feed.user_id == current_user.id)
        .first()
    )
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    return feed


@router.put("/{feed_id}", response_model=FeedSchema)
def update_feed(
    feed_id: int,
    feed_update: FeedUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a feed for the current user."""
    feed = (
        db.query(Feed)
        .filter(Feed.id == feed_id, Feed.user_id == current_user.id)
        .first()
    )
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    update_data = feed_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(feed, key, value)

    db.commit()
    db.refresh(feed)
    return feed


@router.delete("/{feed_id}")
def delete_feed(
    feed_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a feed for the current user. Articles remain but their feed_id is set to None."""
    from app.models.article import Article

    feed = (
        db.query(Feed)
        .filter(Feed.id == feed_id, Feed.user_id == current_user.id)
        .first()
    )
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    # Set feed_id to None for all articles from this feed
    db.query(Article).filter(Article.feed_id == feed_id).update(
        {"feed_id": None}, synchronize_session=False
    )

    db.delete(feed)
    db.commit()
    return {"message": "Feed deleted successfully"}
