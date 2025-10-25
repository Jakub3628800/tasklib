# TaskLib - Final PostgreSQL Schema

## The Complete `tasks` Table

This is exactly what lives in your PostgreSQL database when tasklib is running.

### SQL Definition (as created)

```sql
CREATE TABLE tasks (
    -- Primary Key
    id UUID NOT NULL PRIMARY KEY,

    -- Task Identity
    name VARCHAR NOT NULL,                    -- "send_email", "process_image", etc.

    -- State Management
    state VARCHAR NOT NULL,                   -- "pending" | "running" | "completed" | "failed"
    scheduled_at TIMESTAMP NOT NULL,          -- When to execute
    started_at TIMESTAMP,                     -- When worker started
    completed_at TIMESTAMP,                   -- When finished

    -- Metadata
    created_at TIMESTAMP NOT NULL,            -- When submitted

    -- Arguments (Pydantic-validated)
    args JSONB NOT NULL DEFAULT '{}',         -- Reserved for future use
    kwargs JSONB NOT NULL,                    -- Function keyword arguments

    -- Results
    result JSONB,                             -- {"value": <return_value>}
    error TEXT,                               -- Full exception traceback

    -- Retry Logic
    retry_count INTEGER NOT NULL DEFAULT 0,   -- Current attempt (0 = first try)
    max_retries INTEGER NOT NULL,             -- Max attempts before giving up
    next_retry_at TIMESTAMP,                  -- When to retry (if failed)

    -- Locking & Worker Management
    worker_id VARCHAR,                        -- UUID of worker holding lock
    locked_until TIMESTAMP,                   -- Lock expiry (dead worker detection)

    -- Execution Control
    timeout_seconds INTEGER,                  -- Max execution time

    -- Ordering & Metadata
    priority INTEGER NOT NULL DEFAULT 0,      -- Higher = execute first
    tags JSONB NOT NULL DEFAULT '{}'          -- {"batch": "daily", "type": "email"}
);

-- Indexes (critical for performance)
CREATE INDEX ix_tasks_state ON tasks (state);
CREATE INDEX ix_tasks_scheduled_at ON tasks (scheduled_at);
CREATE INDEX ix_tasks_locked_until ON tasks (locked_until);
CREATE INDEX ix_tasks_priority ON tasks (priority);
CREATE INDEX ix_tasks_name ON tasks (name);
```

## Column-by-Column Breakdown

### Identity Columns

| Column | Type | Nullable | Default | Purpose |
|--------|------|----------|---------|---------|
| **id** | UUID | No | uuid_generate_v4() | Unique task identifier, returned when you submit |
| **name** | VARCHAR | No | - | Function name: `"send_email"`, `"process_image"` |

### State Columns

| Column | Type | Nullable | Default | Purpose |
|--------|------|----------|---------|---------|
| **state** | VARCHAR | No | - | Current state: `"pending"`, `"running"`, `"completed"`, `"failed"` |
| **scheduled_at** | TIMESTAMP | No | - | When task should execute (allows delays) |
| **started_at** | TIMESTAMP | Yes | - | When execution began (set by worker) |
| **completed_at** | TIMESTAMP | Yes | - | When execution finished (set by worker) |

### Parameters & Results

| Column | Type | Nullable | Default | Purpose |
|--------|------|----------|---------|---------|
| **args** | JSONB | No | `{}` | Reserved for future positional arguments |
| **kwargs** | JSONB | No | - | Function parameters: `{"to": "user@example.com", "subject": "Hello"}` |
| **result** | JSONB | Yes | - | Return value: `{"value": true}` or `null` |
| **error** | TEXT | Yes | - | Exception traceback if task failed |

### Retry Management

| Column | Type | Nullable | Default | Purpose |
|--------|------|----------|---------|---------|
| **retry_count** | INTEGER | No | 0 | Current attempt number (0-indexed) |
| **max_retries** | INTEGER | No | - | How many attempts allowed (e.g., 3) |
| **next_retry_at** | TIMESTAMP | Yes | - | When to retry (scheduled via exponential backoff) |

### Worker Locking (Distributed Coordination)

| Column | Type | Nullable | Default | Purpose |
|--------|------|----------|---------|---------|
| **worker_id** | VARCHAR | Yes | - | UUID of worker currently executing (`"worker-a-uuid"`) |
| **locked_until** | TIMESTAMP | Yes | - | When lock expires (dead worker detection) |

### Execution Control

| Column | Type | Nullable | Default | Purpose |
|--------|------|----------|---------|---------|
| **timeout_seconds** | INTEGER | Yes | - | Max execution time before timeout (e.g., 30) |
| **priority** | INTEGER | No | 0 | Task priority: -10 to 100 (higher = first) |

### Custom Metadata

| Column | Type | Nullable | Default | Purpose |
|--------|------|----------|---------|---------|
| **created_at** | TIMESTAMP | No | - | When task was submitted |
| **tags** | JSONB | No | `{}` | Custom metadata: `{"batch": "daily", "user_id": 123}` |

## Real Example Records

### Task 1: Pending (Waiting to Execute)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "send_email",
  "state": "pending",
  "scheduled_at": "2025-10-25T18:00:00",
  "started_at": null,
  "completed_at": null,
  "created_at": "2025-10-25T17:00:00",
  "args": {},
  "kwargs": {
    "to": "alice@example.com",
    "subject": "Welcome!",
    "body": "Hello Alice..."
  },
  "result": null,
  "error": null,
  "retry_count": 0,
  "max_retries": 3,
  "next_retry_at": null,
  "worker_id": null,
  "locked_until": null,
  "timeout_seconds": 30,
  "priority": 0,
  "tags": {
    "batch": "welcome-emails",
    "cohort": "2025-10-25"
  }
}
```

**State:** Ready to execute. Worker will pick it up when `scheduled_at <= NOW()`.

---

### Task 2: Running (Currently Executing)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "name": "send_email",
  "state": "running",
  "scheduled_at": "2025-10-25T18:00:00",
  "started_at": "2025-10-25T18:05:23",
  "completed_at": null,
  "created_at": "2025-10-25T17:00:00",
  "args": {},
  "kwargs": {
    "to": "bob@example.com",
    "subject": "Hello Bob"
  },
  "result": null,
  "error": null,
  "retry_count": 0,
  "max_retries": 3,
  "next_retry_at": null,
  "worker_id": "worker-prod-01-uuid",
  "locked_until": "2025-10-25T18:15:23",
  "timeout_seconds": 30,
  "priority": 0,
  "tags": {}
}
```

**State:** Being executed by a worker. Lock will expire in 10 minutes. If worker dies, another worker can take it over.

---

### Task 3: Completed Successfully

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440003",
  "name": "send_email",
  "state": "completed",
  "scheduled_at": "2025-10-25T18:00:00",
  "started_at": "2025-10-25T18:05:12",
  "completed_at": "2025-10-25T18:05:18",
  "created_at": "2025-10-25T17:00:00",
  "args": {},
  "kwargs": {
    "to": "charlie@example.com",
    "subject": "Success!"
  },
  "result": {
    "value": true
  },
  "error": null,
  "retry_count": 0,
  "max_retries": 3,
  "next_retry_at": null,
  "worker_id": null,
  "locked_until": null,
  "timeout_seconds": 30,
  "priority": 0,
  "tags": {}
}
```

**State:** Finished successfully! Result is stored. Can retrieve and inspect anytime.

---

### Task 4: Failed, Scheduled for Retry

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440004",
  "name": "send_email",
  "state": "failed",
  "scheduled_at": "2025-10-25T18:00:00",
  "started_at": "2025-10-25T18:10:00",
  "completed_at": null,
  "created_at": "2025-10-25T17:00:00",
  "args": {},
  "kwargs": {
    "to": "david@example.com",
    "subject": "Newsletter"
  },
  "result": null,
  "error": "SMTPException: Connection timeout\nTraceback:\n  File \"...\", line 42, in send_email\n    smtp.send_message(...)",
  "retry_count": 1,
  "max_retries": 3,
  "next_retry_at": "2025-10-25T18:10:05",
  "worker_id": null,
  "locked_until": null,
  "timeout_seconds": 30,
  "priority": 0,
  "tags": {}
}
```

**State:** Failed attempt 1 of 3. Will be retried at `18:10:05` (5 seconds later). Full traceback captured for debugging.

---

### Task 5: Permanently Failed (Max Retries Exceeded)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440005",
  "name": "send_email",
  "state": "failed",
  "scheduled_at": "2025-10-25T18:00:00",
  "started_at": "2025-10-25T18:20:30",
  "completed_at": "2025-10-25T18:20:35",
  "created_at": "2025-10-25T17:00:00",
  "args": {},
  "kwargs": {
    "to": "invalid-email-address",
    "subject": "Test"
  },
  "result": null,
  "error": "ValidationError: Invalid email address\nTraceback:\n  File \"...\", line 12, in send_email\n    validate_email(to)",
  "retry_count": 3,
  "max_retries": 3,
  "next_retry_at": null,
  "worker_id": null,
  "locked_until": null,
  "timeout_seconds": 30,
  "priority": 0,
  "tags": {}
}
```

**State:** Gave up after 3 attempts. Error is permanent (invalid email). Won't retry. `completed_at` is set.

---

## Indexes (Performance)

TaskLib creates 5 indexes automatically:

```sql
CREATE INDEX ix_tasks_state ON tasks (state);           -- Filter by state (pending, running, etc.)
CREATE INDEX ix_tasks_scheduled_at ON tasks (scheduled_at);  -- Find tasks ready to execute
CREATE INDEX ix_tasks_locked_until ON tasks (locked_until);  -- Detect dead workers
CREATE INDEX ix_tasks_priority ON tasks (priority);     -- Sort by priority
CREATE INDEX ix_tasks_name ON tasks (name);             -- Filter by task name
```

**Why?** These enable worker queries to be fast:

```sql
-- Worker uses this query every poll (efficient with indexes)
SELECT * FROM tasks
WHERE state IN ('pending', 'failed')
  AND scheduled_at <= NOW()
  AND (locked_until IS NULL OR locked_until < NOW())
ORDER BY priority DESC
LIMIT 1
FOR UPDATE;  -- PostgreSQL row lock
```

**Query Plan:** Uses `ix_tasks_state` + `ix_tasks_scheduled_at` → O(log n) lookup instead of O(n) table scan.

## Size Estimates

**Per Task:**
- Fixed columns: ~200 bytes
- Simple kwargs: ~200 bytes
- Error traceback (on failure): ~2 KB
- **Total:** ~2-10 KB per task

**Example 10K Tasks:**
- Size: ~20-100 MB
- Insert rate: 1000+ tasks/sec
- Query latency: <5ms with indexes

## Cleanup Policy

TaskLib stores results indefinitely (by design). You can clean up manually:

```sql
-- Archive completed tasks older than 30 days
DELETE FROM tasks
WHERE state = 'completed'
AND completed_at < NOW() - INTERVAL '30 days';

-- Clean up failed tasks older than 90 days
DELETE FROM tasks
WHERE state = 'failed'
AND completed_at < NOW() - INTERVAL '90 days'
AND retry_count >= max_retries;
```

Or with cron:

```bash
0 2 * * * psql -d mydb -c "DELETE FROM tasks WHERE state='completed' AND completed_at < NOW() - INTERVAL '30 days';"
```

---

## The Story of a Task

### 1. User submits task (Python)

```python
task_id = await tasklib.submit_task(
    send_email,
    to="user@example.com",
    subject="Hello"
)
# Returns: UUID("550e8400-e29b-41d4-a716-446655440001")
```

**In database:**

```json
{
  "id": "550e8400...",
  "name": "send_email",
  "state": "pending",
  "kwargs": {"to": "user@example.com", "subject": "Hello"},
  "scheduled_at": "2025-10-25T18:00:00",
  ...
}
```

### 2. Worker polls (SELECT FOR UPDATE)

Worker runs this query every 1 second:

```sql
SELECT * FROM tasks
WHERE state IN ('pending', 'failed')
  AND scheduled_at <= NOW()
  AND (locked_until IS NULL OR locked_until < NOW())
ORDER BY priority DESC, created_at ASC
LIMIT 1
FOR UPDATE;  -- Atomic lock
```

**Task found!** Database updates:

```json
{
  "state": "running",
  "worker_id": "worker-01-uuid",
  "locked_until": "2025-10-25T18:10:00",  -- 10 minute timeout
  "started_at": "2025-10-25T18:00:05"
}
```

### 3. Worker executes task

Python function runs:

```python
result = await loop.run_in_executor(
    None,
    lambda: send_email(to="user@example.com", subject="Hello")
)
# Returns: True
```

### 4. Worker updates DB with result

```json
{
  "state": "completed",
  "result": {"value": true},
  "completed_at": "2025-10-25T18:00:08",
  "worker_id": null,
  "locked_until": null
}
```

### 5. Application queries result

```python
task = tasklib.get_task(task_id)
if tasklib.is_completed(task):
    print(f"Task result: {task.result['value']}")
    # Output: Task result: True
```

---

## All in One Place

That's it. Everything about every task is in this one table. No joins. No denormalization needed. Just query what you need:

```sql
-- All pending tasks
SELECT id, name FROM tasks WHERE state = 'pending';

-- Failed tasks (for alerts)
SELECT id, name, error FROM tasks WHERE state = 'failed' AND completed_at > NOW() - INTERVAL '1 hour';

-- Performance metrics
SELECT name, COUNT(*), AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))
FROM tasks WHERE state = 'completed'
GROUP BY name;
```

Simple. Durable. Done.

---

**Last Updated:** 2025-10-25
