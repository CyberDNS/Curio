from pydantic_settings import BaseSettings
from typing import List, Union
from pydantic import field_validator


class Settings(BaseSettings):
    # Database
    POSTGRES_USER: str = "curio"
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "curio"

    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL from components."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # LLM
    OPENAI_API_KEY: str
    LLM_MODEL: str = "gpt-5-nano"

    # Embeddings for duplicate detection
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    DUPLICATE_SIMILARITY_THRESHOLD: float = 0.85

    # Downvote filtering
    DOWNVOTE_SIMILARITY_THRESHOLD: float = (
        0.80  # Similarity threshold to trigger penalty
    )
    DOWNVOTE_MAX_PENALTY: float = 0.4  # Maximum score reduction (0.0 to 1.0)

    # Application
    SECRET_KEY: str
    DEBUG: bool = False
    DEV_MODE: bool = False  # Enables development authentication bypass (INSECURE)
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
