from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.saved_article import Tag, SavedArticle
from app.models.user import User
from app.schemas.saved_article import Tag as TagSchema, TagCreate

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/", response_model=List[dict])
@limiter.limit("60/minute")
async def get_tags(
    request: Request,
    search: Optional[str] = Query(None, description="Search tags by prefix"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all tags for the current user with usage count.

    - Optionally filter by search prefix (for autocomplete)
    - Returns tags with usage count (number of saved articles)
    - Ordered by usage count (most used first)
    """
    query = (
        db.query(
            Tag.id,
            Tag.name,
            Tag.created_at,
            func.count(SavedArticle.id).label("usage_count"),
        )
        .outerjoin(Tag.saved_articles)
        .filter(Tag.user_id == current_user.id)
        .group_by(Tag.id, Tag.name, Tag.created_at)
    )

    # Filter by search prefix if provided
    if search:
        search_term = search.strip().lower()
        query = query.filter(Tag.name.like(f"{search_term}%"))

    # Order by usage count (most used first), then by name
    query = query.order_by(func.count(SavedArticle.id).desc(), Tag.name)

    results = query.all()

    return [
        {
            "id": row.id,
            "name": row.name,
            "created_at": row.created_at,
            "usage_count": row.usage_count,
        }
        for row in results
    ]
