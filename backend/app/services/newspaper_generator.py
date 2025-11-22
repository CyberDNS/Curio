from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from app.models.article import Article
from app.models.category import Category
from app.models.newspaper import Newspaper
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

# Minimum relevance score for articles to appear in newspapers
# Articles below this threshold are considered too low quality
MIN_NEWSPAPER_SCORE = 0.6

# Minimum relevance score for articles to appear in newspapers
# Articles below this threshold are considered too low quality
MIN_NEWSPAPER_SCORE = 0.6


class NewspaperGenerator:
    """
    Generates daily newspapers using rule-based curation (no LLM).

    New approach:
    - Select articles from last 24 hours only
    - Exclude duplicates (is_duplicate=True)
    - "Today" section: Best articles across all categories (score-based with diversity)
    - Category sections: Remaining articles by category
    - New articles appear before existing articles (both sorted by score DESC)
    """

    def __init__(self, db: Session):
        self.db = db

    async def generate_newspapers_for_all_users(self) -> Dict[str, int]:
        """Generate newspapers for all active users."""
        users = self.db.query(User).filter(User.is_active == True).all()

        results = {"total_users": len(users), "successful": 0, "failed": 0}

        for user in users:
            try:
                await self.generate_newspaper_for_user(user.id)
                results["successful"] += 1
                logger.info(f"Generated newspaper for user {user.id}")
            except Exception as e:
                results["failed"] += 1
                logger.error(
                    f"Failed to generate newspaper for user {user.id}: {str(e)}"
                )

        return results

    async def generate_newspaper_for_user(
        self, user_id: int, target_date: Optional[date] = None
    ) -> Newspaper:
        """
        Generate or update newspaper for a specific user and date.

        New behavior:
        - Only processes articles from last 24 hours
        - Uses rule-based selection (no LLM)
        - Incremental updates during the day
        """

        if target_date is None:
            target_date = datetime.now().date()

        target_date_str = target_date.isoformat()

        # Get articles from last 3 days that haven't appeared in newspaper yet
        date_threshold = datetime.utcnow() - timedelta(days=3)

        eligible_articles = (
            self.db.query(Article)
            .filter(
                Article.user_id == user_id,
                Article.is_read == False,
                Article.is_archived == False,
                Article.is_duplicate == False,  # Exclude duplicates
                Article.created_at >= date_threshold,  # Last 3 days
                Article.summary.isnot(None),  # Must be processed
            )
            .all()
        )

        # Filter by minimum score threshold (use adjusted_score if available, otherwise base score)
        eligible_articles = [
            a
            for a in eligible_articles
            if (a.adjusted_relevance_score or a.relevance_score or 0.0)
            >= MIN_NEWSPAPER_SCORE
        ]

        # Filter by minimum score threshold (use adjusted_score if available, otherwise base score)
        eligible_articles = [
            a
            for a in eligible_articles
            if (a.adjusted_relevance_score or a.relevance_score or 0.0)
            >= MIN_NEWSPAPER_SCORE
        ]

        # Filter out articles already in today's newspaper
        new_articles = []
        for article in eligible_articles:
            appearances = article.newspaper_appearances or {}
            if target_date_str not in appearances:
                new_articles.append(article)

        if not new_articles:
            logger.info(f"No new articles for user {user_id} on {target_date}")
            # Check if newspaper exists, if not create empty one
            existing = (
                self.db.query(Newspaper)
                .filter(Newspaper.user_id == user_id, Newspaper.date == target_date)
                .first()
            )
            if not existing:
                return self._create_or_update_newspaper(
                    user_id, target_date, {"today": [], "categories": {}}
                )
            return existing

        logger.info(
            f"Found {len(new_articles)} new articles for user {user_id} on {target_date}"
        )

        # Get user's active (non-deleted) categories (ordered by display_order)
        categories = (
            self.db.query(Category)
            .filter(Category.user_id == user_id, Category.is_deleted == False)
            .order_by(Category.display_order)
            .all()
        )

        # Get existing newspaper if it exists
        existing_newspaper = (
            self.db.query(Newspaper)
            .filter(Newspaper.user_id == user_id, Newspaper.date == target_date)
            .first()
        )

        # Curate articles using rule-based algorithm
        newspaper_structure = self._curate_articles_rule_based(
            new_articles, categories, existing_newspaper, target_date
        )

        # Save newspaper (create or update)
        newspaper = self._create_or_update_newspaper(
            user_id, target_date, newspaper_structure
        )

        return newspaper

    def _curate_articles_rule_based(
        self,
        new_articles: List[Article],
        categories: List[Category],
        existing_newspaper: Optional[Newspaper] = None,
        target_date: Optional[date] = None,
    ) -> Dict:
        """
        Rule-based curation algorithm.

        Process:
        1. Fetch ALL eligible articles from last 24 hours
        2. Apply base filters: score threshold, not read if previously appeared
        3. Distribute articles between Today and category sections based on quality

        "Today" Section Rules:
        - Best articles from each category (score-based selection)
        - Quality-based scaling: 3-9 articles per category depending on scores
        - Higher quality categories get more articles on Today page
        - Unread articles first, then sorted by score

        Category Sections:
        - All remaining eligible articles (not in Today)
        - Sorted by unread first, then score DESC
        - No article appears in both "Today" and category section
        """

        structure = {"today": [], "categories": {}}

        # Get user_id from categories or new_articles
        user_id = (
            categories[0].user_id
            if categories
            else (new_articles[0].user_id if new_articles else None)
        )

        if user_id is None:
            logger.info("No articles or categories available")
            return structure

        # STEP 1: Fetch ALL eligible articles from last 24 hours
        date_threshold = datetime.utcnow() - timedelta(hours=24)

        all_articles = (
            self.db.query(Article)
            .filter(
                Article.user_id == user_id,
                Article.is_archived == False,
                Article.is_duplicate == False,
                Article.created_at >= date_threshold,
                Article.summary.isnot(None),  # Must be processed
            )
            .all()
        )

        logger.info(f"Found {len(all_articles)} articles from last 24 hours")

        # STEP 2: Apply base filters
        # - Must meet minimum score threshold
        # - Exclude articles that appeared in PREVIOUS editions (not today) AND are read
        if target_date is None:
            target_date = datetime.now().date()
        target_date_str = target_date.isoformat()

        eligible_articles = []
        for a in all_articles:
            # Check score threshold
            score = a.adjusted_relevance_score or a.relevance_score or 0.0
            if score < MIN_NEWSPAPER_SCORE:
                continue

            # Check if article appeared in previous editions and is read
            if a.newspaper_appearances and a.is_read:
                # Get all dates this article appeared in (excluding today)
                previous_dates = [
                    d for d in a.newspaper_appearances.keys() if d != target_date_str
                ]
                if previous_dates:
                    # Article appeared in previous editions and is now read - exclude it
                    continue

            eligible_articles.append(a)

        logger.info(
            f"After filtering: {len(eligible_articles)} eligible articles "
            f"(score >= {MIN_NEWSPAPER_SCORE}, not previously read)"
        )

        if not eligible_articles:
            logger.info("No eligible articles for newspaper")
            return structure

        # STEP 3: Group eligible articles by category
        articles_by_category = {}
        articles_uncategorized = []

        for article in eligible_articles:
            if article.category_id:
                if article.category_id not in articles_by_category:
                    articles_by_category[article.category_id] = []
                articles_by_category[article.category_id].append(article)
            else:
                articles_uncategorized.append(article)

        # Sort articles within each category by score (descending)
        for cat_id in articles_by_category:
            articles_by_category[cat_id] = sorted(
                articles_by_category[cat_id],
                key=lambda a: (a.adjusted_relevance_score or a.relevance_score or 0.0),
                reverse=True,
            )

        # Sort uncategorized articles by score
        articles_uncategorized = sorted(
            articles_uncategorized,
            key=lambda a: (a.adjusted_relevance_score or a.relevance_score or 0.0),
            reverse=True,
        )

        # Create category slug lookup
        cat_id_to_slug = {cat.id: cat.slug for cat in categories}

        # STEP 4: Select articles for Today section based on quality tiers
        today_articles = []

        for cat in categories:
            if cat.id not in articles_by_category:
                continue

            cat_articles = articles_by_category[cat.id]
            if not cat_articles:
                continue

            # Determine quality tier based on best article score
            best_score = max(
                (a.adjusted_relevance_score or a.relevance_score or 0.0)
                for a in cat_articles
            )

            # Quality-based scaling:
            # 0.9+: exceptional quality → take up to 9 articles
            # 0.8-0.9: high quality → take up to 6 articles
            # 0.7-0.8: good quality → take up to 4 articles
            # 0.6-0.7: acceptable quality → take up to 3 articles
            if best_score >= 0.9:
                max_for_today = 9
            elif best_score >= 0.8:
                max_for_today = 6
            elif best_score >= 0.7:
                max_for_today = 4
            else:  # 0.6-0.7
                max_for_today = 3

            # Take best N articles for Today
            num_for_today = min(max_for_today, len(cat_articles))
            today_articles.extend(cat_articles[:num_for_today])

            logger.debug(
                f"Category '{cat.slug}': {len(cat_articles)} eligible articles, "
                f"best score={best_score:.2f}, taking {num_for_today} for Today"
            )

        # Add top uncategorized articles to Today (up to 5)
        if articles_uncategorized:
            num_uncategorized_today = min(5, len(articles_uncategorized))
            today_articles.extend(articles_uncategorized[:num_uncategorized_today])
            logger.debug(
                f"Uncategorized: {len(articles_uncategorized)} articles, "
                f"taking {num_uncategorized_today} for Today"
            )

        # Sort Today articles: unread first, then by score
        today_articles = sorted(
            today_articles,
            key=lambda a: (
                a.is_read,  # False (unread) sorts before True (read)
                -(
                    a.adjusted_relevance_score or a.relevance_score or 0.0
                ),  # Descending score
            ),
        )

        structure["today"] = [a.id for a in today_articles]
        logger.info(f"Today section: {len(today_articles)} articles")

        # STEP 5: Distribute remaining articles to category sections
        today_article_ids = set(structure["today"])

        for category in categories:
            cat_slug = category.slug

            if category.id not in articles_by_category:
                structure["categories"][cat_slug] = []
                continue

            # Get articles for this category that are NOT in Today
            cat_remaining = [
                a
                for a in articles_by_category[category.id]
                if a.id not in today_article_ids
            ]

            # Sort: unread first, then by score
            cat_remaining = sorted(
                cat_remaining,
                key=lambda a: (
                    a.is_read,
                    -(a.adjusted_relevance_score or a.relevance_score or 0.0),
                ),
            )

            structure["categories"][cat_slug] = [a.id for a in cat_remaining]

            if cat_remaining:
                logger.debug(
                    f"Category '{cat_slug}' section: {len(cat_remaining)} articles"
                )

        return structure

    def _create_or_update_newspaper(
        self, user_id: int, target_date: date, structure: Dict
    ) -> Newspaper:
        """Create or update newspaper for the given date."""

        # Check if newspaper already exists for this date
        existing = (
            self.db.query(Newspaper)
            .filter(Newspaper.user_id == user_id, Newspaper.date == target_date)
            .first()
        )

        target_date_str = target_date.isoformat()

        # Track which articles appear in which sections
        article_section_map = {}

        # Collect all articles and their sections
        if "today" in structure:
            for article_id in structure["today"]:
                article_section_map[article_id] = "today"

        if "categories" in structure:
            for section_slug, article_ids in structure["categories"].items():
                for article_id in article_ids:
                    # Only track if not already in "today" (today takes priority)
                    if article_id not in article_section_map:
                        article_section_map[article_id] = section_slug

        # Update newspaper_appearances for all articles in this edition
        for article_id, section in article_section_map.items():
            article = self.db.query(Article).filter(Article.id == article_id).first()
            if article:
                appearances = article.newspaper_appearances or {}
                appearances[target_date_str] = section
                article.newspaper_appearances = appearances
                logger.debug(
                    f"Tracked article {article_id} in section '{section}' for {target_date_str}"
                )

        if existing:
            # Update existing newspaper
            existing.structure = structure
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            logger.info(f"Updated newspaper for user {user_id}, date {target_date}")
            return existing
        else:
            # Create new newspaper
            newspaper = Newspaper(
                user_id=user_id, date=target_date, structure=structure
            )
            self.db.add(newspaper)
            self.db.commit()
            self.db.refresh(newspaper)
            logger.info(f"Created newspaper for user {user_id}, date {target_date}")
            return newspaper
