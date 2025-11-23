from openai import AsyncOpenAI
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.article import Article
from app.models.category import Category
from app.models.settings import UserSettings
from app.core.config import settings
from app.services.duplicate_detector import DuplicateDetector
from app.services.downvote_handler import DownvoteHandler
from app.services.rate_limiter import (
    TokenBucketRateLimiter,
    estimate_request_tokens,
)
from slugify import slugify
import logging
import json
import re
import asyncio

logger = logging.getLogger(__name__)

# Shared rate limiter and semaphore across all LLMProcessor instances
# This prevents race conditions when multiple requests process articles in parallel
_shared_rate_limiter = None
_shared_semaphore = None
_article_locks = {}  # Dict of article_id -> asyncio.Lock
_locks_lock = asyncio.Lock()  # Lock for managing the locks dict


def _get_shared_rate_limiter():
    """Get or create the shared rate limiter instance."""
    global _shared_rate_limiter
    if _shared_rate_limiter is None:
        _shared_rate_limiter = TokenBucketRateLimiter(settings.LLM_TPM_LIMIT)
    return _shared_rate_limiter


def _get_shared_semaphore():
    """Get or create the shared semaphore instance."""
    global _shared_semaphore
    if _shared_semaphore is None:
        _shared_semaphore = asyncio.Semaphore(settings.LLM_MAX_CONCURRENT)
    return _shared_semaphore


async def _get_article_lock(article_id: int) -> asyncio.Lock:
    """Get or create a lock for a specific article ID."""
    global _article_locks
    async with _locks_lock:
        if article_id not in _article_locks:
            _article_locks[article_id] = asyncio.Lock()
        return _article_locks[article_id]


class LLMProcessor:
    def __init__(self, db: Session):
        self.db = db
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.duplicate_detector = DuplicateDetector(db)
        # Use shared instances to coordinate across parallel requests
        self.rate_limiter = _get_shared_rate_limiter()
        self.semaphore = _get_shared_semaphore()

    async def process_articles(
        self, article_ids: Optional[List[int]] = None, user_id: Optional[int] = None
    ) -> int:
        """
        Process articles with LLM - comprehensive analysis and categorization.

        New behavior:
        - Only processes articles from last 24 hours (configurable)
        - Assigns articles to categories (no tags)
        - Detects duplicates using embeddings
        - No automatic hot article evaluation (removed)
        """

        # Get unprocessed articles from last 24 hours only (unless specific IDs requested)
        days_back = 1
        date_threshold = datetime.utcnow() - timedelta(days=days_back)

        query = self.db.query(Article).filter(Article.summary == None)

        # Only apply date filter if not processing specific article IDs
        if not article_ids:
            query = query.filter(Article.created_at >= date_threshold)

        if article_ids:
            query = query.filter(Article.id.in_(article_ids))
        if user_id:
            query = query.filter(Article.user_id == user_id)

        articles = query.limit(50).all()  # Process in batches

        if not articles:
            logger.info("No articles to process (within 24-hour window)")
            return 0

        # Get user_id from first article if not provided
        if not user_id and articles:
            user_id = articles[0].user_id

        # Get user's content selection prompt (must filter by user_id for multi-tenancy)
        selection_prompt_setting = (
            self.db.query(UserSettings)
            .filter(
                UserSettings.key == "llm_selection_prompt",
                UserSettings.user_id == user_id,
            )
            .first()
        )

        if not selection_prompt_setting:
            logger.warning(
                f"No LLM selection prompt configured for user {user_id}, using default behavior"
            )
            selection_prompt = (
                "Select all articles that are informative and well-written."
            )
        else:
            selection_prompt = selection_prompt_setting.value

        # Get existing active (non-deleted) categories with descriptions for the LLM to consider
        existing_categories = (
            self.db.query(Category)
            .filter(Category.is_deleted == False, Category.user_id == user_id)
            .all()
        )

        logger.info(f"Processing {len(articles)} articles from last {days_back} day(s)")

        # Process articles in parallel with rate limiting
        tasks = [
            self._process_single_article(article, selection_prompt, existing_categories)
            for article in articles
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful processing
        processed = sum(1 for r in results if r is True)
        failed = sum(1 for r in results if isinstance(r, Exception))

        if failed > 0:
            logger.warning(f"Failed to process {failed} articles")

        logger.info(f"Processed {processed} articles with LLM (parallel)")
        return processed

    async def _process_single_article(
        self,
        article: Article,
        selection_prompt: str,
        existing_categories: List[Category],
    ) -> bool:
        """
        Process a single article with rate limiting and concurrency control.

        Uses per-article locks to prevent concurrent processing of the same article.

        Returns:
            True if successful, False otherwise
        """
        # Get lock for this specific article to prevent concurrent processing
        article_lock = await _get_article_lock(article.id)

        async with article_lock:
            try:
                # Refresh article from DB to get latest state
                self.db.refresh(article)

                # Comprehensive LLM analysis (with rate limiting inside)
                result = await self._analyze_article_comprehensive(
                    article, selection_prompt, existing_categories
                )

                # Update article with LLM-enhanced data
                article.llm_title = result.get("title")
                article.llm_subtitle = result.get("subtitle")
                article.llm_summary = result.get("summary")

                # Backward compatibility fields
                article.summary = result.get("summary", "")
                article.relevance_score = result.get("relevance_score", 0.0)

                # Assign to category (only if LLM found a matching category)
                category_id = result.get("category_id")
                if category_id:
                    article.category_id = category_id
                # If no category match, leave category_id as None

                # Commit article updates before duplicate detection
                self.db.commit()

                # Duplicate detection (generates embedding and checks for duplicates)
                original = self.duplicate_detector.process_article_for_duplicates(
                    article
                )
                if original:
                    logger.info(
                        f"Article {article.id} marked as duplicate of {original.id}"
                    )

                # Apply downvote-based score adjustment
                downvote_handler = DownvoteHandler(self.db, article.user_id)
                penalty_applied = downvote_handler.apply_downvote_penalty(article)
                if penalty_applied:
                    logger.info(
                        f"Article {article.id}: Score adjusted from {article.relevance_score:.2f} "
                        f"to {article.adjusted_relevance_score:.2f} due to downvoted similarity"
                    )

                # Commit downvote adjustments
                self.db.commit()

                logger.info(
                    f"Processed article {article.id}: {article.llm_title or article.title}"
                )
                return True

            except Exception as e:
                logger.error(f"Error processing article {article.id}: {str(e)}")
                self.db.rollback()
                return False

    async def _analyze_article(self, article: Article, selection_prompt: str) -> Dict:
        """Analyze a single article with LLM."""

        system_prompt = """You are a news curator assistant. Your job is to:
1. Summarize the article concisely (2-3 sentences)
2. Score the relevance from 0.0 to 1.0 based on the user's interests

Scoring Guidelines:
- 0.9-1.0: Perfect match (rare!)
- 0.7-0.9: Strong match, directly relevant
- 0.6-0.7: Good match, clearly related
- 0.4-0.6: Weak connection, tangentially related
- 0.0-0.4: Not relevant

Respond in JSON format:
{
    "summary": "Brief summary here",
    "relevance_score": 0.0-1.0
}"""

        user_prompt = f"""Article Title: {article.title}

Article Content:
{article.description or article.content or "No content available"}

User's Interest Criteria:
{selection_prompt}

Analyze this article and provide your assessment."""

        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            logger.error(f"LLM API error: {str(e)}")
            return {
                "summary": article.description[:200] if article.description else "",
                "relevance_score": 0.0,
            }

    async def _analyze_article_comprehensive(
        self,
        article: Article,
        selection_prompt: str,
        existing_categories: List[Category],
    ) -> Dict:
        """
        Comprehensive LLM analysis with category assignment and content enhancement.

        New behavior:
        - Assigns article to one of the existing categories
        - Uses category descriptions to make better assignment decisions
        - No tags (removed)
        """

        # Build category context for LLM
        category_context = ""
        if existing_categories:
            category_list = []
            for cat in existing_categories:
                desc = f" - {cat.description}" if cat.description else ""
                category_list.append(f'  - "{cat.name}" (ID: {cat.id}){desc}')
            category_context = "\n\nAvailable Categories:\n" + "\n".join(category_list)
        else:
            category_context = (
                "\n\nNo categories defined yet. Return null for category_id."
            )

        system_prompt = f"""You are a news curator. Your PRIMARY job is to score articles based on how well they match the user's specific interests.

Tasks:
1. Enhanced Title (max 80 chars, newspaper-style)
2. Subtitle (max 100 chars, catchy tagline)
3. Summary (2-3 sentences)
4. Category ID (from available list, or null)
5. Relevance Score (0.0-1.0) - BASED ON USER'S INTERESTS

CRITICAL RULES:
1. Output MUST match input article's language exactly (no translation)
2. Relevance score MUST reflect how well the article matches the USER'S SPECIFIC INTERESTS provided below
3. Ignore your own judgment - ONLY score based on the user's stated interests

Relevance Scoring - Rate ONLY based on user's interests:
- 0.9-1.0: Directly addresses user's core interests (rare)
- 0.7-0.9: Strongly related to user's interests
- 0.6-0.7: Clearly related to user's interests (recommended threshold)
- 0.4-0.6: Tangentially related to user's interests
- 0.0-0.4: Not related to user's interests

Category Assignment:
- Choose best-matching category ID from list
- Return null if no good match

JSON format:
{{
    "title": "headline",
    "subtitle": "tagline",
    "summary": "2-3 sentences",
    "category_id": 123,
    "relevance_score": 0.85
}}"""

        # Extract content for analysis
        content = article.content or article.description or "No content available"

        # Strip images from content to save LLM tokens
        content_for_llm = self._strip_images_from_content(content)

        # Aggressively truncate content based on max input tokens
        # Reserve tokens for: system prompt (~600), title/author/context (~200), overhead (~200)
        max_content_tokens = settings.LLM_MAX_INPUT_TOKENS - 1000
        content_for_llm = self._truncate_to_tokens(content_for_llm, max_content_tokens)

        user_prompt = f"""Article to Analyze:

Title: {article.title}
Author: {article.author or "Unknown"}
Content:
{content_for_llm}{category_context}

User's Interests:
{selection_prompt}

Analyze and provide comprehensive JSON output."""

        try:
            # Estimate tokens for rate limiting
            estimated_tokens = estimate_request_tokens(
                system_prompt, user_prompt, settings.LLM_MODEL, response_buffer=400
            )

            # Log the request (DEBUG level for details)
            logger.debug("=" * 80)
            logger.debug("LLM REQUEST - Article Analysis")
            logger.debug(f"Article ID: {article.id}")
            logger.debug(f"Model: {settings.LLM_MODEL}")
            logger.debug(f"Estimated tokens: {estimated_tokens}")
            logger.debug("-" * 80)
            logger.debug("SYSTEM PROMPT:")
            logger.debug(system_prompt)
            logger.debug("-" * 80)
            logger.debug("USER PROMPT:")
            logger.debug(user_prompt)
            logger.debug("=" * 80)

            # Apply rate limiting and concurrency control
            async with self.semaphore:
                await self.rate_limiter.acquire(estimated_tokens)

                response = await self.client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                )

                # Report actual usage for better rate limiting
                if response.usage:
                    actual_tokens = response.usage.total_tokens
                    self.rate_limiter.report_actual_usage(
                        actual_tokens, estimated_tokens
                    )

            result = json.loads(response.choices[0].message.content)

            # Log the response (DEBUG level for details)
            logger.debug("=" * 80)
            logger.debug("LLM RESPONSE - Article Analysis")
            logger.debug(f"Article ID: {article.id}")
            logger.debug(f"Usage: {response.usage}")
            logger.debug("-" * 80)
            logger.debug("RAW RESPONSE:")
            logger.debug(response.choices[0].message.content)
            logger.debug("-" * 80)
            logger.debug("PARSED RESULT:")
            logger.debug(json.dumps(result, indent=2))
            logger.debug("=" * 80)

            return result

        except Exception as e:
            logger.error(f"LLM API error: {str(e)}")
            logger.error(f"Full exception: {repr(e)}")
            return {
                "title": article.title,
                "subtitle": "",
                "summary": article.description[:200] if article.description else "",
                "category_id": None,
                "relevance_score": 0.0,
            }

    def _extract_image_urls_from_content(self, content: str) -> List[str]:
        """Extract image URLs from HTML/text content."""
        urls = []

        # Find URLs that end with image extensions
        image_pattern = r'https?://[^\s<>"]+?\.(?:jpg|jpeg|png|gif|webp|svg)'
        urls.extend(re.findall(image_pattern, content, re.IGNORECASE))

        # Find img src attributes
        img_src_pattern = r'<img[^>]+src=["\'](https?://[^"\']+)["\']'
        urls.extend(re.findall(img_src_pattern, content, re.IGNORECASE))

        # Remove duplicates while preserving order
        return list(dict.fromkeys(urls))

    def _strip_images_from_content(self, content: str) -> str:
        """Remove image tags and image URLs from content to save LLM tokens."""
        if not content:
            return content

        # Remove img tags
        content = re.sub(r"<img[^>]*>", "", content, flags=re.IGNORECASE)

        # Remove standalone image URLs (common image extensions)
        content = re.sub(
            r'https?://[^\s<>"]+?\.(?:jpg|jpeg|png|gif|webp|svg|bmp|ico)\b[^\s]*',
            "",
            content,
            flags=re.IGNORECASE,
        )

        # Remove picture tags
        content = re.sub(
            r"<picture[^>]*>.*?</picture>", "", content, flags=re.IGNORECASE | re.DOTALL
        )

        # Remove figure tags (often contain images)
        content = re.sub(
            r"<figure[^>]*>.*?</figure>", "", content, flags=re.IGNORECASE | re.DOTALL
        )

        # Clean up extra whitespace
        content = re.sub(r"\n\s*\n", "\n\n", content)
        content = re.sub(r" +", " ", content)

        return content.strip()

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """
        Truncate text to approximately max_tokens.

        Uses a simple heuristic: ~4 characters per token for English text.
        This is a rough estimate but avoids expensive token counting on every call.

        Args:
            text: Text to truncate
            max_tokens: Maximum number of tokens

        Returns:
            Truncated text
        """
        if not text:
            return text

        # Rough estimate: 4 chars per token
        max_chars = max_tokens * 4

        if len(text) <= max_chars:
            return text

        # Truncate and add ellipsis
        return text[:max_chars] + "..."

    async def regenerate_summaries(self, category_id: Optional[int] = None) -> int:
        """Regenerate summaries for existing articles."""
        query = self.db.query(Article)
        if category_id:
            query = query.filter(Article.category_id == category_id)

        # Reset summaries
        articles = query.all()
        for article in articles:
            article.summary = None
            article.relevance_score = 0.0

        self.db.commit()

        # Reprocess
        article_ids = [a.id for a in articles]
        return await self.process_articles(article_ids)
