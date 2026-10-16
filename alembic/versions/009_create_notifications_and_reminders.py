"""Create notifications and reminders tables

Revision ID: 009_create_notifications_and_reminders
Revises: 008_create_resumes_and_expand_application_tracking
Create Date: 2026-10-17 03:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "009_create_notifications_and_reminders"
down_revision: Union[str, None] = "008_create_resumes_and_expand_application_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create notifications table
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("notification_type", sa.String(length=50), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column("entity_id", sa.String(length=255), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("data", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_id"), "notifications", ["id"], unique=False)
    op.create_index(op.f("ix_notifications_firebase_uid"), "notifications", ["firebase_uid"], unique=False)
    op.create_index(op.f("ix_notifications_notification_type"), "notifications", ["notification_type"], unique=False)
    op.create_index(op.f("ix_notifications_is_read"), "notifications", ["is_read"], unique=False)
    op.create_index("ix_notifications_user_unread", "notifications", ["firebase_uid", "is_read"], unique=False)
    op.create_index("ix_notifications_user_created", "notifications", ["firebase_uid", "created_at"], unique=False)

    # 2. Create reminders table
    op.create_table(
        "reminders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reminder_type", sa.String(length=50), nullable=False, server_default=sa.text("'custom'")),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_dismissed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reminders_id"), "reminders", ["id"], unique=False)
    op.create_index(op.f("ix_reminders_firebase_uid"), "reminders", ["firebase_uid"], unique=False)
    op.create_index(op.f("ix_reminders_job_id"), "reminders", ["job_id"], unique=False)
    op.create_index(op.f("ix_reminders_due_date"), "reminders", ["due_date"], unique=False)
    op.create_index("ix_reminders_user_active", "reminders", ["firebase_uid", "is_completed", "is_dismissed"], unique=False)
    op.create_index("ix_reminders_user_due", "reminders", ["firebase_uid", "due_date"], unique=False)


def downgrade() -> None:
    # 2. Drop reminders
    op.drop_index("ix_reminders_user_due", table_name="reminders")
    op.drop_index("ix_reminders_user_active", table_name="reminders")
    op.drop_index(op.f("ix_reminders_due_date"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_job_id"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_firebase_uid"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_id"), table_name="reminders")
    op.drop_table("reminders")

    # 1. Drop notifications
    op.drop_index("ix_notifications_user_created", table_name="notifications")
    op.drop_index("ix_notifications_user_unread", table_name="notifications")
    op.drop_index(op.f("ix_notifications_is_read"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_notification_type"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_firebase_uid"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_id"), table_name="notifications")
    op.drop_table("notifications")
