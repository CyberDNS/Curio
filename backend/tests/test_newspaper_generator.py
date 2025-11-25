"""Tests for newspaper generation logic."""

import pytest
from datetime import datetime, timedelta, date
from app.models.article import Article
from app.models.category import Category
from app.models.newspaper import Newspaper
from app.services.newspaper_generator import NewspaperGenerator


class TestNewspaperGenerator:
    """Test newspaper generation rules and limits."""

    @pytest.mark.asyncio
    async def test_today_section_respects_per_category_limit(
        self, db_session, test_user
    ):
        """Today section should have max 9 articles per category (quality dependent)."""
        # Create a category
        category = Category(
            user_id=test_user.id, name="Technology", slug="technology", display_order=1
        )
        db_session.add(category)
        db_session.commit()

        # Create 15 high-quality articles (score 0.95) in same category
        # Only 9 should appear in "today" section
        articles = []
        for i in range(15):
            article = Article(
                user_id=test_user.id,
                category_id=category.id,
                title=f"Tech Article {i}",
                link=f"https://example.com/tech-{i}",
                published_date=datetime.utcnow(),
                created_at=datetime.utcnow(),
                relevance_score=0.95,
                summary=f"Summary {i}",
                is_read=False,
                is_archived=False,
                is_duplicate=False,
            )
            articles.append(article)
            db_session.add(article)
        db_session.commit()

        # Generate newspaper
        generator = NewspaperGenerator(db_session)
        newspaper = await generator.generate_newspaper_for_user(test_user.id)

        # Verify "today" section has exactly 9 articles (max for 0.9+ score category)
        today_articles = newspaper.structure.get("today", [])
        assert (
            len(today_articles) == 9
        ), f"Expected 9 articles in today, got {len(today_articles)}"

        # Remaining 6 should be in category section
        tech_section = newspaper.structure.get("categories", {}).get("technology", [])
        assert (
            len(tech_section) == 6
        ), f"Expected 6 articles in tech section, got {len(tech_section)}"

    @pytest.mark.asyncio
    async def test_total_today_articles_respects_quality_limits(
        self, db_session, test_user
    ):
        """Today section should scale per category based on quality."""
        # Create 3 categories with different quality levels
        cat_high = Category(
            user_id=test_user.id, name="High", slug="high", display_order=1
        )
        cat_med = Category(
            user_id=test_user.id, name="Medium", slug="medium", display_order=2
        )
        cat_low = Category(
            user_id=test_user.id, name="Low", slug="low", display_order=3
        )
        db_session.add_all([cat_high, cat_med, cat_low])
        db_session.commit()

        # High quality category: 10 articles at 0.95 score (should get 9 in today)
        for i in range(10):
            db_session.add(
                Article(
                    user_id=test_user.id,
                    category_id=cat_high.id,
                    title=f"High {i}",
                    link=f"https://example.com/high-{i}",
                    published_date=datetime.utcnow(),
                    created_at=datetime.utcnow(),
                    relevance_score=0.95,
                    summary=f"Summary {i}",
                    is_read=False,
                    is_archived=False,
                    is_duplicate=False,
                )
            )

        # Medium quality: 10 articles at 0.75 score (should get 4 in today)
        for i in range(10):
            db_session.add(
                Article(
                    user_id=test_user.id,
                    category_id=cat_med.id,
                    title=f"Med {i}",
                    link=f"https://example.com/med-{i}",
                    published_date=datetime.utcnow(),
                    created_at=datetime.utcnow(),
                    relevance_score=0.75,
                    summary=f"Summary {i}",
                    is_read=False,
                    is_archived=False,
                    is_duplicate=False,
                )
            )

        # Low quality: 10 articles at 0.65 score (should get 3 in today)
        for i in range(10):
            db_session.add(
                Article(
                    user_id=test_user.id,
                    category_id=cat_low.id,
                    title=f"Low {i}",
                    link=f"https://example.com/low-{i}",
                    published_date=datetime.utcnow(),
                    created_at=datetime.utcnow(),
                    relevance_score=0.65,
                    summary=f"Summary {i}",
                    is_read=False,
                    is_archived=False,
                    is_duplicate=False,
                )
            )
        db_session.commit()

        # Generate newspaper
        generator = NewspaperGenerator(db_session)
        newspaper = await generator.generate_newspaper_for_user(test_user.id)

        today_articles = newspaper.structure.get("today", [])

        # Should have 9 + 4 + 3 = 16 total articles
        assert (
            len(today_articles) == 16
        ), f"Expected 16 total in today, got {len(today_articles)}"

    @pytest.mark.asyncio
    async def test_article_not_duplicated_in_today_and_category(
        self, db_session, test_user
    ):
        """Article should appear in either today OR category section, not both."""
        category = Category(
            user_id=test_user.id, name="Tech", slug="tech", display_order=1
        )
        db_session.add(category)
        db_session.commit()

        # Create 5 articles
        for i in range(5):
            db_session.add(
                Article(
                    user_id=test_user.id,
                    category_id=category.id,
                    title=f"Article {i}",
                    link=f"https://example.com/{i}",
                    published_date=datetime.utcnow(),
                    created_at=datetime.utcnow(),
                    relevance_score=0.95,
                    summary=f"Summary {i}",
                    is_read=False,
                    is_archived=False,
                    is_duplicate=False,
                )
            )
        db_session.commit()

        generator = NewspaperGenerator(db_session)
        newspaper = await generator.generate_newspaper_for_user(test_user.id)

        today_ids = set(newspaper.structure.get("today", []))
        tech_ids = set(newspaper.structure.get("categories", {}).get("tech", []))

        # No overlap
        overlap = today_ids & tech_ids
        assert (
            len(overlap) == 0
        ), f"Found {len(overlap)} articles in both today and category section"

    @pytest.mark.asyncio
    async def test_article_in_todays_edition_can_move_sections(
        self, db_session, test_user
    ):
        """Articles in today's newspaper can be re-selected and move between sections."""
        category = Category(
            user_id=test_user.id, name="Tech", slug="tech", display_order=1
        )
        db_session.add(category)
        db_session.commit()

        # Create article that already appeared in today's edition in "tech" section
        today_str = datetime.now().date().isoformat()
        existing_article = Article(
            user_id=test_user.id,
            category_id=category.id,
            title="Existing Article",
            link="https://example.com/existing",
            published_date=datetime.utcnow(),
            created_at=datetime.utcnow(),
            relevance_score=0.70,  # Lower score - might move to category section
            summary="Summary",
            is_read=False,
            is_archived=False,
            is_duplicate=False,
            newspaper_appearances={today_str: "tech"},
        )
        db_session.add(existing_article)

        # Create a higher-scored new article
        new_article = Article(
            user_id=test_user.id,
            category_id=category.id,
            title="New Article",
            link="https://example.com/new",
            published_date=datetime.utcnow(),
            created_at=datetime.utcnow(),
            relevance_score=0.95,  # Higher score - should go to today section
            summary="Summary",
            is_read=False,
            is_archived=False,
            is_duplicate=False,
        )
        db_session.add(new_article)
        db_session.commit()

        # Generate newspaper - both articles should be included
        generator = NewspaperGenerator(db_session)
        newspaper = await generator.generate_newspaper_for_user(test_user.id)

        all_article_ids = newspaper.structure.get("today", [])
        for cat_ids in newspaper.structure.get("categories", {}).values():
            all_article_ids.extend(cat_ids)

        # Both articles should be in the newspaper (somewhere)
        assert (
            len(all_article_ids) == 2
        ), f"Expected 2 articles total, got {len(all_article_ids)}"
        assert (
            existing_article.id in all_article_ids
        ), "Existing article should still be in newspaper"
        assert new_article.id in all_article_ids, "New article should be in newspaper"

    @pytest.mark.asyncio
    async def test_read_article_from_previous_edition_excluded(
        self, db_session, test_user
    ):
        """Articles that appeared in previous editions and are now read should be excluded."""
        category = Category(
            user_id=test_user.id, name="Tech", slug="tech", display_order=1
        )
        db_session.add(category)
        db_session.commit()

        yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()

        # Article appeared yesterday and is now read - should be excluded
        article = Article(
            user_id=test_user.id,
            category_id=category.id,
            title="Old Article",
            link="https://example.com/old",
            published_date=datetime.utcnow(),
            created_at=datetime.utcnow(),
            relevance_score=0.95,
            summary="Summary",
            is_read=True,  # User read it
            is_archived=False,
            is_duplicate=False,
            newspaper_appearances={yesterday: "today"},  # Appeared yesterday
        )
        db_session.add(article)
        db_session.commit()

        # Generate today's newspaper
        generator = NewspaperGenerator(db_session)
        newspaper = await generator.generate_newspaper_for_user(test_user.id)

        all_article_ids = newspaper.structure.get("today", [])
        for cat_ids in newspaper.structure.get("categories", {}).values():
            all_article_ids.extend(cat_ids)

        # Old read article should not appear
        assert (
            article.id not in all_article_ids
        ), "Read article from previous edition should be excluded"

    @pytest.mark.asyncio
    async def test_unread_article_from_previous_edition_included(
        self, db_session, test_user
    ):
        """Unread articles that appeared in previous editions should still appear."""
        category = Category(
            user_id=test_user.id, name="Tech", slug="tech", display_order=1
        )
        db_session.add(category)
        db_session.commit()

        yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()

        # Article appeared yesterday but still unread - should be included
        article = Article(
            user_id=test_user.id,
            category_id=category.id,
            title="Unread Article",
            link="https://example.com/unread",
            published_date=datetime.utcnow(),
            created_at=datetime.utcnow(),
            relevance_score=0.95,
            summary="Summary",
            is_read=False,  # Still unread
            is_archived=False,
            is_duplicate=False,
            newspaper_appearances={yesterday: "today"},  # Appeared yesterday
        )
        db_session.add(article)
        db_session.commit()

        # Generate today's newspaper
        generator = NewspaperGenerator(db_session)
        newspaper = await generator.generate_newspaper_for_user(test_user.id)

        all_article_ids = newspaper.structure.get("today", [])
        for cat_ids in newspaper.structure.get("categories", {}).values():
            all_article_ids.extend(cat_ids)

        # Unread article should appear again
        assert (
            article.id in all_article_ids
        ), "Unread article from previous edition should be included"

    @pytest.mark.asyncio
    async def test_articles_outside_24h_window_excluded(self, db_session, test_user):
        """Articles older than 24 hours should not appear in newspaper."""
        category = Category(
            user_id=test_user.id, name="Tech", slug="tech", display_order=1
        )
        db_session.add(category)
        db_session.commit()

        # Article from 25 hours ago
        old_article = Article(
            user_id=test_user.id,
            category_id=category.id,
            title="Old Article",
            link="https://example.com/old",
            published_date=datetime.utcnow() - timedelta(hours=25),
            created_at=datetime.utcnow() - timedelta(hours=25),
            relevance_score=0.95,
            summary="Summary",
            is_read=False,
            is_archived=False,
            is_duplicate=False,
        )
        db_session.add(old_article)

        # Recent article from 2 hours ago
        recent_article = Article(
            user_id=test_user.id,
            category_id=category.id,
            title="Recent Article",
            link="https://example.com/recent",
            published_date=datetime.utcnow() - timedelta(hours=2),
            created_at=datetime.utcnow() - timedelta(hours=2),
            relevance_score=0.95,
            summary="Summary",
            is_read=False,
            is_archived=False,
            is_duplicate=False,
        )
        db_session.add(recent_article)
        db_session.commit()

        # Generate newspaper
        generator = NewspaperGenerator(db_session)
        newspaper = await generator.generate_newspaper_for_user(test_user.id)

        all_article_ids = newspaper.structure.get("today", [])
        for cat_ids in newspaper.structure.get("categories", {}).values():
            all_article_ids.extend(cat_ids)

        # Only recent article should appear
        assert recent_article.id in all_article_ids, "Recent article should be included"
        assert (
            old_article.id not in all_article_ids
        ), "Article older than 24h should be excluded"

    @pytest.mark.asyncio
    async def test_articles_never_removed_from_edition(self, db_session, test_user):
        """Articles in an edition must never be removed during regeneration."""
        category = Category(
            user_id=test_user.id, name="Tech", slug="tech", display_order=1
        )
        db_session.add(category)
        db_session.commit()

        today_str = datetime.now().date().isoformat()

        # Create 3 articles already in today's edition
        existing_articles = []
        for i in range(3):
            article = Article(
                user_id=test_user.id,
                category_id=category.id,
                title=f"Existing {i}",
                link=f"https://example.com/existing-{i}",
                published_date=datetime.utcnow() - timedelta(hours=3),
                created_at=datetime.utcnow() - timedelta(hours=3),
                relevance_score=0.70,
                summary=f"Summary {i}",
                is_read=False,
                is_archived=False,
                is_duplicate=False,
                newspaper_appearances={today_str: "today"},
            )
            existing_articles.append(article)
            db_session.add(article)
        db_session.commit()

        # Generate first newspaper
        generator = NewspaperGenerator(db_session)
        newspaper1 = await generator.generate_newspaper_for_user(test_user.id)

        initial_ids = set(newspaper1.structure.get("today", []))
        for cat_ids in newspaper1.structure.get("categories", {}).values():
            initial_ids.update(cat_ids)

        # Add new high-priority articles
        for i in range(5):
            article = Article(
                user_id=test_user.id,
                category_id=category.id,
                title=f"New {i}",
                link=f"https://example.com/new-{i}",
                published_date=datetime.utcnow(),
                created_at=datetime.utcnow(),
                relevance_score=0.95,
                summary=f"Summary {i}",
                is_read=False,
                is_archived=False,
                is_duplicate=False,
            )
            db_session.add(article)
        db_session.commit()

        # Regenerate newspaper
        newspaper2 = await generator.generate_newspaper_for_user(test_user.id)

        final_ids = set(newspaper2.structure.get("today", []))
        for cat_ids in newspaper2.structure.get("categories", {}).values():
            final_ids.update(cat_ids)

        # All initial articles must still be present
        assert initial_ids.issubset(
            final_ids
        ), "Existing articles were removed - this should never happen!"
        assert len(final_ids) > len(initial_ids), "New articles should have been added"

    @pytest.mark.asyncio
    async def test_articles_can_move_between_sections(self, db_session, test_user):
        """Articles can move from today to category section or vice versa."""
        cat1 = Category(user_id=test_user.id, name="Tech", slug="tech", display_order=1)
        cat2 = Category(
            user_id=test_user.id, name="Science", slug="science", display_order=2
        )
        db_session.add_all([cat1, cat2])
        db_session.commit()

        today_str = datetime.now().date().isoformat()

        # Article in today section but with lower score
        article_in_today = Article(
            user_id=test_user.id,
            category_id=cat1.id,
            title="In Today",
            link="https://example.com/today",
            published_date=datetime.utcnow(),
            created_at=datetime.utcnow(),
            relevance_score=0.65,
            summary="Summary",
            is_read=False,
            is_archived=False,
            is_duplicate=False,
            newspaper_appearances={today_str: "today"},
        )
        db_session.add(article_in_today)

        # Add many high-scoring articles to push the low-scoring one out
        for i in range(10):
            db_session.add(
                Article(
                    user_id=test_user.id,
                    category_id=cat1.id,
                    title=f"High Score {i}",
                    link=f"https://example.com/high-{i}",
                    published_date=datetime.utcnow(),
                    created_at=datetime.utcnow(),
                    relevance_score=0.95,
                    summary=f"Summary {i}",
                    is_read=False,
                    is_archived=False,
                    is_duplicate=False,
                )
            )
        db_session.commit()

        # Generate newspaper - low-scoring article should move to category
        generator = NewspaperGenerator(db_session)
        newspaper = await generator.generate_newspaper_for_user(test_user.id)

        today_ids = set(newspaper.structure.get("today", []))
        tech_ids = set(newspaper.structure.get("categories", {}).get("tech", []))

        # Article must be in one section or the other
        assert article_in_today.id in (
            today_ids | tech_ids
        ), "Article must still be in newspaper"

        # It's acceptable for it to stay in today or move to category
        # The key is it's not removed
        if article_in_today.id in tech_ids:
            assert (
                article_in_today.id not in today_ids
            ), "Article should not be in both sections"

    @pytest.mark.asyncio
    async def test_score_below_threshold_preserved_if_already_in_edition(
        self, db_session, test_user
    ):
        """Articles with score < 0.6 are kept if already in today's edition."""
        category = Category(
            user_id=test_user.id, name="Tech", slug="tech", display_order=1
        )
        db_session.add(category)
        db_session.commit()

        today_str = datetime.now().date().isoformat()

        # Article with low score but already in edition
        low_score_article = Article(
            user_id=test_user.id,
            category_id=category.id,
            title="Low Score",
            link="https://example.com/low",
            published_date=datetime.utcnow(),
            created_at=datetime.utcnow(),
            relevance_score=0.40,  # Below threshold
            summary="Summary",
            is_read=False,
            is_archived=False,
            is_duplicate=False,
            newspaper_appearances={today_str: "tech"},
        )
        db_session.add(low_score_article)
        db_session.commit()

        # Generate newspaper
        generator = NewspaperGenerator(db_session)
        newspaper = await generator.generate_newspaper_for_user(test_user.id)

        all_ids = set(newspaper.structure.get("today", []))
        for cat_ids in newspaper.structure.get("categories", {}).values():
            all_ids.update(cat_ids)

        # Low-scoring article should be preserved
        assert (
            low_score_article.id in all_ids
        ), "Article with score < 0.6 should be kept if already in edition"

    @pytest.mark.asyncio
    async def test_reading_article_excludes_from_future_editions(
        self, db_session, test_user
    ):
        """Reading an article prevents it from appearing in future editions."""
        category = Category(
            user_id=test_user.id, name="Tech", slug="tech", display_order=1
        )
        db_session.add(category)
        db_session.commit()

        yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()

        # Article that appeared yesterday and is now read
        read_article = Article(
            user_id=test_user.id,
            category_id=category.id,
            title="Read Article",
            link="https://example.com/read",
            published_date=datetime.utcnow(),
            created_at=datetime.utcnow(),
            relevance_score=0.95,
            summary="Summary",
            is_read=True,  # User read it
            is_archived=False,
            is_duplicate=False,
            newspaper_appearances={yesterday: "today"},
        )
        db_session.add(read_article)
        db_session.commit()

        # Generate today's newspaper
        generator = NewspaperGenerator(db_session)
        newspaper = await generator.generate_newspaper_for_user(test_user.id)

        all_ids = set(newspaper.structure.get("today", []))
        for cat_ids in newspaper.structure.get("categories", {}).values():
            all_ids.update(cat_ids)

        # Read article should not appear in today's edition
        assert (
            read_article.id not in all_ids
        ), "Read article from previous edition should not appear in new editions"

    @pytest.mark.asyncio
    async def test_per_category_limit_scaling_by_quality(self, db_session, test_user):
        """Verify per-category limits scale based on quality scores."""
        categories_config = [
            ("exceptional", 0.95, 9),  # 0.9+: max 9 articles
            ("high", 0.85, 6),  # 0.8-0.9: max 6 articles
            ("good", 0.75, 4),  # 0.7-0.8: max 4 articles
            ("acceptable", 0.65, 3),  # 0.6-0.7: max 3 articles
        ]

        for slug, score, expected_max in categories_config:
            cat = Category(
                user_id=test_user.id,
                name=slug.title(),
                slug=slug,
                display_order=len(db_session.query(Category).all()),
            )
            db_session.add(cat)
            db_session.commit()

            # Create 15 articles with the same score
            for i in range(15):
                db_session.add(
                    Article(
                        user_id=test_user.id,
                        category_id=cat.id,
                        title=f"{slug} {i}",
                        link=f"https://example.com/{slug}-{i}",
                        published_date=datetime.utcnow(),
                        created_at=datetime.utcnow(),
                        relevance_score=score,
                        summary=f"Summary {i}",
                        is_read=False,
                        is_archived=False,
                        is_duplicate=False,
                    )
                )
            db_session.commit()

        # Generate newspaper
        generator = NewspaperGenerator(db_session)
        newspaper = await generator.generate_newspaper_for_user(test_user.id)

        today_ids = newspaper.structure.get("today", [])

        # Verify limits per category
        from collections import Counter

        articles = db_session.query(Article).filter(Article.id.in_(today_ids)).all()
        by_category = Counter(a.category_id for a in articles)

        categories = (
            db_session.query(Category).filter(Category.user_id == test_user.id).all()
        )
        for cat in categories:
            count = by_category.get(cat.id, 0)
            # Find expected max for this category
            for slug, score, expected_max in categories_config:
                if cat.slug == slug:
                    assert (
                        count <= expected_max
                    ), f"Category {cat.slug} has {count} articles, expected max {expected_max}"
                    break
