# TaskLib Specification

## Executive Summary

**TaskLib** is a PostgreSQL-backed task queue library optimized for simplicity and durability.

**Core concept:** All task state lives in a single PostgreSQL table. Workers poll the table, claim tasks via `SELECT FOR UPDATE`, execute them, and report results.

## Feature Set

### v1 (Current)

✅ **Task Definition**
- `@task` decorator to mark sync functions as tasks
- Pydantic validation of arguments
- Per-task configuration: max_retries, timeout_seconds

✅ **Task Submission**
- `submit_task()` to queue work for later
- Delayed execution (delay_seconds)
- Priority support
- Metadata tags

✅ **Task Execution**
- Sync function execution only (async in v2)
- Configurable timeout per task
- Full error traceback capture

✅ **Retry Logic**
- Exponential backoff: delay = base * (multiplier ^ attempt)
- Configurable per task or globally
- Default: 5s, 10s, 20s, then fail

✅ **Multi-Worker Support**
- PostgreSQL SELECT FOR UPDATE for atomic locking
- Automatic dead worker detection (lock timeout)
- Distributed workers on any machine with DB access

✅ **Monitoring**
- `get_task(id)` - retrieve single task status
- `list_tasks(state=..., name=...)` - filter tasks
- Direct SQL queries via `psql`

✅ **Durability**
- All state persisted to PostgreSQL
- No in-memory queue (worker death = automatic recovery)
- No external message broker required

### Not Included (v1)

❌ Recurring/cron tasks
❌ Task dependencies/chaining
❌ Admin UI
❌ Async functions
❌ Task result expiry/cleanup (indefinite storage)
❌ Multiple serializers (JSON only)
❌ Distributed consensus features

## Schema

Single table `tasks`:

```
Column             | Type      | Notes
-------------------|-----------|------------------------------------------
id                 | UUID      | Primary key
name               | VARCHAR   | Function name (indexed)
state              | VARCHAR   | pending|running|completed|failed (indexed)
scheduled_at       | TIMESTAMP | When to execute (indexed)
locked_until       | TIMESTAMP | Lock expiry, dead worker detection (indexed)
started_at         | TIMESTAMP | Execution start
completed_at       | TIMESTAMP | Execution end
created_at         | TIMESTAMP | Submission time
args               | JSONB     | Reserved for future use
kwargs             | JSONB     | Function keyword arguments
result             | JSONB     | Return value from function
error              | TEXT      | Full exception traceback
retry_count        | INT       | Current attempt number
max_retries        | INT       | Max attempts allowed
next_retry_at      | TIMESTAMP | When to retry (if failed)
worker_id          | VARCHAR   | Lock holder (worker UUID)
timeout_seconds    | INT       | Max execution time
priority           | INT       | Sort order (higher = first)
tags               | JSONB     | Custom metadata for filtering
```

**Indexes:**
- `(state, scheduled_at)` - Primary query for task pickup
- `(locked_until)` - Dead lock detection
- `(priority)` - Sort order
- `(name)` - Filter by function

## Interface

### Core Functions

```python
# Initialize
tasklib.init(config: Config) -> None

# Register
@tasklib.task
@tasklib.task(max_retries=5, timeout_seconds=30)

# Submit
task_id = await tasklib.submit_task(
    func,
    delay_seconds=0,
    max_retries=None,
    timeout_seconds=None,
    priority=0,
    tags=None,
    **kwargs
) -> UUID

# Monitor
task = tasklib.get_task(task_id: UUID) -> Optional[Task]
tasks = tasklib.list_tasks(state=None, name=None, limit=100) -> list[Task]
registered = tasklib.get_registered_tasks() -> dict[str, tuple]

# Worker
worker = TaskWorker(config, concurrency=1, poll_interval_seconds=1.0)
await worker.run() -> None
```

### Task States

```
pending  - Waiting to execute or retry
running  - Currently executing
completed - Finished successfully
failed   - Gave up after max_retries
```

### Configuration

```python
Config(
    database_url: str,                       # Required: PostgreSQL URL
    max_retries: int = 3,                    # Default max attempts
    base_retry_delay_seconds: float = 5.0,   # First retry delay
    retry_backoff_multiplier: float = 2.0,   # Exponential factor
    lock_timeout_seconds: int = 600,         # Worker lock duration
    default_task_timeout_seconds: Optional[int] = None,  # Execution timeout
    worker_id: Optional[str] = None,         # Worker identity (auto-generated)
)
```

## Behavior

### Task Submission

1. Validate arguments against function signature (Pydantic)
2. Insert row into `tasks` table
3. Set state = "pending"
4. Calculate scheduled_at = now + delay_seconds
5. Return task UUID

### Task Pickup (Worker)

1. Query: `SELECT * FROM tasks WHERE state IN ('pending', 'failed') AND scheduled_at <= NOW() AND (locked_until IS NULL OR locked_until < NOW()) ORDER BY priority DESC, created_at ASC LIMIT 1 FOR UPDATE`
2. If found:
   - Set state = "running"
   - Set worker_id = my_id
   - Set locked_until = now + lock_timeout
   - Commit (atomic)
3. If not found: sleep and retry

### Task Execution

1. Load registered function by name
2. Execute with timeout: `asyncio.wait_for(func(**kwargs), timeout)`
3. On success:
   - Set state = "completed"
   - Set result = {"value": return_value}
   - Set completed_at = now
   - Clear locked_until, worker_id
4. On failure:
   - If retry_count < max_retries:
     - Set state = "failed"
     - Set retry_count += 1
     - Set next_retry_at = now + backoff_delay
     - Clear locked_until, worker_id
     - Task will be picked up again when next_retry_at <= now
   - Else:
     - Set state = "failed" (permanent)
     - Set completed_at = now
     - Clear locked_until, worker_id

### Dead Worker Recovery

1. Worker dies (network partition, crash, etc.)
2. Worker's lock on task expires: locked_until < now()
3. Next polling worker sees stale lock
4. Acquires lock, restarts task from scratch
5. (No "in-flight" data lost, task re-executes from beginning)

## Thread Safety & Concurrency

### Worker Concurrency

```
# 4 concurrent tasks per worker
worker = TaskWorker(config, concurrency=4)

# Each task runs in thread pool (asyncio.to_thread)
# No shared Python objects, no GIL contention
```

### Multi-Worker

```
# Worker A polls, locks task T1
SELECT ... FOR UPDATE -> task T1 locked

# Worker B polls, can't lock T1
SELECT ... FOR UPDATE -> skips T1, gets task T2

# No race conditions: PostgreSQL row-level locking
```

### No Polling Storms

- Each worker sleeps poll_interval_seconds between queries
- With 100 workers: ~100 queries/sec (tunable)
- Add caching or longer intervals if needed

## Failure Modes

### Worker Dies
- **Detection:** Lock timeout (default 10 min)
- **Recovery:** Automatic, task re-executes

### Database Unavailable
- **Worker behavior:** Retry connection on next poll
- **Impact:** Tasks don't execute until DB is back
- **Safety:** No in-memory queue = no data loss

### Corrupted Task Data
- **Handling:** Log error, mark task as failed, continue
- **Reason:** Prevent infinite loops on bad tasks

### Task Timeout
- **Handling:** `asyncio.TimeoutError` caught, triggers retry logic
- **Behavior:** Same as any other exception

### Network Partition
- **Worker side:** Can't reach DB, sleeps and retries
- **Task side:** Left in "running" state until lock timeout
- **Recovery:** Auto-unlock and re-execute after timeout

## Performance

### Submission
- ~1000s tasks/sec (PostgreSQL dependent)
- Single INSERT per task
- Latency: ~5-10ms

### Pickup
- ~100 queries/sec (100 workers at 1 Hz poll)
- Indexed queries: O(n) with index, typically <1ms
- SELECT FOR UPDATE: Atomic, avoids races

### Execution
- Depends on task function
- Timeout enforcement: via asyncio.wait_for
- Concurrent execution: thread pool up to OS limit

### Tuning Knobs

| Parameter | Effect | Default | Tune For |
|-----------|--------|---------|----------|
| concurrency | Tasks/worker | 1 | Parallelism |
| poll_interval_seconds | Query frequency | 1.0 | Latency vs load |
| lock_timeout_seconds | Worker timeout | 600 | Failover speed |
| base_retry_delay_seconds | First retry | 5.0 | Retry aggressiveness |
| retry_backoff_multiplier | Backoff curve | 2.0 | Exponential vs linear |

## Limits

### Tested At
- 100K tasks in queue
- 10 concurrent workers
- ~1000 tasks/min throughput

### Not Tested At
- 10M+ tasks (would need archival/cleanup policy)
- 1000+ concurrent workers (SELECT FOR UPDATE contention)
- < 100ms task execution (polling overhead dominates)

### Recommendations

- **Task volume:** Design for < 1M tasks in DB (add cleanup policy)
- **Workers:** 1-100 per database
- **Task duration:** > 1s (polling adds ~100ms overhead)
- **Database:** PostgreSQL 12+ (tested with 14+)

## Security

### v1 Assumptions
- Private PostgreSQL instance
- Trusted workers (same network/VPC)
- Tasks are trusted code (functions are locally registered)

### Risks (v1)

- Arguments in plain JSON (expose in logs)
- No encryption (add if handling PII)
- No task ownership (all workers can execute all tasks)
- No rate limiting (DOS possible)

### Future

- Argument encryption
- Task ownership & permissions
- Rate limiting & circuit breakers
- Audit logging

## Deployment

### Local Development
```bash
# PostgreSQL running locally
python examples/simple.py  # Submit tasks
python examples/worker.py  # Run worker
```

### Production

```python
# application.py
tasklib.init(Config(
    database_url=os.getenv("DATABASE_URL"),
    max_retries=3,
))

@tasklib.task
def send_email(to: str):
    pass

# worker.py
worker = TaskWorker(
    config,
    concurrency=4,
    poll_interval_seconds=1.0,
)
await worker.run()

# kubernetes/worker-deployment.yaml
replicas: 3  # 3 workers * 4 concurrency = 12 parallel tasks
```

---

**Version:** 1.0.0
**Status:** Stable (v1)
