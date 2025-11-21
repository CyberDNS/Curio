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
        - Best articles from each category (score-based selection)
        - Quality-based scaling: 3-9 articles per category depending on scores
        - Higher quality categories get more articles on Today page
        - All articles sorted by score (no time-based ordering)

        Category Sections:
        - All remaining articles (that meet MIN_NEWSPAPER_SCORE threshold)
        - Sorted by score DESC
        - No article appears in both "Today" and category section
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

        # Select best articles for "Today" section using quality-based algorithm
        # Strategy: Select 3-9 articles per category based on the quality of available articles
        # Higher quality categories get more articles on Today page

        today_articles = []
        category_articles = {}  # Articles that go to category sections

        # Create category slug lookup
        cat_id_to_slug = {cat.id: cat.slug for cat in categories}

        categories_with_articles = [
            cat
            for cat in categories
            if cat.id in articles_by_category and articles_by_category[cat.id]
        ]

        if categories_with_articles:
            articles_per_category = {}
            total_new_articles = sum(
                len(articles_by_category[cat.id]) for cat in categories_with_articles
            )

            logger.info(
                f"Total new articles to curate: {total_new_articles} across {len(categories_with_articles)} categories"
            )

            # Quality-based selection: Determine how many articles to feature on Today
            # based on the quality (score) of the best articles in each category
            for cat in categories_with_articles:
                cat_articles = articles_by_category[cat.id]

                # Get the score of the best article in this category
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
                    max_articles = 9
                elif best_score >= 0.8:
                    max_articles = 6
                elif best_score >= 0.7:
                    max_articles = 4
                else:  # 0.6-0.7
                    max_articles = 3

                # Take the best N articles, but don't exceed available count
                articles_per_category[cat.id] = min(max_articles, len(cat_articles))

                logger.info(
                    f"Category {cat.slug}: {len(cat_articles)} articles, "
                    f"best score={best_score:.2f}, taking {articles_per_category[cat.id]} for Today"
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

        # Re-evaluate ALL eligible articles for Today section (don't just add to existing)
        # Get all articles from the last 24 hours that meet the score threshold
        date_threshold = datetime.utcnow() - timedelta(hours=24)

        # Get user_id from first category or from the new_articles
        user_id = (
            categories[0].user_id
            if categories
            else (new_articles[0].user_id if new_articles else None)
        )

        if user_id is None:
            # No articles and no categories, return empty structure
            structure["today"] = []
            logger.info("No articles or categories available")
        else:
            all_eligible_for_today = (
                self.db.query(Article)
                .filter(
                    Article.user_id == user_id,
                    Article.is_archived == False,
                    Article.is_duplicate == False,
                    Article.created_at >= date_threshold,
                    Article.summary.isnot(None),
                )
                .all()
            )

            # Filter by score threshold
            all_eligible_for_today = [
                a
                for a in all_eligible_for_today
                if (a.adjusted_relevance_score or a.relevance_score or 0.0)
                >= MIN_NEWSPAPER_SCORE
            ]

            # Group by category and select best articles
            today_candidates_by_category = {}
            today_candidates_uncategorized = []

            for article in all_eligible_for_today:
                if article.category_id:
                    if article.category_id not in today_candidates_by_category:
                        today_candidates_by_category[article.category_id] = []
                    today_candidates_by_category[article.category_id].append(article)
                else:
                    today_candidates_uncategorized.append(article)

            # Sort within each category
            for cat_id in today_candidates_by_category:
                today_candidates_by_category[cat_id] = sorted(
                    today_candidates_by_category[cat_id],
                    key=lambda a: (
                        a.adjusted_relevance_score or a.relevance_score or 0.0
                    ),
                    reverse=True,
                )

            # Select best articles per category for Today
            final_today_articles = []

            for cat in categories:
                if cat.id not in today_candidates_by_category:
                    continue

                cat_articles = today_candidates_by_category[cat.id]
                if not cat_articles:
                    continue

                # Determine quality tier
                best_score = max(
                    (a.adjusted_relevance_score or a.relevance_score or 0.0)
                    for a in cat_articles
                )

                if best_score >= 0.9:
                    max_articles = 9
                elif best_score >= 0.8:
                    max_articles = 6
                elif best_score >= 0.7:
                    max_articles = 4
                else:  # 0.6-0.7
                    max_articles = 3

                # Take best N articles
                num_to_take = min(max_articles, len(cat_articles))
                final_today_articles.extend(cat_articles[:num_to_take])

            # Add top uncategorized articles
            if today_candidates_uncategorized:
                today_candidates_uncategorized = sorted(
                    today_candidates_uncategorized,
                    key=lambda a: (
                        a.adjusted_relevance_score or a.relevance_score or 0.0
                    ),
                    reverse=True,
                )
                num_uncategorized = min(5, len(today_candidates_uncategorized))
                final_today_articles.extend(
                    today_candidates_uncategorized[:num_uncategorized]
                )

            # Sort final Today list: unread first, then by score
            final_today_articles = sorted(
                final_today_articles,
                key=lambda a: (
                    a.is_read,  # False (unread) sorts before True (read)
                    -(
                        a.adjusted_relevance_score or a.relevance_score or 0.0
                    ),  # Descending score
                ),
            )

            structure["today"] = [a.id for a in final_today_articles]

            logger.info(
                f"Today section recalculated: {len(structure['today'])} articles"
            )

        # For category sections: Re-evaluate from scratch, don't accumulate
        # Get all articles that aren't in Today section
        today_article_ids = set(structure["today"])

        for category in categories:
            cat_slug = category.slug

            # Get ALL eligible articles for this category (not in Today)
            cat_eligible_articles = (
                self.db.query(Article)
                .filter(
                    Article.user_id == category.user_id,
                    Article.category_id == category.id,
                    Article.is_archived == False,
                    Article.is_duplicate == False,
                    Article.created_at >= date_threshold,
                    Article.summary.isnot(None),
                    ~Article.id.in_(today_article_ids),  # Exclude Today articles
                )
                .all()
            )

            # Filter by score threshold
            cat_eligible_articles = [
                a
                for a in cat_eligible_articles
                if (a.adjusted_relevance_score or a.relevance_score or 0.0)
                >= MIN_NEWSPAPER_SCORE
            ]

            # Sort: unread first, then by score
            cat_eligible_articles = sorted(
                cat_eligible_articles,
                key=lambda a: (
                    a.is_read,  # False (unread) sorts before True (read)
                    -(
                        a.adjusted_relevance_score or a.relevance_score or 0.0
                    ),  # Descending score
                ),
            )

            structure["categories"][cat_slug] = [a.id for a in cat_eligible_articles]

            if cat_eligible_articles:
                logger.info(
                    f"Category '{cat_slug}': {len(cat_eligible_articles)} articles"
                )

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
