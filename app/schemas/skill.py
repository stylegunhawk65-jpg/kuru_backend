"""Pydantic schemas for extracted skills and the skill knowledge graph."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


class SkillEvidenceItem(BaseModel):
    """Concrete evidence reference for an extracted skill."""

    type: str  # manifest_dependency, language_stats, file_heuristic, source_import
    repository: str
    file_path: str
    detail: str


class StudentSkillResponse(BaseModel):
    """Schema representing an evidence-backed skill possessed by the student."""

    id: str
    skill_name: str
    category: str
    confidence_score: float
    evidence: list[SkillEvidenceItem] = []
    source_repositories: list[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SkillGraphNode(BaseModel):
    """Node in the student's skill graph."""

    id: str
    name: str
    category: str
    confidence_score: float
    evidence_count: int
    repo_count: int


class SkillGraphEdgeResponse(BaseModel):
    """Relationship edge in the skill graph."""

    source: str
    target: str
    relationship_type: str
    weight: float


class SkillGraphResponse(BaseModel):
    """Complete serialized skill graph with nodes, edges, and statistics."""

    nodes: list[SkillGraphNode]
    edges: list[SkillGraphEdgeResponse]
    total_skills: int
    total_relationships: int
