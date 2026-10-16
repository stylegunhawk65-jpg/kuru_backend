"""Create SkillProof runs and evidence tables

Revision ID: 006_create_skillproof_tables
Revises: 005_create_agent_workflow_and_approval_tables
Create Date: 2026-10-17 01:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "006_create_skillproof_tables"
down_revision: Union[str, None] = "005_create_agent_workflow_and_approval_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create skillproof_runs table
    op.create_table(
        "skillproof_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("repository_id", sa.String(length=64), nullable=False),
        sa.Column("repository_full_name", sa.String(length=255), nullable=False),
        sa.Column("target_skills", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("honest_reporting", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_skillproof_runs_id"), "skillproof_runs", ["id"], unique=False)
    op.create_index(op.f("ix_skillproof_runs_firebase_uid"), "skillproof_runs", ["firebase_uid"], unique=False)
    op.create_index(op.f("ix_skillproof_runs_repository_id"), "skillproof_runs", ["repository_id"], unique=False)
    op.create_index(op.f("ix_skillproof_runs_status"), "skillproof_runs", ["status"], unique=False)

    # 2. Create skillproof_evidence table
    op.create_table(
        "skillproof_evidence",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("language", sa.String(length=64), nullable=False),
        sa.Column("has_implementation", sa.Boolean(), nullable=False),
        sa.Column("has_dependency", sa.Boolean(), nullable=False),
        sa.Column("skills_detected", sa.JSON(), nullable=False),
        sa.Column("similarity_findings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["skillproof_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_skillproof_evidence_id"), "skillproof_evidence", ["id"], unique=False)
    op.create_index(op.f("ix_skillproof_evidence_run_id"), "skillproof_evidence", ["run_id"], unique=False)
    op.create_index(op.f("ix_skillproof_evidence_firebase_uid"), "skillproof_evidence", ["firebase_uid"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_skillproof_evidence_firebase_uid"), table_name="skillproof_evidence")
    op.drop_index(op.f("ix_skillproof_evidence_run_id"), table_name="skillproof_evidence")
    op.drop_index(op.f("ix_skillproof_evidence_id"), table_name="skillproof_evidence")
    op.drop_table("skillproof_evidence")

    op.drop_index(op.f("ix_skillproof_runs_status"), table_name="skillproof_runs")
    op.drop_index(op.f("ix_skillproof_runs_repository_id"), table_name="skillproof_runs")
    op.drop_index(op.f("ix_skillproof_runs_firebase_uid"), table_name="skillproof_runs")
    op.drop_index(op.f("ix_skillproof_runs_id"), table_name="skillproof_runs")
    op.drop_table("skillproof_runs")
