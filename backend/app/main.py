from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from contextlib import asynccontextmanager
from pathlib import Path
from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging_config import (
    setup_security_logging,
    CorrelationIdMiddleware,
    log_security_event,
)
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
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import logging

# Configure structured JSON logging
security_logger = setup_security_logging()
logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # HTTP Strict Transport Security (HSTS)
        if settings.ENABLE_HSTS and settings.is_production:
            hsts_value = f"max-age={settings.HSTS_MAX_AGE}"
            if settings.HSTS_INCLUDE_SUBDOMAINS:
                hsts_value += "; includeSubDomains"
            if settings.HSTS_PRELOAD:
                hsts_value += "; preload"
            response.headers["Strict-Transport-Security"] = hsts_value

        # X-Content-Type-Options: Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options: Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # X-XSS-Protection: Enable browser XSS filter (legacy)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy: Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content-Security-Policy: Defense in depth
        # Note: This is a basic policy. Adjust based on your needs.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )

        # Permissions-Policy: Restrict browser features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=()"
        )

        return response


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


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

# Add correlation ID middleware (first, so all logs have correlation IDs)
app.add_middleware(CorrelationIdMiddleware)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# Log application startup as security event
log_security_event(
    event_type="app.startup",
    message=f"Curio application starting (production={settings.is_production})",
    event_category="system",
    production=settings.is_production,
    debug=settings.DEBUG,
    dev_mode=settings.DEV_MODE,
)

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
