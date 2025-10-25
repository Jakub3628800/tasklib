# Quick Start

Get TaskLib running in 5 minutes.

## 1. Initialize

```python
import tasklib

config = tasklib.Config(
    database_url="postgresql://user:password@localhost/mydb",
    max_retries=3,
    base_retry_delay_seconds=5.0,
    lock_timeout_seconds=600,
)

tasklib.init(config)
```

## 2. Define Task

```python
@tasklib.task
def send_email(to: str, subject: str) -> bool:
    """Send an email."""
    # Your code here
    print(f"Sending email to {to}: {subject}")
    return True
```

## 3. Submit Task

```python
import asyncio

async def submit():
    task_id = await tasklib.submit_task(
        send_email,
        to="user@example.com",
        subject="Hello!"
    )
    print(f"Task queued: {task_id}")

asyncio.run(submit())
```

## 4. Run Worker (Pick One)

### Option A: Using CLI (Recommended)

```bash
export DATABASE_URL=postgresql://user:password@localhost/mydb
tasklib-worker --task-module myapp.tasks
```

Output:
```
2024-10-25 10:30:45 - tasklib - INFO - Starting TaskLib worker...
2024-10-25 10:30:45 - tasklib - INFO -   Worker ID: abc-123-uuid
2024-10-25 10:30:45 - tasklib - INFO -   Concurrency: 4
2024-10-25 10:30:45 - tasklib - INFO - Importing task modules: myapp.tasks
```

### Option B: Using Python Script

Create `worker.py`:

```python
import asyncio
from tasklib import TaskWorker, Config

async def main():
    config = Config(database_url="postgresql://...")
    worker = TaskWorker(config, concurrency=4)
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
```

Run:
```bash
python worker.py
```

## 5. Monitor

```python
from tasklib import get_task, is_completed

task = get_task(task_id)
print(f"State: {task.state}")          # pending, running, completed, failed
print(f"Is done: {is_completed(task)}")
print(f"Result: {task.result}")         # {"value": true}
```

## Next Steps

- **[Your First Task](first-task.md)** - Detailed walkthrough
- **[Task Definition](../guides/task-definition.md)** - How to define tasks
- **[Running Workers](../guides/workers.md)** - Worker configuration
- **[Examples](../examples/simple.md)** - Real-world code
