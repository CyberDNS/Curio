from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from app.models.article import Article
from app.models.category import Category
from app.models.newspaper import Newspaper
from app.models.user import User
import logging

logger = logging.getLogger(__name__)


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

        # Get user's categories (ordered by display_order)
        categories = (
            self.db.query(Category)
            .filter(Category.user_id == user_id)
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
            new_articles, categories, existing_newspaper
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
    ) -> Dict:
        """
        Rule-based curation algorithm.

        "Today" Section Rules:
        - Best articles from each category (score-based)
        - No limits, all best articles go here

        Category Sections:
        - Remaining articles go to their assigned categories
        - No article appears in both "Today" and a category section

        Ordering:
        - New articles first (sorted by score DESC)
        - Existing articles second (sorted by score DESC)
        """

        # Start with existing structure or empty
        if existing_newspaper and existing_newspaper.structure:
            structure = existing_newspaper.structure.copy()
        else:
            structure = {"today": [], "categories": {}}

        # Ensure structure has required keys
        if "today" not in structure:
            structure["today"] = []
        if "categories" not in structure:
            structure["categories"] = {}

        # Group new articles by category
        articles_by_category = {}
        articles_without_category = []

        for article in new_articles:
            if article.category_id:
                if article.category_id not in articles_by_category:
                    articles_by_category[article.category_id] = []
                articles_by_category[article.category_id].append(article)
            else:
                articles_without_category.append(article)

        # Sort articles within each category by score
        for cat_id in articles_by_category:
            articles_by_category[cat_id] = sorted(
                articles_by_category[cat_id],
                key=lambda a: a.relevance_score or 0.0,
                reverse=True,
            )

        # Sort articles without category by score
        articles_without_category = sorted(
            articles_without_category,
            key=lambda a: a.relevance_score or 0.0,
            reverse=True,
        )

        # Select best articles for "Today" section using dynamic algorithm
        # Strategy: Take top articles from each category proportionally to ensure diversity
        # Aim for ~15-20 articles total on Today page, distributed across categories

        today_articles = []
        category_articles = {}  # Articles that go to category sections

        # Create category slug lookup
        cat_id_to_slug = {cat.id: cat.slug for cat in categories}

        # Calculate how many articles to take from each category for "Today"
        # Target: 15-20 articles total, distributed across categories
        target_today_count = 20
        categories_with_articles = [
            cat
            for cat in categories
            if cat.id in articles_by_category and articles_by_category[cat.id]
        ]

        if categories_with_articles:
            # Distribute slots across categories (at least 1 per category, more for categories with more articles)
            articles_per_category = {}
            total_new_articles = sum(
                len(articles_by_category[cat.id]) for cat in categories_with_articles
            )

            logger.info(
                f"Total new articles to curate: {total_new_articles} across {len(categories_with_articles)} categories"
            )

            # Strategy: Take top 50% of articles from each category for Today (min 1, max based on target)
            # This ensures category pages always have content if there are enough articles
            for cat in categories_with_articles:
                cat_article_count = len(articles_by_category[cat.id])

                # Take roughly 40-50% of articles for today (but at least 1 if only 1-2 articles)
                if cat_article_count <= 2:
                    articles_per_category[cat.id] = 1
                elif cat_article_count <= 5:
                    articles_per_category[cat.id] = 2
                else:
                    # Take roughly half, but cap based on target
                    max_from_category = max(
                        2, target_today_count // len(categories_with_articles)
                    )
                    articles_per_category[cat.id] = min(
                        max_from_category, int(cat_article_count * 0.5)
                    )

                logger.info(
                    f"Category {cat.slug}: {cat_article_count} articles, taking {articles_per_category[cat.id]} for Today"
                )

            # Select top N articles from each category for "Today"
            for cat in categories:
                if cat.id not in articles_by_category:
                    continue

                cat_articles = articles_by_category[cat.id]
                if not cat_articles:
                    continue

                num_for_today = articles_per_category.get(cat.id, 0)

                # Take top N articles for today, rest go to category section
                for i, article in enumerate(cat_articles):
                    if i < num_for_today:
                        today_articles.append(article)
                    else:
                        # Add to category section
                        cat_slug = cat_id_to_slug[cat.id]
                        if cat_slug not in category_articles:
                            category_articles[cat_slug] = []
                        category_articles[cat_slug].append(article)

                # Log what went where
                cat_slug = cat_id_to_slug[cat.id]
                num_in_category = len(category_articles.get(cat_slug, []))
                logger.info(
                    f"  -> {num_for_today} to Today, {num_in_category} to category section"
                )

        # Add uncategorized articles to "Today" (take top 3-5 if many, all if few)
        if articles_without_category:
            num_uncategorized_for_today = min(5, len(articles_without_category))
            for i, article in enumerate(articles_without_category):
                if i < num_uncategorized_for_today:
                    today_articles.append(article)
                # Note: uncategorized articles don't go to category sections

        # Sort all "Today" articles by score
        today_articles = sorted(
            today_articles, key=lambda a: a.relevance_score or 0.0, reverse=True
        )

        # Build today IDs list (new articles only)
        new_today_ids = [a.id for a in today_articles]

        # Get existing "Today" articles and sort by score
        existing_today_ids = set(structure["today"])
        existing_articles_today = []
        if existing_today_ids:
            existing_articles_today = (
                self.db.query(Article).filter(Article.id.in_(existing_today_ids)).all()
            )
            existing_articles_today = sorted(
                existing_articles_today,
                key=lambda a: a.relevance_score or 0.0,
                reverse=True,
            )

        # Combine: new articles first, then existing (both sorted by score)
        structure["today"] = new_today_ids + [a.id for a in existing_articles_today]

        # For category sections: Add new articles, then keep existing articles (both sorted)
        for category in categories:
            cat_slug = category.slug

            # Get new articles for this category
            new_cat_ids = []
            if cat_slug in category_articles:
                new_cat_articles = sorted(
                    category_articles[cat_slug],
                    key=lambda a: a.relevance_score or 0.0,
                    reverse=True,
                )
                new_cat_ids = [a.id for a in new_cat_articles]

            # Get existing articles in this category
            existing_cat_ids = []
            if cat_slug in structure["categories"]:
                existing_cat_ids = structure["categories"][cat_slug]
                if existing_cat_ids:
                    existing_cat_articles = (
                        self.db.query(Article)
                        .filter(Article.id.in_(existing_cat_ids))
                        .all()
                    )
                    # Sort by score
                    existing_cat_articles = sorted(
                        existing_cat_articles,
                        key=lambda a: a.relevance_score or 0.0,
                        reverse=True,
                    )
                    existing_cat_ids = [a.id for a in existing_cat_articles]

            # Combine: new articles first, then existing
            structure["categories"][cat_slug] = new_cat_ids + existing_cat_ids

        logger.info(f"Curated {len(new_today_ids)} new articles for 'Today' section")
        logger.info(f"Total 'Today' articles: {len(structure['today'])}")

        # Log category section stats
        for cat_slug, article_ids in structure["categories"].items():
            if article_ids:
                logger.info(f"Category '{cat_slug}': {len(article_ids)} articles")

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
