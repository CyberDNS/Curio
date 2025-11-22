from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from app.core.database import get_db
from app.core.config import settings
from app.core.auth import (
    create_token_pair,
    create_access_token,
    decode_token,
    get_current_user,
)
from app.models.user import User
from datetime import datetime
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.logging_config import log_security_event, get_client_ip

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Check if OAuth is properly configured
OAUTH_CONFIGURED = (
    settings.OAUTH_SERVER_METADATA_URL
    and not settings.OAUTH_SERVER_METADATA_URL.startswith("https://your-")
)

# Development mode security check
DEV_MODE_ENABLED = settings.DEV_MODE and not OAUTH_CONFIGURED

# Initialize OAuth only if properly configured
if OAUTH_CONFIGURED:
    oauth = OAuth()
    oauth.register(
        name="oidc",
        client_id=settings.OAUTH_CLIENT_ID,
        client_secret=settings.OAUTH_CLIENT_SECRET,
        server_metadata_url=settings.OAUTH_SERVER_METADATA_URL,
        client_kwargs={"scope": "openid email profile"},
    )
elif DEV_MODE_ENABLED:
    logger.warning(
        "⚠️  SECURITY WARNING: Development authentication mode is enabled. "
        "This bypasses all authentication and should NEVER be used in production!"
    )
else:
    logger.error(
        "❌ OAuth is not configured and DEV_MODE is not enabled. "
        "Set DEV_MODE=true in .env for local development, or configure OAuth for production."
    )


@router.get("/login")
@limiter.limit("10/minute")
async def login(request: Request, db: Session = Depends(get_db)):
    """Initiate OAuth2/OIDC login flow."""
    if not OAUTH_CONFIGURED and not DEV_MODE_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Authentication not available. OAuth is not configured and DEV_MODE is not enabled.",
        )

    if DEV_MODE_ENABLED:
        # Development mode - create a mock user and return token directly
        logger.warning("⚠️  Using insecure development authentication bypass")

        client_ip = get_client_ip(request)
        log_security_event(
            event_type="auth.login.dev_mode",
            message="Development mode authentication bypass used",
            level=logging.WARNING,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            request_method="GET",
            request_path="/api/auth/login",
        )

        # Find or create a dev user
        dev_user = db.query(User).filter(User.email == "dev@localhost").first()
        if not dev_user:
            dev_user = User(
                sub="dev-user-local",
                email="dev@localhost",
                name="Development User",
                picture="",
                preferred_username="dev",
                is_active=True,
                last_login=datetime.utcnow(),
            )
            db.add(dev_user)
            db.commit()
            db.refresh(dev_user)
            logger.info("Created development user")

            log_security_event(
                event_type="auth.user.created",
                message="Development user account created",
                user_id=str(dev_user.id),
                username=dev_user.email,
                ip_address=client_ip,
                event_category="authentication",
            )
        else:
            dev_user.last_login = datetime.utcnow()
            db.commit()

        # Create token pair
        access_token, refresh_token = create_token_pair(dev_user.id)

        log_security_event(
            event_type="auth.login.success",
            message="User logged in successfully (dev mode)",
            user_id=str(dev_user.id),
            username=dev_user.email,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            request_method="GET",
            request_path="/api/auth/login",
            event_category="authentication",
            auth_method="dev_mode",
        )

        # Redirect to frontend with tokens in HttpOnly cookies
        frontend_url = (
            settings.CORS_ORIGINS[0]
            if isinstance(settings.CORS_ORIGINS, list)
            else settings.CORS_ORIGINS
        )
        response = RedirectResponse(url=f"{frontend_url}/")

        # Set cookies with environment-aware security settings
        cookie_kwargs = {
            "httponly": True,  # XSS protection
            "secure": settings.COOKIE_SECURE,  # HTTPS only in production
            "samesite": settings.COOKIE_SAMESITE,  # CSRF protection
            "max_age": 60 * 60,  # 1 hour
        }
        if settings.COOKIE_DOMAIN:
            cookie_kwargs["domain"] = settings.COOKIE_DOMAIN

        response.set_cookie(key="auth_token", value=access_token, **cookie_kwargs)

        # Set refresh token cookie (7 days)
        refresh_cookie_kwargs = cookie_kwargs.copy()
        refresh_cookie_kwargs["max_age"] = 60 * 60 * 24 * 7
        response.set_cookie(
            key="refresh_token", value=refresh_token, **refresh_cookie_kwargs
        )

        return response

    # Production OAuth flow
    redirect_uri = settings.OAUTH_REDIRECT_URI
    return await oauth.oidc.authorize_redirect(request, redirect_uri)


@router.get("/callback")
@limiter.limit("20/minute")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    """Handle OAuth2/OIDC callback and create/update user."""
    if not OAUTH_CONFIGURED:
        raise HTTPException(
            status_code=400,
            detail="OAuth not configured. For development, use /login endpoint with DEV_MODE=true",
        )

    try:
        # Get token and user info from OAuth provider
        token = await oauth.oidc.authorize_access_token(request)
        userinfo = token.get("userinfo")

        if not userinfo:
            raise HTTPException(status_code=400, detail="Failed to get user info")

        # Extract user data
        sub = userinfo.get("sub")
        email = userinfo.get("email")
        name = userinfo.get("name", "")
        picture = userinfo.get("picture", "")
        preferred_username = userinfo.get("preferred_username", "")

        if not sub or not email:
            raise HTTPException(
                status_code=400, detail="Missing required user information"
            )

        # Find or create user
        user = db.query(User).filter(User.sub == sub).first()

        client_ip = get_client_ip(request)

        if user:
            # Update existing user
            user.email = email
            user.name = name
            user.picture = picture
            user.preferred_username = preferred_username
            user.last_login = datetime.utcnow()
            logger.info(f"User logged in: {email}")
        else:
            # Create new user
            user = User(
                sub=sub,
                email=email,
                name=name,
                picture=picture,
                preferred_username=preferred_username,
                is_active=True,
                last_login=datetime.utcnow(),
            )
            db.add(user)
            logger.info(f"New user created: {email}")

            log_security_event(
                event_type="auth.user.created",
                message="New user account created via OAuth",
                user_id=str(user.id),
                username=email,
                ip_address=client_ip,
                user_agent=request.headers.get("user-agent"),
                event_category="authentication",
                auth_provider="oauth",
            )

        db.commit()
        db.refresh(user)

        # Create JWT token pair for the user
        access_token, refresh_token = create_token_pair(user.id)

        log_security_event(
            event_type="auth.login.success",
            message="User logged in successfully via OAuth",
            user_id=str(user.id),
            username=user.email,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            request_method="GET",
            request_path="/api/auth/callback",
            event_category="authentication",
            auth_method="oauth",
        )

        # Redirect to frontend with tokens in HttpOnly cookies
        frontend_url = (
            settings.CORS_ORIGINS[0]
            if isinstance(settings.CORS_ORIGINS, list)
            else settings.CORS_ORIGINS
        )
        response = RedirectResponse(url=f"{frontend_url}/")

        # Set cookies with environment-aware security settings
        cookie_kwargs = {
            "httponly": True,  # XSS protection
            "secure": settings.COOKIE_SECURE,  # HTTPS only in production
            "samesite": settings.COOKIE_SAMESITE,  # CSRF protection
            "max_age": 60 * 60,  # 1 hour
        }
        if settings.COOKIE_DOMAIN:
            cookie_kwargs["domain"] = settings.COOKIE_DOMAIN

        response.set_cookie(key="auth_token", value=access_token, **cookie_kwargs)

        # Set refresh token cookie (7 days)
        refresh_cookie_kwargs = cookie_kwargs.copy()
        refresh_cookie_kwargs["max_age"] = 60 * 60 * 24 * 7
        response.set_cookie(
            key="refresh_token", value=refresh_token, **refresh_cookie_kwargs
        )

        return response

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")

        log_security_event(
            event_type="auth.login.failure",
            message=f"OAuth authentication failed: {str(e)}",
            level=logging.ERROR,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            request_method="GET",
            request_path="/api/auth/callback",
            event_category="authentication",
            error_type=type(e).__name__,
        )

        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")


@router.post("/refresh")
@limiter.limit("30/minute")
async def refresh_access_token(request: Request, db: Session = Depends(get_db)):
    """
    Refresh access token using refresh token.

    This endpoint allows clients to get a new access token without re-authenticating.
    The refresh token must be valid and not expired.
    """
    from fastapi.responses import JSONResponse

    # Get refresh token from cookie
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found"
        )

    try:
        # Decode and validate refresh token
        payload = decode_token(refresh_token, token_type="refresh")
        user_id_str = payload.get("sub")

        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        user_id = int(user_id_str)

        # Verify user still exists and is active
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Create new access token (keep same refresh token)
        new_access_token = create_access_token(data={"sub": user_id})

        log_security_event(
            event_type="auth.token.refreshed",
            message="Access token refreshed successfully",
            user_id=user_id,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            request_method="POST",
            request_path="/api/auth/refresh",
            event_category="authentication",
        )

        # Return new access token with secure cookie settings
        response = JSONResponse(content={"message": "Token refreshed successfully"})
        cookie_kwargs = {
            "httponly": True,
            "secure": settings.COOKIE_SECURE,
            "samesite": settings.COOKIE_SAMESITE,
            "max_age": 60 * 60,  # 1 hour
        }
        if settings.COOKIE_DOMAIN:
            cookie_kwargs["domain"] = settings.COOKIE_DOMAIN

        response.set_cookie(key="auth_token", value=new_access_token, **cookie_kwargs)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")

        log_security_event(
            event_type="auth.token.refresh_failed",
            message=f"Token refresh failed: {str(e)}",
            level=logging.WARNING,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            request_method="POST",
            request_path="/api/auth/refresh",
            event_category="authentication",
            error_type=type(e).__name__,
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )


@router.post("/logout")
async def logout(request: Request):
    """Logout endpoint - clears both auth and refresh tokens."""
    # Try to get user info before clearing tokens
    try:
        auth_token = request.cookies.get("auth_token")
        if auth_token:
            payload = decode_token(auth_token)
            user_id = payload.get("sub")
            log_security_event(
                event_type="auth.logout.success",
                message="User logged out successfully",
                user_id=user_id,
                ip_address=get_client_ip(request),
                user_agent=request.headers.get("user-agent"),
                request_method="POST",
                request_path="/api/auth/logout",
                event_category="authentication",
            )
    except Exception:
        # If token is invalid, still proceed with logout
        pass

    response = {"message": "Logged out successfully"}
    from fastapi.responses import JSONResponse

    json_response = JSONResponse(content=response)

    # Delete both cookies
    json_response.delete_cookie(
        key="auth_token",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
    )
    json_response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
    )

    return json_response


@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    logger.debug(
        f"Get user info for user ID: {current_user.id}, email: {current_user.email}"
    )
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "picture": current_user.picture,
        "preferred_username": current_user.preferred_username,
    }


# Debug endpoint removed for security - use proper logging for debugging authentication issues
# If needed for development, enable DEBUG logging level to see authentication details
