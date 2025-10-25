# Task Submission

Learn how to submit tasks to the queue.

See the [full guide](../../FINAL_SUMMARY.md) for detailed examples.

## Basic Submission

```python
import asyncio
from tasklib import submit_task

@task
def my_task(param: str) -> str:
    return f"done: {param}"

async def main():
    task_id = await submit_task(my_task, param="hello")
    print(f"Task queued: {task_id}")

asyncio.run(main())
```

## With Options

```python
task_id = await submit_task(
    my_task,
    delay_seconds=60,      # Run in 1 hour
    priority=10,           # High priority
    tags={"batch": "daily"},
)
```

See [Task Definition](task-definition.md) for all options.
