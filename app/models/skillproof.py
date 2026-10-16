"""SQLAlchemy models for Phase 8 SkillProof Engine."""

from datetime import datetime
from typing import Any
import uuid
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class SkillProofRun(Base, TimestampMixin):
    """A SkillProof analysis run for a specific repository and target skills."""

    __tablename__ = "skillproof_runs"

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
        String(64),
        index=True,
        nullable=False,
    )
    repository_full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
        index=True,
    )  # pending, completed, failed
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    honest_reporting: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # File-level evidence records
    evidence_records: Mapped[list["SkillProofEvidence"]] = relationship(
        "SkillProofEvidence",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="SkillProofEvidence.file_path",
    )


class SkillProofEvidence(Base, TimestampMixin):
    """File-level skill detection and similarity evidence within a SkillProof run."""

    __tablename__ = "skillproof_evidence"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("skillproof_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    firebase_uid: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    language: Mapped[str] = mapped_column(String(64), default="Unknown", nullable=False)
    has_implementation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_dependency: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    skills_detected: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    similarity_findings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    run: Mapped["SkillProofRun"] = relationship("SkillProofRun", back_populates="evidence_records")
