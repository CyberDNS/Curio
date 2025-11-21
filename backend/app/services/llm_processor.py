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
from slugify import slugify
import logging
import json
import re

logger = logging.getLogger(__name__)


class LLMProcessor:
    def __init__(self, db: Session):
        self.db = db
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.duplicate_detector = DuplicateDetector(db)

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

        # Get user's content selection prompt
        selection_prompt_setting = (
            self.db.query(UserSettings)
            .filter(UserSettings.key == "llm_selection_prompt")
            .first()
        )

        if not selection_prompt_setting:
            logger.warning("No LLM selection prompt configured, using default behavior")
            selection_prompt = (
                "Select all articles that are informative and well-written."
            )
        else:
            selection_prompt = selection_prompt_setting.value

        # Get existing active (non-deleted) categories with descriptions for the LLM to consider
        query_categories = self.db.query(Category).filter(Category.is_deleted == False)
        if user_id:
            query_categories = query_categories.filter(Category.user_id == user_id)

        existing_categories = query_categories.all()

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

        logger.info(f"Processing {len(articles)} articles from last {days_back} day(s)")

        processed = 0
        for article in articles:
            try:
                # Comprehensive LLM analysis
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

                processed += 1
                logger.info(
                    f"Processed article {article.id}: {article.llm_title or article.title}"
                )

            except Exception as e:
                logger.error(f"Error processing article {article.id}: {str(e)}")
                self.db.rollback()

        logger.info(f"Processed {processed} articles with LLM")
        return processed

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

        system_prompt = f"""You are an intelligent news editor and curator. Your job is to analyze articles and assign them to appropriate categories.

Analyze the article and provide:

1. **Enhanced Title**: A compelling, newspaper-style headline (max 80 chars)
2. **Subtitle**: A catchy tagline or kicker (max 100 chars)
3. **Summary**: Concise 2-3 sentence summary of the article
4. **Category Assignment**: Select the most appropriate category ID from the available categories
5. **Relevance Score**: Rate relevance to user interests (0.0-1.0)

**LANGUAGE PRESERVATION**:
- CRITICAL: Your output (title, subtitle, summary) MUST be in the SAME LANGUAGE as the input article
- If the article is in German, respond in German
- If the article is in French, respond in French
- If the article is in English, respond in English
- Match the input language exactly - do NOT translate

**CATEGORY ASSIGNMENT GUIDELINES**:
- Carefully read the category descriptions to understand what content belongs in each category
- Assign the article to the SINGLE best-matching category
- If no category is a good fit, return null for category_id
- Consider the article's primary topic and theme when categorizing

**Relevance Scoring Guidelines**:
- Be STRICT and SELECTIVE - the user doesn't want to see everything
- Score conservatively - most articles should score below 0.5
- Only articles that directly relate to the user's interests should score above 0.6
- Articles scoring >= 0.6 will be marked as "Recommended"

**Score Thresholds**:
- 0.9-1.0: Perfect match to user's core interests (rare!)
- 0.7-0.9: Strong match, directly relevant
- 0.6-0.7: Good match, clearly related (RECOMMENDED threshold)
- 0.4-0.6: Weak connection, tangentially related
- 0.0-0.4: Not relevant

Respond ONLY with valid JSON in this exact format:
{{
    "title": "Compelling headline here",
    "subtitle": "Engaging subtitle here",
    "summary": "2-3 sentence summary",
    "category_id": 123,
    "relevance_score": 0.85
}}

Note: category_id should be an integer from the available categories, or null if no good match."""

        # Extract content for analysis
        content = article.content or article.description or "No content available"

        # Strip images from content to save LLM tokens
        content_for_llm = self._strip_images_from_content(content)

        user_prompt = f"""Article to Analyze:

Title: {article.title}
Author: {article.author or "Unknown"}
Content:
{content_for_llm[:3000]}...{category_context}

User's Interests:
{selection_prompt}

Analyze and provide comprehensive JSON output."""

        try:
            # Log the request
            logger.info("=" * 80)
            logger.info("LLM REQUEST - Article Analysis")
            logger.info(f"Article ID: {article.id}")
            logger.info(f"Model: {settings.LLM_MODEL}")
            logger.info("-" * 80)
            logger.info("SYSTEM PROMPT:")
            logger.info(system_prompt)
            logger.info("-" * 80)
            logger.info("USER PROMPT:")
            logger.info(user_prompt)
            logger.info("=" * 80)

            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)

            # Log the response
            logger.info("=" * 80)
            logger.info("LLM RESPONSE - Article Analysis")
            logger.info(f"Article ID: {article.id}")
            logger.info(f"Usage: {response.usage}")
            logger.info("-" * 80)
            logger.info("RAW RESPONSE:")
            logger.info(response.choices[0].message.content)
            logger.info("-" * 80)
            logger.info("PARSED RESULT:")
            logger.info(json.dumps(result, indent=2))
            logger.info("=" * 80)

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
