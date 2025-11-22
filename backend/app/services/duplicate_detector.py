"""
Duplicate detection service using OpenAI embeddings and cosine similarity.
"""

import logging
import json
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import openai
from app.models.article import Article
from app.core.config import settings

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """Service for detecting duplicate articles using embedding-based similarity."""

    def __init__(self, db: Session):
        self.db = db
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.embedding_model = settings.EMBEDDING_MODEL
        self.similarity_threshold = settings.DUPLICATE_SIMILARITY_THRESHOLD

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a text using OpenAI API.

        Args:
            text: Text to generate embedding for (typically article title)

        Returns:
            List of floats representing the embedding vector, or None on error
        """
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model, input=text
            )
            embedding = response.data[0].embedding
            logger.info(
                f"Generated embedding for text: '{text[:50]}...' "
                f"(model: {self.embedding_model}, dims: {len(embedding)})"
            )
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    def find_similar_articles(
        self, article: Article, days_back: int = 1
    ) -> List[Tuple[Article, float]]:
        """
        Find articles similar to the given article based on title embedding.

        Args:
            article: Article to find duplicates for
            days_back: Only check articles from this many days back

        Returns:
            List of tuples (similar_article, similarity_score) above threshold
        """
        if article.title_embedding is None or (
            isinstance(article.title_embedding, str)
            and not article.title_embedding.strip()
        ):
            logger.warning(
                f"Article {article.id} has no embedding, cannot find duplicates"
            )
            return []

        # Calculate date threshold
        date_threshold = datetime.utcnow() - timedelta(days=days_back)

        # Query for articles from same user, same timeframe, with embeddings
        # Exclude the article itself and already marked duplicates
        candidates = (
            self.db.query(Article)
            .filter(
                and_(
                    Article.user_id == article.user_id,
                    Article.id != article.id,
                    Article.created_at >= date_threshold,
                    Article.title_embedding.isnot(None),
                    Article.is_duplicate == False,
                )
            )
            .all()
        )

        if not candidates:
            logger.info(
                f"No candidate articles found for duplicate detection (article {article.id})"
            )
            return []

        # Calculate cosine similarity using manual calculation
        similar_articles = []

        # Parse article embedding once - handle string, list, or numpy array
        if isinstance(article.title_embedding, str):
            article_embedding = json.loads(article.title_embedding)
        elif hasattr(article.title_embedding, "tolist"):
            # numpy array
            article_embedding = article.title_embedding.tolist()
        else:
            article_embedding = article.title_embedding

        for candidate in candidates:
            try:
                # Skip if candidate has no embedding
                if candidate.title_embedding is None or (
                    isinstance(candidate.title_embedding, str)
                    and not candidate.title_embedding.strip()
                ):
                    continue

                # Parse candidate embedding - handle string, list, or numpy array
                if isinstance(candidate.title_embedding, str):
                    candidate_embedding = json.loads(candidate.title_embedding)
                elif hasattr(candidate.title_embedding, "tolist"):
                    # numpy array
                    candidate_embedding = candidate.title_embedding.tolist()
                else:
                    candidate_embedding = candidate.title_embedding

                similarity = self._cosine_similarity(
                    article_embedding, candidate_embedding
                )

                if similarity >= self.similarity_threshold:
                    similar_articles.append((candidate, similarity))
                    logger.info(
                        f"Found similar article: '{candidate.title[:50]}...' "
                        f"(similarity: {similarity:.3f})"
                    )
            except Exception as e:
                logger.error(
                    f"Error calculating similarity for candidate {candidate.id}: {e}"
                )

        # Sort by similarity (highest first)
        similar_articles.sort(key=lambda x: x[1], reverse=True)

        return similar_articles

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First embedding vector
            vec2: Second embedding vector

        Returns:
            Cosine similarity score (0-1)
        """
        import math

        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def mark_as_duplicate(
        self, duplicate_article: Article, original_article: Article
    ) -> None:
        """
        Mark an article as a duplicate of another article.

        Args:
            duplicate_article: Article to mark as duplicate
            original_article: Original/best article this is a duplicate of
        """
        duplicate_article.is_duplicate = True
        duplicate_article.duplicate_of_id = original_article.id
        self.db.commit()

        logger.info(
            f"Marked article {duplicate_article.id} ('{duplicate_article.title[:50]}...') "
            f"as duplicate of article {original_article.id} ('{original_article.title[:50]}...')"
        )

    def process_article_for_duplicates(self, article: Article) -> Optional[Article]:
        """
        Process an article to detect and mark duplicates.

        1. Generates embedding if needed
        2. Finds similar articles
        3. Marks as duplicate if match found

        Args:
            article: Article to process

        Returns:
            The original article if this is a duplicate, None otherwise
        """
        # Generate embedding if not present
        if article.title_embedding is None or (
            isinstance(article.title_embedding, str)
            and not article.title_embedding.strip()
        ):
            embedding = self.generate_embedding(article.title)
            if embedding:
                # Store as JSON string
                article.title_embedding = json.dumps(embedding)
                self.db.commit()
            else:
                logger.error(f"Could not generate embedding for article {article.id}")
                return None

        # Find similar articles
        similar_articles = self.find_similar_articles(article)

        if not similar_articles:
            logger.debug(f"No duplicates found for article {article.id}")
            return None

        # Get the best match (highest similarity, highest score, or earliest)
        original_article = self._select_best_original(article, similar_articles)

        # Mark this article as duplicate
        self.mark_as_duplicate(article, original_article)

        return original_article

    def _select_best_original(
        self, article: Article, similar_articles: List[Tuple[Article, float]]
    ) -> Article:
        """
        Select which article should be considered the "original" among duplicates.

        Priority:
        1. Highest relevance score
        2. Earliest published date
        3. Earliest created date

        Args:
            article: The new article being checked
            similar_articles: List of (article, similarity) tuples

        Returns:
            The article that should be considered the original
        """
        # Include the current article in consideration
        all_articles = [article] + [a for a, _ in similar_articles]

        # Sort by relevance score (desc), published_date (asc), created_at (asc)
        best_article = max(
            all_articles,
            key=lambda a: (
                a.relevance_score or 0.0,
                -(a.published_date.timestamp() if a.published_date else float("inf")),
                -(a.created_at.timestamp() if a.created_at else float("inf")),
            ),
        )

        logger.info(
            f"Selected article {best_article.id} (score: {best_article.relevance_score}) "
            f"as best among {len(all_articles)} duplicates"
        )

        return best_article

    def reprocess_duplicates_for_user(self, user_id: int, days_back: int = 7) -> int:
        """
        Reprocess all articles for a user to detect duplicates.
        Useful for bulk processing or fixing existing data.

        Args:
            user_id: User ID to process articles for
            days_back: Process articles from this many days back

        Returns:
            Number of duplicates found and marked
        """
        date_threshold = datetime.utcnow() - timedelta(days=days_back)

        # Get all articles for user in timeframe, ordered by created_at
        articles = (
            self.db.query(Article)
            .filter(
                and_(
                    Article.user_id == user_id,
                    Article.created_at >= date_threshold,
                    Article.is_duplicate == False,
                )
            )
            .order_by(Article.created_at)
            .all()
        )

        duplicates_found = 0

        for article in articles:
            original = self.process_article_for_duplicates(article)
            if original:
                duplicates_found += 1

        logger.info(
            f"Reprocessed {len(articles)} articles for user {user_id}, "
            f"found {duplicates_found} duplicates"
        )

        return duplicates_found
