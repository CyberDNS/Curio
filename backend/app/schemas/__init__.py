from app.schemas.feed import Feed, FeedCreate, FeedUpdate
from app.schemas.article import Article, ArticleCreate, ArticleUpdate
from app.schemas.category import Category, CategoryCreate, CategoryUpdate
from app.schemas.settings import UserSettings, UserSettingsCreate, UserSettingsUpdate
from app.schemas.newspaper import (
    Newspaper,
    NewspaperCreate,
    NewspaperUpdate,
    NewspaperStructure,
)

__all__ = [
    "Feed",
    "FeedCreate",
    "FeedUpdate",
    "Article",
    "ArticleCreate",
    "ArticleUpdate",
    "Category",
    "CategoryCreate",
    "CategoryUpdate",
    "UserSettings",
    "UserSettingsCreate",
    "UserSettingsUpdate",
    "Newspaper",
    "NewspaperCreate",
    "NewspaperUpdate",
    "NewspaperStructure",
]
