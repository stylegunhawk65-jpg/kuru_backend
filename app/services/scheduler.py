"""Lightweight in-process background scheduler for application deadline and reminder alerts.

Runs periodically inside the FastAPI process lifespan using asyncio.
Avoids heavy external message broker infrastructure (no Celery/RabbitMQ/Redis)
while guaranteeing reliable deadline checks and deduplicated notifications.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.job import JobPosting, SavedJob
from app.models.notification import Notification, Reminder
from app.services.notification_service import notification_service

logger = logging.getLogger("kuru.scheduler")


class NotificationScheduler:
    """Lightweight periodic worker checking deadlines and due reminders."""

    def __init__(self, interval_seconds: int = 300) -> None:
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._running: bool = False

    async def run_check(self, db: AsyncSession) -> dict[str, int]:
        """Perform a single pass checking due reminders and upcoming application deadlines."""
        now_utc = datetime.now(timezone.utc)
        results = {"reminders_processed": 0, "deadlines_processed": 0}

        # ---------------------------------------------------------------------
        # 1. Check Pending Reminders
        # ---------------------------------------------------------------------
        try:
            reminder_stmt = select(Reminder).where(
                Reminder.is_completed == False,
                Reminder.is_dismissed == False,
                Reminder.due_date <= now_utc,
            )
            reminder_res = await db.execute(reminder_stmt)
            due_reminders = list(reminder_res.scalars().all())

            for reminder in due_reminders:
                # Deduplication: check if an unread notification for this reminder already exists
                existing_stmt = select(Notification).where(
                    Notification.firebase_uid == reminder.firebase_uid,
                    Notification.entity_type == "reminder",
                    Notification.entity_id == reminder.id,
                )
                existing_res = await db.execute(existing_stmt)
                if existing_res.scalar_one_or_none():
                    continue

                notif_type = "deadline" if reminder.reminder_type == "deadline" else "follow_up"
                await notification_service.create_notification(
                    db=db,
                    firebase_uid=reminder.firebase_uid,
                    title=f"Reminder: {reminder.title}",
                    message=reminder.description or f"Your reminder '{reminder.title}' is due.",
                    notification_type=notif_type,
                    entity_type="reminder",
                    entity_id=reminder.id,
                    data={"reminder_id": reminder.id, "job_id": reminder.job_id},
                )
                results["reminders_processed"] += 1
        except Exception as e:
            logger.error("Error evaluating due reminders during scheduler pass: %s", e)

        # ---------------------------------------------------------------------
        # 2. Check Approaching Application Deadlines (<= 24 hours)
        # ---------------------------------------------------------------------
        try:
            deadline_horizon = now_utc + timedelta(hours=24)
            app_stmt = select(SavedJob).where(
                SavedJob.status.in_(["saved", "applied", "interviewing"]),
                SavedJob.deadline != None,
                SavedJob.deadline <= deadline_horizon,
            )
            app_res = await db.execute(app_stmt)
            upcoming_jobs = list(app_res.scalars().all())

            for sj in upcoming_jobs:
                if not sj.deadline:
                    continue

                # Deduplication: check if a deadline notification for this job was sent in the last 24 hours
                recent_cutoff = now_utc - timedelta(hours=24)
                existing_stmt = select(Notification).where(
                    Notification.firebase_uid == sj.firebase_uid,
                    Notification.entity_type == "application_deadline",
                    Notification.entity_id == sj.job_id,
                    Notification.created_at >= recent_cutoff,
                )
                existing_res = await db.execute(existing_stmt)
                if existing_res.scalar_one_or_none():
                    continue

                # Load job title and company
                post_stmt = select(JobPosting).where(JobPosting.id == sj.job_id)
                post = (await db.execute(post_stmt)).scalar_one_or_none()
                title_str = post.title if post else "Tracked Application"
                company_str = post.company if post else "Company"

                formatted_due = sj.deadline.strftime("%b %d, %Y") if hasattr(sj.deadline, "strftime") else str(sj.deadline)

                await notification_service.create_notification(
                    db=db,
                    firebase_uid=sj.firebase_uid,
                    title=f"⏰ Upcoming Deadline: {title_str}",
                    message=f"Application deadline for {title_str} at {company_str} is approaching on {formatted_due}.",
                    notification_type="deadline",
                    entity_type="application_deadline",
                    entity_id=sj.job_id,
                    data={"job_id": sj.job_id, "deadline": sj.deadline.isoformat() if hasattr(sj.deadline, "isoformat") else str(sj.deadline)},
                )
                results["deadlines_processed"] += 1
        except Exception as e:
            logger.error("Error evaluating upcoming deadlines during scheduler pass: %s", e)

        return results

    async def _loop(self) -> None:
        """Main loop executing periodic database scans."""
        logger.info("NotificationScheduler background loop active (interval=%ss)", self.interval_seconds)
        while self._running:
            try:
                async with async_session_factory() as db:
                    await self.run_check(db)
            except Exception as e:
                logger.warning("NotificationScheduler background pass failed: %s", e)

            try:
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break

        logger.info("NotificationScheduler background loop terminated cleanly.")

    async def start(self) -> None:
        """Start the background task if not already running."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        """Gracefully stop and cancel the background task."""
        if not self._running:
            return
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None


notification_scheduler = NotificationScheduler()
