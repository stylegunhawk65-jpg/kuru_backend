"""Firebase Authentication and token verification dependency."""

import logging
import os
import time
from typing import Any
import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import httpx
import jwt
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger("kuru.auth")

# Bearer token extractor
security_scheme = HTTPBearer(auto_error=False)

# Cache for Google's public x509 certificates for Firebase ID token verification
_GOOGLE_CERTS_CACHE: dict[str, str] = {}
_GOOGLE_CERTS_EXPIRY: float = 0.0
_CERTS_URL = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"


def get_google_public_certificates() -> dict[str, str]:
    """Retrieve and cache Google's public certificates for Firebase ID tokens."""
    global _GOOGLE_CERTS_CACHE, _GOOGLE_CERTS_EXPIRY
    now = time.time()
    if _GOOGLE_CERTS_CACHE and now < _GOOGLE_CERTS_EXPIRY:
        return _GOOGLE_CERTS_CACHE

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(_CERTS_URL)
            if resp.status_code == 200:
                _GOOGLE_CERTS_CACHE = resp.json()
                # Parse Cache-Control max-age or default to 1 hour
                max_age = 3600
                cache_control = resp.headers.get("cache-control", "")
                if "max-age=" in cache_control:
                    try:
                        max_age = int(cache_control.split("max-age=")[1].split(",")[0].strip())
                    except Exception:
                        pass
                _GOOGLE_CERTS_EXPIRY = now + max_age
                logger.info("Loaded %d Google public certificates for Firebase ID token verification.", len(_GOOGLE_CERTS_CACHE))
                return _GOOGLE_CERTS_CACHE
    except Exception as exc:
        logger.warning("Could not fetch Google public certs: %s", exc)

    return _GOOGLE_CERTS_CACHE


def initialize_firebase() -> firebase_admin.App | None:
    """Initialize Firebase Admin SDK using configured credentials or environment."""
    if firebase_admin._apps:
        return firebase_admin.get_app()

    # 1. Attempt initialization with explicit service account credentials file
    cred_path = settings.FIREBASE_CREDENTIALS_PATH
    if cred_path and os.path.isfile(cred_path):
        try:
            cred = credentials.Certificate(cred_path)
            app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized from service certificate: %s", cred_path)
            return app
        except Exception as exc:
            logger.warning(
                "Certificate at %s could not be loaded as service account: %s",
                cred_path,
                exc,
            )

    # 2. Attempt initialization with Project ID
    if settings.FIREBASE_PROJECT_ID:
        try:
            app = firebase_admin.initialize_app(
                options={"projectId": settings.FIREBASE_PROJECT_ID}
            )
            logger.info(
                "Firebase Admin SDK initialized with project ID: %s",
                settings.FIREBASE_PROJECT_ID,
            )
            return app
        except Exception as exc:
            logger.warning("Firebase Admin initialization with project ID failed: %s", exc)

    # 3. Attempt default application credentials
    try:
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
    decoded_token: dict[str, Any] | None = None

    # Step 1: Attempt verification through Firebase Admin SDK if service account is available
    try:
        decoded_token = firebase_auth.verify_id_token(token, check_revoked=False)
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
        logger.warning("Firebase Admin rejected token: %s", str(exc))
    except Exception as exc:
        logger.info("Firebase Admin verification fallback: %s", str(exc))

    # Step 2: If Firebase Admin was initialized without full credentials, verify cryptographically via Google's public certificates
    if decoded_token is None:
        try:
            unverified_headers = jwt.get_unverified_header(token)
            kid = unverified_headers.get("kid")
            if not kid:
                raise ValueError("Missing kid in token header")

            certs = get_google_public_certificates()
            cert_pem = certs.get(kid)
            if not cert_pem:
                # Force refresh cache once
                certs = get_google_public_certificates()
                cert_pem = certs.get(kid)

            if not cert_pem:
                raise ValueError(f"Unknown key identifier kid={kid}")

            project_id = settings.FIREBASE_PROJECT_ID
            decoded_token = jwt.decode(
                token,
                cert_pem,
                algorithms=["RS256"],
                audience=project_id,
                issuer=f"https://securetoken.google.com/{project_id}",
                options={"verify_exp": True},
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Firebase ID token has expired. Please refresh your credentials.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as exc:
            logger.warning("Cryptographic verification of token failed: %s", str(exc))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Firebase ID token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Derive identity directly from verified token claims
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

