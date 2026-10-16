"""SQLAlchemy models for Job Postings, Job Sources, and Saved Jobs."""

from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class JobPosting(Base, TimestampMixin):
    """Verified job and internship listings aggregated from legitimate sources."""

    __tablename__ = "job_postings"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    source: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    dedup_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    company: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    location: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    job_type: Mapped[str] = mapped_column(
        String(50),
        default="full_time",
        index=True,
        nullable=False,
    )  # full_time, internship, part_time, contract
    description: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)  # Verifiable direct link
    required_skills: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    salary_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    salary_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class JobSource(Base, TimestampMixin):
    """Configuration, sync status, and health metrics for individual job providers."""

    __tablename__ = "job_sources"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    source_name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_sync_status: Mapped[str] = mapped_column(
        String(32),
        default="idle",
        nullable=False,
    )  # idle, in_progress, success, failed
    jobs_synced_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class SavedJob(Base, TimestampMixin):
    """User-bookmarked jobs with personal notes and application status."""

    __tablename__ = "saved_jobs"
    __table_args__ = (
        UniqueConstraint("firebase_uid", "job_id", name="uq_user_saved_job"),
    )

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
    job_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        default="saved",
        nullable=False,
    )  # saved, applied, archived
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
