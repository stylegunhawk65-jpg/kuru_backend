"""Authenticated Career Profile endpoints with per-user data isolation."""

import logging
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

    new_profile = StudentProfile(
        firebase_uid=current_user.uid,  # Strictly from verified token
        full_name=profile_in.full_name,
        email=profile_in.email or current_user.email,
        education=education_data,
        interests=profile_in.interests,
        target_roles=profile_in.target_roles,
        preferred_locations=profile_in.preferred_locations,
        bio=profile_in.bio,
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

    await db.commit()
    await db.refresh(profile)
    logger.info("Updated profile for user %s", current_user.uid)
    return profile


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
