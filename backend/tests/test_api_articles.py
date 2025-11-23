"""Tests for articles API endpoints."""

import pytest
from datetime import datetime, timezone, timedelta
from app.models.article import Article


@pytest.mark.unit
class TestArticlesAPI:
    """Test articles API endpoints."""

    def test_get_articles_list(self, authenticated_client, test_article):
        """Test getting list of articles."""
        response = authenticated_client.get("/api/articles/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["id"] == test_article.id

    def test_get_articles_with_category_filter(
        self, authenticated_client, test_article, test_category
    ):
        """Test filtering articles by category."""
        response = authenticated_client.get(
            "/api/articles/", params={"category_id": test_category.id}
        )

        assert response.status_code == 200
        data = response.json()
        assert all(article["category_id"] == test_category.id for article in data)

    def test_get_articles_selected_only(self, authenticated_client, test_article):
        """Test filtering for selected/recommended articles."""
        # Make article recommended (score >= 0.6)
        test_article.relevance_score = 0.8
        authenticated_client.app.dependency_overrides

        response = authenticated_client.get(
            "/api/articles/", params={"selected_only": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert all(article["relevance_score"] >= 0.6 for article in data)

    def test_get_articles_unread_only(
        self, authenticated_client, multiple_articles, db_session
    ):
        """Test filtering for unread articles."""
        # Mark some as read
        multiple_articles[0].is_read = True
        multiple_articles[1].is_read = True
        db_session.commit()

        response = authenticated_client.get(
            "/api/articles/", params={"unread_only": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert all(not article["is_read"] for article in data)

    def test_get_articles_with_days_back(
        self, authenticated_client, db_session, test_user, test_feed, test_category
    ):
        """Test filtering articles by date."""
        # Create old article
        old_article = Article(
            user_id=test_user.id,
            feed_id=test_feed.id,
            category_id=test_category.id,
            title="Old Article",
            link="https://example.com/old",
            published_date=datetime.now(timezone.utc) - timedelta(days=10),
        )
        db_session.add(old_article)

        # Create recent article
        recent_article = Article(
            user_id=test_user.id,
            feed_id=test_feed.id,
            category_id=test_category.id,
            title="Recent Article",
            link="https://example.com/recent",
            published_date=datetime.now(timezone.utc),
        )
        db_session.add(recent_article)
        db_session.commit()

        response = authenticated_client.get("/api/articles/", params={"days_back": 3})

        assert response.status_code == 200
        data = response.json()
        # Should only include recent article
        assert any(a["title"] == "Recent Article" for a in data)

    def test_get_articles_balanced_mode(self, authenticated_client, multiple_articles):
        """Test balanced mode for Today page."""
        # Make all articles recommended
        for article in multiple_articles:
            article.relevance_score = 0.7
        authenticated_client.app.dependency_overrides

        response = authenticated_client.get(
            "/api/articles/", params={"balanced": True, "selected_only": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_single_article(self, authenticated_client, test_article):
        """Test getting a single article."""
        response = authenticated_client.get(f"/api/articles/{test_article.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_article.id
        assert data["title"] == test_article.title

    def test_get_nonexistent_article(self, authenticated_client):
        """Test getting article that doesn't exist."""
        response = authenticated_client.get("/api/articles/99999")
        assert response.status_code == 404

    def test_update_article(self, authenticated_client, test_article):
        """Test updating article status."""
        response = authenticated_client.put(
            f"/api/articles/{test_article.id}",
            json={"is_read": True, "is_archived": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_read"] is True
        assert data["is_archived"] is False

    def test_mark_all_read(self, authenticated_client, multiple_articles):
        """Test marking all articles as read."""
        response = authenticated_client.post("/api/articles/mark-all-read")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"].endswith("articles as read")

    def test_mark_all_read_by_category(
        self, authenticated_client, multiple_articles, test_category
    ):
        """Test marking all articles in a category as read."""
        response = authenticated_client.post(
            "/api/articles/mark-all-read", params={"category_id": test_category.id}
        )

        assert response.status_code == 200

    def test_downvote_article(self, authenticated_client, test_article):
        """Test downvoting an article."""
        response = authenticated_client.post(
            f"/api/articles/{test_article.id}/downvote"
        )

        assert response.status_code == 200
        data = response.json()
        assert "user_vote" in data
        assert data["user_vote"] == -1

    def test_downvote_toggle(self, authenticated_client, test_article, db_session):
        """Test toggling downvote on/off."""
        # First downvote
        test_article.user_vote = -1
        db_session.commit()

        # Second downvote should remove it
        response = authenticated_client.post(
            f"/api/articles/{test_article.id}/downvote"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_vote"] == 0

    def test_get_related_articles(
        self,
        authenticated_client,
        db_session,
        test_article,
        test_user,
        test_feed,
        test_category,
    ):
        """Test getting related/duplicate articles."""
        # Create duplicate article
        duplicate = Article(
            user_id=test_user.id,
            feed_id=test_feed.id,
            category_id=test_category.id,
            title="Duplicate Article",
            link="https://example.com/duplicate",
            is_duplicate=True,
            duplicate_of_id=test_article.id,
        )
        db_session.add(duplicate)
        db_session.commit()

        response = authenticated_client.get(f"/api/articles/{test_article.id}/related")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(a["id"] == duplicate.id for a in data)

    def test_explain_score_adjustment(
        self, authenticated_client, test_article, db_session
    ):
        """Test getting score adjustment explanation."""
        # Set up adjusted score
        test_article.adjusted_relevance_score = 0.4
        test_article.score_adjustment_reason = "Similar to downvoted content"
        db_session.commit()

        response = authenticated_client.get(
            f"/api/articles/{test_article.id}/explain-adjustment"
        )

        assert response.status_code == 200
        data = response.json()
        assert "explanation" in data
        assert "has_adjustment" in data
        assert "key_points" in data
        assert "similarity_score" in data
        assert "similar_article_title" in data

    def test_articles_require_authentication(self, client):
        """Test that articles endpoints require authentication."""
        response = client.get("/api/articles/")
        assert response.status_code == 401

    def test_user_can_only_see_own_articles(
        self, authenticated_client, db_session, test_feed, test_category
    ):
        """Test that users can only access their own articles."""
        from app.models.user import User

        # Create another user and article
        other_user = User(email="other@example.com", sub="other_123")
        db_session.add(other_user)
        db_session.commit()

        other_article = Article(
            user_id=other_user.id,
            feed_id=test_feed.id,
            category_id=test_category.id,
            title="Other User Article",
            link="https://example.com/other",
        )
        db_session.add(other_article)
        db_session.commit()

        # Try to access other user's article
        response = authenticated_client.get(f"/api/articles/{other_article.id}")
        assert response.status_code == 404  # Should not find it
