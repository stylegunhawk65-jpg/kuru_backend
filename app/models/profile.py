"""Student Career Profile SQLAlchemy model."""

from typing import Any
import uuid
from sqlalchemy import Boolean, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class StudentProfile(Base, TimestampMixin):
    """Student Career Profile table linking student details with Firebase UID."""

    __tablename__ = "student_profiles"

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
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Structured career attributes
    education: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    interests: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    target_roles: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    preferred_locations: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    linkedin_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    certificates: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<StudentProfile(id={self.id}, firebase_uid={self.firebase_uid}, full_name={self.full_name})>"
