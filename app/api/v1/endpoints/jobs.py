"""Authenticated Job and Internship endpoints with personalized transparent matching."""

import logging
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.exceptions import ResourceNotFoundError
from app.db.session import get_db
from app.models.job import JobPosting, SavedJob
from app.models.profile import StudentProfile
from app.models.skill import StudentSkill
from app.schemas.job import (
    JobListResponse,
    JobPostingResponse,
    JobPostingWithMatchResponse,
    JobSourceStatusResponse,
    SavedJobCreate,
    SavedJobResponse,
    SavedJobUpdate,
    SyncTriggerResponse,
)
from app.services.job_sources.aggregator import job_source_manager
from app.services.matcher import calculate_job_match
from app.services.notification_service import notification_service

logger = logging.getLogger("kuru.jobs")
router = APIRouter()


@router.get(
    "/sources/status",
    response_model=list[JobSourceStatusResponse],
    summary="List Job Sources Health and Sync Status",
    description="Check configuration status, health metrics, and last sync timestamp for all job adapters.",
)
async def get_source_statuses(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieve statuses for all configured job sources."""
    return await job_source_manager.get_source_statuses(db)


@router.post(
    "/sources/sync",
    response_model=SyncTriggerResponse,
    summary="Trigger Job Source Sync",
    description="Trigger an immediate synchronization of jobs from one or all enabled sources.",
)
async def trigger_source_sync(
    source_name: str | None = Query(None, description="Specific provider name (e.g., curated_india, arbeitnow)"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SyncTriggerResponse:
    """Synchronize jobs from external/curated providers."""
    if source_name:
        adapter = job_source_manager.get_adapter(source_name)
        if not adapter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job source '{source_name}' does not exist.",
            )
        res = await job_source_manager.sync_source(db, source_name)
        return SyncTriggerResponse(
            message=f"Sync finished for source '{source_name}'.",
            results={source_name: res},
        )

    res = await job_source_manager.sync_all(db)
    return SyncTriggerResponse(
        message="Sync finished for all enabled sources.",
        results=res,
    )


@router.get(
    "/saved",
    response_model=list[SavedJobResponse],
    summary="List User's Saved Jobs",
    description="Retrieve all bookmarked jobs with application status and private notes for the authenticated user.",
)
async def get_saved_jobs(
    status_filter: str | None = Query(None, alias="status", description="Filter by status (saved, applied, interviewing, offered, rejected, archived)"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SavedJobResponse]:
    """Retrieve saved jobs/applications for current user."""
    stmt = (
        select(SavedJob)
        .where(SavedJob.firebase_uid == current_user.uid)
    )
    if status_filter:
        stmt = stmt.where(SavedJob.status == status_filter)
    stmt = stmt.order_by(SavedJob.created_at.desc())

    res = await db.execute(stmt)
    saved_items = res.scalars().all()

    response_items: list[SavedJobResponse] = []
    for item in saved_items:
        # Load associated posting
        post_stmt = select(JobPosting).where(JobPosting.id == item.job_id)
        post_res = await db.execute(post_stmt)
        posting = post_res.scalar_one_or_none()

        posting_schema = JobPostingResponse.model_validate(posting) if posting else None
        response_items.append(
            SavedJobResponse(
                id=item.id,
                firebase_uid=item.firebase_uid,
                job_id=item.job_id,
                status=item.status,
                notes=item.notes,
                deadline=item.deadline,
                submitted_at=item.submitted_at,
                resume_id=item.resume_id,
                application_packet=item.application_packet or {},
                created_at=item.created_at,
                updated_at=item.updated_at,
                job=posting_schema,
            )
        )

    return response_items


@router.patch(
    "/saved/{job_id}",
    response_model=SavedJobResponse,
    summary="Update Saved Job Status or Notes",
    description="Update tracking state (saved, applied, interviewing, offered, rejected, archived), deadline, or notes.",
)
async def update_saved_job(
    job_id: str,
    payload: SavedJobUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SavedJobResponse:
    """Update notes, status, deadline, or submitted date on a saved job."""
    stmt = select(SavedJob).where(
        SavedJob.firebase_uid == current_user.uid,
        SavedJob.job_id == job_id,
    )
    res = await db.execute(stmt)
    saved_record = res.scalar_one_or_none()

    if not saved_record:
        raise ResourceNotFoundError("Saved job record", job_id)

    old_status = saved_record.status
    if payload.status is not None:
        notification_service.validate_status_transition(old_status, payload.status)
        saved_record.status = payload.status
    if payload.notes is not None:
        saved_record.notes = payload.notes
    if payload.deadline is not None:
        saved_record.deadline = payload.deadline
    if payload.submitted_at is not None:
        saved_record.submitted_at = payload.submitted_at
    if payload.resume_id is not None:
        saved_record.resume_id = payload.resume_id

    await db.commit()
    await db.refresh(saved_record)

    if payload.status is not None and payload.status != old_status:
        await notification_service.handle_application_status_change(
            db=db,
            firebase_uid=current_user.uid,
            job_id=job_id,
            old_status=old_status,
            new_status=payload.status,
        )

    # Load associated posting
    post_stmt = select(JobPosting).where(JobPosting.id == job_id)
    post_res = await db.execute(post_stmt)
    posting = post_res.scalar_one_or_none()

    return SavedJobResponse(
        id=saved_record.id,
        firebase_uid=saved_record.firebase_uid,
        job_id=saved_record.job_id,
        status=saved_record.status,
        notes=saved_record.notes,
        deadline=saved_record.deadline,
        submitted_at=saved_record.submitted_at,
        resume_id=saved_record.resume_id,
        application_packet=saved_record.application_packet or {},
        created_at=saved_record.created_at,
        updated_at=saved_record.updated_at,
        job=JobPostingResponse.model_validate(posting) if posting else None,
    )


@router.get(
    "",
    response_model=JobListResponse,
    summary="Search, Filter, and Rank Jobs",
    description="Search active jobs and internships with personalized, transparent match ranking against skills and profile.",
)
async def list_jobs(
    query: str | None = Query(None, description="Search term for title, company, or description"),
    location: str | None = Query(None, description="Location search string (e.g. Bengaluru, Remote)"),
    is_remote: bool | None = Query(None, description="Filter for fully remote opportunities"),
    job_type: str | None = Query(None, description="Job type: full_time, internship, part_time, contract"),
    skill: str | None = Query(None, description="Required skill filter"),
    min_match: float | None = Query(None, ge=0.0, le=100.0, description="Minimum match percentage threshold"),
    sort_by: str = Query("match", pattern="^(match|freshness|created_at)$", description="Sorting criteria"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    """List jobs filtered and ranked by transparent matching formula."""
    # Ensure baseline curated jobs are available if database is empty
    count_stmt = select(JobPosting).limit(1)
    count_res = await db.execute(count_stmt)
    if not count_res.scalar_one_or_none():
        await job_source_manager.sync_source(db, "curated_india")

    # Load authenticated user profile
    prof_stmt = select(StudentProfile).where(StudentProfile.firebase_uid == current_user.uid)
    prof_res = await db.execute(prof_stmt)
    profile = prof_res.scalar_one_or_none()

    # Load authenticated user skills from Phase 3
    skills_stmt = select(StudentSkill).where(StudentSkill.firebase_uid == current_user.uid)
    skills_res = await db.execute(skills_stmt)
    skills = skills_res.scalars().all()

    # Load user's saved job IDs
    saved_stmt = select(SavedJob.job_id).where(SavedJob.firebase_uid == current_user.uid)
    saved_res = await db.execute(saved_stmt)
    saved_ids = set(saved_res.scalars().all())

    # Build DB filter query
    stmt = select(JobPosting).where(JobPosting.is_active == True)

    if is_remote is not None:
        stmt = stmt.where(JobPosting.is_remote == is_remote)
    if job_type:
        stmt = stmt.where(JobPosting.job_type == job_type)
    if location:
        stmt = stmt.where(JobPosting.location.ilike(f"%{location}%"))
    if query:
        q_term = f"%{query}%"
        stmt = stmt.where(
            or_(
                JobPosting.title.ilike(q_term),
                JobPosting.company.ilike(q_term),
                JobPosting.description.ilike(q_term),
            )
        )

    res = await db.execute(stmt)
    postings = res.scalars().all()

    # Process match scoring and memory-level filters (skill list search, threshold)
    enriched_items: list[JobPostingWithMatchResponse] = []
    skill_filter_norm = skill.lower().strip() if skill else None

    for job in postings:
        # Check specific skill if requested
        if skill_filter_norm:
            has_skill = any(
                skill_filter_norm in s.lower() for s in (job.required_skills or [])
            )
            if not has_skill:
                continue

        # Compute transparent baseline match
        match_result = calculate_job_match(job, profile, skills)

        if min_match is not None and match_result.match_score < min_match:
            continue

        enriched_items.append(
            JobPostingWithMatchResponse(
                id=job.id,
                source=job.source,
                source_id=job.source_id,
                title=job.title,
                company=job.company,
                location=job.location,
                is_remote=job.is_remote,
                job_type=job.job_type,
                description=job.description,
                url=job.url,
                required_skills=job.required_skills,
                salary_currency=job.salary_currency,
                salary_min=job.salary_min,
                salary_max=job.salary_max,
                posted_at=job.posted_at,
                last_seen_at=job.last_seen_at,
                is_active=job.is_active,
                created_at=job.created_at,
                match_score=match_result.match_score,
                matched_skills=match_result.matched_skills,
                missing_skills=match_result.missing_skills,
                match_reasons=match_result.match_reasons,
                is_saved=job.id in saved_ids,
            )
        )

    # Sort
    if sort_by == "match":
        enriched_items.sort(key=lambda j: (j.match_score or 0.0), reverse=True)
    elif sort_by == "freshness":
        enriched_items.sort(key=lambda j: j.last_seen_at, reverse=True)
    elif sort_by == "created_at":
        enriched_items.sort(key=lambda j: j.created_at, reverse=True)

    # Paginate
    total = len(enriched_items)
    start = (page - 1) * limit
    paginated_items = enriched_items[start : start + limit]

    return JobListResponse(
        items=paginated_items,
        total=total,
        page=page,
        limit=limit,
        has_next=(start + limit) < total,
    )


@router.get(
    "/{job_id}",
    response_model=JobPostingWithMatchResponse,
    summary="Get Job Details",
    description="Retrieve details for a single job posting with transparent match reasons and saved state.",
)
async def get_job_details(
    job_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobPostingWithMatchResponse:
    """Retrieve posting details with personalized match computation."""
    stmt = select(JobPosting).where(JobPosting.id == job_id)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()

    if not job:
        raise ResourceNotFoundError("Job posting", job_id)

    # Load profile and skills
    prof_stmt = select(StudentProfile).where(StudentProfile.firebase_uid == current_user.uid)
    prof_res = await db.execute(prof_stmt)
    profile = prof_res.scalar_one_or_none()

    skills_stmt = select(StudentSkill).where(StudentSkill.firebase_uid == current_user.uid)
    skills_res = await db.execute(skills_stmt)
    skills = skills_res.scalars().all()

    # Check saved
    saved_stmt = select(SavedJob).where(
        SavedJob.firebase_uid == current_user.uid,
        SavedJob.job_id == job_id,
    )
    saved_res = await db.execute(saved_stmt)
    is_saved = saved_res.scalar_one_or_none() is not None

    match_result = calculate_job_match(job, profile, skills)

    return JobPostingWithMatchResponse(
        id=job.id,
        source=job.source,
        source_id=job.source_id,
        title=job.title,
        company=job.company,
        location=job.location,
        is_remote=job.is_remote,
        job_type=job.job_type,
        description=job.description,
        url=job.url,
        required_skills=job.required_skills,
        salary_currency=job.salary_currency,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        posted_at=job.posted_at,
        last_seen_at=job.last_seen_at,
        is_active=job.is_active,
        created_at=job.created_at,
        match_score=match_result.match_score,
        matched_skills=match_result.matched_skills,
        missing_skills=match_result.missing_skills,
        match_reasons=match_result.match_reasons,
        is_saved=is_saved,
    )


@router.post(
    "/{job_id}/save",
    response_model=SavedJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save / Bookmark Job",
    description="Bookmark a job posting for the authenticated student.",
)
async def save_job(
    job_id: str,
    payload: SavedJobCreate = SavedJobCreate(),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SavedJobResponse:
    """Bookmark a job posting."""
    # Ensure job exists
    job_stmt = select(JobPosting).where(JobPosting.id == job_id)
    job_res = await db.execute(job_stmt)
    job = job_res.scalar_one_or_none()
    if not job:
        raise ResourceNotFoundError("Job posting", job_id)

    # Check if already saved
    stmt = select(SavedJob).where(
        SavedJob.firebase_uid == current_user.uid,
        SavedJob.job_id == job_id,
    )
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()

    if existing:
        existing.status = payload.status
        if payload.notes is not None:
            existing.notes = payload.notes
        if payload.deadline is not None:
            existing.deadline = payload.deadline
        if payload.resume_id is not None:
            existing.resume_id = payload.resume_id
        await db.commit()
        await db.refresh(existing)
        saved_rec = existing
    else:
        new_saved = SavedJob(
            id=str(uuid.uuid4()),
            firebase_uid=current_user.uid,
            job_id=job_id,
            status=payload.status,
            notes=payload.notes,
            deadline=payload.deadline,
            resume_id=payload.resume_id,
        )
        db.add(new_saved)
        await db.commit()
        await db.refresh(new_saved)
        saved_rec = new_saved

    return SavedJobResponse(
        id=saved_rec.id,
        firebase_uid=saved_rec.firebase_uid,
        job_id=saved_rec.job_id,
        status=saved_rec.status,
        notes=saved_rec.notes,
        deadline=saved_rec.deadline,
        submitted_at=saved_rec.submitted_at,
        resume_id=saved_rec.resume_id,
        application_packet=saved_rec.application_packet or {},
        created_at=saved_rec.created_at,
        updated_at=saved_rec.updated_at,
        job=JobPostingResponse.model_validate(job),
    )


@router.delete(
    "/{job_id}/save",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove Saved Job",
    description="Remove a bookmarked job for the authenticated student.",
)
async def unsave_job(
    job_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Remove a bookmark on a job."""
    stmt = select(SavedJob).where(
        SavedJob.firebase_uid == current_user.uid,
        SavedJob.job_id == job_id,
    )
    res = await db.execute(stmt)
    record = res.scalar_one_or_none()

    if not record:
        raise ResourceNotFoundError("Saved job record", job_id)

    await db.delete(record)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
