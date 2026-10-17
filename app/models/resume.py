"""SQLAlchemy model for ATS-friendly tailored resumes."""

from datetime import datetime
from typing import Any
import uuid
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
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


class BaseCV(Base, TimestampMixin):
    """Uploaded user CV/resume document with parsed and confirmed structured data."""

    __tablename__ = "base_cvs"

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
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)  # "pdf" or "docx"
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    @property
    def full_name(self) -> str | None:
        return (self.extracted_data or {}).get("full_name")

    @property
    def email(self) -> str | None:
        return (self.extracted_data or {}).get("email")

    @property
    def phone(self) -> str | None:
        return (self.extracted_data or {}).get("phone")

    @property
    def skills(self) -> list:
        return (self.extracted_data or {}).get("skills", [])

    @property
    def education(self) -> list:
        return (self.extracted_data or {}).get("education", [])

    @property
    def experience(self) -> list:
        return (self.extracted_data or {}).get("experience", [])

