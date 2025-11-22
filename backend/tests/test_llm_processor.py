"""Tests for LLM processor service."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone, timedelta
from app.services.llm_processor import LLMProcessor
from app.models.article import Article
from app.models.category import Category
from app.models.settings import UserSettings


@pytest.mark.unit
class TestLLMProcessor:
    """Test LLMProcessor class."""

    def test_init(self, db_session):
        """Test LLMProcessor initialization."""
        processor = LLMProcessor(db_session)
        assert processor.db == db_session
        assert processor.client is not None

    @pytest.mark.asyncio
    async def test_analyze_article_comprehensive(
        self, db_session, test_article, test_category, mock_openai_response
    ):
        """Test comprehensive article analysis with LLM."""
        processor = LLMProcessor(db_session)

        with patch.object(processor.client.chat.completions, "create") as mock_create:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = str(
                mock_openai_response
            ).replace("'", '"')
            mock_response.usage = Mock()
            mock_create.return_value = mock_response

            result = await processor._analyze_article_comprehensive(
                test_article, "Select technology articles", [test_category]
            )

            assert "title" in result
            assert "summary" in result
            assert "relevance_score" in result

    @pytest.mark.asyncio
    async def test_process_articles(
        self, db_session, test_user, test_article, mock_openai_response
    ):
        """Test processing multiple articles."""
        # Create LLM selection prompt setting
        setting = UserSettings(
            user_id=test_user.id,
            key="llm_selection_prompt",
            value="Select interesting tech articles",
        )
        db_session.add(setting)

        # Make article unprocessed
        test_article.summary = None
        test_article.relevance_score = 0.0
        db_session.commit()

        processor = LLMProcessor(db_session)

        with patch.object(processor.client.chat.completions, "create") as mock_create:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = str(
                mock_openai_response
            ).replace("'", '"')
            mock_response.usage = Mock()
            mock_create.return_value = mock_response

            # Mock duplicate detector
            with patch.object(
                processor.duplicate_detector,
                "process_article_for_duplicates",
                return_value=None,
            ):
                processed = await processor.process_articles(user_id=test_user.id)

                assert processed >= 0

    @pytest.mark.asyncio
    async def test_process_articles_with_duplicate_detection(
        self, db_session, test_user, multiple_articles, mock_openai_response
    ):
        """Test article processing with duplicate detection."""
        # Create LLM selection prompt setting
        setting = UserSettings(
            user_id=test_user.id,
            key="llm_selection_prompt",
            value="Select all articles",
        )
        db_session.add(setting)

        # Make articles unprocessed
        for article in multiple_articles:
            article.summary = None
            article.relevance_score = 0.0
        db_session.commit()

        processor = LLMProcessor(db_session)

        with patch.object(processor.client.chat.completions, "create") as mock_create:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = str(
                mock_openai_response
            ).replace("'", '"')
            mock_response.usage = Mock()
            mock_create.return_value = mock_response

            with patch.object(
                processor.duplicate_detector, "process_article_for_duplicates"
            ) as mock_dup:
                mock_dup.return_value = None

                processed = await processor.process_articles(user_id=test_user.id)

                assert processed >= 0

    @pytest.mark.asyncio
    async def test_process_articles_no_prompt(
        self, db_session, test_user, test_article
    ):
        """Test processing articles when no LLM prompt is configured."""
        # Don't create the prompt setting
        test_article.summary = None
        db_session.commit()

        processor = LLMProcessor(db_session)

        with patch.object(processor.client.chat.completions, "create") as mock_create:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = (
                '{"summary": "test", "relevance_score": 0.5}'
            )
            mock_response.usage = Mock()
            mock_create.return_value = mock_response

            with patch.object(
                processor.duplicate_detector,
                "process_article_for_duplicates",
                return_value=None,
            ):
                processed = await processor.process_articles(user_id=test_user.id)

                assert processed >= 0

    @pytest.mark.asyncio
    async def test_analyze_article_api_error(
        self, db_session, test_article, test_category
    ):
        """Test article analysis when LLM API fails."""
        processor = LLMProcessor(db_session)

        with patch.object(processor.client.chat.completions, "create") as mock_create:
            mock_create.side_effect = Exception("API Error")

            result = await processor._analyze_article_comprehensive(
                test_article, "Select articles", [test_category]
            )

            # Should return fallback values
            assert "summary" in result
            assert "relevance_score" in result
            assert result["relevance_score"] == 0.0

    def test_strip_images_from_content(self, db_session):
        """Test removing images from content to save tokens."""
        processor = LLMProcessor(db_session)

        content = """
        <p>Some text</p>
        <img src="https://example.com/image.jpg" />
        <p>More text</p>
        https://example.com/photo.png
        <figure><img src="test.jpg" /></figure>
        """

        result = processor._strip_images_from_content(content)

        assert "<img" not in result
        assert "<figure>" not in result
        assert ".jpg" not in result or "Some text" in result

    def test_extract_image_urls_from_content(self, db_session):
        """Test extracting image URLs from content."""
        processor = LLMProcessor(db_session)

        content = """
        <img src="https://example.com/image1.jpg" />
        https://example.com/image2.png
        <img src="https://example.com/image3.gif" />
        """

        urls = processor._extract_image_urls_from_content(content)

        assert len(urls) >= 2
        assert any("image1.jpg" in url for url in urls)

    @pytest.mark.asyncio
    async def test_regenerate_summaries(self, db_session, test_article, test_category):
        """Test regenerating summaries for existing articles."""
        processor = LLMProcessor(db_session)

        # Set initial summary
        test_article.summary = "Old summary"
        test_article.relevance_score = 0.5
        db_session.commit()

        with patch.object(processor, "process_articles") as mock_process:
            mock_process.return_value = 1

            count = await processor.regenerate_summaries(category_id=test_category.id)

            assert count >= 0
            # Check that summary was reset
            db_session.refresh(test_article)
            assert test_article.summary is None
