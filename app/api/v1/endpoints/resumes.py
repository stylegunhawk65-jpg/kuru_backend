"""Authenticated endpoints for ATS-compliant resume generation, management, and PDF export."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.schemas.resume import (
    ResumeCreate,
    ResumeGenerateRequest,
    ResumeResponse,
    ResumeUpdate,
)
from app.services.resume.service import resume_service

logger = logging.getLogger("kuru.resumes.api")
router = APIRouter()


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
