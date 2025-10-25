# TaskLib

Simple, durable task queue for PostgreSQL.

Built with SQLModel, Pydantic, and PostgreSQL. Inspired by Celery but drastically simpler.

## Quick Start

```python
from tasklib import task, submit_task, Config, TaskWorker
import asyncio

config = Config(database_url="postgresql://...")
tasklib.init(config)

@task
def send_email(to: str, subject: str) -> bool:
    # Your code here
    return True

# Submit task
async def submit():
    task_id = await submit_task(send_email, to="user@example.com", subject="Hello")
    print(f"Queued: {task_id}")

# Run worker
async def work():
    worker = TaskWorker(config, concurrency=4)
    await worker.run()
```

## Why TaskLib?

| vs. | TaskLib | Alternative |
|-----|---------|-------------|
| **Celery** | PostgreSQL only, ~500 LOC | Redis/RabbitMQ, ~50k LOC |
| **APScheduler** | Multi-worker, distributed | Single machine |
| **SQS/Cloud Tasks** | Self-hosted, no vendor lock-in | Vendor lock-in, per-message costs |

## Features

- ✅ PostgreSQL-backed (single table, no Redis/RabbitMQ)
- ✅ Pydantic validation at submit time
- ✅ Exponential backoff retries
- ✅ Multi-worker support with strict locking
- ✅ Scheduled & delayed execution
- ✅ Per-task timeout & max retries
- ✅ Result storage for debugging

## Next Steps

- [**Installation**](getting-started/installation.md) — Get started
- [**Quick Start**](getting-started/quick-start.md) — First task in 5 minutes
- [**API Reference**](api/core.md) — Complete API
- [**Contributing**](contributing.md) — Help improve TaskLib
