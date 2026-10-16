"""Authenticated Career Intelligence endpoints for skill gaps, recommendations, and simulations."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.models.job import JobPosting
from app.models.profile import StudentProfile
from app.models.skill import SkillGraphEdge, StudentSkill
from app.schemas.intelligence import (
    CareerPathCompareRequest,
    CareerPathCompareResponse,
    SkillGapReportResponse,
    SkillRecommendationItem,
    WhatIfSimulationRequest,
    WhatIfSimulationResponse,
)
from app.services.career_intelligence import career_intelligence_service
from app.services.job_sources.aggregator import job_source_manager

logger = logging.getLogger("kuru.intelligence")
router = APIRouter()


async def _ensure_baseline_jobs(db: AsyncSession) -> None:
    """Ensure baseline job listings are available in database."""
    stmt = select(JobPosting).limit(1)
    res = await db.execute(stmt)
    if not res.scalar_one_or_none():
        await job_source_manager.sync_source(db, "curated_india")


@router.get(
    "/skill-gaps",
    response_model=SkillGapReportResponse,
    summary="Get Career Skill-Gap Assessment Report",
    description="Retrieve a detailed, explainable skill-gap assessment based on verified skills and real market listings.",
)
async def get_skill_gap_report(
    target_role: str = Query("overall", description="Target role name or 'overall'"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Retrieve or compute cached skill-gap assessment report."""
    await _ensure_baseline_jobs(db)
    assessment = await career_intelligence_service.get_or_create_assessment(
        db=db,
        firebase_uid=current_user.uid,
        target_role=target_role,
        force_refresh=False,
    )
    return assessment


@router.post(
    "/skill-gaps/refresh",
    response_model=SkillGapReportResponse,
    summary="Refresh Skill-Gap Assessment Report",
    description="Force re-evaluation of skill gaps, market demand, and readiness scores, persisting a fresh snapshot.",
)
async def refresh_skill_gap_report(
    target_role: str = Query("overall", description="Target role name or 'overall'"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Recompute and update persisted skill-gap assessment report."""
    await _ensure_baseline_jobs(db)
    assessment = await career_intelligence_service.get_or_create_assessment(
        db=db,
        firebase_uid=current_user.uid,
        target_role=target_role,
        force_refresh=True,
    )
    return assessment


@router.get(
    "/recommendations",
    response_model=list[SkillRecommendationItem],
    summary="Get Actionable Skill Recommendations",
    description="Retrieve prioritized skill recommendations with market demand, job unlock impact, and synergy reasons.",
)
async def get_skill_recommendations(
    target_role: str = Query("overall", description="Target role name or 'overall'"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SkillRecommendationItem]:
    """Retrieve top recommended skills with career justification."""
    await _ensure_baseline_jobs(db)
    assessment = await career_intelligence_service.get_or_create_assessment(
        db=db,
        firebase_uid=current_user.uid,
        target_role=target_role,
        force_refresh=False,
    )
    return [
        SkillRecommendationItem.model_validate(rec)
        for rec in (assessment.recommendations or [])
    ]


@router.post(
    "/career-paths/compare",
    response_model=CareerPathCompareResponse,
    summary="Compare Career Tracks and Trajectories",
    description="Compare multiple candidate career paths with market demand, portfolio readiness, and learning runway.",
)
async def compare_career_paths(
    payload: CareerPathCompareRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CareerPathCompareResponse:
    """Compare multiple career tracks with deterministic evaluation."""
    await _ensure_baseline_jobs(db)

    # Load user data
    prof_stmt = select(StudentProfile).where(StudentProfile.firebase_uid == current_user.uid)
    profile = (await db.execute(prof_stmt)).scalar_one_or_none()

    skills_stmt = select(StudentSkill).where(StudentSkill.firebase_uid == current_user.uid)
    skills = (await db.execute(skills_stmt)).scalars().all()

    edges_stmt = select(SkillGraphEdge).where(SkillGraphEdge.firebase_uid == current_user.uid)
    edges = (await db.execute(edges_stmt)).scalars().all()

    jobs_stmt = select(JobPosting).where(JobPosting.is_active == True)
    jobs = (await db.execute(jobs_stmt)).scalars().all()

    return career_intelligence_service.compare_career_paths(
        profile=profile,
        skills=skills,
        edges=edges,
        jobs=jobs,
        roles=payload.roles,
    )


@router.post(
    "/what-if",
    response_model=WhatIfSimulationResponse,
    summary="Simulate Hypothetical Skill Acquisition",
    description="Run a what-if simulation to measure fit score gains and unlocked opportunities from hypothetical skills.",
)
async def simulate_what_if(
    payload: WhatIfSimulationRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WhatIfSimulationResponse:
    """Simulate projected impact of acquiring new skills."""
    await _ensure_baseline_jobs(db)

    # Load user data
    prof_stmt = select(StudentProfile).where(StudentProfile.firebase_uid == current_user.uid)
    profile = (await db.execute(prof_stmt)).scalar_one_or_none()

    skills_stmt = select(StudentSkill).where(StudentSkill.firebase_uid == current_user.uid)
    skills = (await db.execute(skills_stmt)).scalars().all()

    edges_stmt = select(SkillGraphEdge).where(SkillGraphEdge.firebase_uid == current_user.uid)
    edges = (await db.execute(edges_stmt)).scalars().all()

    jobs_stmt = select(JobPosting).where(JobPosting.is_active == True)
    jobs = (await db.execute(jobs_stmt)).scalars().all()

    return career_intelligence_service.simulate_what_if(
        profile=profile,
        skills=skills,
        edges=edges,
        jobs=jobs,
        hypothetical_skills=payload.hypothetical_skills,
        target_role=payload.target_role,
    )
