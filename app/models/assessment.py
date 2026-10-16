"""SQLAlchemy models for Phase 9 SkillProof Practical Assessments."""

from datetime import datetime
from typing import Any
import uuid
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class PracticalAssessment(Base, TimestampMixin):
    """Practical coding assessment evaluating real engineering competency."""

    __tablename__ = "practical_assessments"

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
    repository_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    repository_full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    skill_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    assessment_level: Mapped[str] = mapped_column(String(32), nullable=False)  # basic, intermediate, advanced
    challenge_type: Mapped[str] = mapped_column(String(32), nullable=False)   # coding, debugging, transfer
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        index=True,
        nullable=False,
    )  # pending, in_progress, submitted, passed, failed
    challenge_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    hidden_test_data: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    level_selection_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Submissions
    submissions: Mapped[list["AssessmentSubmission"]] = relationship(
        "AssessmentSubmission",
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="AssessmentSubmission.attempt_number",
    )


class AssessmentSubmission(Base, TimestampMixin):
    """An individual submission attempt for a practical assessment."""

    __tablename__ = "assessment_submissions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    assessment_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("practical_assessments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    firebase_uid: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    submitted_code: Mapped[str] = mapped_column(Text, nullable=False)
    execution_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )  # passed, failed_tests, timeout, runtime_error, security_violation, execution_disabled
    public_results: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    hidden_results: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rubric_feedback: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    execution_metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    assessment: Mapped["PracticalAssessment"] = relationship("PracticalAssessment", back_populates="submissions")
