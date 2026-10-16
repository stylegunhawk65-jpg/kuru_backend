"""Authenticated endpoints for user reminders and follow-up management."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.schemas.notification import (
    ReminderCreate,
    ReminderListResponse,
    ReminderResponse,
    ReminderUpdate,
)
from app.services.notification_service import notification_service

logger = logging.getLogger("kuru.reminders.api")
router = APIRouter()


@router.post(
    "",
    response_model=ReminderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Reminder",
    description="Create a new reminder for application deadlines, interview follow-ups, or custom tasks.",
)
async def create_reminder(
    payload: ReminderCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderResponse:
    """Create a new user reminder."""
    return await notification_service.create_reminder(
        db=db,
        firebase_uid=current_user.uid,
        payload=payload,
    )


@router.get(
    "",
    response_model=ReminderListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Reminders",
    description="Retrieve reminders for the authenticated user, optionally filtered by status (active, completed, dismissed, overdue).",
)
async def list_reminders(
    status: str | None = Query(
        None,
        description="Filter by reminder status: active, completed, dismissed, overdue",
    ),
    job_id: str | None = Query(None, description="Filter by associated job posting ID"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderListResponse:
    """List reminders with computed overdue indicators and status counts."""
    return await notification_service.list_reminders(
        db=db,
        firebase_uid=current_user.uid,
        status_filter=status,
        job_id=job_id,
    )


@router.get(
    "/{reminder_id}",
    response_model=ReminderResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Reminder Details",
    description="Retrieve a single reminder by ID with isolation check.",
)
async def get_reminder(
    reminder_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderResponse:
    """Get reminder details."""
    return await notification_service.get_reminder(
        db=db,
        firebase_uid=current_user.uid,
        reminder_id=reminder_id,
    )


@router.patch(
    "/{reminder_id}",
    response_model=ReminderResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Reminder",
    description="Update reminder title, description, due date, type, or completion status.",
)
async def update_reminder(
    reminder_id: str,
    payload: ReminderUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderResponse:
    """Update a reminder."""
    return await notification_service.update_reminder(
        db=db,
        firebase_uid=current_user.uid,
        reminder_id=reminder_id,
        payload=payload,
    )


@router.post(
    "/{reminder_id}/complete",
    response_model=ReminderResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark Reminder Completed",
    description="Set reminder state to completed and record completion timestamp.",
)
async def complete_reminder(
    reminder_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderResponse:
    """Mark reminder completed."""
    return await notification_service.complete_reminder(
        db=db,
        firebase_uid=current_user.uid,
        reminder_id=reminder_id,
    )


@router.post(
    "/{reminder_id}/dismiss",
    response_model=ReminderResponse,
    status_code=status.HTTP_200_OK,
    summary="Dismiss Reminder",
    description="Dismiss a reminder without marking it completed.",
)
async def dismiss_reminder(
    reminder_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderResponse:
    """Dismiss a reminder."""
    return await notification_service.dismiss_reminder(
        db=db,
        firebase_uid=current_user.uid,
        reminder_id=reminder_id,
    )


@router.delete(
    "/{reminder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Reminder",
    description="Permanently delete a reminder record.",
)
async def delete_reminder(
    reminder_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a reminder."""
    await notification_service.delete_reminder(
        db=db,
        firebase_uid=current_user.uid,
        reminder_id=reminder_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
