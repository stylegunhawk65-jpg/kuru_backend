"""Firebase Authentication and token verification dependency."""

import logging
import os
from typing import Any
import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger("kuru.auth")

# Bearer token extractor
security_scheme = HTTPBearer(auto_error=False)


def initialize_firebase() -> firebase_admin.App | None:
    """Initialize Firebase Admin SDK using configured credentials or environment."""
    if firebase_admin._apps:
        return firebase_admin.get_app()

    try:
        cred_path = settings.FIREBASE_CREDENTIALS_PATH
        if cred_path and os.path.isfile(cred_path):
            cred = credentials.Certificate(cred_path)
            app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized from service certificate: %s", cred_path)
            return app

        if settings.FIREBASE_PROJECT_ID:
            app = firebase_admin.initialize_app(
                options={"projectId": settings.FIREBASE_PROJECT_ID}
            )
            logger.info(
                "Firebase Admin SDK initialized with project ID: %s",
                settings.FIREBASE_PROJECT_ID,
            )
            return app

        # Attempt default application credentials
        app = firebase_admin.initialize_app()
        logger.info("Firebase Admin SDK initialized with Application Default Credentials")
        return app
    except Exception as exc:
        logger.warning(
            "Firebase Admin SDK initialization deferred or unconfigured: %s",
            str(exc),
        )
        return None


# Trigger initial configuration attempt
initialize_firebase()


class AuthenticatedUser(BaseModel):
    """Verified identity claims extracted from Firebase ID token."""

    uid: str
    email: str | None = None
    name: str | None = None
    email_verified: bool = False
    claims: dict[str, Any] = {}


async def get_current_user(
    auth_credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> AuthenticatedUser:
    """Dependency that extracts and verifies the Firebase ID token from Authorization header.

    Guarantees user identity is derived strictly from cryptographic token verification,
    never from client-supplied IDs.
    """
    if not auth_credentials or not auth_credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Missing Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_credentials.credentials.strip()

    try:
        # Verify cryptographically with Firebase Admin SDK
        decoded_token = firebase_auth.verify_id_token(token, check_revoked=True)
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase ID token has expired. Please refresh your credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except firebase_auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase ID token has been revoked.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (firebase_auth.InvalidIdTokenError, ValueError) as exc:
        logger.warning("Invalid Firebase ID token received: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase ID token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as exc:
        logger.error("Error during Firebase token verification: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Derive identity directly from token claims
    uid = (
        decoded_token.get("uid")
        or decoded_token.get("sub")
        or decoded_token.get("user_id")
    )
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token: missing user identifier.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthenticatedUser(
        uid=uid,
        email=decoded_token.get("email"),
        name=decoded_token.get("name"),
        email_verified=decoded_token.get("email_verified", False),
        claims=decoded_token,
    )
