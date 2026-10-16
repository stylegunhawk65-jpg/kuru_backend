"""Create practical assessment tables and add verification_status to student_skills

Revision ID: 007_create_practical_assessment_tables
Revises: 006_create_skillproof_tables
Create Date: 2026-10-17 01:52:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "007_create_practical_assessment_tables"
down_revision: Union[str, None] = "006_create_skillproof_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add verification_status column to student_skills
    op.add_column(
        "student_skills",
        sa.Column(
            "verification_status",
            sa.String(length=50),
            nullable=False,
            server_default="repository_supported",
        ),
    )

    # 2. Create practical_assessments table
    op.create_table(
        "practical_assessments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("repository_id", sa.String(length=64), nullable=True),
        sa.Column("repository_full_name", sa.String(length=255), nullable=True),
        sa.Column("skill_name", sa.String(length=100), nullable=False),
        sa.Column("assessment_level", sa.String(length=32), nullable=False),
        sa.Column("challenge_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("challenge_data", sa.JSON(), nullable=False),
        sa.Column("hidden_test_data", sa.JSON(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("level_selection_rationale", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_practical_assessments_id"), "practical_assessments", ["id"], unique=False)
    op.create_index(op.f("ix_practical_assessments_firebase_uid"), "practical_assessments", ["firebase_uid"], unique=False)
    op.create_index(op.f("ix_practical_assessments_skill_name"), "practical_assessments", ["skill_name"], unique=False)
    op.create_index(op.f("ix_practical_assessments_status"), "practical_assessments", ["status"], unique=False)

    # 3. Create assessment_submissions table
    op.create_table(
        "assessment_submissions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("assessment_id", sa.String(length=36), nullable=False),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("submitted_code", sa.Text(), nullable=False),
        sa.Column("execution_status", sa.String(length=32), nullable=False),
        sa.Column("public_results", sa.JSON(), nullable=False),
        sa.Column("hidden_results", sa.JSON(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("rubric_feedback", sa.JSON(), nullable=False),
        sa.Column("execution_metrics", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["practical_assessments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assessment_submissions_id"), "assessment_submissions", ["id"], unique=False)
    op.create_index(op.f("ix_assessment_submissions_assessment_id"), "assessment_submissions", ["assessment_id"], unique=False)
    op.create_index(op.f("ix_assessment_submissions_firebase_uid"), "assessment_submissions", ["firebase_uid"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_assessment_submissions_firebase_uid"), table_name="assessment_submissions")
    op.drop_index(op.f("ix_assessment_submissions_assessment_id"), table_name="assessment_submissions")
    op.drop_index(op.f("ix_assessment_submissions_id"), table_name="assessment_submissions")
    op.drop_table("assessment_submissions")

    op.drop_index(op.f("ix_practical_assessments_status"), table_name="practical_assessments")
    op.drop_index(op.f("ix_practical_assessments_skill_name"), table_name="practical_assessments")
    op.drop_index(op.f("ix_practical_assessments_firebase_uid"), table_name="practical_assessments")
    op.drop_index(op.f("ix_practical_assessments_id"), table_name="practical_assessments")
    op.drop_table("practical_assessments")

    op.drop_column("student_skills", "verification_status")
