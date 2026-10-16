"""SQLAlchemy models for agent workflow runs, LangGraph persistence, and human approval gates."""

from datetime import datetime
from typing import Any
import uuid
from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AgentApprovalRequest(Base, TimestampMixin):
    """Consequential action queued by an agent requiring explicit human approval."""

    __tablename__ = "agent_approval_requests"

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
    thread_id: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
    )
    action_type: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
    )  # job_application, resume_export, external_submission, etc.
    action_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    target_entity_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        index=True,
        nullable=False,
    )  # pending, approved, rejected, executed, cancelled
    decision_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class AgentWorkflowRun(Base, TimestampMixin):
    """Tracking and audit record for an executed LangGraph agent workflow."""

    __tablename__ = "agent_workflow_runs"

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
    thread_id: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
    )
    workflow_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )  # full_career_twin, roadmap_planning, resume_tailor
    status: Mapped[str] = mapped_column(
        String(32),
        default="running",
        index=True,
        nullable=False,
    )  # running, waiting_approval, completed, failed
    current_step: Mapped[str] = mapped_column(
        String(64),
        default="start",
        nullable=False,
    )
    state_summary: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
