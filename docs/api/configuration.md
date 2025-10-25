# Configuration

TaskLib configuration via the `Config` class.

## Config Class

```python
from tasklib import Config

config = Config(
    database_url="postgresql://user:password@localhost/dbname",
    max_retries=3,
    base_retry_delay_seconds=5.0,
    retry_backoff_multiplier=2.0,
    lock_timeout_seconds=600,
    default_task_timeout_seconds=None,
    worker_id=None,
)

tasklib.init(config)
```

## Parameters

### Required

**`database_url`** (str)
- PostgreSQL connection URL
- Format: `postgresql://[user[:password]@][netloc][:port][/dbname][?param=value...]`
- Example: `postgresql://tasklib:pass@localhost:5432/tasklib`

### Optional (with defaults)

**`max_retries`** (int, default: 3)
- Default max retries for tasks
- Can be overridden per task
- If task fails, retried up to `max_retries` times

**`base_retry_delay_seconds`** (float, default: 5.0)
- Base delay for exponential backoff
- First retry waits this many seconds
- Used in formula: `delay = base * (multiplier ^ attempt)`

**`retry_backoff_multiplier`** (float, default: 2.0)
- Exponential backoff multiplier
- Each retry delay = previous * multiplier
- Default: 5s → 10s → 20s → 40s → ...

**`lock_timeout_seconds`** (int, default: 600)
- How long a worker can lock a task
- If worker dies, lock expires and task is freed
- Typical: 600 (10 minutes)
- Adjust based on longest expected task duration

**`default_task_timeout_seconds`** (int, default: None)
- Default timeout for task execution
- Task aborted if exceeds this time
- Can be overridden per task
- None = no timeout

**`worker_id`** (str, default: None)
- Worker identifier for locking
- Auto-generated if not set (UUID)
- Use for debugging: `worker_id="worker-prod-01"`

## Environment Variables

Instead of hardcoding, use environment variables:

```python
import os
from tasklib import Config

config = Config(
    database_url=os.getenv("DATABASE_URL"),
    max_retries=int(os.getenv("MAX_RETRIES", "3")),
    lock_timeout_seconds=int(os.getenv("LOCK_TIMEOUT", "600")),
)
```

## Environment Setup

```bash
# .env file (or shell export)
DATABASE_URL=postgresql://user:pass@localhost/tasklib
MAX_RETRIES=5
LOCK_TIMEOUT=1200  # 20 minutes
WORKER_ID=worker-prod-01
```

## Production Settings

```python
config = Config(
    database_url=os.getenv("DATABASE_URL"),
    max_retries=5,                    # More retries for reliability
    base_retry_delay_seconds=10.0,    # Longer delays
    retry_backoff_multiplier=2.0,
    lock_timeout_seconds=900,        # 15 minutes
    default_task_timeout_seconds=120, # 2 minute default
    worker_id=os.getenv("HOSTNAME"),  # Use hostname
)
```

## Development Settings

```python
config = Config(
    database_url="postgresql://localhost/tasklib_dev",
    max_retries=3,
    base_retry_delay_seconds=1.0,    # Fast retries
    lock_timeout_seconds=60,          # 1 minute
    default_task_timeout_seconds=None, # No timeout
)
```

## Per-Task Overrides

Task-level settings override config:

```python
@tasklib.task(max_retries=10, timeout_seconds=60)
def important_task() -> bool:
    # Uses max_retries=10 (not config default)
    # Uses timeout_seconds=60 (not config default)
    pass

# Still respects config for defaults
@tasklib.task
def normal_task() -> bool:
    # Uses config max_retries
    # Uses config default_task_timeout_seconds
    pass
```

## Example: Full Setup

```python
# settings.py
import os
from tasklib import Config

config = Config(
    database_url=os.getenv(
        "DATABASE_URL",
        "postgresql://localhost/tasklib"
    ),
    max_retries=int(os.getenv("TASKLIB_MAX_RETRIES", "3")),
    base_retry_delay_seconds=float(os.getenv("TASKLIB_RETRY_DELAY", "5")),
    retry_backoff_multiplier=2.0,
    lock_timeout_seconds=int(os.getenv("TASKLIB_LOCK_TIMEOUT", "600")),
    default_task_timeout_seconds=int(os.getenv("TASKLIB_TIMEOUT", "300")),
    worker_id=os.getenv("TASKLIB_WORKER_ID"),
)

# app.py
from settings import config
import tasklib

tasklib.init(config)

# worker.py
from settings import config
from tasklib import TaskWorker

async def main():
    worker = TaskWorker(config, concurrency=4)
    await worker.run()
```
