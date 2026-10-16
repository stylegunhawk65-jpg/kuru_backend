"""Create student profiles table

Revision ID: 001_create_student_profiles_table
Revises: None
Create Date: 2026-10-16 19:18:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001_create_student_profiles_table"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "student_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("education", sa.JSON(), nullable=False),
        sa.Column("interests", sa.JSON(), nullable=False),
        sa.Column("target_roles", sa.JSON(), nullable=False),
        sa.Column("preferred_locations", sa.JSON(), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_student_profiles_id"),
        "student_profiles",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_student_profiles_firebase_uid"),
        "student_profiles",
        ["firebase_uid"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_student_profiles_firebase_uid"), table_name="student_profiles")
    op.drop_index(op.f("ix_student_profiles_id"), table_name="student_profiles")
    op.drop_table("student_profiles")
