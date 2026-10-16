"""Create job postings, job sources, and saved jobs tables

Revision ID: 003_create_job_and_source_tables
Revises: 002_create_github_and_skill_tables
Create Date: 2026-10-16 19:39:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003_create_job_and_source_tables"
down_revision: Union[str, None] = "002_create_github_and_skill_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. job_postings
    op.create_table(
        "job_postings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=False),
        sa.Column("dedup_hash", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("is_remote", sa.Boolean(), nullable=False),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("required_skills", sa.JSON(), nullable=False),
        sa.Column("salary_currency", sa.String(length=10), nullable=True),
        sa.Column("salary_min", sa.Float(), nullable=True),
        sa.Column("salary_max", sa.Float(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedup_hash", name=op.f("uq_job_postings_dedup_hash")),
    )
    op.create_index(op.f("ix_job_postings_id"), "job_postings", ["id"], unique=False)
    op.create_index(op.f("ix_job_postings_source"), "job_postings", ["source"], unique=False)
    op.create_index(op.f("ix_job_postings_source_id"), "job_postings", ["source_id"], unique=False)
    op.create_index(op.f("ix_job_postings_title"), "job_postings", ["title"], unique=False)
    op.create_index(op.f("ix_job_postings_company"), "job_postings", ["company"], unique=False)
    op.create_index(op.f("ix_job_postings_location"), "job_postings", ["location"], unique=False)
    op.create_index(op.f("ix_job_postings_job_type"), "job_postings", ["job_type"], unique=False)

    # 2. job_sources
    op.create_table(
        "job_sources",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_name", sa.String(length=50), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_status", sa.String(length=32), nullable=False),
        sa.Column("jobs_synced_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_name", name=op.f("uq_job_sources_source_name")),
    )
    op.create_index(op.f("ix_job_sources_id"), "job_sources", ["id"], unique=False)

    # 3. saved_jobs
    op.create_table(
        "saved_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("firebase_uid", "job_id", name="uq_user_saved_job"),
    )
    op.create_index(op.f("ix_saved_jobs_id"), "saved_jobs", ["id"], unique=False)
    op.create_index(op.f("ix_saved_jobs_firebase_uid"), "saved_jobs", ["firebase_uid"], unique=False)
    op.create_index(op.f("ix_saved_jobs_job_id"), "saved_jobs", ["job_id"], unique=False)


def downgrade() -> None:
    op.drop_table("saved_jobs")
    op.drop_table("job_sources")
    op.drop_table("job_postings")
