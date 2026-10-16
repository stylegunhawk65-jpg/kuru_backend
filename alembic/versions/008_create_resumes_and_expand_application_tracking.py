"""Create resumes table and expand saved_jobs with application tracking columns

Revision ID: 008_create_resumes_and_expand_application_tracking
Revises: 007_create_practical_assessment_tables
Create Date: 2026-10-17 02:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "008_create_resumes_and_expand_application_tracking"
down_revision: Union[str, None] = "007_create_practical_assessment_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create resumes table
    op.create_table(
        "resumes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("target_role", sa.String(length=100), nullable=False),
        sa.Column("contact_info", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("skills_by_category", sa.JSON(), nullable=False),
        sa.Column("experience", sa.JSON(), nullable=False),
        sa.Column("projects", sa.JSON(), nullable=False),
        sa.Column("education", sa.JSON(), nullable=False),
        sa.Column("practical_assessments", sa.JSON(), nullable=False),
        sa.Column("tailoring_metadata", sa.JSON(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_resumes_id"), "resumes", ["id"], unique=False)
    op.create_index(op.f("ix_resumes_firebase_uid"), "resumes", ["firebase_uid"], unique=False)
    op.create_index(op.f("ix_resumes_job_id"), "resumes", ["job_id"], unique=False)

    # 2. Add application tracking columns to saved_jobs
    op.add_column("saved_jobs", sa.Column("deadline", sa.DateTime(timezone=True), nullable=True))
    op.add_column("saved_jobs", sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("saved_jobs", sa.Column("resume_id", sa.String(length=36), nullable=True))
    op.add_column("saved_jobs", sa.Column("application_packet", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))


def downgrade() -> None:
    # 1. Drop application tracking columns from saved_jobs
    op.drop_column("saved_jobs", "application_packet")
    op.drop_column("saved_jobs", "resume_id")
    op.drop_column("saved_jobs", "submitted_at")
    op.drop_column("saved_jobs", "deadline")

    # 2. Drop resumes table
    op.drop_index(op.f("ix_resumes_job_id"), table_name="resumes")
    op.drop_index(op.f("ix_resumes_firebase_uid"), table_name="resumes")
    op.drop_index(op.f("ix_resumes_id"), table_name="resumes")
    op.drop_table("resumes")
