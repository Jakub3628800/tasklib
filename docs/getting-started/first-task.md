# Your First Task

Let's create and run your first TaskLib task in just 5 minutes.

## 1. Define a Task

Create a file `tasks.py`:

```python
import tasklib

@tasklib.task
def send_email(to: str, subject: str, body: str = "Hello") -> bool:
    """Send an email"""
    print(f"Sending email to {to}")
    print(f"Subject: {subject}")
    print(f"Body: {body}")
    return True
```

## 2. Submit a Task

Create a file `submit_tasks.py`:

```python
import asyncio
import tasklib
from tasks import send_email

async def main():
    # Initialize tasklib
    config = tasklib.Config(
        database_url="postgresql://tasklib:tasklib_pass@localhost:5432/tasklib"
    )
    await tasklib.init(config)

    # Submit a task
    task_id = await tasklib.submit_task(
        send_email,
        to="user@example.com",
        subject="Welcome"
    )

    print(f"Task submitted: {task_id}")

    # Check task status
    task = await tasklib.get_task(task_id)
    print(f"Task status: {task.state}")

asyncio.run(main())
```

## 3. Run a Worker

Create a file `worker.py`:

```python
import asyncio
import tasklib
from tasks import send_email

async def main():
    config = tasklib.Config(
        database_url="postgresql://tasklib:tasklib_pass@localhost:5432/tasklib"
    )
    await tasklib.init(config)

    worker = tasklib.TaskWorker(config, worker_id="worker-1")
    await worker.run()

asyncio.run(main())
```

## 4. Run Everything

In separate terminals:

```bash
# Terminal 1: Start PostgreSQL
docker-compose up

# Terminal 2: Run the worker
python worker.py

# Terminal 3: Submit tasks
python submit_tasks.py
```

Watch the task execute in the worker terminal!

## What Just Happened?

1. **Defined a task** with the `@tasklib.task` decorator
2. **Submitted it** with `submit_task()` which stored it in PostgreSQL
3. **Worker polled** the database, found the task, and executed it
4. **Result was stored** in the database with state = "completed"

## Next Steps

- [Task Definition Guide](../guides/task-definition.md) - Learn more about defining tasks
- [Task Submission Guide](../guides/task-submission.md) - Advanced submission options
- [Worker Guide](../guides/workers.md) - Running multiple workers
- [Error Handling](../guides/error-handling.md) - Handling failures and retries
