from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, date, timedelta
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.newspaper import Newspaper
from app.models.article import Article
from app.models.user import User
from app.schemas.newspaper import Newspaper as NewspaperSchema
from app.schemas.article import Article as ArticleSchema
from app.services.newspaper_generator import NewspaperGenerator

router = APIRouter()


@router.get("/today", response_model=NewspaperSchema)
async def get_today_newspaper(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get today's newspaper for the current user. Generates if not exists."""
    today = datetime.now().date()

    newspaper = (
        db.query(Newspaper)
        .filter(Newspaper.user_id == current_user.id, Newspaper.date == today)
        .first()
    )

    if not newspaper:
        # Generate newspaper for today
        generator = NewspaperGenerator(db)
        newspaper = await generator.generate_newspaper_for_user(current_user.id, today)

    return newspaper


@router.get("/date/{newspaper_date}", response_model=NewspaperSchema)
async def get_newspaper_by_date(
    newspaper_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get newspaper for a specific date."""
    newspaper = (
        db.query(Newspaper)
        .filter(
            Newspaper.user_id == current_user.id, Newspaper.date == newspaper_date
        )
        .first()
    )

    if not newspaper:
        raise HTTPException(
            status_code=404, detail=f"No newspaper found for {newspaper_date}"
        )

    return newspaper


@router.get("/history", response_model=List[NewspaperSchema])
async def get_newspaper_history(
    days_back: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get historical newspapers for the last N days."""
    start_date = datetime.now().date() - timedelta(days=days_back)

    newspapers = (
        db.query(Newspaper)
        .filter(
            Newspaper.user_id == current_user.id, Newspaper.date >= start_date
        )
        .order_by(Newspaper.date.desc())
        .all()
    )

    return newspapers


@router.get("/dates", response_model=List[date])
async def get_available_dates(
    days_back: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get list of dates with available newspapers."""
    start_date = datetime.now().date() - timedelta(days=days_back)

    newspapers = (
        db.query(Newspaper.date)
        .filter(
            Newspaper.user_id == current_user.id, Newspaper.date >= start_date
        )
        .order_by(Newspaper.date.desc())
        .all()
    )

    return [n.date for n in newspapers]


@router.post("/regenerate")
async def regenerate_today_newspaper(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Manually regenerate today's newspaper."""
    generator = NewspaperGenerator(db)
    newspaper = await generator.generate_newspaper_for_user(current_user.id)

    return {
        "message": "Newspaper regenerated successfully",
        "date": newspaper.date,
        "today_count": len(newspaper.structure.get("today", [])),
        "category_count": len(newspaper.structure.get("categories", {})),
    }


@router.get("/{newspaper_id}/articles", response_model=List[ArticleSchema])
async def get_newspaper_articles(
    newspaper_id: int,
    section: Optional[str] = Query(
        None, description="Section to get articles from (e.g., 'today' or category slug)"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all articles for a newspaper, optionally filtered by section."""
    newspaper = (
        db.query(Newspaper)
        .filter(Newspaper.id == newspaper_id, Newspaper.user_id == current_user.id)
        .first()
    )

    if not newspaper:
        raise HTTPException(status_code=404, detail="Newspaper not found")

    # Collect article IDs based on section filter
    article_ids = []

    if section:
        if section == "today":
            article_ids = newspaper.structure.get("today", [])
        else:
            # Category section
            article_ids = newspaper.structure.get("categories", {}).get(section, [])
    else:
        # All articles
        article_ids = newspaper.structure.get("today", [])
        for cat_articles in newspaper.structure.get("categories", {}).values():
            article_ids.extend(cat_articles)

        # Remove duplicates while preserving order
        seen = set()
        unique_ids = []
        for aid in article_ids:
            if aid not in seen:
                seen.add(aid)
                unique_ids.append(aid)
        article_ids = unique_ids

    # Fetch articles
    if not article_ids:
        return []

    # Fetch articles with feed relationship
    articles = (
        db.query(Article)
        .options(joinedload(Article.feed))
        .filter(Article.id.in_(article_ids), Article.user_id == current_user.id)
        .all()
    )

    # Preserve the LLM's curated order from newspaper structure
    # Create a mapping of article_id to its position in the original list
    id_to_position = {aid: idx for idx, aid in enumerate(article_ids)}

    # Sort by LLM's curated order only (don't move read articles)
    articles.sort(key=lambda a: id_to_position.get(a.id, float('inf')))

    return articles
