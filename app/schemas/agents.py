"""Typed Pydantic schemas for multi-agent workflows, state representations, and approval gates."""

from datetime import datetime
from typing import Any, TypedDict
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1. Consolidated Profile & Skills
# ---------------------------------------------------------------------------

class ConsolidatedProfile(BaseModel):
    """Consolidated student profile and career interests."""

    firebase_uid: str
    full_name: str | None = None
    target_roles: list[str] = Field(default_factory=list)
    primary_target_role: str
    preferred_locations: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    graduation_year: int | None = None
    degree: str | None = None
    institution: str | None = None


class VerifiedSkillItem(BaseModel):
    """Evidence-backed skill with confidence and relational graph context."""

    skill_name: str
    category: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    source_evidence_count: int = 0
    related_skills: list[str] = Field(default_factory=list)
    verification_status: str = "repository_supported"  # practically_demonstrated, repository_supported, not_yet_verified
    evidence_type: str = "repository"  # practical_demonstration, ast_implementation, manifest_dependency, none


# ---------------------------------------------------------------------------
# 2. Matched Jobs & Skill Gaps
# ---------------------------------------------------------------------------

class MatchedJobItem(BaseModel):
    """Transparently ranked real job posting with evidence-backed breakdown."""

    id: str
    title: str
    company: str
    location: str
    match_score: float = Field(..., ge=0.0, le=100.0)
    matching_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    demonstrated_skills: list[str] = Field(default_factory=list)
    repo_supported_skills: list[str] = Field(default_factory=list)
    missing_skills_breakdown: list[dict[str, Any]] = Field(default_factory=list)
    match_reasons: list[str] = Field(default_factory=list)
    source_url: str
    source_name: str


class PrioritizedSkillGapItem(BaseModel):
    """A missing skill prioritized by market demand and graph proximity."""

    skill_name: str
    priority_rank: int
    priority_score: float
    market_demand_pct: float
    graph_proximity: str
    reasons: list[str] = Field(default_factory=list)
    gap_type: str = "absent_evidence"  # demonstrated_need, absent_evidence, dependency_only


# ---------------------------------------------------------------------------
# 3. Career Planning & Learning Resources
# ---------------------------------------------------------------------------

class LearningModuleItem(BaseModel):
    """Weekly study milestone within adaptive learning roadmap."""

    week_number: int
    focus_skill: str
    objective: str
    daily_milestones: list[str] = Field(default_factory=list)
    practical_project: str


class CareerPlanResult(BaseModel):
    """Personalized learning roadmap and readiness plan."""

    target_role: str
    total_weeks: int
    weekly_hours: int
    weekly_modules: list[LearningModuleItem] = Field(default_factory=list)
    learning_principles: list[str] = Field(default_factory=list)
    what_if_readiness: dict[str, Any] = Field(default_factory=dict)


class GenuineResourceItem(BaseModel):
    """Authoritative, verified learning resource."""

    skill_name: str
    title: str
    url: str
    provider: str
    resource_type: str
    difficulty: str
    estimated_hours: int
    description: str
    is_verified: bool = True
    verification_source: str = "official_documentation_whitelist"


# ---------------------------------------------------------------------------
# 4. Project Recommendations
# ---------------------------------------------------------------------------

class ProjectRecommendationItem(BaseModel):
    """Hands-on portfolio project directly addressing skill gaps and target jobs."""

    title: str = Field(..., description="Action-oriented project title")
    description: str = Field(..., description="Detailed project overview and problem solved")
    target_skill_gaps: list[str] = Field(..., description="Skills this project demonstrates")
    tech_stack: list[str] = Field(..., description="Concrete technologies used in the project")
    architecture_overview: str = Field(..., description="High-level architecture design and data flow")
    portfolio_deliverable: str = Field(..., description="Final GitHub repository deliverable and live demo")
    estimated_duration_weeks: int = Field(default=2, ge=1, le=8)
    difficulty_level: str = Field(default="Intermediate", description="Beginner, Intermediate, Advanced")
    validated_job_technologies: list[str] = Field(
        default_factory=list,
        description="Technologies in this project matching selected job requirements",
    )
    job_alignment_summary: str | None = Field(
        default=None,
        description="Explanation of how this project validates candidate for selected job",
    )


class ProjectRecommendationsResponse(BaseModel):
    """LLM structured output for project recommendations."""

    target_role: str
    summary: str
    recommended_projects: list[ProjectRecommendationItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 5. Tailored Resume & Approvals
# ---------------------------------------------------------------------------

class TailoredResumeResult(BaseModel):
    """Structured tailored resume output."""

    target_role: str
    tailored_summary: str
    bullet_points: list[dict[str, Any]] = Field(default_factory=list)
    alignment_explanation: str


class ApprovalRequestResponse(BaseModel):
    """Consequential action queued for user approval."""

    id: str
    thread_id: str
    action_type: str
    action_description: str
    target_entity_id: str | None = None
    payload: dict[str, Any]
    status: str
    decision_notes: str | None = None
    decided_at: datetime | None = None
    created_at: datetime


class ApprovalDecisionRequest(BaseModel):
    """User decision on a queued approval request."""

    notes: str | None = Field(None, max_length=500, description="Optional user notes on approval or rejection")


class WorkflowRunResponse(BaseModel):
    """Execution state and summary of a multi-agent workflow."""

    id: str
    thread_id: str
    workflow_type: str
    status: str
    current_step: str
    state_summary: dict[str, Any]
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class WorkflowTriggerRequest(BaseModel):
    """Request payload to initiate a multi-agent workflow."""

    target_role: str | None = Field(None, max_length=100, description="Target role (defaults to student's primary target)")
    target_job_id: str | None = Field(None, max_length=128, description="Optional specific job to align against")
    weekly_hours_available: int = Field(default=12, ge=4, le=40)
    consequential_action_requested: str | None = Field(
        None,
        description="Optional action to queue for approval: 'job_application', 'resume_export', etc.",
    )


# ---------------------------------------------------------------------------
# 6. LangGraph Shared State (TypedDict)
# ---------------------------------------------------------------------------

class CareerTwinAgentState(TypedDict):
    """Shared typed state across the LangGraph multi-agent pipeline."""

    firebase_uid: str
    thread_id: str
    target_role: str
    target_job_id: str | None
    weekly_hours_available: int
    requested_action: str | None

    # Step outputs
    profile: dict[str, Any] | None
    skills: list[dict[str, Any]]
    matched_jobs: list[dict[str, Any]]
    skill_gaps: list[dict[str, Any]]
    career_plan: dict[str, Any] | None
    resources: dict[str, list[dict[str, Any]]]
    projects: list[dict[str, Any]]
    resume: dict[str, Any] | None

    # Approval and Consequential Gates
    pending_approval: dict[str, Any] | None
    approval_status: str  # "none", "pending", "approved", "rejected"
    executed_action: dict[str, Any] | None

    # Audit & Observability
    step_history: list[str]
    errors: list[str]
