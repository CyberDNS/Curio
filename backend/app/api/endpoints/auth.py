from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from app.core.database import get_db
from app.core.config import settings
from app.core.auth import create_access_token, get_current_user
from app.models.user import User
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Check if OAuth is properly configured
OAUTH_CONFIGURED = (
    settings.OAUTH_SERVER_METADATA_URL
    and not settings.OAUTH_SERVER_METADATA_URL.startswith("https://your-")
)

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
else:
    logger.warning("OAuth not configured - using development mock authentication")


@router.get("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    """Initiate OAuth2/OIDC login flow."""
    if not OAUTH_CONFIGURED:
        # Development mode - create a mock user and return token directly
        logger.info("Using development mock authentication")

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
        else:
            dev_user.last_login = datetime.utcnow()
            db.commit()

        # Create token
        access_token = create_access_token(data={"sub": dev_user.id})

        # Redirect to frontend with token in HttpOnly cookie
        frontend_url = (
            settings.CORS_ORIGINS[0]
            if isinstance(settings.CORS_ORIGINS, list)
            else settings.CORS_ORIGINS
        )
        response = RedirectResponse(url=f"{frontend_url}/")
        response.set_cookie(
            key="auth_token",
            value=access_token,
            httponly=True,  # Not accessible via JavaScript
            secure=settings.COOKIE_SECURE,  # Only sent over HTTPS in production
            samesite="lax",  # CSRF protection
            max_age=60 * 60 * 24 * 7,  # 7 days
        )
        return response

    # Production OAuth flow
    redirect_uri = settings.OAUTH_REDIRECT_URI
    return await oauth.oidc.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    """Handle OAuth2/OIDC callback and create/update user."""
    if not OAUTH_CONFIGURED:
        raise HTTPException(
            status_code=400, detail="OAuth not configured - use /login for dev mode"
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

        db.commit()
        db.refresh(user)

        # Create JWT token for the user
        access_token = create_access_token(data={"sub": user.id})

        # Redirect to frontend with token in HttpOnly cookie
        frontend_url = (
            settings.CORS_ORIGINS[0]
            if isinstance(settings.CORS_ORIGINS, list)
            else settings.CORS_ORIGINS
        )
        response = RedirectResponse(url=f"{frontend_url}/")
        response.set_cookie(
            key="auth_token",
            value=access_token,
            httponly=True,  # Not accessible via JavaScript
            secure=settings.COOKIE_SECURE,  # Only sent over HTTPS in production
            samesite="lax",  # CSRF protection
            max_age=60 * 60 * 24 * 7,  # 7 days
        )
        return response

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")


@router.post("/logout")
async def logout():
    """Logout endpoint - clears the auth cookie."""
    response = {"message": "Logged out successfully"}
    from fastapi.responses import JSONResponse

    json_response = JSONResponse(content=response)
    json_response.delete_cookie(
        key="auth_token",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
    )
    return json_response


@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    logger.info(
        f"Get user info for user ID: {current_user.id}, email: {current_user.email}"
    )
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "picture": current_user.picture,
        "preferred_username": current_user.preferred_username,
    }


@router.get("/debug/token")
async def debug_token(request: Request):
    """Debug endpoint to check token in request."""
    auth_header = request.headers.get("Authorization")
    logger.info(f"Authorization header: {auth_header}")
    return {
        "has_auth_header": auth_header is not None,
        "auth_header": auth_header,
        "all_headers": dict(request.headers),
    }
