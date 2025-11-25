from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
from typing import List, Optional
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.saved_article import SavedArticle, Tag, saved_article_tags
from app.models.article import Article
from app.schemas.saved_article import (
    SavedArticle as SavedArticleSchema,
    SavedArticleCreate,
    SavedArticleUpdateTags,
    SavedArticleWithArticle,
    Tag as TagSchema,
)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


@router.post("/", response_model=SavedArticleSchema)
@limiter.limit("60/minute")
async def save_article(
    request: Request,
    saved_article_data: SavedArticleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Save an article with optional tags.

    - Creates a SavedArticle entry
    - Associates tags (creates new tags if they don't exist)
    - Returns the saved article with its tags
    """
    # Check if article exists and belongs to user
    article = (
        db.query(Article)
        .filter(
            Article.id == saved_article_data.article_id,
            Article.user_id == current_user.id,
        )
        .first()
    )

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Check if already saved
    existing = (
        db.query(SavedArticle)
        .filter(
            SavedArticle.article_id == saved_article_data.article_id,
            SavedArticle.user_id == current_user.id,
        )
        .first()
    )

    if existing:
        raise HTTPException(status_code=400, detail="Article already saved")

    # Create saved article
    saved_article = SavedArticle(
        user_id=current_user.id,
        article_id=saved_article_data.article_id,
    )
    db.add(saved_article)
    db.flush()  # Get the ID without committing

    # Process tags
    if saved_article_data.tag_names:
        for tag_name in saved_article_data.tag_names:
            tag_name = tag_name.strip().lower()
            if not tag_name:
                continue

            # Find or create tag
            tag = (
                db.query(Tag)
                .filter(Tag.user_id == current_user.id, Tag.name == tag_name)
                .first()
            )

            if not tag:
                tag = Tag(user_id=current_user.id, name=tag_name)
                db.add(tag)
                db.flush()

            # Associate tag with saved article
            saved_article.tags.append(tag)

    db.commit()
    db.refresh(saved_article)

    logger.info(
        f"User {current_user.id} saved article {article.id} with {len(saved_article.tags)} tags"
    )

    return saved_article


@router.get("/", response_model=List[SavedArticleWithArticle])
@limiter.limit("60/minute")
async def get_saved_articles(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    tags: Optional[List[str]] = Query(None, description="Filter by tag names"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all saved articles for the current user.

    - Optionally filter by tags (article must have ALL specified tags)
    - Returns saved articles with full article details
    - Ordered by saved_at (most recent first)
    """
    query = (
        db.query(SavedArticle)
        .options(
            joinedload(SavedArticle.article).joinedload(Article.feed),
            joinedload(SavedArticle.tags),
        )
        .filter(SavedArticle.user_id == current_user.id)
    )

    # Filter by tags if specified
    if tags:
        # Normalize tag names
        normalized_tags = [tag.strip().lower() for tag in tags if tag.strip()]

        if normalized_tags:
            # Article must have ALL specified tags
            # Use subquery approach to ensure we match ALL tags
            from sqlalchemy import and_, exists, select

            for tag_name in normalized_tags:
                # Create a subquery that checks if this saved article has this specific tag
                tag_exists = exists(
                    select(1)
                    .select_from(saved_article_tags)
                    .join(Tag, Tag.id == saved_article_tags.c.tag_id)
                    .where(
                        and_(
                            saved_article_tags.c.saved_article_id == SavedArticle.id,
                            Tag.name == tag_name,
                            Tag.user_id == current_user.id,
                        )
                    )
                )
                query = query.filter(tag_exists)

    # Order by most recently saved first
    query = query.order_by(SavedArticle.saved_at.desc())

    saved_articles = query.offset(skip).limit(limit).all()

    return saved_articles


@router.get("/{saved_article_id}", response_model=SavedArticleWithArticle)
@limiter.limit("60/minute")
async def get_saved_article(
    request: Request,
    saved_article_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific saved article by ID."""
    saved_article = (
        db.query(SavedArticle)
        .options(
            joinedload(SavedArticle.article).joinedload(Article.feed),
            joinedload(SavedArticle.tags),
        )
        .filter(
            SavedArticle.id == saved_article_id,
            SavedArticle.user_id == current_user.id,
        )
        .first()
    )

    if not saved_article:
        raise HTTPException(status_code=404, detail="Saved article not found")

    return saved_article


@router.put("/{saved_article_id}/tags", response_model=SavedArticleSchema)
@limiter.limit("60/minute")
async def update_saved_article_tags(
    request: Request,
    saved_article_id: int,
    tag_data: SavedArticleUpdateTags,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update tags for a saved article.

    - Replaces all existing tags with the provided list
    - Creates new tags if they don't exist
    - Returns the updated saved article
    """
    saved_article = (
        db.query(SavedArticle)
        .options(joinedload(SavedArticle.tags))
        .filter(
            SavedArticle.id == saved_article_id,
            SavedArticle.user_id == current_user.id,
        )
        .first()
    )

    if not saved_article:
        raise HTTPException(status_code=404, detail="Saved article not found")

    # Clear existing tags
    saved_article.tags.clear()

    # Add new tags
    for tag_name in tag_data.tag_names:
        tag_name = tag_name.strip().lower()
        if not tag_name:
            continue

        # Find or create tag
        tag = (
            db.query(Tag)
            .filter(Tag.user_id == current_user.id, Tag.name == tag_name)
            .first()
        )

        if not tag:
            tag = Tag(user_id=current_user.id, name=tag_name)
            db.add(tag)
            db.flush()

        saved_article.tags.append(tag)

    db.commit()
    db.refresh(saved_article)

    logger.info(
        f"User {current_user.id} updated tags for saved article {saved_article_id}"
    )

    return saved_article


@router.delete("/{saved_article_id}")
@limiter.limit("60/minute")
async def unsave_article(
    request: Request,
    saved_article_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove an article from saved articles.

    - Deletes the SavedArticle entry
    - Tags remain in the system if used by other saved articles
    """
    saved_article = (
        db.query(SavedArticle)
        .filter(
            SavedArticle.id == saved_article_id,
            SavedArticle.user_id == current_user.id,
        )
        .first()
    )

    if not saved_article:
        raise HTTPException(status_code=404, detail="Saved article not found")

    article_id = saved_article.article_id
    db.delete(saved_article)
    db.commit()

    logger.info(f"User {current_user.id} unsaved article {article_id}")

    return {"message": "Article removed from saved articles"}


@router.get("/check/{article_id}", response_model=dict)
@limiter.limit("60/minute")
async def check_article_saved(
    request: Request,
    article_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Check if an article is saved by the current user.

    Returns: {"is_saved": bool, "saved_article_id": int or None}
    """
    saved_article = (
        db.query(SavedArticle)
        .filter(
            SavedArticle.article_id == article_id,
            SavedArticle.user_id == current_user.id,
        )
        .first()
    )

    return {
        "is_saved": saved_article is not None,
        "saved_article_id": saved_article.id if saved_article else None,
    }
