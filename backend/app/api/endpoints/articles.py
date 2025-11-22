from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import logging
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.article import Article
from app.models.user import User
from app.schemas.article import Article as ArticleSchema, ArticleUpdate
from app.api.validation import (
    validate_positive_int,
    validate_days_back,
    SkipParam,
    LimitParam,
    CategoryIdParam,
    DaysBackParam,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[ArticleSchema])
def get_articles(
    skip: int = SkipParam,
    limit: int = LimitParam,
    category_id: Optional[int] = CategoryIdParam,
    tags: Optional[List[str]] = Query(None, max_length=100),
    selected_only: bool = False,
    unread_only: bool = False,
    days_back: Optional[int] = Query(3, ge=0, le=365),
    balanced: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get articles with optional filters for the current user.

    By default, only shows articles from the last 3 days.
    Set days_back=None to show all articles.
    Set balanced=True for Today page algorithm (top articles from all categories).
    Filter by tags using the tags query parameter (can pass multiple).
    """
    query = (
        db.query(Article)
        .options(joinedload(Article.feed))
        .filter(Article.user_id == current_user.id)
    )

    # Filter by date - only show articles from last N days
    if days_back is not None:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        query = query.filter(Article.published_date >= cutoff_date)

    if category_id:
        query = query.filter(Article.category_id == category_id)

    # Filter by tags - article must have ALL specified tags
    if tags:
        for tag in tags:
            query = query.filter(Article.tags.contains([tag]))

    if selected_only:
        query = query.filter(Article.relevance_score >= 0.6)  # Recommended articles
    if unread_only:
        query = query.filter(Article.is_read == False)

    query = query.filter(Article.is_archived == False)

    # Balanced mode: Top articles from each category (Today page algorithm)
    if balanced and selected_only:
        from app.models.category import Category
        from sqlalchemy import func

        # Get all categories for user
        categories = (
            db.query(Category).filter(Category.user_id == current_user.id).all()
        )

        # If no categories, fall back to regular query
        if not categories:
            query = query.order_by(
                desc(Article.relevance_score), desc(Article.published_date)
            )
            return query.offset(skip).limit(limit).all()

        # Calculate articles per category (aim for 25 total, distribute evenly)
        per_category = max(1, 25 // len(categories))

        result_articles = []

        # Get top articles from each category
        for category in categories:
            category_articles = (
                db.query(Article)
                .options(joinedload(Article.feed))
                .filter(
                    Article.user_id == current_user.id,
                    Article.category_id == category.id,
                    Article.relevance_score >= 0.6,  # Recommended articles
                    Article.is_archived == False,
                )
            )

            # Apply date filter
            if days_back is not None:
                category_articles = category_articles.filter(
                    Article.published_date >= cutoff_date
                )

            # Get top by relevance score
            category_articles = (
                category_articles.order_by(
                    desc(Article.relevance_score), desc(Article.published_date)
                )
                .limit(per_category)
                .all()
            )

            result_articles.extend(category_articles)

        # Sort combined results by relevance score
        result_articles.sort(
            key=lambda x: (x.relevance_score, x.published_date), reverse=True
        )

        # Limit to 25 total
        return result_articles[:25]

    # Regular mode: Simple ordering
    query = query.order_by(desc(Article.published_date), desc(Article.created_at))
    articles = query.offset(skip).limit(limit).all()

    return articles


@router.get("/{article_id}", response_model=ArticleSchema)
def get_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific article by ID for the current user."""
    # Validate article_id
    validate_positive_int(article_id, "article_id")

    article = (
        db.query(Article)
        .options(joinedload(Article.feed))
        .filter(Article.id == article_id, Article.user_id == current_user.id)
        .first()
    )
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    return article


@router.put("/{article_id}", response_model=ArticleSchema)
def update_article(
    article_id: int,
    article_update: ArticleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update article status (read/archived) for the current user."""
    # Validate article_id
    validate_positive_int(article_id, "article_id")

    article = (
        db.query(Article)
        .filter(Article.id == article_id, Article.user_id == current_user.id)
        .first()
    )
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    update_data = article_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(article, key, value)

    db.commit()
    db.refresh(article)
    return article


@router.get("/{article_id}/related", response_model=List[ArticleSchema])
def get_related_articles(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get related articles (duplicates) for a given article."""
    # Validate article_id
    validate_positive_int(article_id, "article_id")

    # Get the article
    article = (
        db.query(Article)
        .filter(Article.id == article_id, Article.user_id == current_user.id)
        .first()
    )
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    related_articles = []

    # If this article is a duplicate, get the original and other duplicates
    if article.is_duplicate and article.duplicate_of_id:
        # Safeguard: don't allow self-referencing duplicates
        if article.duplicate_of_id == article_id:
            logger.warning(
                f"Article {article_id} has self-referencing duplicate_of_id, skipping"
            )
            return []

        # Get the original article
        original = (
            db.query(Article)
            .options(joinedload(Article.feed))
            .filter(
                Article.id == article.duplicate_of_id,
                Article.user_id == current_user.id,
            )
            .first()
        )
        if original and original.id != article_id:
            related_articles.append(original)

        # Get other duplicates of the same original
        other_duplicates = (
            db.query(Article)
            .options(joinedload(Article.feed))
            .filter(
                Article.duplicate_of_id == article.duplicate_of_id,
                Article.id != article_id,
                Article.user_id == current_user.id,
            )
            .all()
        )
        related_articles.extend(other_duplicates)

    # If this article is the original, get all its duplicates
    else:
        duplicates = (
            db.query(Article)
            .options(joinedload(Article.feed))
            .filter(
                Article.duplicate_of_id == article_id,
                Article.user_id == current_user.id,
            )
            .all()
        )
        related_articles.extend(duplicates)

    return related_articles


@router.post("/mark-all-read")
def mark_all_read(
    category_id: Optional[int] = CategoryIdParam,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark all articles as read for the current user."""
    query = db.query(Article).filter(
        Article.is_read == False, Article.user_id == current_user.id
    )
    if category_id:
        query = query.filter(Article.category_id == category_id)

    count = query.update({"is_read": True})
    db.commit()
    return {"message": f"Marked {count} articles as read"}


@router.post("/{article_id}/downvote")
def downvote_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Downvote an article to indicate "less like this".

    Future articles similar to downvoted content will receive lower relevance scores.
    Downvotes can be toggled (downvote again to remove).
    """
    # Validate article_id
    validate_positive_int(article_id, "article_id")

    article = (
        db.query(Article)
        .filter(Article.id == article_id, Article.user_id == current_user.id)
        .first()
    )
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Toggle downvote
    if article.user_vote == -1:
        # Remove downvote
        article.user_vote = 0
        article.vote_updated_at = None
        message = "Downvote removed"
    else:
        # Apply downvote
        article.user_vote = -1
        article.vote_updated_at = datetime.utcnow()
        message = "Article downvoted"

    db.commit()

    # Rebuild prototypes in background (only if we now have downvotes)
    if article.user_vote == -1:
        from app.services.downvote_handler import DownvoteHandler

        handler = DownvoteHandler(db, current_user.id)
        prototype_count = handler.rebuild_prototypes()
        message += f" ({prototype_count} total downvotes)"

    return {"message": message, "user_vote": article.user_vote}


@router.get("/{article_id}/explain-adjustment")
async def explain_score_adjustment(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a human-readable explanation of why an article's score was adjusted.

    Uses LLM to generate natural language explanation comparing the article
    to similar downvoted content.
    """
    # Validate article_id
    validate_positive_int(article_id, "article_id")

    article = (
        db.query(Article)
        .filter(Article.id == article_id, Article.user_id == current_user.id)
        .first()
    )
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if not article.score_adjustment_reason:
        return {
            "explanation": "No score adjustment was applied to this article.",
            "has_adjustment": False,
        }

    # Generate detailed explanation using LLM
    from app.services.downvote_handler import DownvoteHandler

    handler = DownvoteHandler(db, current_user.id)
    explanation = await handler.explain_adjustment(article)

    return {
        "explanation": explanation,
        "has_adjustment": True,
        "original_score": article.relevance_score,
        "adjusted_score": article.adjusted_relevance_score,
        "brief_reason": article.score_adjustment_reason,
    }
