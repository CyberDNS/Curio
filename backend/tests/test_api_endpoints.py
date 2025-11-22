"""Tests for categories API endpoints."""

import pytest
from app.models.category import Category


@pytest.mark.unit
class TestCategoriesAPI:
    """Test categories API endpoints."""

    def test_get_categories(self, authenticated_client, test_category):
        """Test getting list of categories."""
        response = authenticated_client.get("/api/categories/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["id"] == test_category.id
        assert data[0]["name"] == test_category.name

    def test_get_categories_excludes_deleted(
        self, authenticated_client, db_session, test_user
    ):
        """Test that deleted categories are excluded."""
        # Create deleted category
        deleted_cat = Category(
            user_id=test_user.id,
            name="Deleted Category",
            slug="deleted",
            is_deleted=True,
        )
        db_session.add(deleted_cat)
        db_session.commit()

        response = authenticated_client.get("/api/categories/")

        assert response.status_code == 200
        data = response.json()
        # Should not include deleted category
        assert not any(cat["name"] == "Deleted Category" for cat in data)

    def test_create_category(self, authenticated_client):
        """Test creating a new category."""
        category_data = {
            "name": "Science",
            "slug": "science",
            "description": "Scientific news and discoveries",
        }

        response = authenticated_client.post("/api/categories/", json=category_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Science"
        assert data["description"] == "Scientific news and discoveries"
        assert "slug" in data

    def test_create_duplicate_category(self, authenticated_client, test_category):
        """Test creating category with duplicate name."""
        category_data = {
            "name": test_category.name,  # Same name as existing
            "description": "Duplicate",
        }

        response = authenticated_client.post("/api/categories/", json=category_data)

        # Should fail or handle gracefully
        assert response.status_code in [400, 422]

    def test_update_category(self, authenticated_client, test_category):
        """Test updating a category."""
        update_data = {
            "name": "Updated Technology",
            "description": "Updated description",
        }

        response = authenticated_client.put(
            f"/api/categories/{test_category.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Technology"
        assert data["description"] == "Updated description"

    def test_delete_category_soft_delete(
        self, authenticated_client, test_category, db_session
    ):
        """Test soft deleting a category."""
        response = authenticated_client.delete(f"/api/categories/{test_category.id}")

        assert response.status_code == 200

        # Verify soft delete
        db_session.refresh(test_category)
        assert test_category.is_deleted is True
        assert test_category.deleted_at is not None

    def test_reorder_categories(self, authenticated_client, db_session, test_user):
        """Test reordering categories."""
        # Create multiple categories
        cat1 = Category(user_id=test_user.id, name="Cat1", slug="cat1", display_order=1)
        cat2 = Category(user_id=test_user.id, name="Cat2", slug="cat2", display_order=2)
        cat3 = Category(user_id=test_user.id, name="Cat3", slug="cat3", display_order=3)
        db_session.add_all([cat1, cat2, cat3])
        db_session.commit()

        # Reorder: swap cat1 and cat3
        new_order = [cat3.id, cat2.id, cat1.id]

        response = authenticated_client.post("/api/categories/reorder", json=new_order)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3

    # Note: No GET /categories/{id} endpoint exists, only GET /categories/
    # This test is removed as the endpoint is not implemented

    def test_user_can_only_see_own_categories(self, authenticated_client, db_session):
        """Test that users can only access their own categories."""
        from app.models.user import User

        # Create another user and category
        other_user = User(email="other@example.com", sub="other_cat_123")
        db_session.add(other_user)
        db_session.commit()

        other_category = Category(
            user_id=other_user.id, name="Other Category", slug="other"
        )
        db_session.add(other_category)
        db_session.commit()

        # Should not see other user's category
        response = authenticated_client.get("/api/categories/")
        data = response.json()
        assert not any(cat["name"] == "Other Category" for cat in data)


@pytest.mark.unit
class TestFeedsAPI:
    """Test feeds API endpoints."""

    def test_get_feeds(self, authenticated_client, test_feed):
        """Test getting list of feeds."""
        response = authenticated_client.get("/api/feeds/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["url"] == test_feed.url

    def test_create_feed(self, authenticated_client):
        """Test creating a new feed."""
        feed_data = {"url": "https://example.com/newfeed.xml"}

        response = authenticated_client.post("/api/feeds/", json=feed_data)

        assert response.status_code == 200
        data = response.json()
        assert data["url"] == "https://example.com/newfeed.xml"
        assert data["is_active"] is True

    def test_create_duplicate_feed(self, authenticated_client, test_feed):
        """Test creating feed with duplicate URL."""
        feed_data = {"url": test_feed.url}

        response = authenticated_client.post("/api/feeds/", json=feed_data)

        # Should fail
        assert response.status_code in [400, 422]

    def test_update_feed(self, authenticated_client, test_feed):
        """Test updating a feed."""
        update_data = {"is_active": False, "source_title": "New Source Title"}

        response = authenticated_client.put(
            f"/api/feeds/{test_feed.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
        assert data["source_title"] == "New Source Title"

    def test_delete_feed(self, authenticated_client, test_feed, db_session):
        """Test deleting a feed."""
        response = authenticated_client.delete(f"/api/feeds/{test_feed.id}")

        assert response.status_code == 200

        # Verify feed is deleted
        from app.models.feed import Feed

        deleted_feed = db_session.query(Feed).filter(Feed.id == test_feed.id).first()
        assert deleted_feed is None
