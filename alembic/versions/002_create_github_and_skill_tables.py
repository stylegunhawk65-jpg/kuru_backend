"""Create github connections, repositories, analyses, student skills, and skill graph tables

Revision ID: 002_create_github_and_skill_tables
Revises: 001_create_student_profiles_table
Create Date: 2026-10-16 19:28:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002_create_github_and_skill_tables"
down_revision: Union[str, None] = "001_create_student_profiles_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. github_connections
    op.create_table(
        "github_connections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("encrypted_access_token", sa.Text(), nullable=True),
        sa.Column("github_user_id", sa.String(length=64), nullable=True),
        sa.Column("github_username", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_github_connections_id"),
        "github_connections",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_github_connections_firebase_uid"),
        "github_connections",
        ["firebase_uid"],
        unique=True,
    )

    # 2. github_repositories
    op.create_table(
        "github_repositories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("github_repo_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("is_private", sa.Boolean(), nullable=False),
        sa.Column("html_url", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_branch", sa.String(length=64), nullable=False),
        sa.Column("primary_language", sa.String(length=100), nullable=True),
        sa.Column("stars_count", sa.Integer(), nullable=False),
        sa.Column("forks_count", sa.Integer(), nullable=False),
        sa.Column("selected_for_analysis", sa.Boolean(), nullable=False),
        sa.Column("last_analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_github_repositories_id"),
        "github_repositories",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_github_repositories_firebase_uid"),
        "github_repositories",
        ["firebase_uid"],
        unique=False,
    )

    # 3. repository_analyses
    op.create_table(
        "repository_analyses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("repository_id", sa.String(length=36), nullable=False),
        sa.Column("repository_full_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("languages_breakdown", sa.JSON(), nullable=False),
        sa.Column("extracted_skills", sa.JSON(), nullable=False),
        sa.Column("file_tree_summary", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_repository_analyses_id"),
        "repository_analyses",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_repository_analyses_firebase_uid"),
        "repository_analyses",
        ["firebase_uid"],
        unique=False,
    )
    op.create_index(
        op.f("ix_repository_analyses_repository_id"),
        "repository_analyses",
        ["repository_id"],
        unique=False,
    )

    # 4. student_skills
    op.create_table(
        "student_skills",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("skill_name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("source_repositories", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_student_skills_id"),
        "student_skills",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_student_skills_firebase_uid"),
        "student_skills",
        ["firebase_uid"],
        unique=False,
    )
    op.create_index(
        op.f("ix_student_skills_skill_name"),
        "student_skills",
        ["skill_name"],
        unique=False,
    )

    # 5. skill_graph_edges
    op.create_table(
        "skill_graph_edges",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("source_skill", sa.String(length=100), nullable=False),
        sa.Column("target_skill", sa.String(length=100), nullable=False),
        sa.Column("relationship_type", sa.String(length=50), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_skill_graph_edges_id"),
        "skill_graph_edges",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_skill_graph_edges_firebase_uid"),
        "skill_graph_edges",
        ["firebase_uid"],
        unique=False,
    )
    op.create_index(
        op.f("ix_skill_graph_edges_source_skill"),
        "skill_graph_edges",
        ["source_skill"],
        unique=False,
    )
    op.create_index(
        op.f("ix_skill_graph_edges_target_skill"),
        "skill_graph_edges",
        ["target_skill"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("skill_graph_edges")
    op.drop_table("student_skills")
    op.drop_table("repository_analyses")
    op.drop_table("github_repositories")
    op.drop_table("github_connections")
