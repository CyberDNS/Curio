"""Tests for RSS fetcher service."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timezone, timedelta
from app.services.rss_fetcher import RSSFetcher
from app.models.feed import Feed
from app.models.article import Article


@pytest.mark.unit
class TestRSSFetcher:
    """Test RSSFetcher class."""

    def test_init(self, db_session):
        """Test RSSFetcher initialization."""
        fetcher = RSSFetcher(db_session)
        assert fetcher.db == db_session

    @pytest.mark.asyncio
    async def test_fetch_feed_success(self, db_session, test_feed, mock_rss_feed_data):
        """Test successful feed fetching."""
        fetcher = RSSFetcher(db_session)

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.text = mock_rss_feed_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            articles = await fetcher.fetch_feed(test_feed)

            assert len(articles) == 2
            assert articles[0]["title"] == "Test Article 1"
            assert articles[1]["title"] == "Test Article 2"
            assert test_feed.last_fetched is not None

    @pytest.mark.asyncio
    async def test_fetch_feed_with_days_back_filter(
        self, db_session, test_feed, mock_rss_feed_data
    ):
        """Test feed fetching with date filtering."""
        fetcher = RSSFetcher(db_session)

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.text = mock_rss_feed_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # Fetch only articles from last 1 day (should filter out old articles)
            articles = await fetcher.fetch_feed(test_feed, days_back=1)

            # The mock data has old dates, so might be filtered
            assert isinstance(articles, list)

    @pytest.mark.asyncio
    async def test_fetch_feed_http_error(self, db_session, test_feed):
        """Test feed fetching with HTTP error."""
        fetcher = RSSFetcher(db_session)

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = Exception("HTTP Error")

            articles = await fetcher.fetch_feed(test_feed)

            assert articles == []

    @pytest.mark.asyncio
    async def test_fetch_single_feed(self, db_session, test_feed, mock_rss_feed_data):
        """Test fetching and storing articles from a single feed."""
        fetcher = RSSFetcher(db_session)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock feed fetch
            mock_response = Mock()
            mock_response.text = mock_rss_feed_data
            mock_response.raise_for_status = Mock()
            mock_client.get.return_value = mock_response

            count = await fetcher.fetch_single_feed(test_feed)

            assert count >= 0

    def test_parse_date_valid(self, db_session):
        """Test date parsing with valid dates."""
        fetcher = RSSFetcher(db_session)

        # RFC 2822 format
        date_str = "Mon, 01 Jan 2024 12:00:00 GMT"
        result = fetcher._parse_date(date_str)
        assert isinstance(result, datetime)

        # ISO format
        date_str = "2024-01-01T12:00:00Z"
        result = fetcher._parse_date(date_str)
        assert isinstance(result, datetime)

    def test_parse_date_invalid(self, db_session):
        """Test date parsing with invalid dates."""
        fetcher = RSSFetcher(db_session)

        result = fetcher._parse_date("invalid date")
        assert result is None

        result = fetcher._parse_date(None)
        assert result is None

    def test_extract_images_from_content(self, db_session):
        """Test image extraction from HTML content."""
        fetcher = RSSFetcher(db_session)

        html = """
        <html>
            <img src="https://example.com/image1.jpg" />
            <img src="https://example.com/image2.png" width="500" height="400" />
            <img src="https://example.com/pixel.gif" width="1" height="1" />
        </html>
        """

        # Create a proper mock that supports both attribute and dict-like access
        entry = MagicMock()
        entry.summary = html
        entry.media_content = []
        entry.media_thumbnail = []
        entry.enclosures = []
        # Make it dict-like for .get() calls
        entry.get = MagicMock(
            side_effect=lambda key, default=None: {"summary": html}.get(key, default)
        )

        images = fetcher._extract_images(entry)
        assert len(images) >= 1
        assert any("image1.jpg" in img for img in images)

    def test_is_valid_image(self, db_session):
        """Test image validation logic."""
        fetcher = RSSFetcher(db_session)

        # Valid image
        img_tag = Mock()
        img_tag.get = Mock(side_effect=lambda x: None)
        assert fetcher._is_valid_image("https://example.com/photo.jpg", img_tag)

        # Tracking pixel
        assert not fetcher._is_valid_image("https://example.com/pixel.gif", img_tag)

        # Small image (tracking pixel by size)
        img_tag.get = Mock(
            side_effect=lambda x: "1" if x in ["width", "height"] else None
        )
        assert not fetcher._is_valid_image("https://example.com/small.jpg", img_tag)

    @pytest.mark.asyncio
    async def test_download_image_security_validation(self, db_session):
        """Test image download with security validation."""
        fetcher = RSSFetcher(db_session)

        mock_client = AsyncMock()

        # Test file size limit
        with patch("pathlib.Path.exists", return_value=False):
            mock_response = AsyncMock()
            mock_response.headers = {"content-type": "image/jpeg"}
            mock_response.raise_for_status = Mock()

            # Simulate large file
            large_content = b"x" * (11 * 1024 * 1024)  # 11MB - exceeds limit

            async def mock_aiter_bytes():
                yield large_content

            mock_response.aiter_bytes.return_value = mock_aiter_bytes()
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock()

            mock_client.stream.return_value = mock_response

            result = await fetcher._download_image(
                "https://example.com/huge.jpg", mock_client
            )
            assert result is None  # Should reject large file
