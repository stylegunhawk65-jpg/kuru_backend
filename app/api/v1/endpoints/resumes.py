"""Authenticated endpoints for ATS-compliant resume generation, management, and PDF export."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.schemas.resume import (
    BaseCVConfirmRequest,
    BaseCVResponse,
    ResumeCreate,
    ResumeGenerateRequest,
    ResumeResponse,
    ResumeUpdate,
)
from app.services.resume.cv_parser import CVParserError
from app.services.resume.service import resume_service

logger = logging.getLogger("kuru.resumes.api")
router = APIRouter()


@router.post(
    "/cv/upload",
    response_model=BaseCVResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and Parse Base CV",
    description="Upload a PDF or DOCX CV document. Validates file integrity, extracts structured candidate details, and stores securely.",
)
async def upload_base_cv(
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Upload and parse a base CV/resume file."""
    content = await file.read()
    try:
        return await resume_service.upload_base_cv(
            db=db,
            firebase_uid=current_user.uid,
            filename=file.filename or "cv.pdf",
            content=content,
        )
    except CVParserError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/cv",
    response_model=BaseCVResponse | None,
    summary="Get Current Base CV",
    description="Retrieve active base CV and parsed details for the authenticated user.",
)
async def get_base_cv(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Retrieve the uploaded base CV."""
    return await resume_service.get_base_cv(db=db, firebase_uid=current_user.uid)


@router.put(
    "/cv/confirm",
    response_model=BaseCVResponse,
    summary="Confirm or Edit Extracted CV Details",
    description="Allows the candidate to review, correct, and confirm extracted CV information before using it for tailoring.",
)
async def confirm_base_cv(
    payload: BaseCVConfirmRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Confirm or update extracted entities on the base CV."""
    return await resume_service.confirm_base_cv(
        db=db,
        firebase_uid=current_user.uid,
        payload=payload,
    )


class ResumeTailorRequest(BaseModel):
    """Payload to tailor resume for role and company."""

    target_role: str = Field(default="Software Engineer", description="Target role name")
    target_company: str | None = Field(default=None, description="Target company name")
    job_id: str | None = Field(default=None, description="Optional job ID")


@router.post(
    "/tailor",
    response_model=ResumeResponse,
    status_code=status.HTTP_200_OK,
    summary="Tailor Resume for Role and Company",
    description="Synthesize an ATS resume tailored for a specific role and company.",
)
async def tailor_resume(
    payload: ResumeTailorRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Tailor resume for role and company."""
    gen_req = ResumeGenerateRequest(
        target_role=payload.target_role,
        target_company=payload.target_company,
        job_id=payload.job_id,
        custom_instructions=f"Target company: {payload.target_company}" if payload.target_company else None,
        save_to_db=True,
    )
    return await resume_service.generate_resume(
        db=db,
        firebase_uid=current_user.uid,
        request=gen_req,
    )


@router.post(
    "/generate",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate ATS-Friendly Tailored Resume",
    description=(
        "Synthesize an evidence-backed ATS resume from verified candidate profile, "
        "GitHub projects, and practical coding assessments, tailored against a real job description. "
        "Strictly prevents hallucination."
    ),
)
async def generate_resume(
    payload: ResumeGenerateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Generate and optionally persist a tailored ATS resume."""
    return await resume_service.generate_resume(
        db=db,
        firebase_uid=current_user.uid,
        request=payload,
    )


@router.post(
    "",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save Customized Resume",
    description="Save a new or customized resume document with full per-user data isolation.",
)
async def create_resume(
    payload: ResumeCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Persist a customized resume."""
    return await resume_service.create_resume(
        db=db,
        firebase_uid=current_user.uid,
        payload=payload,
    )


@router.get(
    "",
    response_model=list[ResumeResponse],
    summary="List Saved Resumes",
    description="Retrieve all tailored resumes saved by the authenticated user.",
)
async def list_resumes(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List resumes for the current authenticated user."""
    return await resume_service.list_resumes(
        db=db,
        firebase_uid=current_user.uid,
    )


@router.get(
    "/{id}",
    response_model=ResumeResponse,
    summary="Get Resume Preview",
    description="Retrieve structured resume details for preview and rendering.",
)
async def get_resume(
    id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get a single resume by ID."""
    return await resume_service.get_resume(
        db=db,
        firebase_uid=current_user.uid,
        resume_id=id,
    )


@router.put(
    "/{id}",
    response_model=ResumeResponse,
    summary="Edit Resume",
    description="Update summary, bullet points, skills, or projects in an existing resume.",
)
async def update_resume(
    id: str,
    payload: ResumeUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update resume fields."""
    return await resume_service.update_resume(
        db=db,
        firebase_uid=current_user.uid,
        resume_id=id,
        payload=payload,
    )


@router.post(
    "/{id}/regenerate",
    response_model=ResumeResponse,
    summary="Regenerate Resume",
    description="Re-tailor an existing resume with updated portfolio evidence and optional instructions.",
)
async def regenerate_resume(
    id: str,
    custom_instructions: str | None = Query(None, description="Optional custom instructions to guide regeneration"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Regenerate resume with fresh evidence."""
    return await resume_service.regenerate_resume(
        db=db,
        firebase_uid=current_user.uid,
        resume_id=id,
        custom_instructions=custom_instructions,
    )


@router.get(
    "/{id}/pdf",
    summary="Export Resume to ATS-Compliant PDF",
    description="Render the resume into a clean, professional, ATS-parseable PDF document.",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Binary PDF document stream.",
        }
    },
)
async def export_resume_pdf(
    id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export resume as binary PDF."""
    pdf_bytes, filename = await resume_service.export_pdf(
        db=db,
        firebase_uid=current_user.uid,
        resume_id=id,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/pdf",
        },
    )


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Resume",
    description="Remove a saved resume.",
)
async def delete_resume(
    id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete resume."""
    await resume_service.delete_resume(
        db=db,
        firebase_uid=current_user.uid,
        resume_id=id,
    )
