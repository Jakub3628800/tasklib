# Quick Start

Get TaskLib running in 5 minutes.

## 1. Initialize

```python
import tasklib

config = tasklib.Config(database_url="postgresql://tasklib:tasklib_pass@localhost/tasklib")
tasklib.init(config)
```

## 2. Define a Task

```python
@tasklib.task
def send_email(to: str, subject: str) -> bool:
    print(f"Sending email to {to}: {subject}")
    return True
```

## 3. Submit Task

```python
import asyncio

async def main():
    task_id = await tasklib.submit_task(send_email, to="user@example.com", subject="Hello!")
    print(f"Queued: {task_id}")

asyncio.run(main())
```

## 4. Run Worker

```bash
export DATABASE_URL=postgresql://tasklib:tasklib_pass@localhost/tasklib
tasklib-worker --task-module myapp.tasks
```

That's it! Your task will be executed by the worker.

## Next Steps

- [**Your First Task**](first-task.md) — Detailed walkthrough
- [**Task Definition**](../guides/task-definition.md) — Learn more about tasks
- [**Running Workers**](../guides/workers.md) — Worker configuration
