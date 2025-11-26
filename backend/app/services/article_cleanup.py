"""
Article cleanup service - removes old articles and associated images.

Runs periodically to clean up articles older than 8 days that are not saved.
Also removes orphaned image files.
"""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import and_, not_, exists, or_

from app.models.article import Article
from app.models.saved_article import SavedArticle
from app.core.config import settings

logger = logging.getLogger(__name__)


class ArticleCleanupService:
    """Service for cleaning up old articles and their images."""

    def __init__(self, db: Session):
        self.db = db

    def cleanup_old_articles(self, days_to_keep: int = 8) -> dict:
        """
        Delete articles older than specified days that are not saved.

        Args:
            days_to_keep: Number of days to keep articles (default 8)

        Returns:
            dict with cleanup statistics
        """
        logger.info(
            f"Starting article cleanup (keeping articles from last {days_to_keep} days)"
        )

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

        # Find articles that are:
        # 1. Older than cutoff date
        # 2. Not saved by any user
        # 3. Not duplicates of saved articles (to preserve the original)

        # Subquery to check if article is saved
        from sqlalchemy import select

        is_saved = exists(
            select(SavedArticle.id).where(SavedArticle.article_id == Article.id)
        )

        # Find articles to delete
        articles_to_delete = (
            self.db.query(Article)
            .filter(
                and_(
                    Article.published_date < cutoff_date,
                    not_(is_saved),
                )
            )
            .all()
        )

        # Collect image URLs before deletion
        image_urls_to_clean = []
        for article in articles_to_delete:
            if article.image_urls:
                image_urls_to_clean.extend(article.image_urls)

        deleted_count = len(articles_to_delete)
        article_ids = [a.id for a in articles_to_delete]

        # Delete articles
        if deleted_count > 0:
            # First, break circular dependencies by setting duplicate_of_id to NULL
            # for any articles that reference articles being deleted
            article_ids_set = set(article_ids)
            self.db.query(Article).filter(
                Article.duplicate_of_id.in_(article_ids_set)
            ).update({"duplicate_of_id": None}, synchronize_session=False)
            self.db.commit()

            # Now delete the articles
            for article in articles_to_delete:
                self.db.delete(article)

            self.db.commit()
            logger.info(f"Deleted {deleted_count} old articles")
        else:
            logger.info("No old articles to delete")

        # Clean up orphaned images
        cleaned_images = self.cleanup_orphaned_images(image_urls_to_clean)

        return {
            "deleted_articles": deleted_count,
            "article_ids": article_ids,
            "cutoff_date": cutoff_date.isoformat(),
            "cleaned_images": cleaned_images,
        }

    def cleanup_orphaned_images(self, candidate_urls: List[str] = None) -> int:
        """
        Remove image files that are no longer referenced by any article.

        Args:
            candidate_urls: Optional list of image URLs to check. If None, checks all files.

        Returns:
            Number of images deleted
        """
        media_root = Path(settings.MEDIA_ROOT)
        images_dir = media_root / "images"

        if not images_dir.exists():
            logger.info("Images directory does not exist, skipping cleanup")
            return 0

        deleted_count = 0

        # If specific URLs provided, check only those
        if candidate_urls:
            for url in candidate_urls:
                if self._is_local_image(url):
                    deleted_count += self._delete_image_if_orphaned(url)
        else:
            # Check all image files in the directory
            for image_file in images_dir.rglob("*"):
                if image_file.is_file():
                    # Construct the URL path
                    relative_path = image_file.relative_to(media_root)
                    url = f"/api/media/{relative_path}"
                    deleted_count += self._delete_image_if_orphaned(url)

        logger.info(f"Cleaned up {deleted_count} orphaned images")
        return deleted_count

    def _is_local_image(self, url: str) -> bool:
        """Check if URL is a local image (not external)."""
        return url.startswith("/api/media/") or url.startswith("/static/")

    def _delete_image_if_orphaned(self, url: str) -> int:
        """
        Delete image file if it's not referenced by any article.

        Returns:
            1 if deleted, 0 if kept
        """
        # Check if any article references this image
        is_referenced = (
            self.db.query(Article.id).filter(Article.image_urls.contains([url])).first()
        )

        if is_referenced:
            return 0  # Image is still in use

        # Convert URL to file path
        media_root = Path(settings.MEDIA_ROOT)

        if url.startswith("/api/media/"):
            relative_path = url.replace("/api/media/", "")
        elif url.startswith("/static/"):
            relative_path = url.replace("/static/", "")
        else:
            return 0  # Not a local file

        file_path = media_root / relative_path

        if file_path.exists() and file_path.is_file():
            try:
                file_path.unlink()
                logger.debug(f"Deleted orphaned image: {file_path}")
                return 1
            except Exception as e:
                logger.error(f"Failed to delete image {file_path}: {e}")
                return 0

        return 0

    def get_cleanup_stats(self, days_to_keep: int = 8) -> dict:
        """
        Get statistics about what would be cleaned up (dry run).

        Args:
            days_to_keep: Number of days to keep articles

        Returns:
            dict with statistics
        """
        from sqlalchemy import select

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

        # Count articles that would be deleted
        is_saved = exists(
            select(SavedArticle.id).where(SavedArticle.article_id == Article.id)
        )

        deletable_count = (
            self.db.query(Article)
            .filter(
                and_(
                    Article.published_date < cutoff_date,
                    not_(is_saved),
                )
            )
            .count()
        )

        # Count saved articles (will be kept)
        saved_count = (
            self.db.query(Article)
            .filter(Article.published_date < cutoff_date)
            .filter(is_saved)
            .count()
        )

        return {
            "cutoff_date": cutoff_date.isoformat(),
            "articles_to_delete": deletable_count,
            "old_saved_articles_kept": saved_count,
            "days_to_keep": days_to_keep,
        }


def cleanup_old_articles(db: Session, days_to_keep: int = 8) -> dict:
    """
    Convenience function to run article cleanup.

    Args:
        db: Database session
        days_to_keep: Number of days to keep articles (default 8)

    Returns:
        dict with cleanup results
    """
    service = ArticleCleanupService(db)
    return service.cleanup_old_articles(days_to_keep)
