"""Service layer for Notifications, Reminders, and Application Status Transitions."""

from datetime import datetime, timezone
import logging
from typing import Any
import uuid

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, ResourceNotFoundError
from app.models.job import JobPosting, SavedJob
from app.models.notification import Notification, Reminder
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    ReminderCreate,
    ReminderListResponse,
    ReminderResponse,
    ReminderUpdate,
)

logger = logging.getLogger("kuru.notifications.service")

# Allowed application lifecycle status transitions
VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "saved": {"saved", "applied", "interviewing", "archived"},
    "applied": {"applied", "interviewing", "offered", "rejected", "archived"},
    "interviewing": {"interviewing", "offered", "rejected", "archived"},
    "offered": {"offered", "rejected", "archived"},
    "rejected": {"rejected", "archived", "saved"},
    "archived": {"archived", "saved"},
}


class NotificationService:
    """Service managing in-app notifications, user reminders, and application lifecycle triggers."""

    # -------------------------------------------------------------------------
    # Status Transition Validation & Automated Lifecycle Notifications
    # -------------------------------------------------------------------------

    @classmethod
    def validate_status_transition(cls, current_status: str, new_status: str) -> None:
        """Enforce strict lifecycle state machine rules for job applications."""
        allowed = VALID_STATUS_TRANSITIONS.get(current_status, set())
        if new_status not in allowed:
            raise AppException(
                detail=(
                    f"Invalid application status transition from '{current_status}' to '{new_status}'. "
                    f"Allowed transitions: {sorted(list(allowed))}."
                ),
                status_code=400,
                error_code="INVALID_STATUS_TRANSITION",
            )

    @classmethod
    async def handle_application_status_change(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        job_id: str,
        old_status: str,
        new_status: str,
    ) -> Notification | None:
        """Trigger an automated in-app notification when an application status updates."""
        if old_status == new_status:
            return None

        # Fetch job posting details for friendly notification message
        job_stmt = select(JobPosting).where(JobPosting.id == job_id)
        job = (await db.execute(job_stmt)).scalar_one_or_none()
        title_str = job.title if job else "Position"
        company_str = job.company if job else "Target Company"

        notification_type = "application_update"
        title = "Application Updated"
        message = f"Your application for {title_str} at {company_str} was changed to {new_status}."

        if new_status == "interviewing":
            notification_type = "interview"
            title = "🎉 Interview Stage Reached!"
            message = f"Great news! Your application for {title_str} at {company_str} is now in the Interviewing stage."
        elif new_status == "offered":
            notification_type = "application_update"
            title = "🌟 Job Offer Received!"
            message = f"Congratulations! You received an offer for {title_str} at {company_str}."
        elif new_status == "applied":
            notification_type = "application_update"
            title = "Application Submitted"
            message = f"Your application materials for {title_str} at {company_str} have been submitted."
        elif new_status == "rejected":
            notification_type = "application_update"
            title = "Application Update"
            message = f"Application status for {title_str} at {company_str} has been marked as rejected."
        elif new_status == "archived":
            notification_type = "application_update"
            title = "Application Archived"
            message = f"Your application for {title_str} at {company_str} has been archived."
        elif new_status == "saved":
            notification_type = "application_update"
            title = "Application Restored"
            message = f"Your application for {title_str} at {company_str} has been restored to Saved."

        return await cls.create_notification(
            db=db,
            firebase_uid=firebase_uid,
            title=title,
            message=message,
            notification_type=notification_type,
            entity_type="application",
            entity_id=job_id,
            data={"job_id": job_id, "previous_status": old_status, "new_status": new_status},
        )

    # -------------------------------------------------------------------------
    # Notification CRUD & Queries
    # -------------------------------------------------------------------------

    @classmethod
    async def create_notification(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        title: str,
        message: str,
        notification_type: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> Notification:
        """Create and persist an in-app notification for the user."""
        notification = Notification(
            id=str(uuid.uuid4()),
            firebase_uid=firebase_uid,
            title=title,
            message=message,
            notification_type=notification_type,
            entity_type=entity_type,
            entity_id=entity_id,
            is_read=False,
            data=data or {},
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        logger.info(
            "Created notification '%s' (type=%s) for user '%s'",
            notification.id,
            notification_type,
            firebase_uid,
        )
        return notification

    @classmethod
    async def list_notifications(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        is_read: bool | None = None,
        notification_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> NotificationListResponse:
        """Retrieve paginated notifications for the user with unread counter."""
        base_query = select(Notification).where(Notification.firebase_uid == firebase_uid)

        if is_read is not None:
            base_query = base_query.where(Notification.is_read == is_read)
        if notification_type:
            base_query = base_query.where(Notification.notification_type == notification_type)

        # Count total matching query
        count_query = select(func.count(Notification.id)).where(Notification.firebase_uid == firebase_uid)
        if is_read is not None:
            count_query = count_query.where(Notification.is_read == is_read)
        if notification_type:
            count_query = count_query.where(Notification.notification_type == notification_type)

        total_res = await db.execute(count_query)
        total = total_res.scalar_one() or 0

        # Count overall unread
        unread_query = select(func.count(Notification.id)).where(
            Notification.firebase_uid == firebase_uid,
            Notification.is_read == False,
        )
        unread_res = await db.execute(unread_query)
        unread_count = unread_res.scalar_one() or 0

        # Execute paginated fetch
        items_query = base_query.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
        items_res = await db.execute(items_query)
        items = list(items_res.scalars().all())

        return NotificationListResponse(
            items=[NotificationResponse.model_validate(n) for n in items],
            total=total,
            unread_count=unread_count,
        )

    @classmethod
    async def get_unread_count(cls, db: AsyncSession, firebase_uid: str) -> int:
        """Count unread notifications for bell badge."""
        query = select(func.count(Notification.id)).where(
            Notification.firebase_uid == firebase_uid,
            Notification.is_read == False,
        )
        res = await db.execute(query)
        return res.scalar_one() or 0

    @classmethod
    async def mark_as_read(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        notification_id: str,
        is_read: bool = True,
    ) -> NotificationResponse:
        """Mark a single notification as read or unread."""
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.firebase_uid == firebase_uid,
        )
        res = await db.execute(stmt)
        notification = res.scalar_one_or_none()
        if not notification:
            raise ResourceNotFoundError("Notification", notification_id)

        notification.is_read = is_read
        await db.commit()
        await db.refresh(notification)
        return NotificationResponse.model_validate(notification)

    @classmethod
    async def mark_all_as_read(cls, db: AsyncSession, firebase_uid: str) -> int:
        """Mark all unread notifications as read for current user."""
        stmt = (
            update(Notification)
            .where(
                Notification.firebase_uid == firebase_uid,
                Notification.is_read == False,
            )
            .values(is_read=True)
        )
        res = await db.execute(stmt)
        await db.commit()
        return res.rowcount or 0

    @classmethod
    async def delete_notification(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        notification_id: str,
    ) -> None:
        """Remove a notification record."""
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.firebase_uid == firebase_uid,
        )
        res = await db.execute(stmt)
        notification = res.scalar_one_or_none()
        if not notification:
            raise ResourceNotFoundError("Notification", notification_id)

        await db.delete(notification)
        await db.commit()

    # -------------------------------------------------------------------------
    # Reminder CRUD & Queries
    # -------------------------------------------------------------------------

    @classmethod
    async def create_reminder(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        payload: ReminderCreate,
    ) -> ReminderResponse:
        """Create a user-configurable reminder with due date."""
        due_utc = payload.due_date
        if due_utc.tzinfo is None:
            due_utc = due_utc.replace(tzinfo=timezone.utc)

        reminder = Reminder(
            id=str(uuid.uuid4()),
            firebase_uid=firebase_uid,
            job_id=payload.job_id,
            title=payload.title,
            description=payload.description,
            due_date=due_utc,
            reminder_type=payload.reminder_type,
            is_completed=False,
            is_dismissed=False,
        )
        db.add(reminder)
        await db.commit()
        await db.refresh(reminder)
        return ReminderResponse.from_orm_model(reminder)

    @classmethod
    async def list_reminders(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        status_filter: str | None = None,
        job_id: str | None = None,
    ) -> ReminderListResponse:
        """Retrieve user reminders, filtering by active, completed, dismissed, or overdue."""
        now = datetime.now(timezone.utc)
        stmt = select(Reminder).where(Reminder.firebase_uid == firebase_uid)

        if job_id:
            stmt = stmt.where(Reminder.job_id == job_id)

        if status_filter == "active":
            stmt = stmt.where(Reminder.is_completed == False, Reminder.is_dismissed == False)
        elif status_filter == "completed":
            stmt = stmt.where(Reminder.is_completed == True)
        elif status_filter == "dismissed":
            stmt = stmt.where(Reminder.is_dismissed == True)
        elif status_filter == "overdue":
            stmt = stmt.where(
                Reminder.is_completed == False,
                Reminder.is_dismissed == False,
                Reminder.due_date < now,
            )

        stmt = stmt.order_by(Reminder.due_date.asc())
        res = await db.execute(stmt)
        records = list(res.scalars().all())

        # Calculate counts
        all_res = await db.execute(select(Reminder).where(Reminder.firebase_uid == firebase_uid))
        all_user_reminders = list(all_res.scalars().all())

        active_count = sum(1 for r in all_user_reminders if not r.is_completed and not r.is_dismissed)
        overdue_count = sum(
            1
            for r in all_user_reminders
            if (not r.is_completed)
            and (not r.is_dismissed)
            and ((r.due_date.replace(tzinfo=timezone.utc) if r.due_date.tzinfo is None else r.due_date) < now)
        )

        return ReminderListResponse(
            items=[ReminderResponse.from_orm_model(r) for r in records],
            total=len(records),
            active_count=active_count,
            overdue_count=overdue_count,
        )

    @classmethod
    async def get_reminder(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        reminder_id: str,
    ) -> ReminderResponse:
        """Retrieve single reminder by ID."""
        stmt = select(Reminder).where(
            Reminder.id == reminder_id,
            Reminder.firebase_uid == firebase_uid,
        )
        res = await db.execute(stmt)
        reminder = res.scalar_one_or_none()
        if not reminder:
            raise ResourceNotFoundError("Reminder", reminder_id)
        return ReminderResponse.from_orm_model(reminder)

    @classmethod
    async def update_reminder(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        reminder_id: str,
        payload: ReminderUpdate,
    ) -> ReminderResponse:
        """Update reminder fields."""
        stmt = select(Reminder).where(
            Reminder.id == reminder_id,
            Reminder.firebase_uid == firebase_uid,
        )
        res = await db.execute(stmt)
        reminder = res.scalar_one_or_none()
        if not reminder:
            raise ResourceNotFoundError("Reminder", reminder_id)

        if payload.title is not None:
            reminder.title = payload.title
        if payload.description is not None:
            reminder.description = payload.description
        if payload.due_date is not None:
            due_utc = payload.due_date
            if due_utc.tzinfo is None:
                due_utc = due_utc.replace(tzinfo=timezone.utc)
            reminder.due_date = due_utc
        if payload.reminder_type is not None:
            reminder.reminder_type = payload.reminder_type
        if payload.is_completed is not None:
            reminder.is_completed = payload.is_completed
            reminder.completed_at = datetime.now(timezone.utc) if payload.is_completed else None
        if payload.is_dismissed is not None:
            reminder.is_dismissed = payload.is_dismissed

        await db.commit()
        await db.refresh(reminder)
        return ReminderResponse.from_orm_model(reminder)

    @classmethod
    async def complete_reminder(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        reminder_id: str,
    ) -> ReminderResponse:
        """Mark a reminder as completed."""
        return await cls.update_reminder(
            db=db,
            firebase_uid=firebase_uid,
            reminder_id=reminder_id,
            payload=ReminderUpdate(is_completed=True),
        )

    @classmethod
    async def dismiss_reminder(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        reminder_id: str,
    ) -> ReminderResponse:
        """Dismiss a reminder without marking it completed."""
        return await cls.update_reminder(
            db=db,
            firebase_uid=firebase_uid,
            reminder_id=reminder_id,
            payload=ReminderUpdate(is_dismissed=True),
        )

    @classmethod
    async def delete_reminder(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        reminder_id: str,
    ) -> None:
        """Delete a reminder record."""
        stmt = select(Reminder).where(
            Reminder.id == reminder_id,
            Reminder.firebase_uid == firebase_uid,
        )
        res = await db.execute(stmt)
        reminder = res.scalar_one_or_none()
        if not reminder:
            raise ResourceNotFoundError("Reminder", reminder_id)

        await db.delete(reminder)
        await db.commit()


notification_service = NotificationService()
