# TaskLib

**Simple, durable task queue for PostgreSQL.** Built with SQLModel, Pydantic, and PostgreSQL. Inspired by Celery but drastically simpler.

> **Goal:** 80% of Celery's use cases with 10% of the complexity.

## Features

 **Sync tasks only** (v1) - Execute synchronous functions reliably
 **Delayed execution** - Schedule tasks to run later
 **Exponential backoff retries** - Automatic retry with configurable backoff
 **Multi-worker support** - PostgreSQL-level locking for distributed workers
 **Strict locking** - Dead worker detection via lock timeout
 **Configurable timeout** - Per-task execution timeout
 **Pydantic validation** - Type-safe task arguments
 **Indefinite result storage** - Store task results for debugging/inspection
 **Single table design** - Everything in one PostgreSQL table, ultra-simple

## Installation

```bash
uv add tasklib
```

Or clone and install from source:

```bash
git clone https://github.com/username/tasklib
cd tasklib
uv sync
```

## Quick Start

### 1. Initialize TaskLib

```python
import tasklib

config = tasklib.Config(
    database_url="postgresql://user:password@localhost/mydb",
    max_retries=3,
    base_retry_delay_seconds=5.0,
    lock_timeout_seconds=600,  # 10 minutes
)

tasklib.init(config)
```

### 2. Define Tasks

```python
@tasklib.task
def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email. Must be a sync function."""
    # Your email logic here
    print(f"Sending email to {to}: {subject}")
    return True

@tasklib.task(max_retries=5, timeout_seconds=30)
def process_image(image_path: str) -> str:
    """Process an image with custom retry/timeout."""
    # Your image processing logic
    return f"processed_{image_path}"
```

### 3. Submit Tasks

```python
# Immediate execution
task_id = await tasklib.submit_task(send_email, to="user@example.com", subject="Hello")

# Delayed execution (in 60 seconds)
task_id = await tasklib.submit_task(
    send_email,
    delay_seconds=60,
    to="user@example.com",
    subject="Scheduled email"
)

# With custom priority and metadata
task_id = await tasklib.submit_task(
    process_image,
    image_path="/tmp/photo.jpg",
    priority=10,  # Higher priority
    tags={"batch": "daily-processing"}  # For filtering
)
```

### 4. Run Workers

```python
import asyncio
from tasklib import TaskWorker, Config

async def main():
    config = Config(database_url="postgresql://...")
    worker = TaskWorker(config, concurrency=4)
    await worker.run()  # Blocks until shutdown (Ctrl+C)

if __name__ == "__main__":
    asyncio.run(main())
```

### 5. Monitor Tasks

```python
# Get specific task
task = tasklib.get_task(task_id)
print(f"State: {task.state}")  # pending, running, completed, failed
print(f"Result: {task.result}")
print(f"Error: {task.error}")

# List tasks
pending_tasks = tasklib.list_tasks(state="pending")
failed_tasks = tasklib.list_tasks(state="failed", name="send_email")

# Get all registered tasks
tasks_dict = tasklib.get_registered_tasks()
```

## Architecture

### Database Schema

Everything lives in a single `tasks` table:

```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    name VARCHAR NOT NULL,           -- Task function name
    args JSONB,                      -- Positional arguments
    kwargs JSONB,                    -- Keyword arguments
    state VARCHAR NOT NULL,          -- pending, running, completed, failed
    result JSONB,                    -- Task result (for completed tasks)
    error TEXT,                      -- Error traceback (for failed tasks)
    retry_count INT,                 -- Current attempt number
    max_retries INT,                 -- Max attempts allowed
    scheduled_at TIMESTAMP,          -- When to execute
    started_at TIMESTAMP,            -- When execution started
    completed_at TIMESTAMP,          -- When execution finished
    created_at TIMESTAMP,            -- When submitted
    next_retry_at TIMESTAMP,         -- When to retry (if failed)
    worker_id VARCHAR,               -- Lock holder (worker UUID)
    locked_until TIMESTAMP,          -- When lock expires (dead worker detection)
    timeout_seconds INT,             -- Max execution time
    priority INT,                    -- Higher = process first
    tags JSONB                       -- Custom metadata
);
```

### Task Lifecycle

```
pending � running � completed
           �
         failed � (retry) � pending � running � ...
           �
        (max retries exceeded)
         FINAL_FAILED
```

### Locking Strategy

- **PostgreSQL SELECT FOR UPDATE**: Workers use `SELECT FOR UPDATE` to atomically claim tasks
- **Lock Timeout**: `locked_until` timestamp tracks when a lock expires
- **Dead Worker Detection**: If `locked_until < now()`, lock is considered stale and task is released
- **Configurable Lock Duration**: Default 10 minutes, configurable per config

### Retry Strategy

Tasks use **exponential backoff**:

```
Attempt 1: Immediate (fail � retry in base_delay)
Attempt 2: base_delay * multiplier^1
Attempt 3: base_delay * multiplier^2
...
```

Default: `base_delay=5s`, `multiplier=2.0`, `max_retries=3`
- Retry 1: after 5 seconds
- Retry 2: after 10 seconds
- Retry 3: after 20 seconds
- If all fail: marked as `failed` permanently

## Configuration

```python
config = tasklib.Config(
    # Required
    database_url: str,

    # Optional (with defaults)
    max_retries: int = 3,
    base_retry_delay_seconds: float = 5.0,
    retry_backoff_multiplier: float = 2.0,
    lock_timeout_seconds: int = 600,
    default_task_timeout_seconds: Optional[int] = None,  # No timeout by default
    worker_id: Optional[str] = None,  # Auto-generated if not set
)
```

## API Reference

### Task Decorator

```python
@tasklib.task
def my_task(**kwargs): pass

@tasklib.task(max_retries=5, timeout_seconds=30)
def my_task_custom(**kwargs): pass
```

Parameters:
- `max_retries` (int, optional): Override default max retries
- `timeout_seconds` (int, optional): Max execution time in seconds

### submit_task()

```python
task_id = await tasklib.submit_task(
    func: Callable,
    *,
    delay_seconds: int = 0,
    max_retries: Optional[int] = None,
    timeout_seconds: Optional[int] = None,
    priority: int = 0,
    tags: Optional[dict] = None,
    **kwargs
) -> UUID
```

### Monitoring

```python
task = tasklib.get_task(task_id: UUID) -> Optional[Task]
tasks = tasklib.list_tasks(
    state: Optional[str] = None,
    name: Optional[str] = None,
    limit: int = 100
) -> list[Task]
```

### Worker

```python
worker = tasklib.TaskWorker(
    config: Config,
    concurrency: int = 1,
    poll_interval_seconds: float = 1.0
)
await worker.run()  # Blocks until shutdown
await worker.shutdown()  # Graceful shutdown
```

## Examples

See `examples/` directory for complete examples:

- `simple.py` - Basic task submission and worker
- `with_monitoring.py` - Monitoring and debugging tasks

## Design Decisions

### Why Single Table?

Ultra-simplicity. Everything about a task is in one row. No joins needed. Easy to understand, debug, and reason about.

### Why Sync Functions Only?

For v1, we optimize for the common case: simple I/O-bound work (network requests, DB calls, file I/O). Async tasks can be added in v2 if needed.

### Why PostgreSQL SELECT FOR UPDATE?

It's battle-tested, atomic, and avoids race conditions. No distributed consensus needed.

### Why No Celery Features?

Celery has 15 years of complexity. TaskLib focuses on the 80/20: delayed execution, retries, multi-worker support. Everything else is a future enhancement.

## Performance Considerations

- **Task polling**: Default 1 second interval. Adjust `poll_interval_seconds` based on your load
- **Concurrency**: Start with `concurrency=4` per worker, tune based on workload
- **Lock timeout**: Default 10 minutes. Increase if tasks take longer, decrease for faster failover
- **Database indexes**: Table is indexed on: `state`, `scheduled_at`, `locked_until`, `priority`, `name`

## Roadmap (Future)

- [ ] Async task support
- [ ] Cron-like recurring tasks
- [ ] Task chaining/dependencies
- [ ] Admin UI for monitoring
- [ ] Dead letter queue for unhandled errors
- [ ] Task result pagination
- [ ] Prometheus metrics
- [ ] Multi-database support (MySQL, etc.)

## Development

### Setup

```bash
# Install with dev dependencies
uv sync --extra dev

# Start PostgreSQL (required for integration tests)
docker-compose up -d
```

### Testing

```bash
# Run all tests (unit + integration)
make test

# Run only unit tests (no DB required)
make test-unit

# Run only integration tests
make test-integration

# Run pytest directly
uv run pytest tests/ -v
uv run pytest tests/test_integration.py::TestTaskSubmissionAndExecution -v  # Specific test
```

### Code Quality

```bash
# Format code
make format

# Lint
make lint

# Run all checks (lint + tests)
make check
```

### Stopping PostgreSQL

```bash
docker-compose down
```

See [TESTING.md](TESTING.md) for detailed testing documentation.

## License

MIT

## Contributing

Contributions welcome! Please:

1. Fork the repo
2. Create a feature branch
3. Add tests for new functionality
4. Ensure tests pass
5. Submit PR

## Contact

Questions? Open an issue or discussion on GitHub.

---

Built with d by @username
