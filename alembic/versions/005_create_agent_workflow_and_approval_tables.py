"""Create agent workflow runs and approval requests tables

Revision ID: 005_create_agent_workflow_and_approval_tables
Revises: 004_create_career_intelligence_tables
Create Date: 2026-10-16 21:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "005_create_agent_workflow_and_approval_tables"
down_revision: Union[str, None] = "004_create_career_intelligence_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create agent_approval_requests table
    op.create_table(
        "agent_approval_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("thread_id", sa.String(length=128), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("action_description", sa.Text(), nullable=False),
        sa.Column("target_entity_id", sa.String(length=128), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("decision_notes", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_approval_requests_id"), "agent_approval_requests", ["id"], unique=False)
    op.create_index(op.f("ix_agent_approval_requests_firebase_uid"), "agent_approval_requests", ["firebase_uid"], unique=False)
    op.create_index(op.f("ix_agent_approval_requests_thread_id"), "agent_approval_requests", ["thread_id"], unique=False)
    op.create_index(op.f("ix_agent_approval_requests_action_type"), "agent_approval_requests", ["action_type"], unique=False)
    op.create_index(op.f("ix_agent_approval_requests_status"), "agent_approval_requests", ["status"], unique=False)

    # 2. Create agent_workflow_runs table
    op.create_table(
        "agent_workflow_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("thread_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_step", sa.String(length=64), nullable=False),
        sa.Column("state_summary", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_workflow_runs_id"), "agent_workflow_runs", ["id"], unique=False)
    op.create_index(op.f("ix_agent_workflow_runs_firebase_uid"), "agent_workflow_runs", ["firebase_uid"], unique=False)
    op.create_index(op.f("ix_agent_workflow_runs_thread_id"), "agent_workflow_runs", ["thread_id"], unique=False)
    op.create_index(op.f("ix_agent_workflow_runs_status"), "agent_workflow_runs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_table("agent_workflow_runs")
    op.drop_table("agent_approval_requests")
