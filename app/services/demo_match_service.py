"""Service layer for isolated 100% demo match scenario and actionable notifications.

DEMO SAFETY GUARANTEES:
- Uses isolated fixtures ('demo-job-python-100', 'demo-user-100', 'demo-cv-100').
- Real user profile, skills, scores, CVs, and applications are never overwritten.
- Scores are genuinely computed using the existing calculate_job_match() engine.
- Idempotent: repeated calls do not duplicate notifications, jobs, or applications.
- Does not automatically submit job applications.
"""

from copy import deepcopy
from datetime import datetime, timezone
import logging
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppException, ResourceNotFoundError
from app.models.job import JobPosting
from app.models.notification import Notification
from app.models.profile import StudentProfile
from app.models.skill import StudentSkill
from app.services.matcher import calculate_job_match, JobMatchResult
from app.services.notification_service import notification_service

logger = logging.getLogger("kuru.demo_match")

# Controlled Demo Job: Requirements mathematically crafted to achieve 100% with Demo Profile
DEMO_JOB_ID = "demo-job-python-100"
DEMO_CV_ID = "demo-cv-100"

DEMO_JOB = JobPosting(
    id=DEMO_JOB_ID,
    source="demo",
    source_id="demo-fixture-100",
    title="Python Developer",
    company="DemoTech (DEMO)",
    location="Remote",
    is_remote=True,
    job_type="Full-time",
    description=(
        "Exciting software architecture building high-scale Python cloud backend services. "
        "Looking for candidates with practical FastAPI, PostgreSQL, and Docker experience."
    ),
    url="https://demo.kuru.careers/jobs/demo-job-python-100",
    required_skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
    salary_currency="INR",
    salary_min=1200000,
    salary_max=1800000,
    is_active=True,
)

DEMO_PROFILE = StudentProfile(
    id="demo-profile-100",
    firebase_uid="demo-user-100",
    full_name="Demo Candidate (DEMO)",
    email="demo.candidate@kuru.careers",
    target_roles=["Python Developer"],
    preferred_locations=["Remote"],
    interests=["Software Architecture", "Python Cloud Backend"],
    bio="Demonstration profile designed to show verified 100% transparent scoring.",
)

DEMO_SKILLS = [
    StudentSkill(
        id="demo-skill-1",
        firebase_uid="demo-user-100",
        skill_name="Python",
        confidence_score=1.0,
        verification_status="practically_demonstrated",
    ),
    StudentSkill(
        id="demo-skill-2",
        firebase_uid="demo-user-100",
        skill_name="FastAPI",
        confidence_score=1.0,
        verification_status="practically_demonstrated",
    ),
    StudentSkill(
        id="demo-skill-3",
        firebase_uid="demo-user-100",
        skill_name="PostgreSQL",
        confidence_score=1.0,
        verification_status="practically_demonstrated",
    ),
    StudentSkill(
        id="demo-skill-4",
        firebase_uid="demo-user-100",
        skill_name="Docker",
        confidence_score=1.0,
        verification_status="practically_demonstrated",
    ),
]

# Separate Demo CV fixture
DEFAULT_DEMO_CV: dict[str, Any] = {
    "id": DEMO_CV_ID,
    "version": "v1.0-demo",
    "title": "DemoTech Tailored Resume (DEMO)",
    "target_role": "Python Developer",
    "target_company": "DemoTech (DEMO)",
    "contact_info": {
        "full_name": "Demo Candidate",
        "email": "demo.candidate@kuru.careers",
        "phone": "+91 98765 43210",
        "location": "Remote, India",
    },
    "summary": "Proven Python Developer with 100% verified competency in FastAPI, PostgreSQL, and Docker architecture.",
    "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Software Architecture"],
    "experience": [
        {
            "role": "Backend Engineer Intern",
            "company": "Kuru Sandbox Labs",
            "start_date": "Jan 2025",
            "end_date": "Present",
            "bullet_points": [
                "Engineered high-throughput REST APIs using FastAPI and asyncpg.",
                "Containerized backend microservices using Docker with CI/CD automation.",
            ],
        }
    ],
    "education": [
        {
            "institution": "National Institute of Technology",
            "degree": "B.Tech Computer Science",
            "graduation_year": "2026",
        }
    ],
    "is_reviewed": False,
    "review_status": "pending_review",
    "disclaimer": "DEMO FIXTURE: Controlled verification scenario for demonstration purposes only. Does not guarantee employment.",
}

# Per-user demo CV state store (in-memory for demo isolation)
_user_demo_cv_store: dict[str, dict[str, Any]] = {}


class DemoMatchService:
    """Orchestrates genuine 100% match computation, notification dispatch, and action lifecycles."""

    @classmethod
    def compute_genuine_100_match(cls) -> JobMatchResult:
        """Calculate match score using the REAL scoring formula.
        
        Verifies that every criterion matches legitimately:
        - Skills match: 4/4 skills @ 1.0 confidence = 50.0 / 50.0
        - Target role: 'Python Developer' in title = 25.0 / 25.0
        - Location: 'Remote' matches remote preference = 15.0 / 15.0
        - Career interests: 2 matching keywords = 10.0 / 10.0
        Total = 100.0%
        """
        result = calculate_job_match(DEMO_JOB, DEMO_PROFILE, DEMO_SKILLS)
        if result.match_score != 100.0:
            raise AppException(
                detail=(
                    f"Scoring engine produced {result.match_score}%, expected genuine 100.0%. "
                    f"Reasons: {result.match_reasons}"
                ),
                status_code=500,
                error_code="DEMO_SCORING_MISMATCH",
            )
        return result

    @classmethod
    async def trigger_demo_100_match(
        cls,
        db: AsyncSession,
        firebase_uid: str,
    ) -> dict[str, Any]:
        """Trigger an isolated 100% match event and idempotent actionable notification."""
        # Ensure demo mode is allowed in non-production
        if settings.ENVIRONMENT == "production" and not getattr(settings, "ENABLE_DEMO_ENDPOINTS", False):
            raise AppException(
                detail="Demo endpoints are disabled in production environment.",
                status_code=403,
                error_code="DEMO_DISABLED_IN_PROD",
            )

        # 1. Genuine computation
        match_result = cls.compute_genuine_100_match()

        # 2. Reset or initialize user's demo CV state
        if firebase_uid not in _user_demo_cv_store:
            _user_demo_cv_store[firebase_uid] = deepcopy(DEFAULT_DEMO_CV)

        demo_cv = _user_demo_cv_store[firebase_uid]

        # 3. Notification payload with actionable buttons
        notif_title = "Kuru — 100% Job Match!"
        notif_message = (
            "Your profile matches all assessed requirements for Python Developer at DemoTech. "
            "Review your CV and choose an action."
        )

        notif_data = {
            "is_demo": True,
            "job_id": DEMO_JOB_ID,
            "job_title": DEMO_JOB.title,
            "company": DEMO_JOB.company,
            "match_score": match_result.match_score,
            "cv_id": DEMO_CV_ID,
            "cv_version": demo_cv.get("version", "v1.0-demo"),
            "cv_title": demo_cv.get("title"),
            "available_actions": ["APPROVE_CV", "REJECT", "UPDATE_CV"],
            "status": "pending_review",
            "is_reviewed": demo_cv.get("is_reviewed", False),
            "match_reasons": match_result.match_reasons,
            "notification_channel": "job_alerts",
            "is_actionable": True,
            "honest_disclaimer": "100% match reflects criteria alignment under rule engine. Does not guarantee employment.",
        }

        # 4. Check for existing demo notification to guarantee IDEMPOTENCY
        stmt = (
            select(Notification)
            .where(
                Notification.firebase_uid == firebase_uid,
                Notification.entity_id == DEMO_JOB_ID,
            )
            .order_by(Notification.created_at.desc())
        )
        existing_res = await db.execute(stmt)
        existing_notif = existing_res.scalar_one_or_none()

        if existing_notif:
            existing_notif.title = notif_title
            existing_notif.message = notif_message
            existing_notif.is_read = False
            existing_notif.data = notif_data
            notification_obj = existing_notif
            logger.info("Updated existing demo notification %s for user %s", notification_obj.id, firebase_uid)
        else:
            notification_obj = Notification(
                id=str(uuid.uuid4()),
                firebase_uid=firebase_uid,
                title=notif_title,
                message=notif_message,
                notification_type="job_match",
                entity_type="demo_job",
                entity_id=DEMO_JOB_ID,
                is_read=False,
                data=notif_data,
            )
            db.add(notification_obj)
            logger.info("Created new demo notification %s for user %s", notification_obj.id, firebase_uid)

        await db.commit()
        await db.refresh(notification_obj)

        return {
            "success": True,
            "match_score": match_result.match_score,
            "job": {
                "id": DEMO_JOB.id,
                "title": DEMO_JOB.title,
                "company": DEMO_JOB.company,
                "location": DEMO_JOB.location,
                "is_remote": DEMO_JOB.is_remote,
                "required_skills": DEMO_JOB.required_skills,
                "source": "DEMO",
            },
            "notification": {
                "id": notification_obj.id,
                "title": notification_obj.title,
                "message": notification_obj.message,
                "data": notification_obj.data,
            },
            "demo_cv": demo_cv,
            "match_reasons": match_result.match_reasons,
        }

    @classmethod
    async def handle_demo_action(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        notification_id: str,
        action: str,
        confirmed_reviewed: bool = False,
    ) -> dict[str, Any]:
        """Handle YES — APPROVE CV, NO — REJECT, or UPDATE CV from notification."""
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.firebase_uid == firebase_uid,
        )
        res = await db.execute(stmt)
        notif = res.scalar_one_or_none()

        if not notif:
            raise ResourceNotFoundError("Demo Notification", notification_id)

        current_data = dict(notif.data or {})
        user_cv = _user_demo_cv_store.get(firebase_uid, deepcopy(DEFAULT_DEMO_CV))

        if action == "APPROVE_CV":
            # Safety requirement: explicit confirmation that candidate reviewed the CV
            if not confirmed_reviewed and not user_cv.get("is_reviewed", False):
                return {
                    "success": False,
                    "status": "review_required",
                    "notification_id": notification_id,
                    "cv_id": DEMO_CV_ID,
                    "cv_version": user_cv.get("version", "v1.0-demo"),
                    "message": "Explicit confirmation required: Please review the tailored CV before approving.",
                    "requires_dialog": True,
                }

            # Record approval against the correct CV version
            user_cv["is_reviewed"] = True
            user_cv["review_status"] = "approved"
            _user_demo_cv_store[firebase_uid] = user_cv

            current_data["status"] = "approved"
            current_data["approved_at"] = datetime.now(timezone.utc).isoformat()
            current_data["approved_cv_version"] = user_cv.get("version", "v1.0-demo")
            notif.data = current_data
            notif.is_read = True
            await db.commit()

            return {
                "success": True,
                "status": "approved",
                "notification_id": notification_id,
                "cv_version": user_cv.get("version"),
                "message": (
                    f"CV {user_cv.get('version')} approved for {DEMO_JOB.title} at {DEMO_JOB.company}. "
                    "Note: Application is NOT submitted automatically."
                ),
            }

        elif action == "REJECT":
            # Record dismissal/rejection without touching real applications or CVs
            current_data["status"] = "rejected"
            current_data["rejected_at"] = datetime.now(timezone.utc).isoformat()
            notif.data = current_data
            notif.is_read = True
            await db.commit()

            return {
                "success": True,
                "status": "rejected",
                "notification_id": notification_id,
                "message": "Demo match alert dismissed. Real application and profile records are untouched.",
            }

        elif action == "UPDATE_CV":
            return {
                "success": True,
                "status": "editing",
                "notification_id": notification_id,
                "cv": user_cv,
                "message": "Demo CV ready for review and update.",
            }

        else:
            raise AppException(
                detail=f"Unknown demo action '{action}'. Allowed: APPROVE_CV, REJECT, UPDATE_CV.",
                status_code=400,
                error_code="INVALID_DEMO_ACTION",
            )

    @classmethod
    def get_demo_cv(cls, firebase_uid: str) -> dict[str, Any]:
        """Retrieve current demo CV for user."""
        if firebase_uid not in _user_demo_cv_store:
            _user_demo_cv_store[firebase_uid] = deepcopy(DEFAULT_DEMO_CV)
        return _user_demo_cv_store[firebase_uid]

    @classmethod
    def update_demo_cv(
        cls,
        firebase_uid: str,
        cv_updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Update demo CV and increment version string to v1.1-demo."""
        if firebase_uid not in _user_demo_cv_store:
            _user_demo_cv_store[firebase_uid] = deepcopy(DEFAULT_DEMO_CV)

        cv = _user_demo_cv_store[firebase_uid]
        if "summary" in cv_updates:
            cv["summary"] = cv_updates["summary"]
        if "skills" in cv_updates:
            cv["skills"] = cv_updates["skills"]
        if "target_role" in cv_updates:
            cv["target_role"] = cv_updates["target_role"]

        # Increment version to reflect change
        cv["version"] = "v1.1-demo"
        cv["updated_at"] = datetime.now(timezone.utc).isoformat()
        cv["is_reviewed"] = True  # User edited it, so they reviewed it
        cv["review_status"] = "edited_and_reviewed"
        _user_demo_cv_store[firebase_uid] = cv

        logger.info("Updated demo CV for user %s to version %s", firebase_uid, cv["version"])
        return cv


demo_match_service = DemoMatchService()
