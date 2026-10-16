"""Service coordinating resume generation, preview, editing, regeneration, and PDF export."""

import logging
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError
from app.models.resume import Resume
from app.schemas.resume import (
    ResumeCreate,
    ResumeGenerateRequest,
    ResumeResponse,
    ResumeUpdate,
)
from app.services.llm.base import BaseLLMProvider
from app.services.resume.generator import resume_generator
from app.services.resume.pdf_exporter import resume_pdf_exporter

logger = logging.getLogger("kuru.resume.service")


class ResumeService:
    """Service handling high-level operations for ATS tailored resumes."""

    @classmethod
    async def generate_resume(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        request: ResumeGenerateRequest,
        provider: BaseLLMProvider | None = None,
    ) -> Resume:
        """Synthesize tailored resume data from real student portfolio and optionally persist."""
        data = await resume_generator.generate_resume_data(
            db=db,
            firebase_uid=firebase_uid,
            request=request,
            provider=provider,
        )

        resume_id = str(uuid.uuid4())
        record = Resume(
            id=resume_id,
            firebase_uid=firebase_uid,
            job_id=data.get("job_id"),
            title=data.get("title", f"{request.target_role} Resume"),
            target_role=request.target_role,
            contact_info=data["contact_info"],
            summary=data["summary"],
            skills_by_category=data["skills_by_category"],
            experience=data["experience"],
            projects=data["projects"],
            education=data["education"],
            practical_assessments=data["practical_assessments"],
            tailoring_metadata=data["tailoring_metadata"],
            is_primary=False,
        )

        if request.save_to_db:
            db.add(record)
            await db.commit()
            await db.refresh(record)

        return record

    @classmethod
    async def create_resume(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        payload: ResumeCreate,
    ) -> Resume:
        """Persist a newly authored or customized resume."""
        record = Resume(
            id=str(uuid.uuid4()),
            firebase_uid=firebase_uid,
            job_id=payload.job_id,
            title=payload.title,
            target_role=payload.target_role,
            contact_info=payload.contact_info.model_dump(),
            summary=payload.summary,
            skills_by_category={k: [s.model_dump() for s in v] for k, v in payload.skills_by_category.items()},
            experience=[e.model_dump() for e in payload.experience],
            projects=[p.model_dump() for p in payload.projects],
            education=[e.model_dump() for e in payload.education],
            practical_assessments=[a.model_dump() for a in payload.practical_assessments],
            tailoring_metadata=payload.tailoring_metadata.model_dump() if payload.tailoring_metadata else {},
            is_primary=payload.is_primary,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @classmethod
    async def list_resumes(
        cls,
        db: AsyncSession,
        firebase_uid: str,
    ) -> list[Resume]:
        """List all resumes saved by the authenticated user."""
        stmt = (
            select(Resume)
            .where(Resume.firebase_uid == firebase_uid)
            .order_by(Resume.created_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def get_resume(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        resume_id: str,
    ) -> Resume:
        """Retrieve a specific resume ensuring per-user isolation."""
        stmt = select(Resume).where(
            Resume.id == resume_id,
            Resume.firebase_uid == firebase_uid,
        )
        res = await db.execute(stmt)
        record = res.scalar_one_or_none()
        if not record:
            raise ResourceNotFoundError("Resume", resume_id)
        return record

    @classmethod
    async def update_resume(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        resume_id: str,
        payload: ResumeUpdate,
    ) -> Resume:
        """Edit an existing resume."""
        record = await cls.get_resume(db, firebase_uid, resume_id)

        if payload.title is not None:
            record.title = payload.title
        if payload.target_role is not None:
            record.target_role = payload.target_role
        if payload.contact_info is not None:
            record.contact_info = payload.contact_info.model_dump()
        if payload.summary is not None:
            record.summary = payload.summary
        if payload.skills_by_category is not None:
            record.skills_by_category = {k: [s.model_dump() for s in v] for k, v in payload.skills_by_category.items()}
        if payload.experience is not None:
            record.experience = [e.model_dump() for e in payload.experience]
        if payload.projects is not None:
            record.projects = [p.model_dump() for p in payload.projects]
        if payload.education is not None:
            record.education = [e.model_dump() for e in payload.education]
        if payload.practical_assessments is not None:
            record.practical_assessments = [a.model_dump() for a in payload.practical_assessments]
        if payload.is_primary is not None:
            record.is_primary = payload.is_primary

        await db.commit()
        await db.refresh(record)
        return record

    @classmethod
    async def regenerate_resume(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        resume_id: str,
        custom_instructions: str | None = None,
        provider: BaseLLMProvider | None = None,
    ) -> Resume:
        """Re-tailor an existing resume with updated portfolio evidence and optional instructions."""
        existing = await cls.get_resume(db, firebase_uid, resume_id)

        req = ResumeGenerateRequest(
            target_role=existing.target_role,
            job_id=existing.job_id,
            custom_instructions=custom_instructions,
            save_to_db=False,
        )

        fresh_data = await resume_generator.generate_resume_data(
            db=db,
            firebase_uid=firebase_uid,
            request=req,
            provider=provider,
        )

        existing.summary = fresh_data["summary"]
        existing.skills_by_category = fresh_data["skills_by_category"]
        existing.projects = fresh_data["projects"]
        existing.practical_assessments = fresh_data["practical_assessments"]
        existing.tailoring_metadata = fresh_data["tailoring_metadata"]

        await db.commit()
        await db.refresh(existing)
        return existing

    @classmethod
    async def export_pdf(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        resume_id: str,
    ) -> tuple[bytes, str]:
        """Generate PDF bytes for a resume and formulate filename."""
        record = await cls.get_resume(db, firebase_uid, resume_id)

        resume_dict = {
            "title": record.title,
            "target_role": record.target_role,
            "contact_info": record.contact_info,
            "summary": record.summary,
            "skills_by_category": record.skills_by_category,
            "experience": record.experience,
            "projects": record.projects,
            "education": record.education,
            "practical_assessments": record.practical_assessments,
            "tailoring_metadata": record.tailoring_metadata,
        }

        pdf_bytes = resume_pdf_exporter.export_pdf(resume_dict)

        clean_name = (record.contact_info.get("full_name") or "Resume").replace(" ", "_")
        clean_role = record.target_role.replace(" ", "_")
        filename = f"{clean_name}_{clean_role}_Resume.pdf"

        return pdf_bytes, filename

    @classmethod
    async def delete_resume(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        resume_id: str,
    ) -> None:
        """Delete a saved resume."""
        record = await cls.get_resume(db, firebase_uid, resume_id)
        await db.delete(record)
        await db.commit()


resume_service = ResumeService()
