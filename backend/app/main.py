from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
from app.core.config import settings
from app.core.database import engine, Base
from app.api.endpoints import (
    feeds,
    articles,
    categories,
    settings as settings_endpoints,
    actions,
    proxy,
    auth,
    newspapers,
)
from app.services.scheduler import scheduler
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("Starting Curio application...")

    # Security check: Ensure authentication is properly configured
    from app.api.endpoints.auth import OAUTH_CONFIGURED, DEV_MODE_ENABLED

    if not OAUTH_CONFIGURED and not DEV_MODE_ENABLED:
        logger.critical(
            "❌ SECURITY ERROR: Application cannot start without authentication!\n"
            "   Option 1 (Production): Configure OAuth in .env file\n"
            "   Option 2 (Development): Set DEV_MODE=true in .env file\n\n"
            "   WARNING: DEV_MODE bypasses authentication and is INSECURE!"
        )
        raise RuntimeError(
            "Authentication not configured. Set up OAuth or enable DEV_MODE for development."
        )

    if DEV_MODE_ENABLED:
        logger.warning(
            "\n" + "=" * 80 + "\n"
            "⚠️  SECURITY WARNING: DEV_MODE IS ENABLED\n"
            "   Authentication is bypassed - any user can access the application\n"
            "   This mode should NEVER be used in production!\n"
            "=" * 80 + "\n"
        )

    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")

    # Start scheduler
    scheduler.start()

    yield

    # Shutdown
    logger.info("Shutting down Curio application...")
    scheduler.shutdown()


app = FastAPI(
    title="Curio - Personalized News Aggregator",
    description="RSS feed aggregator with LLM-powered content curation",
    version="1.0.0",
    lifespan=lifespan,
)

# Add session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(feeds.router, prefix="/api/feeds", tags=["feeds"])
app.include_router(articles.router, prefix="/api/articles", tags=["articles"])
app.include_router(categories.router, prefix="/api/categories", tags=["categories"])
app.include_router(newspapers.router, prefix="/api/newspapers", tags=["newspapers"])
app.include_router(settings_endpoints.router, prefix="/api/settings", tags=["settings"])
app.include_router(actions.router, prefix="/api/actions", tags=["actions"])
app.include_router(proxy.router, prefix="/api/proxy", tags=["proxy"])

# Mount media files for serving downloaded images
media_path = Path(settings.MEDIA_ROOT)
media_path.mkdir(parents=True, exist_ok=True)
app.mount("/api/media", StaticFiles(directory=str(media_path)), name="media")


@app.get("/")
def root():
    return {
        "name": "Curio",
        "version": "1.0.0",
        "description": "Personalized News Aggregator",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
