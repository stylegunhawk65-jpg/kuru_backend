"""Authenticated endpoints for job application preparation, lifecycle tracking, and approval gates."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.schemas.application import (
    ApplicationDetailResponse,
    ApplicationPrepareRequest,
    ApplicationPrepareResponse,
    ApplicationUpdateRequest,
)
from app.services.application_service import application_service

logger = logging.getLogger("kuru.applications.api")
router = APIRouter()


@router.post(
    "/prepare",
    response_model=ApplicationPrepareResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Prepare Application Materials and Queue Approval",
    description=(
        "Synthesizes job-specific application materials (tailored ATS resume, evidence citations, cover note) "
        "and queues an AgentApprovalRequest. External auto-application is blocked until explicit user approval."
    ),
)
async def prepare_application(
    payload: ApplicationPrepareRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Prepare job application materials and stage approval request."""
    return await application_service.prepare_application(
        db=db,
        firebase_uid=current_user.uid,
        request=payload,
    )


@router.get(
    "",
    response_model=list[ApplicationDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="List Tracked Applications",
    description="Retrieve all tracked job applications for the authenticated user, optionally filtered by status.",
)
async def list_applications(
    status: str | None = Query(
        default=None,
        description="Filter by lifecycle status: saved, applied, interviewing, offered, rejected, archived",
    ),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List tracked applications for the authenticated user."""
    return await application_service.list_applications(
        db=db,
        firebase_uid=current_user.uid,
        status_filter=status,
    )


@router.get(
    "/{job_id}",
    response_model=ApplicationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Application Details",
    description="Retrieve single tracked application record with job posting details and application packet.",
)
async def get_application(
    job_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Retrieve application details by job ID."""
    return await application_service.get_application(
        db=db,
        firebase_uid=current_user.uid,
        job_id=job_id,
    )


@router.patch(
    "/{job_id}",
    response_model=ApplicationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Application Tracking Status & Notes",
    description="Update tracking status (saved, applied, interviewing, offered, rejected, archived), personal notes, or deadlines.",
)
async def update_application(
    job_id: str,
    payload: ApplicationUpdateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update tracking status, notes, or deadlines."""
    return await application_service.update_application(
        db=db,
        firebase_uid=current_user.uid,
        job_id=job_id,
        payload=payload,
    )


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Application Record",
    description="Remove an application tracking record for the authenticated user.",
)
async def delete_application(
    job_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete an application record."""
    await application_service.delete_application(
        db=db,
        firebase_uid=current_user.uid,
        job_id=job_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
