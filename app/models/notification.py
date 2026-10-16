"""SQLAlchemy models for in-app Notifications and User Reminders."""

from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Notification(Base, TimestampMixin):
    """In-app notifications for application lifecycle updates, interviews, deadlines, and approvals."""

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    firebase_uid: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
    )  # application_update, interview, deadline, follow_up, system
    entity_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )  # job, application, reminder, approval
    entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        Index("ix_notifications_user_unread", "firebase_uid", "is_read"),
        Index("ix_notifications_user_created", "firebase_uid", "created_at"),
    )


class Reminder(Base, TimestampMixin):
    """User-configurable reminders for follow-ups, upcoming deadlines, and custom action items."""

    __tablename__ = "reminders"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    firebase_uid: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
    )
    job_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=False,
    )
    reminder_type: Mapped[str] = mapped_column(
        String(50),
        default="custom",
        nullable=False,
    )  # follow_up, deadline, custom
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_reminders_user_active", "firebase_uid", "is_completed", "is_dismissed"),
        Index("ix_reminders_user_due", "firebase_uid", "due_date"),
    )
