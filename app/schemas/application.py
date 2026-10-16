"""Pydantic schemas for Job Application preparation, tracking, and approval workflow."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.job import JobPostingResponse


class ApplicationPrepareRequest(BaseModel):
    """Payload to synthesize job-specific application materials and stage for human approval."""

    job_id: str = Field(..., description="Target JobPosting ID")
    resume_id: str | None = Field(default=None, description="Optional tailored Resume ID (generated if omitted)")
    cover_note: str | None = Field(default=None, max_length=2000, description="Optional customized statement of interest")
    notes: str | None = Field(default=None, max_length=1000, description="Personal application tracking notes")
    deadline: datetime | None = Field(default=None, description="Application submission deadline")


class ApplicationPrepareResponse(BaseModel):
    """Result of application material preparation with queued approval request."""

    job_id: str
    approval_request_id: str
    status: str = "pending_approval"
    application_packet: dict[str, Any]
    consequential_action_notice: str = (
        "HUMAN-IN-THE-LOOP REQUIREMENT: Application materials have been staged and queued. "
        "The system will NEVER submit an application externally without your explicit cryptographic approval."
    )


class ApplicationUpdateRequest(BaseModel):
    """Payload to update an existing application's tracking stage or notes."""

    status: str | None = Field(
        default=None,
        pattern="^(saved|applied|interviewing|offered|rejected|archived)$",
    )
    notes: str | None = Field(default=None, max_length=1000)
    deadline: datetime | None = None
    submitted_at: datetime | None = None


class ApplicationDetailResponse(BaseModel):
    """Complete application tracking record with embedded job and packet details."""

    id: str
    firebase_uid: str
    job_id: str
    status: str
    notes: str | None = None
    deadline: datetime | None = None
    submitted_at: datetime | None = None
    resume_id: str | None = None
    application_packet: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    job: JobPostingResponse | None = None

    model_config = ConfigDict(from_attributes=True)
