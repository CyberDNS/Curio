import feedparser
import httpx
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.models.feed import Feed
from app.models.article import Article
from app.models.category import Category
from bs4 import BeautifulSoup
import logging
import re
import hashlib
import os
from pathlib import Path
import magic

logger = logging.getLogger(__name__)


class RSSFetcher:
    def __init__(self, db: Session):
        self.db = db

    async def fetch_feed(self, feed: Feed, days_back: int = None) -> List[Dict]:
        """Fetch and parse a single RSS feed."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(feed.url)
                response.raise_for_status()

            parsed = feedparser.parse(response.text)

            # Update feed metadata
            if parsed.feed.get("title"):
                feed.title = parsed.feed.title
            if parsed.feed.get("description"):
                feed.description = parsed.feed.description
            feed.last_fetched = datetime.utcnow()

            # Calculate cutoff date if days_back is specified
            cutoff_date = None
            if days_back is not None:
                from datetime import timedelta, timezone

                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)

            articles = []
            for entry in parsed.entries:
                published_date = self._parse_date(
                    entry.get("published", entry.get("updated"))
                )

                # Skip articles older than cutoff_date if specified
                # Only filter if we have both cutoff_date and a valid published_date
                if cutoff_date and published_date:
                    # Ensure both datetimes are timezone-aware for comparison
                    if published_date.tzinfo is None:
                        from datetime import timezone

                        published_date = published_date.replace(tzinfo=timezone.utc)
                    if published_date < cutoff_date:
                        continue

                # Extract all image URLs from RSS entry
                extracted_images = self._extract_images(entry)

                article_data = {
                    "title": entry.get("title", "No Title"),
                    "link": entry.get("link", ""),
                    "description": entry.get("summary", entry.get("description", "")),
                    "content": (
                        entry.get("content", [{}])[0].get("value", "")
                        if entry.get("content")
                        else ""
                    ),
                    "author": entry.get("author", ""),
                    "published_date": published_date,
                    "extracted_images": extracted_images,  # Store temporarily for download
                }
                articles.append(article_data)

            self.db.commit()
            logger.debug(f"Fetched {len(articles)} articles from {feed.url}")
            return articles

        except Exception as e:
            logger.error(f"Error fetching feed {feed.url}: {str(e)}")
            return []

    async def fetch_single_feed(self, feed: Feed, days_back: int = None) -> int:
        """Fetch a single feed and store articles with image caching."""
        total_articles = 0

        # Create HTTP client for downloading images
        async with httpx.AsyncClient(timeout=30.0) as client:
            articles_data = await self.fetch_feed(feed, days_back=days_back)

            for article_data in articles_data:
                try:
                    # Check if article already exists
                    existing = (
                        self.db.query(Article)
                        .filter(Article.link == article_data["link"])
                        .first()
                    )

                    if not existing:
                        # Download and cache all images if available
                        extracted_images = article_data.pop("extracted_images", [])
                        image_urls = []

                        for img_url in extracted_images:
                            local_path = await self._download_image(img_url, client)
                            if local_path:
                                image_urls.append(local_path)
                            else:
                                # If download fails, keep original URL
                                image_urls.append(img_url)

                        article_data["image_urls"] = image_urls

                        article = Article(
                            user_id=feed.user_id,
                            feed_id=feed.id,
                            **article_data,
                        )
                        self.db.add(article)
                        self.db.flush()  # Flush to catch constraint violations before commit
                        total_articles += 1
                except Exception as e:
                    # Handle duplicate key or other errors for individual articles
                    logger.error(
                        f"Skipping article {article_data.get('link')}: {str(e)}"
                    )
                    self.db.rollback()
                    continue

            try:
                self.db.commit()
            except Exception as e:
                logger.error(f"Error committing articles for feed {feed.url}: {str(e)}")
                self.db.rollback()

        logger.info(f"Fetched {total_articles} new articles from {feed.url}")
        return total_articles

    async def fetch_all_feeds(self, days_back: int = None) -> int:
        """Fetch all active feeds and store articles."""
        feeds = self.db.query(Feed).filter(Feed.is_active == True).all()
        total_articles = 0

        # Create HTTP client for downloading images
        async with httpx.AsyncClient(timeout=30.0) as client:
            for feed in feeds:
                articles_data = await self.fetch_feed(feed, days_back=days_back)

                for article_data in articles_data:
                    try:
                        # Check if article already exists
                        existing = (
                            self.db.query(Article)
                            .filter(Article.link == article_data["link"])
                            .first()
                        )

                        if not existing:
                            # Download and cache all images if available
                            extracted_images = article_data.pop("extracted_images", [])
                            image_urls = []

                            for img_url in extracted_images:
                                local_path = await self._download_image(img_url, client)
                                if local_path:
                                    image_urls.append(local_path)
                                else:
                                    # If download fails, keep original URL
                                    image_urls.append(img_url)

                            article_data["image_urls"] = image_urls

                            article = Article(
                                user_id=feed.user_id,
                                feed_id=feed.id,
                                **article_data,
                            )
                            self.db.add(article)
                            self.db.flush()  # Flush to catch constraint violations before commit
                            total_articles += 1
                    except Exception as e:
                        # Handle duplicate key or other errors for individual articles
                        logger.error(
                            f"Skipping article {article_data.get('link')}: {str(e)}"
                        )
                        self.db.rollback()
                        continue

                try:
                    self.db.commit()
                except Exception as e:
                    logger.error(
                        f"Error committing articles for feed {feed.url}: {str(e)}"
                    )
                    self.db.rollback()

        logger.info(f"Fetched total of {total_articles} new articles")
        return total_articles

    def _parse_date(self, date_string: Optional[str]) -> Optional[datetime]:
        """Parse various date formats from RSS feeds."""
        if not date_string:
            return None

        try:
            from email.utils import parsedate_to_datetime

            return parsedate_to_datetime(date_string)
        except:
            try:
                return datetime.fromisoformat(date_string.replace("Z", "+00:00"))
            except:
                logger.warning(f"Could not parse date: {date_string}")
                return None

    def _extract_images(self, entry: Dict) -> List[str]:
        """Extract all image URLs from an RSS feed entry."""
        images = []

        # Try media:content or media:thumbnail (common in RSS 2.0 feeds)
        if hasattr(entry, "media_content") and entry.media_content:
            for media in entry.media_content:
                if media.get("medium") == "image" or media.get("type", "").startswith(
                    "image/"
                ):
                    url = media.get("url")
                    if url:
                        images.append(url)

        if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
            for thumb in entry.media_thumbnail:
                url = thumb.get("url")
                if url:
                    images.append(url)

        # Try enclosures (podcasts and some feeds use this)
        if hasattr(entry, "enclosures") and entry.enclosures:
            for enclosure in entry.enclosures:
                if enclosure.get("type", "").startswith("image/"):
                    url = enclosure.get("href") or enclosure.get("url")
                    if url:
                        images.append(url)

        # Try to parse HTML content for images
        content_html = None
        if entry.get("content"):
            content_html = entry.content[0].get("value", "")
        elif entry.get("summary"):
            content_html = entry.summary

        if content_html:
            soup = BeautifulSoup(content_html, "html.parser")

            # First try to find og:image meta tag
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                images.append(og_image["content"])

            # Find all img tags
            img_tags = soup.find_all("img")
            for img in img_tags:
                if img.get("src"):
                    img_url = img["src"]
                    # Filter out tracking pixels and small images
                    if self._is_valid_image(img_url, img):
                        images.append(img_url)

        # Remove duplicates while preserving order
        return list(dict.fromkeys(images))

    def _is_valid_image(self, url: str, img_tag) -> bool:
        """Check if the image URL is likely a real content image."""

        # Filter out common tracking pixel patterns
        tracking_patterns = [
            r"1x1",
            r"pixel",
            r"tracker",
            r"beacon",
            r"analytics",
        ]

        url_lower = url.lower()
        for pattern in tracking_patterns:
            if re.search(pattern, url_lower):
                return False

        # Check image dimensions if available
        width = img_tag.get("width")
        height = img_tag.get("height")

        if width and height:
            try:
                w = int(width)
                h = int(height)
                # Reject very small images (likely tracking pixels)
                if w < 50 or h < 50:
                    return False
            except ValueError:
                pass

        return True

    async def _download_image(
        self, image_url: str, client: httpx.AsyncClient
    ) -> Optional[str]:
        """Download an image with security validation and save it locally.

        Security features:
        - File size limit enforcement (10MB per file)
        - Content-Type validation
        - Magic byte verification (checks actual file type, not just extension)
        - Total storage quota enforcement (1GB)
        - Allowed file type whitelist
        """
        try:
            # Skip if already a local path
            if image_url.startswith("/media/"):
                return image_url

            # Use configured media root for image storage
            from app.core.config import settings

            images_dir = Path(settings.MEDIA_ROOT) / "images"
            images_dir.mkdir(parents=True, exist_ok=True)

            # Generate a unique filename based on URL hash using SHA-256
            # SHA-256 is cryptographically stronger than MD5 and resistant to collision attacks
            url_hash = hashlib.sha256(image_url.encode()).hexdigest()

            # Get file extension from URL or default to .jpg
            ext = os.path.splitext(image_url.split("?")[0])[1]
            if not ext or ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"]:
                ext = ".jpg"

            filename = f"{url_hash}{ext}"
            filepath = images_dir / filename

            # Check if image already exists
            if filepath.exists():
                # Collision detection: Verify the existing file is for the same URL
                # by checking if a metadata file exists with the original URL
                metadata_file = filepath.with_suffix(filepath.suffix + ".meta")
                if metadata_file.exists():
                    with open(metadata_file, "r") as f:
                        stored_url = f.read().strip()
                        if stored_url != image_url:
                            # Hash collision detected! Add timestamp suffix to make unique
                            logger.warning(f"Hash collision detected for {image_url}")
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                            filename = f"{url_hash}_{timestamp}{ext}"
                            filepath = images_dir / filename
                        else:
                            # Same URL, return cached version
                            return f"/media/images/{filename}"
                else:
                    # No metadata file, assume it's the correct file (legacy)
                    return f"/media/images/{filename}"

            # Check total storage usage before downloading
            total_size = sum(
                f.stat().st_size for f in images_dir.glob("**/*") if f.is_file()
            )
            if total_size >= settings.MAX_TOTAL_STORAGE:
                logger.warning(
                    f"Storage quota exceeded ({total_size} bytes). Cannot download {image_url}"
                )
                return None

            # Download the image with streaming to check size before saving
            async with client.stream(
                "GET", image_url, follow_redirects=True
            ) as response:
                response.raise_for_status()

                # Validate Content-Type header
                content_type = response.headers.get("content-type", "").lower()
                if content_type and not any(
                    allowed in content_type for allowed in settings.ALLOWED_IMAGE_TYPES
                ):
                    logger.warning(
                        f"Invalid content-type '{content_type}' for {image_url}"
                    )
                    return None

                # Read content with size limit
                content = b""
                async for chunk in response.aiter_bytes():
                    content += chunk
                    if len(content) > settings.MAX_IMAGE_SIZE:
                        logger.warning(
                            f"Image too large (>{settings.MAX_IMAGE_SIZE} bytes): {image_url}"
                        )
                        return None

            # Validate actual file type using magic bytes
            mime_type = magic.from_buffer(content, mime=True)
            if mime_type not in settings.ALLOWED_IMAGE_TYPES:
                logger.warning(
                    f"Invalid file type '{mime_type}' (magic bytes) for {image_url}"
                )
                return None

            # Additional size check after download
            if len(content) == 0:
                logger.warning(f"Empty file downloaded from {image_url}")
                return None

            # Save the image
            with open(filepath, "wb") as f:
                f.write(content)

            # Save metadata file for collision detection
            # This stores the original URL to verify the hash corresponds to the correct source
            metadata_file = filepath.with_suffix(filepath.suffix + ".meta")
            with open(metadata_file, "w") as f:
                f.write(image_url)

            logger.debug(
                f"Downloaded and validated image: {filename} ({len(content)} bytes, type: {mime_type})"
            )
            return f"/media/images/{filename}"

        except httpx.HTTPStatusError as e:
            logger.warning(
                f"HTTP error downloading image {image_url}: {e.response.status_code}"
            )
            return None
        except httpx.RequestError as e:
            logger.warning(f"Network error downloading image {image_url}: {str(e)}")
            return None
        except Exception as e:
            logger.warning(f"Failed to download image {image_url}: {str(e)}")
            return None
