"""API validation schemas package."""

from app.schemas.github import (
    AnalysisResultItem,
    GitHubAnalyzeRequest,
    GitHubAnalyzeResponse,
    GitHubConnectionResponse,
    GitHubConnectRequest,
    GitHubRepoItem,
    GitHubRepoListResponse,
    GitHubRepoSelectRequest,
)
from app.schemas.profile import (
    EducationEntry,
    StudentProfileCreate,
    StudentProfileResponse,
    StudentProfileUpdate,
)
from app.schemas.skill import (
    SkillEvidenceItem,
    SkillGraphEdgeResponse,
    SkillGraphNode,
    SkillGraphResponse,
    StudentSkillResponse,
)

__all__ = [
    "EducationEntry",
    "StudentProfileCreate",
    "StudentProfileUpdate",
    "StudentProfileResponse",
    "GitHubConnectRequest",
    "GitHubConnectionResponse",
    "GitHubRepoItem",
    "GitHubRepoListResponse",
    "GitHubRepoSelectRequest",
    "GitHubAnalyzeRequest",
    "GitHubAnalyzeResponse",
    "AnalysisResultItem",
    "SkillEvidenceItem",
    "StudentSkillResponse",
    "SkillGraphNode",
    "SkillGraphEdgeResponse",
    "SkillGraphResponse",
]
