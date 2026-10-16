"""Pydantic schemas for Phase 8 SkillProof Engine."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class SkillProofRepoItem(BaseModel):
    """Repository item with SkillProof status."""

    github_repo_id: str
    name: str
    full_name: str
    default_branch: str = "main"
    primary_language: str | None = None
    is_private: bool = False
    description: str | None = None
    html_url: str
    last_analyzed_at: datetime | None = None
    skillproof_run_count: int = 0


class SkillEvidenceItem(BaseModel):
    """Granular evidence item for a skill."""

    type: str = Field(..., description="manifest_dependency, source_implementation, or source_import")
    file_path: str
    line_start: int | None = None
    line_end: int | None = None
    code_snippet: str | None = None
    detail: str


class DetectedSkillItem(BaseModel):
    """Detected skill distinguishing dependency vs implementation."""

    skill_name: str
    category: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    has_dependency_evidence: bool
    has_implementation_evidence: bool
    status: str = Field(..., description="'implemented', 'dependency_only', or 'implementation_only'")
    dependency_evidence_count: int = 0
    implementation_evidence_count: int = 0
    mapped_files: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class SkillProofDetectResponse(BaseModel):
    """Response containing detected repository skills with evidence."""

    repository_full_name: str
    default_branch: str
    skills_count: int
    implemented_count: int
    dependency_only_count: int
    skills: list[DetectedSkillItem]


class SkillProofAnalyzeRequest(BaseModel):
    """Payload to trigger targeted or full-repo SkillProof analysis."""

    repo_id: str = Field(..., description="GitHub repository ID or full_name ('owner/repo')")
    selected_skills: list[str] | None = Field(
        default=None,
        description="Optional list of skills for targeted analysis. If empty or None, analyzes entire repository.",
    )
    max_files: int = Field(default=25, ge=1, le=100, description="Max source files to inspect")


class SimilarityFindingItem(BaseModel):
    """Legitimate code similarity finding with reference provenance."""

    reference_id: str
    reference_name: str
    provenance: str
    license: str
    canonical_url: str
    skill: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    exact_score: float = Field(default=0.0, ge=0.0, le=1.0)
    normalized_score: float = Field(default=0.0, ge=0.0, le=1.0)
    token_score: float = Field(default=0.0, ge=0.0, le=1.0)
    ast_score: float = Field(default=0.0, ge=0.0, le=1.0)
    coverage_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    primary_modality: str
    matched_snippets: list[str] = Field(default_factory=list)


class SkillProofEvidenceItem(BaseModel):
    """File-level evidence record within a SkillProof run."""

    file_path: str
    language: str
    has_implementation: bool
    has_dependency: bool
    skills_detected: list[dict[str, Any]] = Field(default_factory=list)
    similarity_findings: list[SimilarityFindingItem] = Field(default_factory=list)


class SkillProofHonestReporting(BaseModel):
    """Honest reporting metadata and disclaimers."""

    plagiarism_claim: bool = False
    ai_generation_claim: bool = False
    disclaimer: str
    missing_references: list[dict[str, Any]] = Field(default_factory=list)
    coverage_scope: dict[str, Any] = Field(default_factory=dict)


class SkillProofRunResponse(BaseModel):
    """Complete SkillProof analysis report."""

    id: str
    firebase_uid: str
    repository_id: str
    repository_full_name: str
    status: str
    target_skills: list[str]
    summary: dict[str, Any]
    honest_reporting: SkillProofHonestReporting
    evidence_records: list[SkillProofEvidenceItem]
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class SkillProofRunListItem(BaseModel):
    """Summary item for listing past SkillProof runs."""

    id: str
    repository_id: str
    repository_full_name: str
    status: str
    target_skills: list[str]
    skills_detected_count: int
    average_similarity_score: float
    created_at: datetime
    completed_at: datetime | None = None
