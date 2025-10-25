# Simple Example

A complete working example demonstrating TaskLib features.

## Task Definitions

```python
import tasklib

@tasklib.task
def add(a: int, b: int) -> int:
    """Add two numbers."""
    print(f"Adding {a} + {b}")
    return a + b

@tasklib.task(timeout_seconds=5)
def slow_task(seconds: int) -> str:
    """Sleep for N seconds."""
    import time
    print(f"Sleeping for {seconds} seconds...")
    time.sleep(seconds)
    return f"Slept for {seconds}s"

@tasklib.task(max_retries=2)
def unreliable_task() -> str:
    """Task that might fail."""
    import random
    if random.random() < 0.5:
        raise RuntimeError("Random failure!")
    return "Success!"
```

## Submitting Tasks

```python
async def submit_examples():
    """Submit some example tasks."""

    # Immediate task
    task1 = await tasklib.submit_task(add, a=5, b=3)
    print(f"Task 1: {task1}")

    # Delayed task (2 seconds)
    task2 = await tasklib.submit_task(
        slow_task,
        delay_seconds=2,
        seconds=2
    )
    print(f"Task 2: {task2}")

    # High-priority task with tags
    task3 = await tasklib.submit_task(
        add,
        a=100,
        b=200,
        priority=10,
        tags={"type": "important"}
    )
    print(f"Task 3: {task3}")

    # Task with timeout
    task4 = await tasklib.submit_task(slow_task, seconds=10)

    # Unreliable task (will retry on failure)
    task5 = await tasklib.submit_task(unreliable_task)

    return [task1, task2, task3, task4, task5]
```

## Checking Task Status

```python
async def check_status(task_ids: list):
    """Check status of tasks."""
    import asyncio
    await asyncio.sleep(10)

    for task_id in task_ids:
        task = tasklib.get_task(task_id)
        if task:
            print(f"Task {task_id}:")
            print(f"  State: {task.state}")
            print(f"  Result: {task.result}")
            print(f"  Error: {task.error}")
            print(f"  Retries: {task.retry_count}/{task.max_retries}")
```

## Running the Example

### 1. Start PostgreSQL

```bash
docker-compose up
```

### 2. Initialize the Database

```bash
# In your project
alembic upgrade head
```

### 3. Run the Example

```bash
python -m examples.simple
```

### 4. Run the Worker

In another terminal:

```bash
python -m examples.worker
```

## Example Output

```
Submitting tasks...
Task 1 (immediate): uuid-1
Task 2 (delayed 2s): uuid-2
Task 3 (high priority): uuid-3
Task 4 (will timeout): uuid-4
Task 5 (unreliable): uuid-5

Checking task status (sleeping 10s)...
Task uuid-1:
  State: completed
  Result: 8
  Error: None
  Retries: 0/3

Task uuid-2:
  State: pending
  Result: None
  Error: None
  Retries: 0/3
```

## What This Example Shows

- ✅ Basic task definition with `@tasklib.task`
- ✅ Task submission with different options
- ✅ Delayed task execution with `delay_seconds`
- ✅ Task priorities
- ✅ Task tags for metadata
- ✅ Timeout enforcement
- ✅ Automatic retries on failure
- ✅ Status checking and task monitoring

## Next Steps

- Run the worker in a separate process
- Submit more tasks
- Observe retry behavior when unreliable_task fails
- Check database directly for task details
- See [Worker Guide](../guides/workers.md) for multi-worker setup
