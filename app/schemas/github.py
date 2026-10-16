"""Pydantic schemas for GitHub integration, repositories, and analysis."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class GitHubConnectRequest(BaseModel):
    """Payload to connect a GitHub account using an OAuth token or PAT."""

    token: str = Field(..., min_length=1, description="GitHub Personal Access Token or OAuth Access Token")


class GitHubConnectionResponse(BaseModel):
    """Safe response revealing connection state without leaking the access token."""

    is_connected: bool
    github_username: str | None = None
    github_user_id: str | None = None
    avatar_url: str | None = None
    scopes: list[str] = []
    connected_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class GitHubRepoItem(BaseModel):
    """Repository representation for user selection and listing."""

    id: str | None = None
    github_repo_id: str
    name: str
    full_name: str
    is_private: bool = False
    html_url: str
    description: str | None = None
    default_branch: str = "main"
    primary_language: str | None = None
    stars_count: int = 0
    forks_count: int = 0
    selected_for_analysis: bool = True
    last_analyzed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class GitHubRepoListResponse(BaseModel):
    """Paginated list of repositories accessible from user's GitHub account."""

    total: int
    page: int
    per_page: int
    repositories: list[GitHubRepoItem]


class GitHubRepoSelectRequest(BaseModel):
    """Payload for selecting which repositories to track and analyze."""

    repo_ids: list[str] = Field(..., description="List of GitHub repository IDs or full names to track")


class GitHubAnalyzeRequest(BaseModel):
    """Payload to trigger static analysis on selected repositories."""

    repo_ids: list[str] | None = Field(
        None,
        description="Optional list of tracked repository IDs to analyze. If omitted, analyzes all selected repositories.",
    )


class AnalysisResultItem(BaseModel):
    """Details and extracted skills for a single repository analysis."""

    id: str
    repository_id: str
    repository_full_name: str
    status: str  # pending, completed, failed
    languages_breakdown: dict[str, Any] = {}
    extracted_skills: list[dict[str, Any]] = []
    file_tree_summary: dict[str, Any] = {}
    error_message: str | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GitHubAnalyzeResponse(BaseModel):
    """Response returned when triggering repository analyses."""

    message: str
    total_analyzed: int
    analyses: list[AnalysisResultItem]
