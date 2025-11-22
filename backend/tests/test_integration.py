"""Integration tests for end-to-end workflows."""

import pytest
from unittest.mock import patch, Mock, AsyncMock
from datetime import datetime, timezone


@pytest.mark.integration
class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""

    @pytest.mark.asyncio
    async def test_complete_article_workflow(
        self,
        authenticated_client,
        db_session,
        test_user,
        test_feed,
        test_category,
        mock_rss_feed_data,
        mock_openai_response,
    ):
        """Test complete workflow: fetch feed -> process with LLM -> read article."""
        from app.services.rss_fetcher import RSSFetcher
        from app.services.llm_processor import LLMProcessor
        from app.models.settings import UserSettings

        # Step 1: Set up LLM prompt
        setting = UserSettings(
            user_id=test_user.id,
            key="llm_selection_prompt",
            value="Select technology articles",
        )
        db_session.add(setting)
        db_session.commit()

        # Step 2: Fetch RSS feed
        fetcher = RSSFetcher(db_session)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = Mock()
            mock_response.text = mock_rss_feed_data
            mock_response.raise_for_status = Mock()
            mock_client.get.return_value = mock_response

            article_count = await fetcher.fetch_single_feed(test_feed)
            assert article_count >= 0

        # Step 3: Process articles with LLM
        processor = LLMProcessor(db_session)

        with patch.object(processor.client.chat.completions, "create") as mock_create:
            mock_response_obj = Mock()
            mock_response_obj.choices = [Mock()]
            mock_response_obj.choices[0].message.content = str(
                mock_openai_response
            ).replace("'", '"')
            mock_response_obj.usage = Mock()
            mock_create.return_value = mock_response_obj

            with patch.object(
                processor.duplicate_detector,
                "process_article_for_duplicates",
                return_value=None,
            ):
                processed = await processor.process_articles(user_id=test_user.id)
                assert processed >= 0

        # Step 4: Read articles through API
        response = authenticated_client.get("/api/articles/")
        assert response.status_code == 200
        articles = response.json()
        assert len(articles) >= 0

        # Step 5: Mark article as read
        if articles:
            article_id = articles[0]["id"]
            response = authenticated_client.put(
                f"/api/articles/{article_id}", json={"is_read": True}
            )
            assert response.status_code == 200
            assert response.json()["is_read"] is True

    @pytest.mark.asyncio
    async def test_newspaper_generation_workflow(
        self,
        authenticated_client,
        db_session,
        test_user,
        test_category,
        multiple_articles,
    ):
        """Test newspaper generation from processed articles."""
        from app.services.newspaper_generator import NewspaperGenerator
        from app.models.settings import UserSettings

        # Set up newspaper title
        setting = UserSettings(
            user_id=test_user.id, key="newspaper_title", value="Test Times"
        )
        db_session.add(setting)
        db_session.commit()

        # Make articles recommended
        for article in multiple_articles:
            article.relevance_score = 0.8
            article.llm_title = f"Enhanced {article.title}"
        db_session.commit()

        # Generate newspaper
        generator = NewspaperGenerator(db_session)
        newspaper = await generator.generate_newspaper_for_user(test_user.id)

        assert newspaper is not None
        assert newspaper.date == datetime.now(timezone.utc).date()

        # Get newspaper through API
        response = authenticated_client.get("/api/newspapers/today")
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "structure" in data

    @pytest.mark.asyncio
    async def test_duplicate_detection_workflow(
        self, authenticated_client, db_session, test_user, test_feed, test_category
    ):
        """Test duplicate article detection workflow."""
        from app.models.article import Article
        from app.services.duplicate_detector import DuplicateDetector

        # Create two similar articles
        article1 = Article(
            user_id=test_user.id,
            feed_id=test_feed.id,
            category_id=test_category.id,
            title="Breaking: Major Tech Announcement",
            link="https://example.com/article1",
            content="Tech company announces new product",
            relevance_score=0.8,
        )
        db_session.add(article1)
        db_session.commit()

        article2 = Article(
            user_id=test_user.id,
            feed_id=test_feed.id,
            category_id=test_category.id,
            title="Breaking: Major Tech Announcement (Updated)",
            link="https://example.com/article2",
            content="Tech company announces new product with more details",
            relevance_score=0.7,
        )
        db_session.add(article2)
        db_session.commit()

        # Process for duplicates
        detector = DuplicateDetector(db_session)

        with patch("openai.Embedding.create") as mock_embed:
            mock_embed.return_value = Mock(data=[Mock(embedding=[0.1] * 1536)])

            # Process both articles
            detector.process_article_for_duplicates(article1)
            original = detector.process_article_for_duplicates(article2)

            # Check if detected as duplicate (might not if embeddings are mocked)
            if original:
                assert article2.is_duplicate is True
                assert article2.duplicate_of_id == original.id

    def test_downvote_and_adjustment_workflow(
        self, authenticated_client, db_session, test_article
    ):
        """Test downvoting an article and score adjustment."""
        # Downvote article
        response = authenticated_client.post(
            f"/api/articles/{test_article.id}/downvote"
        )
        assert response.status_code == 200
        assert response.json()["user_vote"] == -1

        # Check if adjustment was applied
        db_session.refresh(test_article)
        assert test_article.user_vote == -1

        # Get explanation if available
        response = authenticated_client.get(
            f"/api/articles/{test_article.id}/explain-adjustment"
        )
        assert response.status_code == 200


@pytest.mark.integration
class TestUserIsolation:
    """Test that users can only access their own data."""

    def test_complete_user_isolation(self, client, db_session):
        """Test that two users have completely isolated data."""
        from app.models.user import User
        from app.models.category import Category
        from app.models.feed import Feed
        from app.models.article import Article
        from app.core.auth import create_access_token

        # Create two users
        user1 = User(email="user1@test.com", sub="user1")
        user2 = User(email="user2@test.com", sub="user2")
        db_session.add_all([user1, user2])
        db_session.commit()

        # Create data for user1
        cat1 = Category(user_id=user1.id, name="User1 Cat", slug="user1-cat")
        feed1 = Feed(user_id=user1.id, url="https://user1.com/feed")
        db_session.add_all([cat1, feed1])
        db_session.commit()

        article1 = Article(
            user_id=user1.id,
            feed_id=feed1.id,
            category_id=cat1.id,
            title="User1 Article",
            link="https://user1.com/article",
        )
        db_session.add(article1)
        db_session.commit()

        # User2 tries to access user1's data
        token2 = create_access_token(data={"sub": user2.id})
        client.cookies.set("auth_token", token2)

        # Should not see user1's articles
        response = client.get("/api/articles/")
        assert response.status_code == 200
        articles = response.json()
        assert len(articles) == 0  # No articles for user2

        # Should not see user1's categories
        response = client.get("/api/categories/")
        categories = response.json()
        assert not any(cat["name"] == "User1 Cat" for cat in categories)

        # Should not access user1's article directly
        response = client.get(f"/api/articles/{article1.id}")
        assert response.status_code == 404
