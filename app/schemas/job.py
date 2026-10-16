"""Validation and serialization schemas for jobs, saved jobs, and source sync status."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class JobPostingResponse(BaseModel):
    """Schema representing an individual job posting."""

    id: str
    source: str
    source_id: str
    title: str
    company: str
    location: str
    is_remote: bool
    job_type: str
    description: str
    url: str
    required_skills: list[str] = []
    salary_currency: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    posted_at: datetime | None = None
    last_seen_at: datetime
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobPostingWithMatchResponse(JobPostingResponse):
    """Job posting enriched with personalized baseline match breakdown and saved state."""

    match_score: float | None = None
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    match_reasons: list[str] = []
    is_saved: bool = False


class JobListResponse(BaseModel):
    """Paginated collection of job postings with total count."""

    items: list[JobPostingWithMatchResponse]
    total: int
    page: int
    limit: int
    has_next: bool


class SavedJobCreate(BaseModel):
    """Request payload to bookmark/save a job posting."""

    notes: str | None = Field(None, max_length=1000, description="Personal application notes")
    status: str = Field(
        default="saved",
        pattern="^(saved|applied|archived)$",
        description="Tracking status: saved, applied, or archived",
    )


class SavedJobUpdate(BaseModel):
    """Request payload to update tracking status or notes for a saved job."""

    notes: str | None = Field(None, max_length=1000)
    status: str | None = Field(None, pattern="^(saved|applied|archived)$")


class SavedJobResponse(BaseModel):
    """User-bookmarked job record with embedded posting details."""

    id: str
    firebase_uid: str
    job_id: str
    status: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    job: JobPostingResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class JobSourceStatusResponse(BaseModel):
    """Health, sync metrics, and configuration status for an external provider."""

    id: str
    source_name: str
    is_enabled: bool
    is_configured: bool
    last_sync_at: datetime | None = None
    last_sync_status: str
    jobs_synced_count: int
    error_message: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SyncTriggerResponse(BaseModel):
    """Response returned upon triggering a job source synchronization."""

    message: str
    results: dict[str, Any]
