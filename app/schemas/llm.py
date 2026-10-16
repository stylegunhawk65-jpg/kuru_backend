"""Pydantic validation schemas for LLM-driven Career Twin tasks."""

from typing import Any
from pydantic import BaseModel, Field


class BulletPointItem(BaseModel):
    """An individual tailored resume bullet point with impact metrics and keywords."""

    original: str = Field(..., description="Original user bullet point or draft")
    tailored: str = Field(..., description="Action-oriented, keyword-optimized bullet point")
    highlighted_skills: list[str] = Field(default_factory=list, description="Verified skills incorporated")
    impact_metric: str = Field(..., description="Quantifiable engineering result or metric")


class ResumeTailorRequest(BaseModel):
    """Request payload to optimize resume bullet points for a target role or job."""

    target_role: str = Field(..., min_length=2, max_length=100, description="Target career role (e.g. Backend Engineer)")
    bullet_points: list[str] = Field(..., min_length=1, max_length=10, description="List of draft or project bullet points")
    job_description: str | None = Field(None, max_length=5000, description="Optional job description to align keywords against")


class ResumeTailorResponse(BaseModel):
    """Optimized resume bullet points with quantifiable metrics and skill alignment."""

    target_role: str
    tailored_summary: str
    bullet_points: list[BulletPointItem]
    alignment_explanation: str


class RoadmapModuleItem(BaseModel):
    """Weekly study module within an adaptive learning roadmap."""

    week_number: int = Field(..., ge=1, le=52)
    focus_skill: str = Field(..., description="Primary skill or framework to master")
    objective: str = Field(..., description="Concrete weekly competency goal")
    daily_milestones: list[str] = Field(..., description="Daily task breakdowns for the week")
    practical_project: str = Field(..., description="Portfolio-grade hands-on deliverable")


class RoadmapGenerateRequest(BaseModel):
    """Request payload to construct a personalized learning roadmap."""

    target_role: str = Field(..., min_length=2, max_length=100)
    focus_skills: list[str] = Field(default_factory=list, max_length=10, description="Specific skills to prioritize (defaults to top gaps)")
    weekly_hours_available: int = Field(default=12, ge=4, le=40, description="Weekly hours dedicated to study")
    assessment_insights: list[str] = Field(default_factory=list, description="Targeted insights and weak areas from practical assessments")


class RoadmapGenerateResponse(BaseModel):
    """Actionable, milestone-driven technical learning roadmap."""

    target_role: str
    total_estimated_weeks: int
    weekly_hours_required: int
    weekly_modules: list[RoadmapModuleItem]
    learning_principles: list[str] = []


class TechnicalQuestionItem(BaseModel):
    """A technical interview question with rubric points."""

    question: str
    expected_answer_points: list[str]
    difficulty: str  # "Easy", "Medium", "Hard"
    category: str


class InterviewPrepRequest(BaseModel):
    """Request payload for technical interview preparation."""

    target_role: str = Field(..., min_length=2, max_length=100)
    company_name: str | None = Field(None, max_length=100)
    focus_skills: list[str] = Field(default_factory=list, max_length=10)


class InterviewPrepResponse(BaseModel):
    """Technical interview preparation briefing with questions, challenges, and tips."""

    target_role: str
    company_focus: str
    technical_questions: list[TechnicalQuestionItem]
    coding_challenge_topics: list[str] = []
    behavioral_tips: list[str] = []


class ModelHealthResponse(BaseModel):
    """Health, hardware capability, and status of the local LLM system."""

    provider: str
    model_id: str
    is_ready: bool
    device: str
    quantization: str
    cuda_available: bool
    vram_allocated_mb: float
    vram_reserved_mb: float


class BenchmarkResultResponse(BaseModel):
    """Measured performance metrics on Career Twin tasks."""

    task_name: str
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    latency_seconds: float
    tokens_per_second: float
    structured_output_valid: bool
    vram_used_mb: float
