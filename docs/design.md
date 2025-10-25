# TaskLib Design Document

## Overview

TaskLib is a minimal, PostgreSQL-backed task queue library designed for simplicity and durability. It's inspired by Celery but removes the complexity, focusing on the 80/20 use cases: delayed execution, retries, and multi-worker support.

**Philosophy:** Single table, simple interface, PostgreSQL as the source of truth.

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Code                          │
│  @task decorator │ submit_task() │ monitoring API            │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    TaskLib Core (core.py)                    │
│  Task registration │ Submission logic │ Argument validation   │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              SQLModel + PostgreSQL (models.py)               │
│  Task table │ State management │ Locking & retries          │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              Task Workers (worker.py)                        │
│  Poll & lock │ Execute │ Handle failures & retries          │
└─────────────────────────────────────────────────────────────┘
```

### The Single Table: `tasks`

All task state lives in one PostgreSQL table:

```python
class Task(SQLModel, table=True):
    # Identification
    id: UUID                    # Primary key
    name: str                   # Function name

    # Payload
    args: dict                  # Positional args (reserved for future)
    kwargs: dict                # Keyword args

    # Execution state
    state: str                  # pending|running|completed|failed
    result: Optional[dict]      # Return value
    error: Optional[str]        # Traceback

    # Retry logic
    retry_count: int            # Current attempt
    max_retries: int            # Max attempts
    next_retry_at: Optional[dt] # When to retry

    # Timing
    scheduled_at: datetime      # When to execute
    started_at: Optional[dt]    # Execution start
    completed_at: Optional[dt]  # Execution end
    created_at: datetime        # When submitted

    # Worker locking
    worker_id: Optional[str]    # Lock holder
    locked_until: Optional[dt]  # Lock expiry (dead worker detection)

    # Configuration
    timeout_seconds: Optional[int]  # Max execution time
    priority: int                   # Higher = process first
    tags: dict                      # Metadata
```

**Why single table?**
- Ultra-simplicity: Everything about a task in one row
- No joins needed
- Easy to inspect in `psql`
- Easy to reason about state transitions
- Perfect for small-to-medium workloads

## Task Lifecycle

```
┌─────────┐
│ PENDING │  <- Task submitted, waiting for scheduled_at
└────┬────┘
     │ scheduled_at <= now AND (not locked OR locked_until < now)
     │
     ↓
┌─────────────────────────────────────────────────────────┐
│ Worker tries to lock task with SELECT FOR UPDATE        │
│ - Fails: task already locked by another worker          │
│ - Success: acquire lock, set state=running              │
└──────────────┬──────────────────────────────────────────┘
               │
               ↓
        ┌────────────┐
        │  RUNNING   │  <- Actively executing
        └────┬───────┘
             │
        ┌────┴────────────────────────┐
        │                             │
    SUCCESS                        FAILURE
        │                             │
        ↓                             ↓
   ┌──────────┐           ┌────────────────────┐
   │COMPLETED │           │ Can retry?         │
   └──────────┘           │ (retry_count < max)│
        │                 └────────┬───────────┘
        │                          │
        │                    ┌─────┴──────────────┐
        │                    │                    │
        │                YES │                 NO │
        │                    ↓                    ↓
        │            ┌──────────────────┐  ┌──────────┐
        │            │ state = failed    │  │ FAILED   │
        │            │ next_retry_at =   │  │ (final)  │
        │            │   backoff delay   │  └──────────┘
        │            │ retry_count += 1  │
        │            │ reset lock        │
        │            └──────────────────┘
        │                    │
        │                    │ (next poll cycle)
        │                    ↓
        │               (back to PENDING)
        │
        └──────────────┬─────────────────────────────────┐
                       │ Both paths mark locked_until=NULL
                       │ and worker_id=NULL (release lock)
                       ↓
                   [END]
```

## Locking Strategy

### Problem
With multiple workers, we need to ensure:
1. Each task is executed exactly once per retry
2. Dead workers don't block tasks forever
3. No distributed consensus required

### Solution: PostgreSQL SELECT FOR UPDATE + Timestamp

```python
# Atomic acquisition
statement = (
    select(Task)
    .where(Task.state.in_(["pending", "failed"]))
    .where(Task.scheduled_at <= now)
    .where(
        (Task.locked_until.is_(None))
        | (Task.locked_until < now)  # Stale lock detection
    )
    .with_for_update()  # PostgreSQL SELECT FOR UPDATE
)
task = session.exec(statement).first()

if task:
    task.state = "running"
    task.locked_until = now + timedelta(seconds=lock_timeout)
    session.commit()  # Atomic: lock acquired
```

### How it works

1. **SELECT FOR UPDATE**: PostgreSQL row-level lock - atomically selects task and locks it
2. **locked_until timestamp**: Tracks when lock expires
3. **Stale lock detection**: If `locked_until < now()`, the lock is considered stale (worker died)
4. **Lock timeout**: Default 10 minutes - adjust based on longest expected task

### Properties

- ✅ Atomic: Either worker gets lock or doesn't (no race conditions)
- ✅ Simple: No distributed consensus, no Redis, no Zookeeper
- ✅ Dead worker recovery: Automatic via timeout
- ✅ Works across many workers on different machines

## Retry Strategy

### Exponential Backoff with Jitter (Optional)

When a task fails and `retry_count < max_retries`:

```python
delay = base_retry_delay * (backoff_multiplier ^ retry_count)
next_retry_at = now + timedelta(seconds=delay)
```

**Default settings:**
- `base_retry_delay_seconds = 5`
- `retry_backoff_multiplier = 2.0`
- `max_retries = 3`

**Retry schedule:**
- Attempt 1: Immediate (fail)
- Wait: 5 seconds
- Attempt 2: +10 seconds (fail)
- Wait: 10 seconds
- Attempt 3: +20 seconds (fail)
- Wait: 20 seconds
- Attempt 4: +40 seconds (fail)
- **Result:** Task marked as FAILED (permanent)

**Why exponential backoff?**
- Avoids hammering the system if there's a widespread outage
- Gives time for temporary issues to resolve
- Configurable per task or globally

## Task Execution

### Worker Flow

```python
while not shutdown:
    # Poll for available tasks (concurrency slots)
    for _ in range(concurrency - len(running_tasks)):
        task = try_acquire_task()
        if task:
            asyncio.create_task(execute_task(task))

    await asyncio.sleep(poll_interval)
```

### Execution (Sync Functions)

```python
async def execute_task(task):
    try:
        # Get registered function
        func, _ = task_registry[task.name]

        # Execute with timeout
        result = await asyncio.wait_for(
            run_sync_in_executor(func, **task.kwargs),
            timeout=task.timeout_seconds
        )

        # Mark completed
        task.state = "completed"
        task.result = {"value": result}
        task.completed_at = now

    except asyncio.TimeoutError:
        # Trigger retry logic
        handle_failure(task, TaskTimeoutError(...))
    except Exception as e:
        # Trigger retry logic
        handle_failure(task, e)
```

**Note:** v1 uses sync functions executed in a thread pool. Async support is a future enhancement.

## Configuration

```python
@dataclass
class Config:
    # Required
    database_url: str

    # Retry strategy
    max_retries: int = 3
    base_retry_delay_seconds: float = 5.0
    retry_backoff_multiplier: float = 2.0

    # Locking
    lock_timeout_seconds: int = 600  # 10 minutes

    # Task execution
    default_task_timeout_seconds: Optional[int] = None

    # Worker identity
    worker_id: Optional[str] = None  # Auto-generated if not set
```

### Tuning

**Increasing load:**
- Increase `concurrency` on workers
- Increase `lock_timeout_seconds` if tasks take longer
- Decrease `poll_interval_seconds` for faster responsiveness (use ~1s)

**Decreasing latency:**
- Decrease `base_retry_delay_seconds` for faster retries
- Decrease `poll_interval_seconds` for faster task pickup

**Dead worker detection:**
- Tune `lock_timeout_seconds`:
  - Too short: False positives, premature lock release
  - Too long: Delayed detection of dead workers
  - Sweet spot: 2-3x longest expected task time

## API Design

### Task Decorator

```python
@task
def my_task(x: int) -> int:
    return x * 2

@task(max_retries=5, timeout_seconds=30)
def slow_task(path: str) -> dict:
    # ...
```

**Design decisions:**
- Simple: `@task` with optional kwargs
- No handler callbacks (keep it simple for v1)
- Type hints used for validation via Pydantic

### Task Submission

```python
task_id = await submit_task(
    my_task,
    delay_seconds=60,
    max_retries=5,
    timeout_seconds=30,
    priority=10,
    tags={"batch": "daily"},
    x=5  # Function arguments
)
```

**Why kwargs only?**
- Simpler: no varargs/args confusion
- Better for serialization to JSON
- Type hints work well with pydantic validation

### Monitoring

```python
task = get_task(task_id)  # Get single task

tasks = list_tasks(
    state="pending",
    name="my_task",
    limit=100
)
```

**Direct DB access:**
```sql
SELECT * FROM tasks WHERE state='pending' ORDER BY priority DESC;
SELECT COUNT(*) FROM tasks WHERE state='failed';
SELECT AVG(completed_at - started_at) FROM tasks WHERE state='completed';
```

## Error Handling

### Task-Level Errors

When task execution fails:

1. Capture full traceback → `task.error`
2. If retries available → schedule retry with backoff
3. If no retries → mark as `failed` (permanent)

### Worker-Level Errors

- Dead worker: Lock expires after `lock_timeout_seconds`
- Database connection lost: Reconnect on next poll cycle
- Corrupted task data: Log error, skip task (prevent infinite loop)

### Application-Level Errors

- Task not registered: Raise `TaskNotFound` at submission time
- Invalid arguments: Raise `TaskExecutionError` at submission time
- DB not initialized: Raise `RuntimeError` with helpful message

## Performance Characteristics

### Task Submission
- **Complexity:** O(1) - single INSERT
- **Latency:** ~5-10ms (network + DB round trip)
- **Throughput:** ~1000s tasks/sec (tuned by DB)

### Task Pickup (per worker)
- **Query complexity:** O(n) worst case, but with indexes
- **Index on:** `state, scheduled_at, locked_until, priority`
- **Latency:** ~5-10ms per poll
- **Result:** ~1-10 ms to acquire + execute simple task

### Task Completion
- **Complexity:** O(1) - single UPDATE
- **Latency:** ~5ms

### Considerations

**Polling overhead:**
- Each worker polls every 1s by default
- With 100 workers: 100 queries/second
- Mitigate with `poll_interval_seconds=5` or longer

**Lock contention:**
- SELECT FOR UPDATE is fast
- Most contention during peak submissions
- PostgreSQL handles well up to 10K+ concurrent workers

**Long-running tasks:**
- Don't block other workers
- Each worker can handle N tasks concurrently
- Increase `concurrency` per worker for more parallelism

## Security Considerations

### v1 (Current)

- **No authentication:** SQLite/PostgreSQL auth required at DB level
- **No encryption:** Arguments stored in plain JSON
- **No audit:** Minimal logging by default

### Future Enhancements

- Argument encryption for sensitive data
- Audit logs for compliance
- Task ownership/permissions

## Testing Strategy

### Unit Tests
- Task decorator registration
- Argument validation
- Configuration defaults
- Task state transitions

### Integration Tests
- Submit → list → retrieve flow
- Retry logic with mock time
- Multiple worker simulation
- Lock acquisition and timeout

### Stress Tests
- 10K+ task submissions
- Multiple workers under load
- Lock contention scenarios
- Network failure simulation

## Comparison to Celery

| Feature | TaskLib | Celery |
|---------|---------|--------|
| Setup complexity | Minimal (just DB) | Complex (broker, backend) |
| Learning curve | Shallow | Steep |
| Flexibility | Limited | Unlimited |
| Multi-worker | ✅ Simple | ✅ Complex |
| Delayed tasks | ✅ Yes | ✅ Yes |
| Retries | ✅ Basic | ✅ Advanced |
| Recurring tasks | ❌ Future | ✅ Yes |
| Task dependencies | ❌ Future | ✅ Yes |
| Admin UI | ❌ Future | ✅ Yes |

**Use TaskLib when:**
- You want simplicity over flexibility
- PostgreSQL is already in your stack
- You don't need complex task orchestration
- Single table operations are acceptable

**Use Celery when:**
- You need advanced task workflows
- You require many broker options
- You need production monitoring UI
- You're willing to manage more components

## Future Enhancements

### v1.1 (Minor)
- Async function support
- Better error context in failures
- Task result pagination

### v2.0 (Major)
- Cron-like recurring tasks
- Task chaining/dependencies
- Distributed tracing
- Admin API + UI
- Dead letter queue
- Prometheus metrics

### Later
- Multi-database support (MySQL, etc.)
- Task result compression
- Custom serializers (Protobuf, etc.)
- Rate limiting
- Circuit breakers

## Code Organization

```
tasklib/
├── src/tasklib/
│   ├── __init__.py        # Public API
│   ├── core.py            # Task decorator, submit_task
│   ├── models.py          # SQLModel Task
│   ├── worker.py          # Worker implementation
│   ├── config.py          # Configuration
│   └── exceptions.py      # Custom exceptions
├── tests/
│   ├── test_core.py       # Core functionality tests
│   └── test_worker.py     # Worker tests (future)
├── examples/
│   ├── simple.py          # Basic example
│   └── worker.py          # Worker example
├── README.md              # User guide
├── DESIGN.md              # This file
└── Makefile               # Development shortcuts
```

## Contributing

When adding features:

1. Keep interface simple (fewer functions, not more)
2. Maintain single-table design where possible
3. Add tests for new functionality
4. Update README with examples
5. Consider PostgreSQL-only features (advisory locks, JSONB, etc.)

---

**Last updated:** 2025-10-25
**Author:** TaskLib Contributors
