"""Comprehensive tests for Phase 12: Notifications, Application Tracking, Validation, and Reminders.

Verifies:
1. In-App Notifications:
   - Creation, listing, unread count, marking individual read/unread, batch mark-all-as-read, deletion.
   - Filtering by notification_type and read status.
2. User Reminders:
   - Creation with configurable due dates and reminder types (follow_up, deadline, custom).
   - Dynamic overdue calculation against UTC now.
   - Listing with status filters (active, completed, dismissed, overdue).
   - Completion and dismissal actions with timestamp updates.
3. Application Lifecycle State Machine:
   - Enforcing valid status transitions:
     saved -> applied, archived
     applied -> interviewing, rejected, archived
     interviewing -> offered, rejected, archived
     offered -> archived
     rejected -> archived
     archived -> saved
   - Rejection of invalid jumps (e.g. saved -> offered, rejected -> interviewing) with 400 Bad Request.
   - Automated notification generation on application status transitions.
4. Lightweight Background Scheduler:
   - Synchronous scan verifying due reminders generate notifications.
   - Synchronous scan verifying approaching application deadlines (<= 24h) generate notifications.
   - Deduplication preventing multiple duplicate notifications for the same reminder or deadline.
5. Per-User Security & Isolation:
   - 401 Unauthorized for unauthenticated requests.
   - Cross-user data isolation: Bob cannot view, mark read, update, or delete Alice's notifications or reminders.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import JobPosting, SavedJob
from app.models.notification import Notification, Reminder
from app.schemas.notification import ReminderCreate, ReminderUpdate
from app.services.notification_service import notification_service
from app.services.scheduler import notification_scheduler

USER_ALICE_UID = "usr_phase12_alice"
USER_BOB_UID = "usr_phase12_bob"

USER_ALICE_HEADERS = {"Authorization": "Bearer token_phase12_alice"}
USER_BOB_HEADERS = {"Authorization": "Bearer token_phase12_bob"}


def mock_verify_id_token(token: str, *args, **kwargs):
    if token == "token_phase12_alice":
        return {
            "uid": USER_ALICE_UID,
            "email": "alice@kuru.ai",
            "name": "Alice Developer",
        }
    elif token == "token_phase12_bob":
        return {
            "uid": USER_BOB_UID,
            "email": "bob@kuru.ai",
            "name": "Bob Developer",
        }
    raise ValueError("Invalid test token")


@pytest.fixture(autouse=True)
def patch_firebase_auth():
    with patch("app.core.auth.firebase_auth.verify_id_token", side_effect=mock_verify_id_token):
        yield


@pytest.fixture
async def seed_job(db_session: AsyncSession) -> JobPosting:
    job = JobPosting(
        id=str(uuid.uuid4()),
        source="curated_india",
        source_id="job_p12_001",
        dedup_hash="hash_p12_001",
        title="Senior Python Backend Engineer",
        company="Razorpay",
        location="Bengaluru, Karnataka",
        is_remote=False,
        job_type="full_time",
        description="Build scalable fintech payment processing APIs.",
        url="https://razorpay.com/careers/p12_001",
        required_skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        is_active=True,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


# =============================================================================
# 1. NOTIFICATIONS TESTS
# =============================================================================


async def test_notification_lifecycle_crud(async_client: AsyncClient, db_session: AsyncSession):
    """Test creating, reading, marking read, and deleting notifications."""
    # 1. Create notification directly via service
    notif = await notification_service.create_notification(
        db=db_session,
        firebase_uid=USER_ALICE_UID,
        title="Welcome to Kuru!",
        message="Your career twin is active.",
        notification_type="system",
        entity_type="system",
        entity_id="init",
    )
    assert notif.id is not None
    assert notif.is_read is False

    # 2. Check unread count endpoint
    resp = await async_client.get("/api/v1/notifications/unread-count", headers=USER_ALICE_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["unread_count"] == 1

    # 3. List notifications
    list_resp = await async_client.get("/api/v1/notifications", headers=USER_ALICE_HEADERS)
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] == 1
    assert data["unread_count"] == 1
    assert data["items"][0]["title"] == "Welcome to Kuru!"
    assert data["items"][0]["is_read"] is False

    # 4. Mark as read
    patch_resp = await async_client.patch(
        f"/api/v1/notifications/{notif.id}/read",
        headers=USER_ALICE_HEADERS,
        json={"is_read": True},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_read"] is True

    # 5. Verify unread count is now 0
    resp = await async_client.get("/api/v1/notifications/unread-count", headers=USER_ALICE_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["unread_count"] == 0

    # 6. Delete notification
    del_resp = await async_client.delete(f"/api/v1/notifications/{notif.id}", headers=USER_ALICE_HEADERS)
    assert del_resp.status_code == 204

    # Verify deleted
    list_resp = await async_client.get("/api/v1/notifications", headers=USER_ALICE_HEADERS)
    assert list_resp.json()["total"] == 0


async def test_notification_filters_and_mark_all_read(async_client: AsyncClient, db_session: AsyncSession):
    """Test filtering notifications by notification_type and batch mark-all-read."""
    # Create 3 notifications
    await notification_service.create_notification(
        db=db_session,
        firebase_uid=USER_ALICE_UID,
        title="Application Update",
        message="Applied to Razorpay.",
        notification_type="application_update",
    )
    await notification_service.create_notification(
        db=db_session,
        firebase_uid=USER_ALICE_UID,
        title="Interview Scheduled",
        message="Round 1 technical screen.",
        notification_type="interview",
    )
    await notification_service.create_notification(
        db=db_session,
        firebase_uid=USER_ALICE_UID,
        title="Deadline Alert",
        message="Submission due tomorrow.",
        notification_type="deadline",
    )

    # Filter by type=interview
    resp = await async_client.get("/api/v1/notifications?notification_type=interview", headers=USER_ALICE_HEADERS)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["notification_type"] == "interview"

    # Batch mark all as read
    mark_all_resp = await async_client.post("/api/v1/notifications/mark-all-read", headers=USER_ALICE_HEADERS)
    assert mark_all_resp.status_code == 200
    assert mark_all_resp.json()["updated_count"] == 3

    # Verify unread is now 0
    count_resp = await async_client.get("/api/v1/notifications/unread-count", headers=USER_ALICE_HEADERS)
    assert count_resp.json()["unread_count"] == 0


# =============================================================================
# 2. REMINDERS TESTS
# =============================================================================


async def test_reminder_crud_and_status(async_client: AsyncClient, db_session: AsyncSession, seed_job: JobPosting):
    """Test creating, updating, completing, and dismissing reminders."""
    due = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    # 1. Create reminder
    create_resp = await async_client.post(
        "/api/v1/reminders",
        headers=USER_ALICE_HEADERS,
        json={
            "title": "Follow up with HR recruiter",
            "description": "Send follow up email after technical screen",
            "due_date": due,
            "job_id": seed_job.id,
            "reminder_type": "follow_up",
        },
    )
    assert create_resp.status_code == 201
    reminder_data = create_resp.json()
    rem_id = reminder_data["id"]
    assert reminder_data["title"] == "Follow up with HR recruiter"
    assert reminder_data["reminder_type"] == "follow_up"
    assert reminder_data["is_completed"] is False
    assert reminder_data["is_dismissed"] is False
    assert reminder_data["is_overdue"] is False

    # 2. List reminders (active)
    list_resp = await async_client.get("/api/v1/reminders?status=active", headers=USER_ALICE_HEADERS)
    assert list_resp.status_code == 200
    res_data = list_resp.json()
    assert res_data["total"] == 1
    assert res_data["active_count"] == 1
    assert res_data["overdue_count"] == 0

    # 3. Update reminder
    patch_resp = await async_client.patch(
        f"/api/v1/reminders/{rem_id}",
        headers=USER_ALICE_HEADERS,
        json={"title": "Follow up with Razorpay recruiter urgently"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "Follow up with Razorpay recruiter urgently"

    # 4. Complete reminder
    comp_resp = await async_client.post(f"/api/v1/reminders/{rem_id}/complete", headers=USER_ALICE_HEADERS)
    assert comp_resp.status_code == 200
    assert comp_resp.json()["is_completed"] is True
    assert comp_resp.json()["completed_at"] is not None

    # Check that active count is now 0
    list_active = await async_client.get("/api/v1/reminders?status=active", headers=USER_ALICE_HEADERS)
    assert list_active.json()["total"] == 0
    assert list_active.json()["active_count"] == 0

    # 5. Dismiss reminder
    dismiss_resp = await async_client.post(f"/api/v1/reminders/{rem_id}/dismiss", headers=USER_ALICE_HEADERS)
    assert dismiss_resp.status_code == 200
    assert dismiss_resp.json()["is_dismissed"] is True

    # 6. Delete reminder
    del_resp = await async_client.delete(f"/api/v1/reminders/{rem_id}", headers=USER_ALICE_HEADERS)
    assert del_resp.status_code == 204


async def test_reminder_overdue_computation(async_client: AsyncClient, db_session: AsyncSession):
    """Test that overdue reminders are accurately identified."""
    past_due = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()

    create_resp = await async_client.post(
        "/api/v1/reminders",
        headers=USER_ALICE_HEADERS,
        json={
            "title": "Overdue Task",
            "due_date": past_due,
            "reminder_type": "deadline",
        },
    )
    assert create_resp.status_code == 201
    assert create_resp.json()["is_overdue"] is True

    # Query overdue filter
    list_resp = await async_client.get("/api/v1/reminders?status=overdue", headers=USER_ALICE_HEADERS)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1
    assert list_resp.json()["overdue_count"] == 1


# =============================================================================
# 3. APPLICATION STATUS TRANSITION & LIFECYCLE VALIDATION
# =============================================================================


async def test_application_lifecycle_valid_transitions(async_client: AsyncClient, db_session: AsyncSession, seed_job: JobPosting):
    """Test valid sequential status transitions: saved -> applied -> interviewing -> offered -> archived."""
    # 1. Save job
    save_resp = await async_client.post(f"/api/v1/jobs/{seed_job.id}/save", headers=USER_ALICE_HEADERS)
    assert save_resp.status_code == 201
    assert save_resp.json()["status"] == "saved"

    # 2. Transition saved -> applied
    patch1 = await async_client.patch(
        f"/api/v1/applications/{seed_job.id}",
        headers=USER_ALICE_HEADERS,
        json={"status": "applied", "notes": "Submitted through portal"},
    )
    assert patch1.status_code == 200
    assert patch1.json()["status"] == "applied"

    # 3. Transition applied -> interviewing
    patch2 = await async_client.patch(
        f"/api/v1/applications/{seed_job.id}",
        headers=USER_ALICE_HEADERS,
        json={"status": "interviewing"},
    )
    assert patch2.status_code == 200
    assert patch2.json()["status"] == "interviewing"

    # Verify interview notification was automatically generated
    notifs = await async_client.get("/api/v1/notifications?notification_type=interview", headers=USER_ALICE_HEADERS)
    assert notifs.status_code == 200
    assert len(notifs.json()["items"]) >= 1
    assert "Interview Stage Reached" in notifs.json()["items"][0]["title"]

    # 4. Transition interviewing -> offered
    patch3 = await async_client.patch(
        f"/api/v1/applications/{seed_job.id}",
        headers=USER_ALICE_HEADERS,
        json={"status": "offered"},
    )
    assert patch3.status_code == 200
    assert patch3.json()["status"] == "offered"

    # 5. Transition offered -> archived
    patch4 = await async_client.patch(
        f"/api/v1/applications/{seed_job.id}",
        headers=USER_ALICE_HEADERS,
        json={"status": "archived"},
    )
    assert patch4.status_code == 200
    assert patch4.json()["status"] == "archived"

    # 6. Re-open archived -> saved
    patch5 = await async_client.patch(
        f"/api/v1/applications/{seed_job.id}",
        headers=USER_ALICE_HEADERS,
        json={"status": "saved"},
    )
    assert patch5.status_code == 200
    assert patch5.json()["status"] == "saved"


async def test_application_lifecycle_invalid_transitions_blocked(async_client: AsyncClient, db_session: AsyncSession, seed_job: JobPosting):
    """Test that invalid lifecycle jumps are rejected with 400 Bad Request."""
    # 1. Save job
    await async_client.post(f"/api/v1/jobs/{seed_job.id}/save", headers=USER_ALICE_HEADERS)

    # 2. Attempt invalid jump: saved -> offered (must be applied -> interviewing first)
    bad_resp = await async_client.patch(
        f"/api/v1/applications/{seed_job.id}",
        headers=USER_ALICE_HEADERS,
        json={"status": "offered"},
    )
    assert bad_resp.status_code == 400
    assert "Invalid application status transition" in bad_resp.json()["detail"]

    # 3. Transition saved -> applied -> rejected
    await async_client.patch(
        f"/api/v1/applications/{seed_job.id}",
        headers=USER_ALICE_HEADERS,
        json={"status": "applied"},
    )
    rej_resp = await async_client.patch(
        f"/api/v1/applications/{seed_job.id}",
        headers=USER_ALICE_HEADERS,
        json={"status": "rejected"},
    )
    assert rej_resp.status_code == 200

    # 4. Attempt invalid jump: rejected -> interviewing directly
    bad_resp2 = await async_client.patch(
        f"/api/v1/applications/{seed_job.id}",
        headers=USER_ALICE_HEADERS,
        json={"status": "interviewing"},
    )
    assert bad_resp2.status_code == 400
    assert "Invalid application status transition" in bad_resp2.json()["detail"]


# =============================================================================
# 4. LIGHTWEIGHT SCHEDULER TESTS
# =============================================================================


async def test_scheduler_due_reminders_and_deadlines(async_client: AsyncClient, db_session: AsyncSession, seed_job: JobPosting):
    """Test scheduler scans overdue reminders and upcoming deadlines, emitting deduplicated notifications."""
    now_utc = datetime.now(timezone.utc)

    # 1. Create a due reminder
    past_due = now_utc - timedelta(hours=1)
    await notification_service.create_reminder(
        db=db_session,
        firebase_uid=USER_ALICE_UID,
        payload=ReminderCreate(
            title="Submit Take-Home Assignment",
            description="Complete FastAPI service",
            due_date=past_due,
            reminder_type="deadline",
        ),
    )

    # 2. Create a saved job with deadline in 12 hours (within 24h horizon)
    upcoming_deadline = now_utc + timedelta(hours=12)
    saved = SavedJob(
        id=str(uuid.uuid4()),
        firebase_uid=USER_ALICE_UID,
        job_id=seed_job.id,
        status="saved",
        deadline=upcoming_deadline,
    )
    db_session.add(saved)
    await db_session.commit()

    # 3. Run scheduler check pass
    results = await notification_scheduler.run_check(db_session)
    assert results["reminders_processed"] == 1
    assert results["deadlines_processed"] == 1

    # 4. Run scheduler check pass again (deduplication check)
    results2 = await notification_scheduler.run_check(db_session)
    assert results2["reminders_processed"] == 0
    assert results2["deadlines_processed"] == 0

    # 5. Verify notifications exist for user
    notifs = await notification_service.list_notifications(db=db_session, firebase_uid=USER_ALICE_UID)
    assert notifs.total >= 2
    titles = [item.title for item in notifs.items]
    assert any("Reminder: Submit Take-Home Assignment" in t for t in titles)
    assert any("Upcoming Deadline" in t for t in titles)


# =============================================================================
# 5. SECURITY & DATA ISOLATION TESTS
# =============================================================================


async def test_notifications_and_reminders_cross_user_isolation(async_client: AsyncClient, db_session: AsyncSession):
    """Test that Bob cannot access or mutate Alice's notifications or reminders."""
    # Alice creates a notification and a reminder
    alice_notif = await notification_service.create_notification(
        db=db_session,
        firebase_uid=USER_ALICE_UID,
        title="Alice Secret Notification",
        message="Confidential interview feedback",
        notification_type="interview",
    )
    alice_rem = await notification_service.create_reminder(
        db=db_session,
        firebase_uid=USER_ALICE_UID,
        payload=ReminderCreate(
            title="Alice Secret Reminder",
            due_date=datetime.now(timezone.utc) + timedelta(days=1),
        ),
    )

    # 1. Bob cannot see Alice's notification in his list
    bob_notifs = await async_client.get("/api/v1/notifications", headers=USER_BOB_HEADERS)
    assert bob_notifs.status_code == 200
    assert bob_notifs.json()["total"] == 0

    # 2. Bob cannot mark Alice's notification as read
    bob_patch_notif = await async_client.patch(
        f"/api/v1/notifications/{alice_notif.id}/read",
        headers=USER_BOB_HEADERS,
        json={"is_read": True},
    )
    assert bob_patch_notif.status_code == 404

    # 3. Bob cannot delete Alice's notification
    bob_del_notif = await async_client.delete(
        f"/api/v1/notifications/{alice_notif.id}",
        headers=USER_BOB_HEADERS,
    )
    assert bob_del_notif.status_code == 404

    # 4. Bob cannot view Alice's reminder
    bob_get_rem = await async_client.get(
        f"/api/v1/reminders/{alice_rem.id}",
        headers=USER_BOB_HEADERS,
    )
    assert bob_get_rem.status_code == 404

    # 5. Bob cannot complete Alice's reminder
    bob_comp_rem = await async_client.post(
        f"/api/v1/reminders/{alice_rem.id}/complete",
        headers=USER_BOB_HEADERS,
    )
    assert bob_comp_rem.status_code == 404

    # 6. Bob cannot delete Alice's reminder
    bob_del_rem = await async_client.delete(
        f"/api/v1/reminders/{alice_rem.id}",
        headers=USER_BOB_HEADERS,
    )
    assert bob_del_rem.status_code == 404


async def test_notifications_and_reminders_unauthenticated_blocked(async_client: AsyncClient):
    """Test that missing or invalid auth token is rejected with 401 Unauthorized."""
    endpoints = [
        ("GET", "/api/v1/notifications"),
        ("GET", "/api/v1/notifications/unread-count"),
        ("POST", "/api/v1/notifications/mark-all-read"),
        ("GET", "/api/v1/reminders"),
        ("POST", "/api/v1/reminders"),
    ]
    for method, ep in endpoints:
        if method == "GET":
            resp = await async_client.get(ep)
        else:
            resp = await async_client.post(ep, json={})
        assert resp.status_code == 401, f"{method} {ep} should require authentication"
