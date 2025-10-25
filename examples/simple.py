"""Simple example of tasklib usage."""

import asyncio

import tasklib


# Task definitions
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


async def submit_examples():
    """Submit some example tasks."""
    print("Submitting tasks...")

    # Submit immediate task
    task1 = await tasklib.submit_task(add, a=5, b=3)
    print(f"Task 1 (immediate): {task1}")

    # Submit delayed task
    task2 = await tasklib.submit_task(slow_task, delay_seconds=2, seconds=2)
    print(f"Task 2 (delayed 2s): {task2}")

    # Submit high-priority task
    task3 = await tasklib.submit_task(add, a=100, b=200, priority=10, tags={"type": "important"})
    print(f"Task 3 (high priority): {task3}")

    # Submit task with low timeout (will fail if slow)
    task4 = await tasklib.submit_task(slow_task, seconds=10)
    print(f"Task 4 (will timeout): {task4}")

    # Submit unreliable task
    task5 = await tasklib.submit_task(unreliable_task)
    print(f"Task 5 (unreliable): {task5}")

    return [task1, task2, task3, task4, task5]


async def check_status(task_ids: list):
    """Check status of tasks."""
    print("\nChecking task status (sleeping 10s)...")
    await asyncio.sleep(10)

    for task_id in task_ids:
        task = tasklib.get_task(task_id)
        if task:
            print(
                f"\nTask {task_id}:"
                f"\n  State: {task.state}"
                f"\n  Result: {task.result}"
                f"\n  Error: {task.error}"
                f"\n  Retries: {task.retry_count}/{task.max_retries}"
            )


async def main():
    """Main entry point."""
    # Get DB URL from environment or use default
    db_url = "postgresql://postgres:postgres@localhost:5432/tasklib_test"

    # Initialize tasklib
    config = tasklib.Config(
        database_url=db_url,
        max_retries=3,
        base_retry_delay_seconds=1.0,  # Faster retries for demo
        lock_timeout_seconds=5,  # Shorter timeout for demo
    )

    tasklib.init(config)

    # Submit some tasks
    task_ids = await submit_examples()

    # Check their status after a bit
    await check_status(task_ids)

    # List all tasks
    print("\n\nAll tasks in queue:")
    all_tasks = tasklib.list_tasks(limit=20)
    for task in all_tasks:
        print(f"  {task.name} ({task.state}) - {task.id}")

    print("\n\nNow run: python -m examples.worker")


if __name__ == "__main__":
    asyncio.run(main())
