-- TaskLib Migration: Add tasks table
--
-- This SQL script adds the tasklib tasks table to an existing PostgreSQL database.
--
-- Usage:
--   psql -U username -d database_name -f 001_add_tasks_table.sql
--
-- Or from psql:
--   \i /path/to/001_add_tasks_table.sql

CREATE TABLE IF NOT EXISTS tasks (
    id UUID NOT NULL,
    name VARCHAR NOT NULL,
    state VARCHAR NOT NULL,
    scheduled_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    args JSONB NOT NULL,
    kwargs JSONB NOT NULL,
    result JSONB,
    error TEXT,
    retry_count INTEGER NOT NULL,
    max_retries INTEGER NOT NULL,
    next_retry_at TIMESTAMP,
    worker_id VARCHAR,
    locked_until TIMESTAMP,
    timeout_seconds INTEGER,
    priority INTEGER NOT NULL,
    tags JSONB NOT NULL,
    PRIMARY KEY (id)
);

-- Create indexes for efficient querying
-- These are critical for performance with multiple workers
CREATE INDEX IF NOT EXISTS ix_tasks_state ON tasks (state);
CREATE INDEX IF NOT EXISTS ix_tasks_scheduled_at ON tasks (scheduled_at);
CREATE INDEX IF NOT EXISTS ix_tasks_locked_until ON tasks (locked_until);
CREATE INDEX IF NOT EXISTS ix_tasks_priority ON tasks (priority);
CREATE INDEX IF NOT EXISTS ix_tasks_name ON tasks (name);

-- Grant permissions (adjust to your needs)
-- GRANT SELECT, INSERT, UPDATE ON tasks TO app_user;

-- Verify table was created
SELECT to_regclass('public.tasks') AS table_exists;
