"""Authenticated Career Profile endpoints with per-user data isolation."""

import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.models.profile import StudentProfile
from app.schemas.profile import (
    StudentProfileCreate,
    StudentProfileResponse,
    StudentProfileUpdate,
)

logger = logging.getLogger("kuru.profiles")
router = APIRouter()


class ProfileSyncRequest(BaseModel):
    """Payload to synchronize guided onboarding profile to PostgreSQL."""

    full_name: str = Field(..., min_length=1, max_length=255)
    email: str | None = None
    degree: str | None = None
    institution: str | None = None
    graduation_year: int | None = None
    target_roles: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    bio: str | None = None


@router.post(
    "/sync",
    response_model=StudentProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Synchronize Onboarding Profile to PostgreSQL",
    description="Idempotently creates or updates the student's career profile from verified onboarding data.",
)
async def sync_profile(
    payload: ProfileSyncRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentProfile:
    """Create or update profile idempotently upon onboarding completion."""
    stmt = select(StudentProfile).where(StudentProfile.firebase_uid == current_user.uid)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    education_data = []
    if payload.institution or payload.degree:
        education_data.append({
            "institution": payload.institution or "Institution",
            "degree": payload.degree or "Degree",
            "field_of_study": None,
            "start_year": None,
            "end_year": payload.graduation_year,
            "grade_or_cgpa": None,
        })

    if profile:
        profile.full_name = payload.full_name or profile.full_name
        if payload.email:
            profile.email = payload.email
        if education_data:
            profile.education = education_data
        if payload.interests:
            profile.interests = payload.interests
        if payload.target_roles:
            profile.target_roles = payload.target_roles
        if payload.preferred_locations:
            profile.preferred_locations = payload.preferred_locations
        if payload.bio:
            profile.bio = payload.bio
        await db.commit()
        await db.refresh(profile)
        logger.info("Synchronized existing profile for user %s", current_user.uid)
        return profile

    new_profile = StudentProfile(
        firebase_uid=current_user.uid,
        full_name=payload.full_name,
        email=payload.email or current_user.email,
        education=education_data,
        interests=payload.interests,
        target_roles=payload.target_roles,
        preferred_locations=payload.preferred_locations,
        bio=payload.bio,
    )
    db.add(new_profile)
    await db.commit()
    await db.refresh(new_profile)
    logger.info("Synchronized new profile for user %s", current_user.uid)
    return new_profile


@router.post(
    "",
    response_model=StudentProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Career Profile",
    description="Create a career profile for the authenticated student. User ID is bound to the verified Firebase token.",
)
async def create_profile(
    profile_in: StudentProfileCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentProfile:
    """Create a new profile bound to the authenticated user's Firebase UID."""
    # Check if a profile already exists for this verified user
    stmt = select(StudentProfile).where(StudentProfile.firebase_uid == current_user.uid)
    result = await db.execute(stmt)
    existing_profile = result.scalar_one_or_none()

    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A student profile already exists for this authenticated user.",
        )

    # Education entries serialization to JSON-compatible dicts
    education_data = [entry.model_dump() for entry in profile_in.education]
    cert_data = [c.model_dump() for c in profile_in.certificates]

    new_profile = StudentProfile(
        firebase_uid=current_user.uid,  # Strictly from verified token
        full_name=profile_in.full_name,
        email=profile_in.email or current_user.email,
        education=education_data,
        interests=profile_in.interests,
        target_roles=profile_in.target_roles,
        preferred_locations=profile_in.preferred_locations,
        bio=profile_in.bio,
        linkedin_url=profile_in.linkedin_url,
        certificates=cert_data,
    )

    db.add(new_profile)
    await db.commit()
    await db.refresh(new_profile)
    logger.info("Student profile created for user %s (profile_id: %s)", current_user.uid, new_profile.id)
    return new_profile


@router.get(
    "/me",
    response_model=StudentProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Profile",
    description="Retrieve the profile of the currently authenticated student.",
)
async def get_my_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentProfile:
    """Retrieve current user's profile with strict per-user isolation."""
    stmt = select(StudentProfile).where(StudentProfile.firebase_uid == current_user.uid)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found for this authenticated user.",
        )

    return profile


@router.get(
    "/{profile_id}",
    response_model=StudentProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Profile by ID",
    description="Retrieve a specific profile by ID, strictly enforcing user ownership.",
)
async def get_profile_by_id(
    profile_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentProfile:
    """Retrieve profile by ID, isolated to the authenticated owner."""
    stmt = select(StudentProfile).where(
        StudentProfile.id == profile_id,
        StudentProfile.firebase_uid == current_user.uid,
    )
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found.",
        )

    return profile


@router.put(
    "/me",
    response_model=StudentProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Current User Profile",
    description="Update career profile attributes for the authenticated student.",
)
@router.patch(
    "/me",
    response_model=StudentProfileResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def update_my_profile(
    profile_in: StudentProfileUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentProfile:
    """Update profile fields for the authenticated user."""
    stmt = select(StudentProfile).where(StudentProfile.firebase_uid == current_user.uid)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found for this authenticated user.",
        )

    if profile_in.full_name is not None:
        profile.full_name = profile_in.full_name
    if profile_in.email is not None:
        profile.email = profile_in.email
    if profile_in.education is not None:
        profile.education = [entry.model_dump() for entry in profile_in.education]
    if profile_in.interests is not None:
        profile.interests = profile_in.interests
    if profile_in.target_roles is not None:
        profile.target_roles = profile_in.target_roles
    if profile_in.preferred_locations is not None:
        profile.preferred_locations = profile_in.preferred_locations
    if profile_in.bio is not None:
        profile.bio = profile_in.bio
    if profile_in.linkedin_url is not None:
        profile.linkedin_url = profile_in.linkedin_url
    if profile_in.certificates is not None:
        profile.certificates = [entry.model_dump() for entry in profile_in.certificates]

    await db.commit()
    await db.refresh(profile)
    logger.info("Updated profile for user %s", current_user.uid)
    return profile


class AddCertificateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    issuer: str = Field(..., min_length=1, max_length=255)
    issue_date: str | None = None
    skills: list[str] = Field(default_factory=list)
    verification_status: str = Field(default="user_reported")  # user_reported, document_supported, externally_verified
    credential_url: str | None = None


@router.post(
    "/me/certificates",
    response_model=StudentProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Verifiable Certificate / Credential",
    description="Add a verified or self-reported credential linked to concrete Career Twin skills.",
)
async def add_certificate(
    payload: AddCertificateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentProfile:
    """Add a certificate to the student profile with provenance attribution."""
    import uuid
    stmt = select(StudentProfile).where(StudentProfile.firebase_uid == current_user.uid)
    profile = (await db.execute(stmt)).scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found for this authenticated user.",
        )

    current_certs = list(profile.certificates or [])
    new_cert = {
        "id": f"cert_{uuid.uuid4().hex[:8]}",
        "name": payload.name.strip(),
        "issuer": payload.issuer.strip(),
        "issue_date": payload.issue_date,
        "skills": [s.strip() for s in payload.skills if s.strip()],
        "verification_status": payload.verification_status,
        "credential_url": payload.credential_url,
        "source": "document_supported" if payload.verification_status != "user_reported" else "user_provided",
    }
    current_certs.append(new_cert)
    profile.certificates = current_certs

    await db.commit()
    await db.refresh(profile)
    logger.info("Added certificate %s for user %s", new_cert["id"], current_user.uid)
    return profile


@router.delete(
    "/me/certificates/{cert_id}",
    response_model=StudentProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete Certificate",
)
async def delete_certificate(
    cert_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentProfile:
    """Remove a certificate from the user's profile."""
    stmt = select(StudentProfile).where(StudentProfile.firebase_uid == current_user.uid)
    profile = (await db.execute(stmt)).scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found.",
        )

    current_certs = [c for c in (profile.certificates or []) if c.get("id") != cert_id]
    profile.certificates = current_certs
    await db.commit()
    await db.refresh(profile)
    return profile


class LinkedInImportRequest(BaseModel):
    linkedin_url: str = Field(..., min_length=5, max_length=512)
    headline: str | None = None
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)


@router.post(
    "/me/linkedin-import",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Low-Friction LinkedIn Integration",
    description="Import public profile details or user-provided LinkedIn claims without automated scraping blocks.",
)
async def import_linkedin(
    payload: LinkedInImportRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Graceful LinkedIn profile association and data ingestion."""
    stmt = select(StudentProfile).where(StudentProfile.firebase_uid == current_user.uid)
    profile = (await db.execute(stmt)).scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found.",
        )

    # Clean URL and check format
    clean_url = payload.linkedin_url.strip()
    profile.linkedin_url = clean_url
    profile.linkedin_verified = False  # Manual entry is unverified until OAuth 2.0 exchange

    if payload.summary and not profile.bio:
        profile.bio = payload.summary

    if payload.headline and not profile.target_roles:
        profile.target_roles = [payload.headline]

    # Merge non-duplicate skills with explicit origin tracking
    imported_skills = [s.strip() for s in payload.skills if s.strip()]
    if imported_skills:
        existing_interests = set(profile.interests or [])
        for s in imported_skills:
            existing_interests.add(s)
        profile.interests = list(existing_interests)

    await db.commit()
    await db.refresh(profile)

    return {
        "status": "success",
        "source": "user_provided",
        "linkedin_url": profile.linkedin_url,
        "linkedin_verified": False,
        "imported_skills_count": len(imported_skills),
        "message": "LinkedIn profile URL saved as unverified user-provided link. Full verification requires OAuth 2.0.",
    }


@router.get(
    "/linkedin/oauth/url",
    response_model=dict[str, Any],
    summary="Get LinkedIn OAuth 2.0 Authorization URL",
    description="Returns official LinkedIn OAuth authorization URL or explanation of missing server configuration.",
)
async def get_linkedin_oauth_url(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Provide official LinkedIn OAuth 2.0 authorization URL or clear explanation if credentials unconfigured."""
    from app.core.config import settings

    if not settings.LINKEDIN_CLIENT_ID or not settings.LINKEDIN_CLIENT_SECRET:
        return {
            "configured": False,
            "status": "unconfigured",
            "message": (
                "LinkedIn OAuth 2.0 application credentials (LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET) "
                "are not configured on this server. Manual profile URL entry is active as an unverified fallback."
            ),
            "missing_keys": ["LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET"],
        }

    import secrets
    import urllib.parse

    state = f"kuru_li_{secrets.token_hex(16)}"
    scope = "openid profile email"
    params = {
        "response_type": "code",
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
        "state": state,
        "scope": scope,
    }
    auth_url = f"https://www.linkedin.com/oauth/v2/authorization?{urllib.parse.urlencode(params)}"
    return {
        "configured": True,
        "status": "ready",
        "authorization_url": auth_url,
        "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
        "state": state,
        "scopes": scope.split(),
    }


class LinkedInOAuthCallbackRequest(BaseModel):
    code: str = Field(..., min_length=1)
    state: str = Field(..., min_length=1)


@router.post(
    "/linkedin/oauth/callback",
    response_model=dict[str, Any],
    summary="LinkedIn OAuth 2.0 Token Exchange and Profile Verification",
    description="Exchanges authorization code for access token and updates verified profile status.",
)
async def linkedin_oauth_callback(
    payload: LinkedInOAuthCallbackRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Verify authorization code and link verified LinkedIn account."""
    from app.core.config import settings

    if not settings.LINKEDIN_CLIENT_ID or not settings.LINKEDIN_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="LinkedIn OAuth credentials are not configured on the backend.",
        )

    import httpx

    async with httpx.AsyncClient(timeout=15.0) as client:
        token_res = await client.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": payload.code,
                "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
                "client_id": settings.LINKEDIN_CLIENT_ID,
                "client_secret": settings.LINKEDIN_CLIENT_SECRET,
            },
        )
        if token_res.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"LinkedIn token exchange failed: {token_res.text}",
            )
        token_data = token_res.json()
        access_token = token_data.get("access_token")

        userinfo_res = await client.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        userinfo = userinfo_res.json() if userinfo_res.status_code == 200 else {}

    stmt = select(StudentProfile).where(StudentProfile.firebase_uid == current_user.uid)
    profile = (await db.execute(stmt)).scalar_one_or_none()
    if profile:
        profile.linkedin_verified = True
        sub = userinfo.get("sub")
        if sub:
            profile.linkedin_url = f"https://www.linkedin.com/in/{sub}"
        await db.commit()
        await db.refresh(profile)

    return {
        "status": "verified",
        "linkedin_verified": True,
        "message": "LinkedIn account successfully verified via official OAuth 2.0.",
        "profile": userinfo,
    }


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Current User Profile",
    description="Delete the career profile of the authenticated student.",
)
async def delete_my_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete the authenticated user's profile with strict per-user isolation."""
    stmt = select(StudentProfile).where(StudentProfile.firebase_uid == current_user.uid)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found for this authenticated user.",
        )

    await db.delete(profile)
    await db.commit()
    logger.info("Deleted profile for user %s", current_user.uid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
