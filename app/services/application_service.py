"""Application preparation and tracking service.

Enforces strict human-in-the-loop approval: prepares job application materials
(tailored resume, evidence citations, cover note) and queues a consequential approval request.
Never auto-applies to external platforms without explicit user decision.
"""

from datetime import datetime, timezone
import logging
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError
from app.models.job import JobPosting, SavedJob
from app.models.profile import StudentProfile
from app.models.resume import Resume
from app.models.skill import StudentSkill
from app.schemas.application import (
    ApplicationDetailResponse,
    ApplicationPrepareRequest,
    ApplicationPrepareResponse,
    ApplicationUpdateRequest,
)
from app.schemas.job import JobPostingResponse
from app.schemas.resume import ResumeGenerateRequest
from app.services.agents.approval_agent import approval_workflow_agent
from app.services.llm.base import BaseLLMProvider
from app.services.matcher import calculate_job_match
from app.services.resume.service import resume_service

logger = logging.getLogger("kuru.applications.service")


def _coerce_datetime(val: Any) -> datetime | None:
    """Safely coerce ISO strings or datetime objects to a timezone-aware datetime."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo is not None else val.replace(tzinfo=timezone.utc)
    if isinstance(val, str):
        try:
            cleaned = val.replace("Z", "+00:00")
            if len(cleaned) == 10 and "-" in cleaned:
                return datetime.fromisoformat(f"{cleaned}T00:00:00+00:00")
            dt = datetime.fromisoformat(cleaned)
            return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


class ApplicationService:
    """Service orchestrating application material synthesis, tracking, and approval gates."""

    @classmethod
    async def prepare_application(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        request: ApplicationPrepareRequest,
        provider: BaseLLMProvider | None = None,
    ) -> ApplicationPrepareResponse:
        """Synthesize job-specific application materials and queue human approval gate."""
        logger.info("Preparing application for user '%s' on job '%s'...", firebase_uid, request.job_id)

        # 1. Fetch Target Job
        job_stmt = select(JobPosting).where(JobPosting.id == request.job_id)
        job_res = await db.execute(job_stmt)
        job = job_res.scalar_one_or_none()
        if not job:
            raise ResourceNotFoundError("Job posting", request.job_id)

        # 2. Fetch or Generate Tailored Resume
        resume: Resume | None = None
        if request.resume_id:
            resume = await resume_service.get_resume(db, firebase_uid, request.resume_id)
        else:
            # Check if user already has a resume tailored for this job
            existing_resume_stmt = select(Resume).where(
                Resume.firebase_uid == firebase_uid,
                Resume.job_id == job.id,
            )
            res = await db.execute(existing_resume_stmt)
            resume = res.scalar_one_or_none()

            # Otherwise generate a fresh tailored resume
            if not resume:
                resume = await resume_service.generate_resume(
                    db=db,
                    firebase_uid=firebase_uid,
                    request=ResumeGenerateRequest(
                        target_role=job.title,
                        job_id=job.id,
                        save_to_db=True,
                    ),
                    provider=provider,
                )

        # 3. Fetch candidate profile and skills
        prof_stmt = select(StudentProfile).where(StudentProfile.firebase_uid == firebase_uid)
        profile = (await db.execute(prof_stmt)).scalar_one_or_none()

        skills_stmt = select(StudentSkill).where(StudentSkill.firebase_uid == firebase_uid)
        skills = list((await db.execute(skills_stmt)).scalars().all())

        match_calc = calculate_job_match(job=job, profile=profile, skills=skills)

        # 4. Synthesize Cover Note (grounded strictly in real skills and match points)
        candidate_name = profile.full_name if profile and profile.full_name else "Candidate"
        candidate_email = profile.email if profile and profile.email else f"{firebase_uid[:8]}@kuru.ai"

        matching_skills_str = ", ".join(match_calc.matched_skills[:4]) if match_calc.matched_skills else "software engineering foundations"
        cover_note = request.cover_note
        if not cover_note:
            cover_note = (
                f"Dear {job.company} Hiring Team,\n\n"
                f"I am writing to express my strong interest in the {job.title} role. "
                f"Through hands-on development and isolated sandbox practical testing, I have demonstrated competency in {matching_skills_str}. "
                f"My portfolio projects directly align with {job.company}'s engineering architecture, and my skills have been validated through concrete AST code evidence.\n\n"
                f"Thank you for considering my application. I look forward to the opportunity to discuss how my technical skills can contribute to {job.company}.\n\n"
                f"Sincerely,\n{candidate_name}"
            )

        # 5. Formulate Application Packet
        packet: dict[str, Any] = {
            "job_id": job.id,
            "job_title": job.title,
            "company": job.company,
            "location": job.location,
            "resume_id": resume.id,
            "resume_title": resume.title,
            "candidate_name": candidate_name,
            "candidate_email": candidate_email,
            "cover_note": cover_note,
            "match_score": match_calc.match_score,
            "matching_skills": match_calc.matched_skills,
            "missing_skills": match_calc.missing_skills,
            "prepared_at": datetime.now(timezone.utc).isoformat(),
            "requires_human_approval": True,
            "auto_submission_prevented": True,
        }

        # 6. Upsert SavedJob Application Tracker Record
        sj_stmt = select(SavedJob).where(
            SavedJob.firebase_uid == firebase_uid,
            SavedJob.job_id == job.id,
        )
        sj_res = await db.execute(sj_stmt)
        saved_rec = sj_res.scalar_one_or_none()

        parsed_deadline = _coerce_datetime(request.deadline)
        if saved_rec:
            saved_rec.resume_id = resume.id
            if request.notes:
                saved_rec.notes = request.notes
            if parsed_deadline is not None:
                saved_rec.deadline = parsed_deadline
            saved_rec.application_packet = packet
        else:
            saved_rec = SavedJob(
                id=str(uuid.uuid4()),
                firebase_uid=firebase_uid,
                job_id=job.id,
                status="saved",
                notes=request.notes,
                deadline=parsed_deadline,
                resume_id=resume.id,
                application_packet=packet,
            )
            db.add(saved_rec)

        await db.commit()
        await db.refresh(saved_rec)

        # 7. Queue Human Approval Gate
        approval = await approval_workflow_agent.queue_approval_request(
            db=db,
            firebase_uid=firebase_uid,
            thread_id=f"app_thread_{job.id[:8]}",
            action_type="job_application",
            action_description=f"Submit application to {job.company} for {job.title}",
            payload=packet,
            target_entity_id=job.id,
        )

        return ApplicationPrepareResponse(
            job_id=job.id,
            approval_request_id=approval.id,
            status="pending_approval",
            application_packet=packet,
        )

    @classmethod
    async def list_applications(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        status_filter: str | None = None,
    ) -> list[ApplicationDetailResponse]:
        """List tracked applications with associated posting details."""
        stmt = (
            select(SavedJob)
            .where(SavedJob.firebase_uid == firebase_uid)
        )
        if status_filter:
            stmt = stmt.where(SavedJob.status == status_filter)
        stmt = stmt.order_by(SavedJob.created_at.desc())

        res = await db.execute(stmt)
        records = res.scalars().all()

        results: list[ApplicationDetailResponse] = []
        for rec in records:
            post_stmt = select(JobPosting).where(JobPosting.id == rec.job_id)
            posting = (await db.execute(post_stmt)).scalar_one_or_none()

            results.append(
                ApplicationDetailResponse(
                    id=rec.id,
                    firebase_uid=rec.firebase_uid,
                    job_id=rec.job_id,
                    status=rec.status,
                    notes=rec.notes,
                    deadline=rec.deadline,
                    submitted_at=rec.submitted_at,
                    resume_id=rec.resume_id,
                    application_packet=rec.application_packet or {},
                    created_at=rec.created_at,
                    updated_at=rec.updated_at,
                    job=JobPostingResponse.model_validate(posting) if posting else None,
                )
            )

        return results

    @classmethod
    async def get_application(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        job_id: str,
    ) -> ApplicationDetailResponse:
        """Retrieve single application tracking record."""
        stmt = select(SavedJob).where(
            SavedJob.firebase_uid == firebase_uid,
            SavedJob.job_id == job_id,
        )
        res = await db.execute(stmt)
        rec = res.scalar_one_or_none()
        if not rec:
            raise ResourceNotFoundError("Job application", job_id)

        post_stmt = select(JobPosting).where(JobPosting.id == rec.job_id)
        posting = (await db.execute(post_stmt)).scalar_one_or_none()

        return ApplicationDetailResponse(
            id=rec.id,
            firebase_uid=rec.firebase_uid,
            job_id=rec.job_id,
            status=rec.status,
            notes=rec.notes,
            deadline=rec.deadline,
            submitted_at=rec.submitted_at,
            resume_id=rec.resume_id,
            application_packet=rec.application_packet or {},
            created_at=rec.created_at,
            updated_at=rec.updated_at,
            job=JobPostingResponse.model_validate(posting) if posting else None,
        )

    @classmethod
    async def update_application(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        job_id: str,
        payload: ApplicationUpdateRequest,
    ) -> ApplicationDetailResponse:
        """Update tracking status, notes, or deadlines."""
        stmt = select(SavedJob).where(
            SavedJob.firebase_uid == firebase_uid,
            SavedJob.job_id == job_id,
        )
        res = await db.execute(stmt)
        rec = res.scalar_one_or_none()
        if not rec:
            raise ResourceNotFoundError("Job application", job_id)

        if payload.status is not None:
            rec.status = payload.status
        if payload.notes is not None:
            rec.notes = payload.notes
        if payload.deadline is not None:
            rec.deadline = _coerce_datetime(payload.deadline)
        if payload.submitted_at is not None:
            rec.submitted_at = _coerce_datetime(payload.submitted_at)

        await db.commit()
        await db.refresh(rec)

        post_stmt = select(JobPosting).where(JobPosting.id == rec.job_id)
        posting = (await db.execute(post_stmt)).scalar_one_or_none()

        return ApplicationDetailResponse(
            id=rec.id,
            firebase_uid=rec.firebase_uid,
            job_id=rec.job_id,
            status=rec.status,
            notes=rec.notes,
            deadline=rec.deadline,
            submitted_at=rec.submitted_at,
            resume_id=rec.resume_id,
            application_packet=rec.application_packet or {},
            created_at=rec.created_at,
            updated_at=rec.updated_at,
            job=JobPostingResponse.model_validate(posting) if posting else None,
        )

    @classmethod
    async def delete_application(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        job_id: str,
    ) -> None:
        """Delete an application record."""
        stmt = select(SavedJob).where(
            SavedJob.firebase_uid == firebase_uid,
            SavedJob.job_id == job_id,
        )
        res = await db.execute(stmt)
        rec = res.scalar_one_or_none()
        if not rec:
            raise ResourceNotFoundError("Job application", job_id)

        await db.delete(rec)
        await db.commit()


application_service = ApplicationService()
