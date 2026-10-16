"""SQLAlchemy model for ATS-friendly tailored resumes."""

from datetime import datetime
from typing import Any
import uuid
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Resume(Base, TimestampMixin):
    """ATS-compliant, evidence-backed tailored resume."""

    __tablename__ = "resumes"

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
    job_id: Mapped[str | None] = mapped_column(
        String(36),
        index=True,
        nullable=True,
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )  # e.g., "Full-Stack Engineer - Swiggy" or "Core Backend Resume"
    target_role: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    contact_info: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    skills_by_category: Mapped[dict[str, list[dict[str, Any]]]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    experience: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    projects: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    education: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    practical_assessments: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    tailoring_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
