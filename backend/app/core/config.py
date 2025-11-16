from pydantic_settings import BaseSettings
from typing import List, Union
from pydantic import field_validator


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # LLM
    OPENAI_API_KEY: str
    LLM_MODEL: str = "gpt-4-turbo-preview"

    # Embeddings for duplicate detection
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    DUPLICATE_SIMILARITY_THRESHOLD: float = 0.85

    # Application
    SECRET_KEY: str
    DEBUG: bool = False
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            # Split by comma or keep as single item
            return [origin.strip() for origin in v.split(",")]
        return v

    # RSS
    RSS_FETCH_INTERVAL: int = 60  # minutes

    # Storage
    MEDIA_ROOT: str = (
        "./media"  # Path for media storage (use /app/media in production container)
    )

    # OAuth2 / OpenID Connect
    OAUTH_CLIENT_ID: str
    OAUTH_CLIENT_SECRET: str
    OAUTH_SERVER_METADATA_URL: str
    OAUTH_REDIRECT_URI: str

    # Cookie Security
    COOKIE_SECURE: bool = True  # Set to False for local development without HTTPS

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env


settings = Settings()
