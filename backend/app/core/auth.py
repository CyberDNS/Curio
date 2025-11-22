from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.models.user import User
from typing import Optional, Tuple
from datetime import datetime, timedelta, timezone
import logging
import uuid

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour (reduced from 7 days for security)
REFRESH_TOKEN_EXPIRE_DAYS = 7  # 7 days for refresh tokens


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Token payload data
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    # Ensure sub is a string (JWT spec requirement)
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])

    # Use timezone-aware datetime
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # Add standard JWT claims
    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "jti": str(uuid.uuid4()),  # JWT ID for tracking
            "type": "access",
        }
    )

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Create a JWT refresh token with longer expiration.

    Args:
        data: Token payload data

    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])

    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "jti": str(uuid.uuid4()),
            "type": "refresh",
        }
    )

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_token_pair(user_id: int) -> Tuple[str, str]:
    """
    Create both access and refresh tokens for a user.

    Args:
        user_id: User ID to create tokens for

    Returns:
        Tuple of (access_token, refresh_token)
    """
    access_token = create_access_token(data={"sub": user_id})
    refresh_token = create_refresh_token(data={"sub": user_id})
    return access_token, refresh_token


def decode_token(token: str, token_type: str = "access") -> dict:
    """
    Decode and validate JWT token.

    Args:
        token: JWT token to decode
        token_type: Expected token type ('access' or 'refresh')

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or wrong type
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])

        # Verify token type
        if payload.get("type") != token_type:
            logger.warning(
                f"Token type mismatch: expected {token_type}, got {payload.get('type')}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Get the current authenticated user from JWT token (cookie or Authorization header)."""
    token = None

    # Try to get token from cookie first
    token = request.cookies.get("auth_token")

    # Fall back to Authorization header if no cookie
    if not token and credentials:
        token = credentials.credentials

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)

    user_id_str: str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Get the current user if authenticated, otherwise return None."""
    token = request.cookies.get("auth_token")
    if not token and not credentials:
        return None

    try:
        return await get_current_user(request, credentials, db)
    except HTTPException:
        return None
