"""Create career assessments table

Revision ID: 004_create_career_intelligence_tables
Revises: 003_create_job_and_source_tables
Create Date: 2026-10-16 19:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "004_create_career_intelligence_tables"
down_revision: Union[str, None] = "003_create_job_and_source_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "career_assessments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("target_role", sa.String(length=100), nullable=False),
        sa.Column("overall_fit_score", sa.Float(), nullable=False),
        sa.Column("readiness_level", sa.String(length=32), nullable=False),
        sa.Column("matched_skills", sa.JSON(), nullable=False),
        sa.Column("missing_skills", sa.JSON(), nullable=False),
        sa.Column("prioritized_gaps", sa.JSON(), nullable=False),
        sa.Column("recommendations", sa.JSON(), nullable=False),
        sa.Column("assessed_jobs_count", sa.Integer(), nullable=False),
        sa.Column("summary_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_career_assessments_id"), "career_assessments", ["id"], unique=False)
    op.create_index(op.f("ix_career_assessments_firebase_uid"), "career_assessments", ["firebase_uid"], unique=False)
    op.create_index(op.f("ix_career_assessments_target_role"), "career_assessments", ["target_role"], unique=False)


def downgrade() -> None:
    op.drop_table("career_assessments")
