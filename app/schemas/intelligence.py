"""Pydantic validation schemas for Career Intelligence, Skill Gaps, and What-If Simulations."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class MatchedSkillItem(BaseModel):
    """Details of a student skill matched against job requirements."""

    skill_name: str
    category: str
    confidence_score: float
    evidence_count: int = 0
    source_repositories: list[str] = []
    verification_status: str | None = "repository_supported"  # practically_demonstrated, repository_supported, not_yet_verified
    demonstrated_score: float | None = None

    model_config = ConfigDict(from_attributes=True)


class MissingSkillItem(BaseModel):
    """Details of an absent skill observed across market listings."""

    skill_name: str
    demand_count: int
    demand_pct: float
    importance: str  # Critical, Important, Beneficial
    gap_type: str = "absent_evidence"  # demonstrated_need, absent_evidence, dependency_only
    gap_reason: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PrioritizedGapItem(BaseModel):
    """Ranked skill gap with explainable justification."""

    skill_name: str
    priority_rank: int
    priority_score: float
    market_demand_pct: float
    graph_proximity: str
    reasons: list[str]
    gap_type: str = "absent_evidence"  # demonstrated_need, absent_evidence, dependency_only

    model_config = ConfigDict(from_attributes=True)


class SkillRecommendationItem(BaseModel):
    """Actionable skill recommendation with expected career impact."""

    skill_name: str
    category: str
    market_demand_pct: float
    unlocked_jobs_count: int
    effort_estimate: str
    reason: str

    model_config = ConfigDict(from_attributes=True)


class SkillGapReportResponse(BaseModel):
    """Comprehensive skill gap and readiness assessment report."""

    id: str | None = None
    firebase_uid: str
    target_role: str
    overall_fit_score: float
    readiness_level: str
    assessed_jobs_count: int
    matched_skills: list[MatchedSkillItem] = []
    missing_skills: list[MissingSkillItem] = []
    prioritized_gaps: list[PrioritizedGapItem] = []
    recommendations: list[SkillRecommendationItem] = []
    verified_readiness_score: float | None = None
    readiness_breakdown: dict[str, Any] | None = None
    honest_disclaimer: str = (
        "Readiness is calculated strictly from objective code and assessment evidence. "
        "Repository similarity percentages in SkillProof are NEVER equated with competency or treated as AI generation indicators."
    )
    summary_notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CareerPathItem(BaseModel):
    """Comparative metrics for a single career trajectory."""

    role_name: str
    active_jobs_count: int
    readiness_score: float
    readiness_level: str
    matched_skills_count: int
    missing_skills_count: int
    top_matched_skills: list[str] = []
    critical_gaps: list[str] = []
    estimated_runway_weeks: str
    assumptions: str

    model_config = ConfigDict(from_attributes=True)


class CareerPathCompareRequest(BaseModel):
    """Request payload to compare multiple career tracks."""

    roles: list[str] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="List of 2 to 5 distinct role names to evaluate and compare",
    )


class CareerPathCompareResponse(BaseModel):
    """Comparative analysis across candidate career paths."""

    compared_roles: list[CareerPathItem]
    recommended_role: str
    recommendation_reason: str


class WhatIfSimulationRequest(BaseModel):
    """Request payload for simulating hypothetical skill acquisition."""

    hypothetical_skills: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Hypothetical skills to add to the student portfolio",
    )
    target_role: str = Field(
        default="overall",
        description="Target role scope for the simulation ('overall' or specific role)",
    )


class WhatIfSimulationResponse(BaseModel):
    """Outcomes and projected impact of acquiring hypothetical skills."""

    target_role: str
    simulated_skills: list[str]
    baseline_fit_score: float
    simulated_fit_score: float
    score_delta: float
    baseline_readiness_level: str
    simulated_readiness_level: str
    newly_unlocked_jobs_count: int
    resolved_gaps: list[str]
    remaining_gaps: list[str]
    assumptions: str
    disclaimer: str = (
        "PROJECTION ONLY (NOT A HIRING GUARANTEE): Estimates reflect potential alignment gains "
        "from demonstrated competency based on deterministic rules, not subjective hiring decisions or employment guarantees."
    )
