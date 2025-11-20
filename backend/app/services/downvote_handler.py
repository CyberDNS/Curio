from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
from app.models.article import Article
from openai import AsyncOpenAI
from app.core.config import settings
import numpy as np
import json
import logging
from sklearn.cluster import KMeans
from datetime import datetime

logger = logging.getLogger(__name__)


class DownvoteHandler:
    """
    Handles downvote-based content filtering using embedding similarity.

    Uses prototype vectors (cluster centroids) to efficiently match new articles
    against downvoted content without exploding token costs or memory usage.
    """

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._prototypes: Optional[List[np.ndarray]] = None
        self._downvote_count: int = 0

    def _load_downvoted_articles(self) -> List[Article]:
        """Load all downvoted articles with embeddings for this user."""
        return (
            self.db.query(Article)
            .filter(
                Article.user_id == self.user_id,
                Article.user_vote == -1,
                Article.title_embedding.isnot(None),
            )
            .all()
        )

    def _compute_prototypes(self, max_prototypes: int = 10) -> List[np.ndarray]:
        """
        Compute prototype vectors representing clusters of downvoted content.

        Uses k-means clustering to find representative vectors, reducing
        memory footprint and comparison cost from O(N) to O(k) where k ≈ 10.
        """
        downvoted = self._load_downvoted_articles()
        self._downvote_count = len(downvoted)

        if not downvoted:
            logger.info(f"User {self.user_id}: No downvoted articles yet")
            return []

        # Parse embeddings from JSON
        embeddings = []
        for article in downvoted:
            try:
                embedding = json.loads(article.title_embedding)
                embeddings.append(embedding)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(
                    f"Failed to parse embedding for article {article.id}: {e}"
                )
                continue

        if not embeddings:
            return []

        embeddings_array = np.array(embeddings)

        # If we have fewer articles than max_prototypes, use all as prototypes
        if len(embeddings) <= max_prototypes:
            logger.info(
                f"User {self.user_id}: Using all {len(embeddings)} downvoted articles as prototypes"
            )
            return [emb for emb in embeddings_array]

        # Use k-means to find representative prototypes
        n_clusters = min(
            max_prototypes, len(embeddings) // 3
        )  # At least 3 articles per cluster
        n_clusters = max(1, n_clusters)  # At least 1 cluster

        logger.info(
            f"User {self.user_id}: Computing {n_clusters} prototypes from {len(embeddings)} downvoted articles"
        )

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        kmeans.fit(embeddings_array)

        return [center for center in kmeans.cluster_centers_]

    def get_prototypes(self, force_rebuild: bool = False) -> List[np.ndarray]:
        """
        Get prototype vectors, computing them if needed.

        Prototypes are cached in memory for the lifetime of the handler instance.
        Call with force_rebuild=True to recompute after new downvotes.
        """
        if self._prototypes is None or force_rebuild:
            self._prototypes = self._compute_prototypes()
        return self._prototypes

    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def find_most_similar_downvote(
        self, article: Article
    ) -> Tuple[Optional[float], Optional[Article]]:
        """
        Find the most similar downvoted article to the given article.

        Returns:
            (max_similarity, most_similar_article) or (None, None) if no comparison possible
        """
        if not article.title_embedding:
            return None, None

        prototypes = self.get_prototypes()
        if not prototypes:
            return None, None

        # Parse article embedding
        try:
            article_embedding = np.array(json.loads(article.title_embedding))
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse embedding for article {article.id}: {e}")
            return None, None

        # Find maximum similarity to any prototype
        similarities = [
            self.cosine_similarity(article_embedding, prototype)
            for prototype in prototypes
        ]
        max_similarity = max(similarities) if similarities else 0.0

        # Find the actual most similar downvoted article for reference
        # (We compare to prototypes for performance, but return actual article for context)
        downvoted_articles = self._load_downvoted_articles()
        if not downvoted_articles:
            return max_similarity, None

        most_similar_article = None
        max_actual_similarity = 0.0

        for downvoted in downvoted_articles[:20]:  # Check top 20 for performance
            try:
                downvoted_embedding = np.array(json.loads(downvoted.title_embedding))
                similarity = self.cosine_similarity(
                    article_embedding, downvoted_embedding
                )
                if similarity > max_actual_similarity:
                    max_actual_similarity = similarity
                    most_similar_article = downvoted
            except (json.JSONDecodeError, TypeError):
                continue

        return max_similarity, most_similar_article

    def apply_downvote_penalty(self, article: Article) -> bool:
        """
        Adjust article relevance score based on similarity to downvoted content.

        Returns:
            True if penalty was applied, False otherwise
        """
        if not article.relevance_score or not article.title_embedding:
            # No score or embedding to work with
            article.adjusted_relevance_score = article.relevance_score
            return False

        max_similarity, most_similar_article = self.find_most_similar_downvote(article)

        if max_similarity is None:
            # No downvoted articles to compare against
            article.adjusted_relevance_score = article.relevance_score
            return False

        # Apply progressive penalty based on similarity threshold
        # Similarity > 0.80 = very similar, apply penalty
        SIMILARITY_THRESHOLD = 0.80

        if max_similarity > SIMILARITY_THRESHOLD:
            # Scale penalty: similarity 0.80 -> penalty ~0, similarity 1.0 -> penalty ~0.4
            penalty = min(0.4, (max_similarity - SIMILARITY_THRESHOLD) * 2.0)
            adjusted_score = max(0.0, article.relevance_score - penalty)

            # Store adjustment
            article.adjusted_relevance_score = adjusted_score

            # Create brief explanation for UI
            if most_similar_article:
                similar_title = (
                    most_similar_article.llm_title or most_similar_article.title
                )
                article.score_adjustment_reason = (
                    f"Similar to downvoted: '{similar_title[:60]}...' "
                    f"(similarity: {max_similarity:.0%})"
                )
            else:
                article.score_adjustment_reason = (
                    f"Similar to downvoted content (similarity: {max_similarity:.0%})"
                )

            logger.info(
                f"Article {article.id} ({article.llm_title or article.title[:50]}): "
                f"similarity={max_similarity:.3f}, penalty={penalty:.3f}, "
                f"{article.relevance_score:.2f} → {adjusted_score:.2f}"
            )

            return True
        else:
            # Below threshold, no penalty
            article.adjusted_relevance_score = article.relevance_score
            return False

    async def explain_adjustment(self, article: Article) -> str:
        """
        Generate human-readable explanation of why the score was adjusted.

        Uses LLM to create a natural language explanation by comparing the
        article to the most similar downvoted content.
        """
        if not article.score_adjustment_reason:
            return "No score adjustment was applied to this article."

        max_similarity, most_similar_article = self.find_most_similar_downvote(article)

        if not most_similar_article or max_similarity is None:
            return article.score_adjustment_reason

        # Get article content for comparison
        current_title = article.llm_title or article.title
        current_summary = (
            article.llm_summary or article.summary or article.description or ""
        )

        similar_title = most_similar_article.llm_title or most_similar_article.title
        similar_summary = (
            most_similar_article.llm_summary
            or most_similar_article.summary
            or most_similar_article.description
            or ""
        )

        system_prompt = """You are a helpful assistant explaining content filtering decisions to users.

Your task is to explain why an article's relevance score was adjusted downward based on similarity to previously downvoted content.

Be:
- Clear and concise (2-3 sentences max)
- Specific about what makes them similar
- Helpful in understanding the filtering logic
- Not judgmental about user preferences

Focus on explaining the SIMILARITY, not criticizing either article."""

        user_prompt = f"""The user downvoted this article in the past:

Title: {similar_title}
Summary: {similar_summary[:300]}

Now they received this new article:

Title: {current_title}
Summary: {current_summary[:300]}

The system detected {max_similarity:.0%} similarity and reduced the relevance score from {article.relevance_score:.2f} to {article.adjusted_relevance_score:.2f}.

Explain in 2-3 sentences why these articles are similar and why the score was adjusted. Be specific about the common themes, topics, or angles they share."""

        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=200,
                temperature=0.7,
            )

            explanation = response.choices[0].message.content.strip()

            logger.info(f"Generated explanation for article {article.id}")

            return explanation

        except Exception as e:
            logger.error(f"Failed to generate explanation: {e}")
            # Fallback to simple explanation
            return (
                f"This article was scored lower because it's {max_similarity:.0%} similar "
                f"to '{similar_title[:60]}...', which you previously downvoted. "
                f"Both articles appear to cover related topics or themes."
            )

    def rebuild_prototypes(self) -> int:
        """
        Force rebuild of prototype vectors.

        Call this after new downvotes to update the filtering model.

        Returns:
            Number of downvoted articles used to build prototypes
        """
        self._prototypes = None
        self.get_prototypes(force_rebuild=True)
        return self._downvote_count
