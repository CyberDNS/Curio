from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.rss_fetcher import RSSFetcher
from app.services.llm_processor import LLMProcessor

router = APIRouter()


@router.post("/fetch-feeds")
async def fetch_feeds(
    background_tasks: BackgroundTasks,
    feed_id: int = None,
    days_back: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually trigger RSS feed fetching.

    Args:
        feed_id: Optional specific feed ID to fetch. If None, fetches all feeds.
        days_back: Optional number of days to go back (not currently used, for future implementation)
    """
    from app.models.feed import Feed

    fetcher = RSSFetcher(db)

    if feed_id:
        # Fetch specific feed
        feed = db.query(Feed).filter(Feed.id == feed_id).first()
        if not feed:
            return {"error": "Feed not found"}, 404

        article_count = await fetcher.fetch_single_feed(feed, days_back=days_back)

        return {
            "message": f"Feed '{feed.title or feed.url}' fetched successfully",
            "new_articles": article_count,
        }
    else:
        # Fetch all feeds
        article_count = await fetcher.fetch_all_feeds(days_back=days_back)
        return {
            "message": "All feeds fetched successfully",
            "new_articles": article_count,
        }


@router.post("/process-articles")
async def process_articles(
    days_back: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually trigger LLM processing of articles.

    Args:
        days_back: Optional number of days to go back for selecting unprocessed articles
    """
    from app.models.article import Article
    from datetime import timedelta, timezone, datetime

    processor = LLMProcessor(db)

    # If days_back is specified, filter articles by date
    article_ids = None
    if days_back is not None:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        articles = (
            db.query(Article)
            .filter(Article.summary == None, Article.created_at >= cutoff_date)
            .all()
        )
        article_ids = [a.id for a in articles]

    processed = await processor.process_articles(article_ids=article_ids)
    return {"message": "Articles processed successfully", "processed_count": processed}


@router.post("/regenerate-summaries")
async def regenerate_summaries(
    category_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Regenerate all article summaries."""
    processor = LLMProcessor(db)
    count = await processor.regenerate_summaries(category_id)
    return {"message": "Summaries regenerated successfully", "count": count}


@router.post("/reprocess-article/{article_id}")
async def reprocess_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reprocess a single article with LLM and recalculate duplicate detection."""
    from app.models.article import Article

    # Reset the article's LLM data and duplicate status
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        return {"error": "Article not found"}, 404

    article.summary = None
    article.llm_title = None
    article.llm_subtitle = None
    article.llm_summary = None
    article.llm_category_suggestion = None
    article.relevance_score = 0.0
    # Reset duplicate status to recalculate
    article.is_duplicate = False
    article.duplicate_of_id = None
    article.title_embedding = None
    db.commit()

    # Reprocess the article (includes duplicate detection)
    processor = LLMProcessor(db)
    processed = await processor.process_articles(article_ids=[article_id])

    return {"message": "Article reprocessed successfully", "processed": processed > 0}


@router.post("/download-article-images")
async def download_article_images(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Download images for articles that have external URLs."""
    from app.models.article import Article
    import httpx

    articles = db.query(Article).all()
    updated_count = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        for article in articles:
            updated = False

            # Download primary image if it's external
            if article.image_url and not article.image_url.startswith("/static/"):
                fetcher = RSSFetcher(db)
                local_path = await fetcher._download_image(article.image_url, client)
                if local_path:
                    article.image_url = local_path
                    updated = True

            # Download additional images if they're external
            if article.image_urls:
                new_urls = []
                for url in article.image_urls:
                    if url.startswith("/static/"):
                        new_urls.append(url)
                    else:
                        fetcher = RSSFetcher(db)
                        local_path = await fetcher._download_image(url, client)
                        if local_path:
                            new_urls.append(local_path)

                if new_urls:
                    article.image_urls = new_urls
                    updated = True

            if updated:
                updated_count += 1

        db.commit()

    return {
        "message": "Article images downloaded successfully",
        "updated_count": updated_count,
    }
