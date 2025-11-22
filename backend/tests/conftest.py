"""
Pytest configuration and fixtures for Curio tests.
"""

import pytest
import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.core.config import settings
from app.main import app
from app.models.user import User
from app.models.category import Category
from app.models.feed import Feed
from app.models.article import Article
from app.core.auth import create_access_token


# Use in-memory SQLite database for tests
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_engine():
    """Create a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=db_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def test_app(db_session):
    """Create a FastAPI test app without lifespan events."""
    from fastapi import FastAPI
    from app.api.endpoints import categories, feeds, articles, newspapers, auth
    from app.core.config import settings

    # Create app without lifespan to avoid event loop issues
    test_app = FastAPI(title="Curio - Test", version="1.0.0")

    # Include all routers
    test_app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    test_app.include_router(
        categories.router, prefix="/api/categories", tags=["categories"]
    )
    test_app.include_router(feeds.router, prefix="/api/feeds", tags=["feeds"])
    test_app.include_router(articles.router, prefix="/api/articles", tags=["articles"])
    test_app.include_router(
        newspapers.router, prefix="/api/newspapers", tags=["newspapers"]
    )

    # Add health endpoint for testing
    @test_app.get("/health")
    def health():
        return {"status": "ok"}

    # Override database dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    test_app.dependency_overrides[get_db] = override_get_db

    return test_app


@pytest.fixture(scope="function")
def client(test_app) -> TestClient:
    """Create a test client without entering context manager."""
    return TestClient(test_app, raise_server_exceptions=False)


@pytest.fixture(scope="function")
def test_user(db_session) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com", sub="test_oauth_123", name="Test User", is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(test_user) -> dict:
    """Create authentication headers for test requests."""
    access_token = create_access_token(data={"sub": test_user.id})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture(scope="function")
def authenticated_client(client, test_user) -> TestClient:
    """Create an authenticated test client."""
    access_token = create_access_token(data={"sub": test_user.id})
    client.cookies.set("auth_token", access_token)
    return client


@pytest.fixture(scope="function")
def test_category(db_session, test_user) -> Category:
    """Create a test category."""
    category = Category(
        user_id=test_user.id,
        name="Technology",
        slug="technology",
        description="Tech news and updates",
        display_order=1,
        is_deleted=False,
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


@pytest.fixture(scope="function")
def test_feed(db_session, test_user) -> Feed:
    """Create a test feed."""
    feed = Feed(
        user_id=test_user.id,
        url="https://example.com/feed.xml",
        title="Example Feed",
        description="A test feed",
        is_active=True,
        source_title="Example News",
    )
    db_session.add(feed)
    db_session.commit()
    db_session.refresh(feed)
    return feed


@pytest.fixture(scope="function")
def test_article(db_session, test_user, test_feed, test_category) -> Article:
    """Create a test article."""
    from datetime import datetime, timezone

    article = Article(
        user_id=test_user.id,
        feed_id=test_feed.id,
        category_id=test_category.id,
        title="Test Article",
        link="https://example.com/article-1",
        description="This is a test article description",
        content="Full article content goes here",
        author="Test Author",
        published_date=datetime.now(timezone.utc),
        llm_title="Enhanced Test Article",
        llm_subtitle="An AI-enhanced subtitle",
        llm_summary="AI-generated summary of the article",
        summary="Test summary",
        relevance_score=0.75,
        is_read=False,
        is_archived=False,
    )
    db_session.add(article)
    db_session.commit()
    db_session.refresh(article)
    return article


@pytest.fixture(scope="function")
def multiple_articles(db_session, test_user, test_feed, test_category) -> list[Article]:
    """Create multiple test articles."""
    from datetime import datetime, timezone, timedelta

    articles = []
    for i in range(5):
        article = Article(
            user_id=test_user.id,
            feed_id=test_feed.id,
            category_id=test_category.id,
            title=f"Test Article {i+1}",
            link=f"https://example.com/article-{i+1}",
            description=f"Description for article {i+1}",
            content=f"Content for article {i+1}",
            published_date=datetime.now(timezone.utc) - timedelta(hours=i),
            relevance_score=0.5 + (i * 0.1),
            is_read=False,
            is_archived=False,
        )
        db_session.add(article)
        articles.append(article)

    db_session.commit()
    for article in articles:
        db_session.refresh(article)

    return articles


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    return {
        "title": "Enhanced Article Title",
        "subtitle": "An engaging subtitle",
        "summary": "A comprehensive summary of the article content.",
        "category_id": 1,
        "relevance_score": 0.85,
    }


@pytest.fixture
def mock_rss_feed_data():
    """Mock RSS feed data."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Test Feed</title>
        <link>https://example.com</link>
        <description>A test RSS feed</description>
        <item>
            <title>Test Article 1</title>
            <link>https://example.com/article1</link>
            <description>Description of article 1</description>
            <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
            <author>Test Author</author>
        </item>
        <item>
            <title>Test Article 2</title>
            <link>https://example.com/article2</link>
            <description>Description of article 2</description>
            <pubDate>Tue, 02 Jan 2024 12:00:00 GMT</pubDate>
        </item>
    </channel>
</rss>
"""


# Environment setup for tests
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment variables."""
    test_env = {
        "OPENAI_API_KEY": "test_key_123",
        "SECRET_KEY": "test_secret_key_for_testing_only",
        "POSTGRES_PASSWORD": "test_password",
        "DEV_MODE": "true",  # Enable dev mode for testing
        "COOKIE_SECURE": "false",  # Disable secure cookies for tests
    }
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
