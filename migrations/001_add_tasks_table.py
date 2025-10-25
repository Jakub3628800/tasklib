"""Alembic migration: Add tasks table for tasklib.

This migration adds the tasklib tasks table to an existing database.
It's designed to be used as-is or copied into an existing Alembic migrations directory.

Usage:
  1. Copy this file to your project's alembic/versions/ directory
  2. Run: alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision = "001_add_tasklib_tasks_table"
down_revision = None  # Change to your latest migration if this isn't the first
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the tasks table for tasklib."""
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("args", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("kwargs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column("worker_id", sa.String(), nullable=True),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("timeout_seconds", sa.Integer(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for efficient querying
    op.create_index("ix_tasks_state", "tasks", ["state"])
    op.create_index("ix_tasks_scheduled_at", "tasks", ["scheduled_at"])
    op.create_index("ix_tasks_locked_until", "tasks", ["locked_until"])
    op.create_index("ix_tasks_priority", "tasks", ["priority"])
    op.create_index("ix_tasks_name", "tasks", ["name"])


def downgrade() -> None:
    """Drop the tasks table."""
    # Drop indexes
    op.drop_index("ix_tasks_name", table_name="tasks")
    op.drop_index("ix_tasks_priority", table_name="tasks")
    op.drop_index("ix_tasks_locked_until", table_name="tasks")
    op.drop_index("ix_tasks_scheduled_at", table_name="tasks")
    op.drop_index("ix_tasks_state", table_name="tasks")

    # Drop table
    op.drop_table("tasks")
