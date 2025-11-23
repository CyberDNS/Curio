from pydantic_settings import BaseSettings
from typing import List, Union, Optional
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

    # LLM Rate Limiting & Parallelization
    LLM_MAX_CONCURRENT: int = 5  # Max concurrent LLM API calls
    LLM_TPM_LIMIT: int = 90000  # Tokens per minute limit (adjust per your tier)
    LLM_MAX_INPUT_TOKENS: int = 2000  # Max tokens to send per request

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

    # File Upload Security
    MAX_IMAGE_SIZE: int = 10 * 1024 * 1024  # 10MB per image
    MAX_TOTAL_STORAGE: int = 1024 * 1024 * 1024  # 1GB total storage
    ALLOWED_IMAGE_TYPES: List[str] = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/svg+xml",
    ]

    # OAuth2 / OpenID Connect
    OAUTH_CLIENT_ID: str
    OAUTH_CLIENT_SECRET: str
    OAUTH_SERVER_METADATA_URL: str
    OAUTH_REDIRECT_URI: str

    # Cookie Security
    COOKIE_SECURE: bool = True  # Set to False for local development without HTTPS
    COOKIE_SAMESITE: str = "lax"  # Options: "strict", "lax", "none"
    COOKIE_DOMAIN: Optional[str] = None  # Optional: restrict cookies to specific domain
    ENABLE_HSTS: bool = True  # HTTP Strict Transport Security
    HSTS_MAX_AGE: int = 31536000  # 1 year in seconds
    HSTS_INCLUDE_SUBDOMAINS: bool = True  # Apply HSTS to all subdomains
    HSTS_PRELOAD: bool = False  # Submit to browser HSTS preload lists

    @property
    def is_production(self) -> bool:
        """Detect if running in production environment."""
        # Production indicators:
        # 1. COOKIE_SECURE is True (requires HTTPS)
        # 2. Not in DEBUG mode
        # 3. Not in DEV_MODE
        # 4. OAUTH is properly configured
        return self.COOKIE_SECURE and not self.DEBUG and not self.DEV_MODE

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env


settings = Settings()
