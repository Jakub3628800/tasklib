# Database Schema

TaskLib uses a single `tasks` table.

## Table Structure

```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
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
    tags JSONB NOT NULL
);
```

See [FINAL_SCHEMA.md](../../FINAL_SCHEMA.md) for detailed documentation.
