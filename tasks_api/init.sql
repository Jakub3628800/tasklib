-- Initialize TaskLib database with test data

-- Create tasks table if it doesn't exist
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY,
    name VARCHAR NOT NULL,
    state VARCHAR NOT NULL,
    scheduled_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    args JSONB NOT NULL DEFAULT '{}',
    kwargs JSONB NOT NULL DEFAULT '{}',
    result JSONB,
    error TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL,
    next_retry_at TIMESTAMP,
    worker_id VARCHAR,
    locked_until TIMESTAMP,
    timeout_seconds INTEGER,
    priority INTEGER NOT NULL DEFAULT 0,
    tags JSONB NOT NULL DEFAULT '{}'
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_tasks_name ON tasks(name);
CREATE INDEX IF NOT EXISTS idx_tasks_state ON tasks(state);
CREATE INDEX IF NOT EXISTS idx_tasks_scheduled_at ON tasks(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_tasks_locked_until ON tasks(locked_until);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);

-- Clear existing test data
TRUNCATE TABLE tasks;

-- Insert test data with various states and timestamps
-- Recent pending tasks (last 1 hour)
INSERT INTO tasks (id, name, state, scheduled_at, created_at, max_retries, priority, tags)
VALUES
    ('550e8400-e29b-41d4-a716-446655440001'::uuid, 'process_payment', 'pending', NOW() + INTERVAL '1 minute', NOW(), 3, 1, '{"type": "payment"}'),
    ('550e8400-e29b-41d4-a716-446655440002'::uuid, 'send_email', 'pending', NOW() + INTERVAL '2 minutes', NOW(), 2, 0, '{"type": "notification"}'),
    ('550e8400-e29b-41d4-a716-446655440003'::uuid, 'generate_report', 'pending', NOW() + INTERVAL '5 minutes', NOW() - INTERVAL '10 minutes', 5, 2, '{"type": "report"}');

-- Running tasks (currently locked by workers)
INSERT INTO tasks (id, name, state, scheduled_at, started_at, created_at, worker_id, locked_until, max_retries, priority, tags)
VALUES
    ('550e8400-e29b-41d4-a716-446655440011'::uuid, 'export_data', 'running', NOW() - INTERVAL '30 minutes', NOW() - INTERVAL '10 minutes', NOW() - INTERVAL '30 minutes', 'worker-1', NOW() + INTERVAL '20 minutes', 3, 1, '{"type": "export"}'),
    ('550e8400-e29b-41d4-a716-446655440012'::uuid, 'sync_external_api', 'running', NOW() - INTERVAL '45 minutes', NOW() - INTERVAL '5 minutes', NOW() - INTERVAL '45 minutes', 'worker-2', NOW() + INTERVAL '15 minutes', 2, 0, '{"type": "sync"}');

-- Completed tasks (1 hour ago)
INSERT INTO tasks (id, name, state, scheduled_at, started_at, completed_at, created_at, max_retries, priority, result, tags)
VALUES
    ('550e8400-e29b-41d4-a716-446655440021'::uuid, 'cleanup_cache', 'completed', NOW() - INTERVAL '1 hour' - INTERVAL '30 minutes', NOW() - INTERVAL '1 hour' - INTERVAL '20 minutes', NOW() - INTERVAL '1 hour', NOW() - INTERVAL '1 hour' - INTERVAL '30 minutes', 1, 0, '{"cleaned_items": 1520}', '{"type": "maintenance"}'),
    ('550e8400-e29b-41d4-a716-446655440022'::uuid, 'generate_invoice', 'completed', NOW() - INTERVAL '1.5 hours', NOW() - INTERVAL '1 hour' - INTERVAL '20 minutes', NOW() - INTERVAL '1 hour' - INTERVAL '10 minutes', NOW() - INTERVAL '1.5 hours', 2, 1, '{"invoice_id": "INV-2024-001"}', '{"type": "billing"}');

-- Failed tasks (6 hours ago)
INSERT INTO tasks (id, name, state, scheduled_at, started_at, completed_at, created_at, max_retries, priority, retry_count, error, tags)
VALUES
    ('550e8400-e29b-41d4-a716-446655440031'::uuid, 'fetch_external_data', 'failed', NOW() - INTERVAL '6 hours' - INTERVAL '30 minutes', NOW() - INTERVAL '6 hours' - INTERVAL '20 minutes', NOW() - INTERVAL '6 hours', NOW() - INTERVAL '6 hours' - INTERVAL '30 minutes', 3, 1, 2, 'Connection timeout after 30 seconds', '{"type": "data_fetch"}'),
    ('550e8400-e29b-41d4-a716-446655440032'::uuid, 'validate_transaction', 'failed', NOW() - INTERVAL '6 hours' - INTERVAL '15 minutes', NOW() - INTERVAL '6 hours' - INTERVAL '5 minutes', NOW() - INTERVAL '6 hours', NOW() - INTERVAL '6 hours' - INTERVAL '15 minutes', 2, 0, 2, 'Validation failed: insufficient balance', '{"type": "payment"}');

-- Permanent failures (max retries exceeded, 24 hours ago)
INSERT INTO tasks (id, name, state, scheduled_at, started_at, completed_at, created_at, max_retries, priority, retry_count, error, tags)
VALUES
    ('550e8400-e29b-41d4-a716-446655440041'::uuid, 'process_legacy_data', 'failed', NOW() - INTERVAL '24 hours', NOW() - INTERVAL '24 hours' + INTERVAL '1 minute', NOW() - INTERVAL '24 hours' + INTERVAL '5 minutes', NOW() - INTERVAL '24 hours', 3, 0, 3, 'Incompatible data format, all retries exhausted', '{"type": "legacy"}'),
    ('550e8400-e29b-41d4-a716-446655440042'::uuid, 'send_webhook', 'failed', NOW() - INTERVAL '24 hours' - INTERVAL '6 hours', NOW() - INTERVAL '24 hours' - INTERVAL '5 hours', NOW() - INTERVAL '24 hours' - INTERVAL '4 hours', NOW() - INTERVAL '24 hours' - INTERVAL '6 hours', 3, 2, 3, 'Webhook endpoint permanently unreachable (404)', '{"type": "integration"}');

-- More completed tasks (30 days ago - for testing 30d filter)
INSERT INTO tasks (id, name, state, scheduled_at, started_at, completed_at, created_at, max_retries, priority, result, tags)
VALUES
    ('550e8400-e29b-41d4-a716-446655440051'::uuid, 'archive_old_records', 'completed', NOW() - INTERVAL '30 days', NOW() - INTERVAL '30 days' + INTERVAL '10 minutes', NOW() - INTERVAL '30 days' + INTERVAL '30 minutes', NOW() - INTERVAL '30 days', 1, 0, '{"archived_count": 5000}', '{"type": "maintenance"}'),
    ('550e8400-e29b-41d4-a716-446655440052'::uuid, 'backup_database', 'completed', NOW() - INTERVAL '30 days' - INTERVAL '1 hour', NOW() - INTERVAL '30 days' - INTERVAL '50 minutes', NOW() - INTERVAL '30 days' - INTERVAL '20 minutes', NOW() - INTERVAL '30 days' - INTERVAL '1 hour', 1, 1, '{"backup_size_mb": 2048}', '{"type": "backup"}');

-- Pending tasks from 7 days ago
INSERT INTO tasks (id, name, state, scheduled_at, created_at, max_retries, priority, tags)
VALUES
    ('550e8400-e29b-41d4-a716-446655440061'::uuid, 'old_pending_task', 'pending', NOW() - INTERVAL '7 days', NOW() - INTERVAL '7 days', 2, 0, '{"type": "old"}');
