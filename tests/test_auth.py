"""Tests for Firebase Authentication, token verification, and security edge cases."""

from unittest.mock import patch
import pytest
from firebase_admin import auth as firebase_auth
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_missing_header_rejected(async_client: AsyncClient):
    """Ensure requests without an Authorization header are rejected with 401."""
    response = await async_client.get("/api/v1/profiles/me")
    assert response.status_code == 401
    assert "Authentication required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_auth_invalid_header_scheme(async_client: AsyncClient):
    """Ensure non-Bearer authorization schemes are rejected with 401."""
    response = await async_client.get(
        "/api/v1/profiles/me",
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_empty_bearer_token(async_client: AsyncClient):
    """Ensure empty Bearer tokens are rejected with 401."""
    response = await async_client.get(
        "/api/v1/profiles/me",
        headers={"Authorization": "Bearer "},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_invalid_token_rejected(async_client: AsyncClient):
    """Ensure invalid Firebase tokens trigger 401 Invalid Token."""
    with patch(
        "app.core.auth.firebase_auth.verify_id_token",
        side_effect=firebase_auth.InvalidIdTokenError("Invalid token signature"),
    ):
        response = await async_client.get(
            "/api/v1/profiles/me",
            headers={"Authorization": "Bearer invalid_signature_token"},
        )
        assert response.status_code == 401
        assert "Invalid Firebase ID token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_auth_expired_token_rejected(async_client: AsyncClient):
    """Ensure expired Firebase tokens trigger 401 Expired Token."""
    with patch(
        "app.core.auth.firebase_auth.verify_id_token",
        side_effect=firebase_auth.ExpiredIdTokenError(
            "Token has expired",
            cause=None,
        ),
    ):
        response = await async_client.get(
            "/api/v1/profiles/me",
            headers={"Authorization": "Bearer expired_token"},
        )
        assert response.status_code == 401
        assert "expired" in response.json()["detail"]


@pytest.mark.asyncio
async def test_auth_revoked_token_rejected(async_client: AsyncClient):
    """Ensure revoked Firebase tokens trigger 401 Revoked Token."""
    with patch(
        "app.core.auth.firebase_auth.verify_id_token",
        side_effect=firebase_auth.RevokedIdTokenError("Token has been revoked"),
    ):
        response = await async_client.get(
            "/api/v1/profiles/me",
            headers={"Authorization": "Bearer revoked_token"},
        )
        assert response.status_code == 401
        assert "revoked" in response.json()["detail"]


@pytest.mark.asyncio
async def test_auth_malformed_token_missing_uid(async_client: AsyncClient):
    """Ensure tokens without user identifier claim are rejected."""
    with patch(
        "app.core.auth.firebase_auth.verify_id_token",
        return_value={"email": "anonymous@test.com"},  # No uid/sub/user_id
    ):
        response = await async_client.get(
            "/api/v1/profiles/me",
            headers={"Authorization": "Bearer token_without_uid"},
        )
        assert response.status_code == 401
        assert "missing user identifier" in response.json()["detail"]


@pytest.mark.asyncio
async def test_auth_valid_token_accepted(async_client: AsyncClient):
    """Ensure valid tokens allow request to proceed to the controller."""
    with patch(
        "app.core.auth.firebase_auth.verify_id_token",
        return_value={
            "uid": "test_verified_user_1",
            "email": "student@example.com",
            "name": "Jane Doe",
        },
    ):
        # User has no profile yet, so it should pass auth and return 404 (not 401)
        response = await async_client.get(
            "/api/v1/profiles/me",
            headers={"Authorization": "Bearer valid_signed_token"},
        )
        assert response.status_code == 404
        assert "Student profile not found" in response.json()["detail"]
