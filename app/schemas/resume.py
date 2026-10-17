"""Pydantic schemas for ATS-friendly, evidence-backed resumes."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ResumeContactInfo(BaseModel):
    """Candidate contact details extracted from verified profile."""

    full_name: str
    email: str
    phone: str | None = None
    location: str | None = None
    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None


class ResumeSkillItem(BaseModel):
    """Technical skill item with verified evidence tracking."""

    skill_name: str
    category: str
    confidence_score: float = 0.85
    verification_status: str = "repository_supported"  # practically_demonstrated, repository_supported, unverified
    evidence_sources: list[str] = Field(default_factory=list)


class ResumeProjectItem(BaseModel):
    """GitHub portfolio project with concrete tech stack and honest impact metrics."""

    title: str
    description: str
    tech_stack: list[str] = Field(default_factory=list)
    bullet_points: list[str] = Field(default_factory=list)
    repo_url: str | None = None
    evidence_tags: list[str] = Field(default_factory=list)


class ResumeExperienceItem(BaseModel):
    """Professional or internship experience item."""

    role: str
    company: str
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool = False
    bullet_points: list[str] = Field(default_factory=list)
    highlighted_skills: list[str] = Field(default_factory=list)


class ResumeEducationItem(BaseModel):
    """Formal degree, coursework, and academic credential."""

    degree: str
    institution: str
    field_of_study: str | None = None
    graduation_year: int | str | None = None
    grade_or_gpa: str | None = None


class ResumeAssessmentItem(BaseModel):
    """Phase 9 Practical Assessment results certifying real coding competency."""

    skill_name: str
    assessment_level: str
    challenge_type: str
    score: float
    passed: bool = True
    verification_status: str = "practically_demonstrated"
    verified_at: str | None = None


class ResumeTailoringMetadata(BaseModel):
    """Metadata detailing alignment with target job, evidence citations, and honest reporting."""

    job_id: str | None = None
    job_title: str | None = None
    company: str | None = None
    match_score: float | None = None
    matching_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    evidence_citations: dict[str, list[str]] = Field(default_factory=dict)
    ats_score_estimate: float = 85.0
    honest_disclaimer: str = (
        "Anti-Hallucination Guarantee: All listed skills, projects, and achievements are "
        "derived strictly from verified student profile data, repository AST analysis, "
        "and sandbox practical assessments. No experience or metrics are fabricated."
    )


class ResumeGenerateRequest(BaseModel):
    """Request payload to generate an ATS-friendly tailored resume."""

    target_role: str = Field(default="Backend Engineer", description="Target role name")
    target_company: str | None = Field(default=None, description="Optional target company name")
    job_id: str | None = Field(default=None, description="Optional ID of real JobPosting to tailor against")
    custom_instructions: str | None = Field(default=None, max_length=500, description="Optional specific emphasis instructions")
    save_to_db: bool = Field(default=True, description="Whether to automatically persist the generated resume snapshot")


class ResumeCreate(BaseModel):
    """Payload to save a tailored resume."""

    title: str = Field(..., max_length=200)
    target_role: str = Field(..., max_length=100)
    job_id: str | None = None
    contact_info: ResumeContactInfo
    summary: str
    skills_by_category: dict[str, list[ResumeSkillItem]] = Field(default_factory=dict)
    experience: list[ResumeExperienceItem] = Field(default_factory=list)
    projects: list[ResumeProjectItem] = Field(default_factory=list)
    education: list[ResumeEducationItem] = Field(default_factory=list)
    practical_assessments: list[ResumeAssessmentItem] = Field(default_factory=list)
    tailoring_metadata: ResumeTailoringMetadata | None = None
    is_primary: bool = False


class ResumeUpdate(BaseModel):
    """Payload to update an existing resume."""

    title: str | None = None
    target_role: str | None = None
    contact_info: ResumeContactInfo | None = None
    summary: str | None = None
    skills_by_category: dict[str, list[ResumeSkillItem]] | None = None
    experience: list[ResumeExperienceItem] | None = None
    projects: list[ResumeProjectItem] | None = None
    education: list[ResumeEducationItem] | None = None
    practical_assessments: list[ResumeAssessmentItem] | None = None
    is_primary: bool | None = None


class ResumeResponse(BaseModel):
    """Full structured ATS-compliant resume response."""

    id: str
    firebase_uid: str
    job_id: str | None = None
    title: str
    target_role: str
    contact_info: ResumeContactInfo
    summary: str
    skills_by_category: dict[str, list[ResumeSkillItem]]
    experience: list[ResumeExperienceItem]
    projects: list[ResumeProjectItem]
    education: list[ResumeEducationItem]
    practical_assessments: list[ResumeAssessmentItem]
    tailoring_metadata: ResumeTailoringMetadata
    is_primary: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BaseCVConfirmRequest(BaseModel):
    """Payload to confirm or adjust extracted CV entities before generating tailored resumes."""

    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    github_handle: str | None = None
    linkedin_handle: str | None = None
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    education: list[dict[str, Any]] = Field(default_factory=list)
    experience: list[dict[str, Any]] = Field(default_factory=list)
    projects: list[dict[str, Any]] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class BaseCVResponse(BaseModel):
    """Structured information extracted from uploaded base CV."""

    id: str
    firebase_uid: str
    filename: str
    file_type: str
    file_size_bytes: int
    raw_text: str
    extracted_data: dict[str, Any]
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    skills: list[str] = Field(default_factory=list)
    education: list[dict[str, Any]] = Field(default_factory=list)
    experience: list[dict[str, Any]] = Field(default_factory=list)
    is_confirmed: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

