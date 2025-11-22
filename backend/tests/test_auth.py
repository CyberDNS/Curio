"""Tests for authentication and authorization."""

import pytest
from datetime import datetime, timezone, timedelta
from jose import jwt
from app.core.auth import (
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
    ALGORITHM,
)
from app.core.config import settings


@pytest.mark.unit
class TestAuthentication:
    """Test authentication utilities."""

    def test_create_access_token(self, test_user):
        """Test creating access token."""
        token = create_access_token(data={"sub": test_user.id})

        assert token is not None
        assert isinstance(token, str)

        # Decode and verify
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == str(test_user.id)
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload

    def test_create_access_token_with_custom_expiry(self, test_user):
        """Test creating access token with custom expiration."""
        custom_delta = timedelta(hours=2)
        token = create_access_token(
            data={"sub": test_user.id}, expires_delta=custom_delta
        )

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat_time = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)

        # Check that expiration is roughly 2 hours from issue time
        time_diff = (exp_time - iat_time).total_seconds()
        assert 7100 < time_diff < 7300  # Around 2 hours (allowing small variance)

    def test_create_refresh_token(self, test_user):
        """Test creating refresh token."""
        token = create_refresh_token(data={"sub": test_user.id})

        assert token is not None
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == str(test_user.id)
        assert payload["type"] == "refresh"

    def test_create_token_pair(self, test_user):
        """Test creating access and refresh token pair."""
        access_token, refresh_token = create_token_pair(test_user.id)

        assert access_token is not None
        assert refresh_token is not None

        access_payload = jwt.decode(
            access_token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        refresh_payload = jwt.decode(
            refresh_token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )

        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"
        assert access_payload["sub"] == refresh_payload["sub"]

    def test_decode_token_valid(self, test_user):
        """Test decoding valid token."""
        token = create_access_token(data={"sub": test_user.id})
        payload = decode_token(token, token_type="access")

        assert payload["sub"] == str(test_user.id)
        assert payload["type"] == "access"

    def test_decode_token_wrong_type(self, test_user):
        """Test decoding token with wrong type."""
        token = create_access_token(data={"sub": test_user.id})

        with pytest.raises(Exception):  # Should raise HTTPException
            decode_token(token, token_type="refresh")

    def test_decode_token_expired(self, test_user):
        """Test decoding expired token."""
        # Create token that expires immediately
        token = create_access_token(
            data={"sub": test_user.id},
            expires_delta=timedelta(seconds=-1),  # Already expired
        )

        with pytest.raises(Exception):  # Should raise HTTPException
            decode_token(token)

    def test_decode_token_invalid(self):
        """Test decoding invalid token."""
        with pytest.raises(Exception):
            decode_token("invalid.token.here")

    @pytest.mark.asyncio
    async def test_get_current_user(self, authenticated_client, test_user):
        """Test getting current user from token."""
        response = authenticated_client.get("/health")  # Any endpoint
        assert response.status_code == 200

        # Test with valid auth
        response = authenticated_client.get("/api/articles/")
        # Should not be 401 Unauthorized
        assert response.status_code != 401

    def test_token_contains_security_claims(self, test_user):
        """Test that tokens contain all required security claims."""
        token = create_access_token(data={"sub": test_user.id})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])

        # Check for standard JWT claims
        assert "sub" in payload  # Subject (user ID)
        assert "exp" in payload  # Expiration time
        assert "iat" in payload  # Issued at
        assert "jti" in payload  # JWT ID (for tracking/revocation)
        assert "type" in payload  # Token type (access/refresh)

        # Ensure JTI is unique-looking (UUID format)
        jti = payload["jti"]
        assert len(jti) == 36  # UUID format
        assert jti.count("-") == 4  # UUID has 4 hyphens


@pytest.mark.unit
class TestAuthorizationEndpoints:
    """Test authorization on protected endpoints."""

    def test_protected_endpoint_without_auth(self, client):
        """Test accessing protected endpoint without authentication."""
        response = client.get("/api/articles/")
        assert response.status_code == 401

    def test_protected_endpoint_with_auth(self, authenticated_client):
        """Test accessing protected endpoint with authentication."""
        response = authenticated_client.get("/api/articles/")
        # Should be 200 or other valid response (not 401)
        assert response.status_code != 401

    def test_protected_endpoint_with_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token."""
        client.cookies.set("auth_token", "invalid_token")
        response = client.get("/api/articles/")
        assert response.status_code == 401
