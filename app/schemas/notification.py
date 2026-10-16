"""Pydantic schemas for Notifications and Reminders."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    """Schema for returning an in-app notification."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    firebase_uid: str
    title: str
    message: str
    notification_type: str = Field(..., description="application_update, interview, deadline, follow_up, system")
    entity_type: str | None = None
    entity_id: str | None = None
    is_read: bool = False
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class NotificationUpdate(BaseModel):
    """Schema for updating a notification (e.g. mark read/unread)."""

    is_read: bool


class NotificationListResponse(BaseModel):
    """Schema for paginated/filtered list of notifications."""

    items: list[NotificationResponse]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    """Schema for lightweight notification bell badge count."""

    unread_count: int


class ReminderCreate(BaseModel):
    """Schema for creating a user reminder."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    due_date: datetime = Field(..., description="UTC timestamp when the reminder is due")
    job_id: str | None = None
    reminder_type: str = Field(
        default="custom",
        pattern="^(follow_up|deadline|custom)$",
        description="Type of reminder: follow_up, deadline, or custom",
    )


class ReminderUpdate(BaseModel):
    """Schema for modifying an existing reminder."""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    due_date: datetime | None = None
    reminder_type: str | None = Field(None, pattern="^(follow_up|deadline|custom)$")
    is_completed: bool | None = None
    is_dismissed: bool | None = None


class ReminderResponse(BaseModel):
    """Schema for returning a reminder with computed overdue status."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    firebase_uid: str
    job_id: str | None = None
    title: str
    description: str | None = None
    due_date: datetime
    reminder_type: str
    is_completed: bool = False
    is_dismissed: bool = False
    is_overdue: bool = False
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm_model(cls, reminder: Any) -> "ReminderResponse":
        """Compute is_overdue dynamically against current UTC time."""
        now = datetime.now(timezone.utc)
        due = reminder.due_date
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        is_overdue = (not reminder.is_completed) and (not reminder.is_dismissed) and (due < now)

        return cls(
            id=reminder.id,
            firebase_uid=reminder.firebase_uid,
            job_id=reminder.job_id,
            title=reminder.title,
            description=reminder.description,
            due_date=reminder.due_date,
            reminder_type=reminder.reminder_type,
            is_completed=reminder.is_completed,
            is_dismissed=reminder.is_dismissed,
            is_overdue=is_overdue,
            completed_at=reminder.completed_at,
            created_at=reminder.created_at,
            updated_at=reminder.updated_at,
        )


class ReminderListResponse(BaseModel):
    """Schema for list of reminders with active and overdue counters."""

    items: list[ReminderResponse]
    total: int
    active_count: int
    overdue_count: int
