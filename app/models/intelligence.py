"""SQLAlchemy model for persisting Career Intelligence assessments and skill-gap reports."""

from typing import Any
import uuid
from sqlalchemy import JSON, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class CareerAssessment(Base, TimestampMixin):
    """Persisted snapshot of a student's career intelligence, skill gaps, and recommendations."""

    __tablename__ = "career_assessments"

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
    target_role: Mapped[str] = mapped_column(
        String(100),
        default="overall",
        index=True,
        nullable=False,
    )
    overall_fit_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    readiness_level: Mapped[str] = mapped_column(
        String(32),
        default="Early",
        nullable=False,
    )  # Ready, High, Moderate, Developing, Early
    matched_skills: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    missing_skills: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    prioritized_gaps: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    recommendations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    assessed_jobs_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
