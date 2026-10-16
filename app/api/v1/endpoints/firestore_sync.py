"""Authenticated endpoints for Firestore real-time preferences and mobile notes synchronization."""

import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.auth import AuthenticatedUser, get_current_user
from app.services.firestore import firestore_service

logger = logging.getLogger("kuru.api.firestore_sync")
router = APIRouter()


class UserPreferencesPayload(BaseModel):
    """Schema for updating user preferences."""

    theme_mode: str | None = Field(None, description="Preferred app theme (system, light, dark)")
    notifications_enabled: bool = Field(True, description="Enable push/real-time alerts")
    weekly_study_goal_hours: int = Field(12, ge=1, le=80, description="Weekly target commitment")
    preferred_role: str | None = Field(None, description="Preferred target job title")
    custom_settings: dict[str, Any] = Field(default_factory=dict, description="Arbitrary custom settings")


class CreateNotePayload(BaseModel):
    """Schema for creating a career/study note."""

    title: str = Field(..., min_length=1, max_length=200, description="Title of note")
    content: str = Field(..., min_length=1, max_length=10000, description="Markdown or text content")
    tags: list[str] = Field(default_factory=list, description="Categorization tags")


@router.get(
    "/preferences",
    response_model=dict[str, Any],
    summary="Get user-isolated mobile preferences from Firestore",
)
async def get_preferences(
    target_uid: str | None = Query(None, description="Optional target UID to verify isolation"),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve personal preferences for authenticated student."""
    uid_to_fetch = target_uid or current_user.uid
    return await firestore_service.get_user_preferences(
        authenticated_uid=current_user.uid,
        target_uid=uid_to_fetch,
    )


@router.put(
    "/preferences",
    response_model=dict[str, Any],
    summary="Update user-isolated mobile preferences in Firestore",
)
async def update_preferences(
    payload: UserPreferencesPayload,
    target_uid: str | None = Query(None, description="Optional target UID to verify isolation"),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Update or merge personal preferences for authenticated student."""
    uid_to_update = target_uid or current_user.uid
    return await firestore_service.set_user_preferences(
        authenticated_uid=current_user.uid,
        target_uid=uid_to_update,
        preferences=payload.model_dump(exclude_unset=True),
    )


@router.get(
    "/notes",
    response_model=list[dict[str, Any]],
    summary="List user-isolated career notes from Firestore",
)
async def list_notes(
    target_uid: str | None = Query(None, description="Optional target UID to verify isolation"),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Retrieve all personal notes for authenticated student."""
    uid_to_fetch = target_uid or current_user.uid
    return await firestore_service.list_user_notes(
        authenticated_uid=current_user.uid,
        target_uid=uid_to_fetch,
    )


@router.post(
    "/notes",
    response_model=dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Create a personal career note in Firestore",
)
async def create_note(
    payload: CreateNotePayload,
    target_uid: str | None = Query(None, description="Optional target UID to verify isolation"),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Create a new note strictly isolated to authenticated student."""
    uid_to_create = target_uid or current_user.uid
    return await firestore_service.create_user_note(
        authenticated_uid=current_user.uid,
        target_uid=uid_to_create,
        title=payload.title,
        content=payload.content,
        tags=payload.tags,
    )


@router.delete(
    "/notes/{note_id}",
    response_model=dict[str, bool],
    summary="Delete a personal career note from Firestore",
)
async def delete_note(
    note_id: str,
    target_uid: str | None = Query(None, description="Optional target UID to verify isolation"),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, bool]:
    """Delete a note strictly isolated to authenticated student."""
    uid_to_delete = target_uid or current_user.uid
    deleted = await firestore_service.delete_user_note(
        authenticated_uid=current_user.uid,
        target_uid=uid_to_delete,
        note_id=note_id,
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return {"deleted": True}
