"""Authenticated endpoints for user notifications and unread badges."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    NotificationUpdate,
    UnreadCountResponse,
)
from app.services.notification_service import notification_service

logger = logging.getLogger("kuru.notifications.api")
router = APIRouter()


@router.get(
    "",
    response_model=NotificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Notifications",
    description="Retrieve paginated in-app notifications for the authenticated user, optionally filtered by read status or type.",
)
async def list_notifications(
    is_read: bool | None = Query(None, description="Filter by read status (true or false)"),
    notification_type: str | None = Query(
        None,
        description="Filter by type: application_update, interview, deadline, follow_up, system",
    ),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationListResponse:
    """List in-app notifications for the authenticated user."""
    return await notification_service.list_notifications(
        db=db,
        firebase_uid=current_user.uid,
        is_read=is_read,
        notification_type=notification_type,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Unread Notification Count",
    description="Retrieve the total count of unread notifications for badge display.",
)
async def get_unread_count(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnreadCountResponse:
    """Retrieve unread notification count."""
    count = await notification_service.get_unread_count(
        db=db,
        firebase_uid=current_user.uid,
    )
    return UnreadCountResponse(unread_count=count)


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark Notification Read / Unread",
    description="Update the read status of a specific notification.",
)
async def mark_as_read(
    notification_id: str,
    payload: NotificationUpdate = NotificationUpdate(is_read=True),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    """Mark a notification as read or unread."""
    return await notification_service.mark_as_read(
        db=db,
        firebase_uid=current_user.uid,
        notification_id=notification_id,
        is_read=payload.is_read,
    )


@router.post(
    "/mark-all-read",
    status_code=status.HTTP_200_OK,
    summary="Mark All Notifications as Read",
    description="Batch update all unread notifications for the current user to read.",
)
async def mark_all_as_read(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Mark all unread notifications as read."""
    count = await notification_service.mark_all_as_read(
        db=db,
        firebase_uid=current_user.uid,
    )
    return {"message": "All notifications marked as read.", "updated_count": count}


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Notification",
    description="Remove an individual notification record.",
)
async def delete_notification(
    notification_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a notification."""
    await notification_service.delete_notification(
        db=db,
        firebase_uid=current_user.uid,
        notification_id=notification_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
