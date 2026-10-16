"""SQLAlchemy models for extracted student skills and the skill knowledge graph."""

from typing import Any
import uuid
from sqlalchemy import JSON, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class StudentSkill(Base, TimestampMixin):
    """Evidence-backed skill extracted for a student across repositories."""

    __tablename__ = "student_skills"

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
    skill_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # Language, Framework, Database, DevOps/Tool, Library
    confidence_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    source_repositories: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    verification_status: Mapped[str] = mapped_column(
        String(50),
        default="repository_supported",
        nullable=False,
    )  # repository_supported, practically_demonstrated, not_yet_verified


class SkillGraphEdge(Base, TimestampMixin):
    """Directed/undirected relationships between skills in a student's portfolio."""

    __tablename__ = "skill_graph_edges"

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
    source_skill: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    target_skill: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    relationship_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # built_on, requires_language, integrates_with, tooling_for, ecosystem
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
