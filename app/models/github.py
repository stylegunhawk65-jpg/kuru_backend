"""SQLAlchemy models for GitHub connections, repositories, and analyses."""

from datetime import datetime
from typing import Any
import uuid
from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class GithubConnection(Base, TimestampMixin):
    """User GitHub OAuth connection with encrypted token storage."""

    __tablename__ = "github_connections"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    firebase_uid: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        index=True,
        nullable=False,
    )
    encrypted_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    github_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class GithubRepository(Base, TimestampMixin):
    """Repositories selected by the user for code analysis."""

    __tablename__ = "github_repositories"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    firebase_uid: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
    )
    github_repo_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    html_url: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_branch: Mapped[str] = mapped_column(String(64), default="main", nullable=False)
    primary_language: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stars_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    forks_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    selected_for_analysis: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_analyzed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class RepositoryAnalysis(Base, TimestampMixin):
    """Static analysis records for individual repositories."""

    __tablename__ = "repository_analyses"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    firebase_uid: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
    )
    repository_id: Mapped[str] = mapped_column(
        String(36),
        index=True,
        nullable=False,
    )
    repository_full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
    )  # pending, completed, failed
    languages_breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    extracted_skills: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    file_tree_summary: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
