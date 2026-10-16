"""Pydantic schemas for Phase 9 SkillProof Practical Assessments."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class CreateAssessmentRequest(BaseModel):
    """Request payload to initiate a practical assessment."""

    skill_name: str = Field(..., min_length=1, max_length=100, description="Name of the skill to verify")
    repository_id: str | None = Field(None, description="Optional repository ID containing reference evidence")
    forced_level: str | None = Field(
        None,
        description="Optional forced level: 'basic', 'intermediate', or 'advanced'. If omitted, adaptively selected.",
    )


class ChallengePublicView(BaseModel):
    """Challenge specification presented to the student (hidden tests strictly omitted)."""

    title: str
    description: str
    entry_function: str
    starter_code: str
    public_tests: list[dict[str, Any]] = Field(default_factory=list)
    difficulty: str
    rubric: dict[str, int] = Field(default_factory=dict)


class AssessmentPublicResponse(BaseModel):
    """Assessment metadata and active challenge specification."""

    assessment_id: str
    skill_name: str
    assessment_level: str
    challenge_type: str
    status: str
    attempt_count: int
    max_attempts: int
    challenge: ChallengePublicView
    level_selection_rationale: str | None = None


class SubmitSolutionRequest(BaseModel):
    """Code submission payload."""

    submitted_code: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Student implementation code to be evaluated in sandbox",
    )


class RubricCriterionItem(BaseModel):
    """Individual rubric criterion evaluation."""

    criterion: str
    weight: int
    score_percentage: float
    feedback: str


class RubricFeedbackResponse(BaseModel):
    """Rubric evaluation breakdown."""

    overall_rubric_score: float
    criteria: list[RubricCriterionItem]
    summary_verdict: str


class SubmitSolutionResponse(BaseModel):
    """Evaluation result for a student code submission."""

    submission_id: str
    assessment_id: str
    attempt_number: int
    execution_status: str
    score: float
    passed: bool
    public_results: dict[str, Any]
    hidden_results: dict[str, Any]
    rubric_feedback: RubricFeedbackResponse
    execution_metrics: dict[str, Any]
    assessment_status: str


class PracticalAssessmentListItem(BaseModel):
    """Summary item for listing user assessments."""

    id: str
    skill_name: str
    assessment_level: str
    challenge_type: str
    status: str
    attempt_count: int
    max_attempts: int
    score: float | None = None
    passed: bool | None = None
    created_at: datetime
    completed_at: datetime | None = None
