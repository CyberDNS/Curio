from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.rss_fetcher import RSSFetcher
from app.services.llm_processor import LLMProcessor
from app.services.newspaper_generator import NewspaperGenerator
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class FeedScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    async def fetch_and_process(self):
        """
        Fetch RSS feeds and process with LLM.

        New pipeline:
        1. Fetch new articles from RSS feeds (7-day window for duplicate prevention)
        2. Archive old articles (>7 days)
        3. Process articles from last 24 hours with LLM (classify + score + deduplicate)
        4. Generate/update newspapers for all users (rule-based, incremental)
        """
        db = SessionLocal()
        try:
            # Fetch new articles from last 7 days (URL-based dedup)
            fetcher = RSSFetcher(db)
            article_count = await fetcher.fetch_all_feeds(days_back=7)
            logger.info(f"Scheduled fetch completed: {article_count} new articles")

            # Archive articles older than 7 days
            from app.models.article import Article
            from datetime import datetime, timedelta, timezone

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
            archived_count = (
                db.query(Article)
                .filter(
                    Article.published_date < cutoff_date, Article.is_archived == False
                )
                .update({"is_archived": True})
            )
            db.commit()
            logger.info(f"Archived {archived_count} articles older than 7 days")

            # Clean up old articles (>8 days) and their images
            from app.services.article_cleanup import cleanup_old_articles

            cleanup_result = cleanup_old_articles(db, days_to_keep=8)
            logger.info(
                f"Cleanup completed: {cleanup_result['deleted_articles']} articles "
                f"and {cleanup_result['cleaned_images']} images deleted"
            )

            # Process articles from last 24 hours with LLM
            # (Classification, scoring, duplicate detection)
            processor = LLMProcessor(db)
            processed = await processor.process_articles()
            logger.info(f"Processed {processed} articles with LLM (last 24 hours)")

            # Generate/update newspapers for all users (rule-based curation)
            generator = NewspaperGenerator(db)
            results = await generator.generate_newspapers_for_all_users()
            logger.info(
                f"Generated newspapers: {results['successful']} successful, {results['failed']} failed"
            )

        except Exception as e:
            logger.error(f"Error in scheduled fetch: {str(e)}")
        finally:
            db.close()

    def start(self):
        """Start the scheduler."""
        self.scheduler.add_job(
            self.fetch_and_process,
            trigger=IntervalTrigger(minutes=settings.RSS_FETCH_INTERVAL),
            id="fetch_feeds",
            name="Fetch RSS feeds and process",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info(
            f"Scheduler started with interval: {settings.RSS_FETCH_INTERVAL} minutes"
        )

    def shutdown(self):
        """Shutdown the scheduler."""
        self.scheduler.shutdown()
        logger.info("Scheduler shutdown")


# Global scheduler instance
scheduler = FeedScheduler()
