"""Example: Submit various tasks to demonstrate TaskLib features.

This script submits different types of tasks with various options.
Run the worker in another terminal to execute them:

    # Terminal 1: Start the worker
    tasklib-worker --task-module examples.tasks

    # Terminal 2: Submit tasks
    python -m examples.submit_example

Then monitor progress:

    # Terminal 3: Monitor
    python -m examples.monitor_example
"""

import asyncio
import os
import sys
from datetime import datetime
from uuid import UUID

# Add parent directory to path to import tasklib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tasklib import Config, init, submit_task

# Import tasks to register them
from .tasks import (  # pyrefly: ignore
    batch_process,
    calculate_statistics,
    cpu_work,
    database_task,
    generate_report,
    greet,
    io_task,
    memory_task,
    process_text,
    send_email,
    simple_add,
    task_with_custom_retries,
    unreliable_task,
    validation_task,
)


async def submit_all_tasks() -> list[tuple[str, UUID]]:
    """Submit various tasks and return their IDs."""
    task_ids = []

    print("=" * 80)
    print("TaskLib Example: Submitting Tasks")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}\n")

    # ========================================================================
    # Section 1: Simple Tasks
    # ========================================================================
    print("\n📌 Section 1: Simple Tasks")
    print("-" * 80)

    print("Task 1: Simple addition (immediate)")
    task_id = await submit_task(simple_add, a=5, b=3)
    print(f"  Submitted: {task_id}\n")
    task_ids.append(("simple_add(5, 3)", task_id))

    print("Task 2: Greeting with default parameter")
    task_id = await submit_task(greet, name="Alice")
    print(f"  Submitted: {task_id}\n")
    task_ids.append(("greet(name='Alice')", task_id))

    print("Task 3: Greeting with custom greeting")
    task_id = await submit_task(greet, name="Bob", greeting="Hi")
    print(f"  Submitted: {task_id}\n")
    task_ids.append(("greet(name='Bob', greeting='Hi')", task_id))

    # ========================================================================
    # Section 2: Delayed Tasks
    # ========================================================================
    print("\n📌 Section 2: Delayed Tasks")
    print("-" * 80)

    print("Task 4: Delayed task (execute in 5 seconds)")
    task_id = await submit_task(simple_add, a=100, b=200, delay_seconds=5)
    print(f"  Submitted: {task_id}\n")
    task_ids.append(("simple_add(100, 200) [delayed 5s]", task_id))

    print("Task 5: Delayed greeting (execute in 3 seconds)")
    task_id = await submit_task(greet, name="Charlie", delay_seconds=3)
    print(f"  Submitted: {task_id}\n")
    task_ids.append(("greet(name='Charlie') [delayed 3s]", task_id))

    # ========================================================================
    # Section 3: Priority Tasks
    # ========================================================================
    print("\n📌 Section 3: Priority Tasks")
    print("-" * 80)

    print("Task 6: Low priority task (priority=1)")
    task_id = await submit_task(simple_add, a=1, b=1, priority=1, tags={"importance": "low"})
    print(f"  Submitted: {task_id}\n")
    task_ids.append(("simple_add(1, 1) [priority=1]", task_id))

    print("Task 7: High priority task (priority=10)")
    task_id = await submit_task(simple_add, a=10, b=10, priority=10, tags={"importance": "high"})
    print(f"  Submitted: {task_id}\n")
    task_ids.append(("simple_add(10, 10) [priority=10]", task_id))

    # ========================================================================
    # Section 4: Complex Tasks
    # ========================================================================
    print("\n📌 Section 4: Complex Tasks")
    print("-" * 80)

    print("Task 8: Text processing")
    text = "Hello World! This is a test of the TaskLib library."
    task_id = await submit_task(process_text, text=text)
    print(f"  Submitted: {task_id}\n")
    task_ids.append(("process_text(...)", task_id))

    print("Task 9: Batch processing")
    items = ["apple", "banana", "cherry", "date", "elderberry"]
    task_id = await submit_task(batch_process, items=items)
    print(f"  Submitted: {task_id}\n")
    task_ids.append(("batch_process([...])", task_id))

    print("Task 10: Statistics calculation")
    data = [1.5, 2.7, 3.2, 4.1, 5.8, 6.3, 7.9]
    task_id = await submit_task(calculate_statistics, data=data)
    print(f"  Submitted: {task_id}\n")
    task_ids.append(("calculate_statistics([...])", task_id))

    # ========================================================================
    # Section 5: I/O Tasks
    # ========================================================================
    print("\n📌 Section 5: I/O Tasks")
    print("-" * 80)

    print("Task 11: I/O task (sleep 1 second)")
    task_id = await submit_task(io_task, duration_seconds=1)
    print(f"  Submitted: {task_id}\n")
    task_ids.append(("io_task(1s)", task_id))

    print("Task 12: I/O task with longer duration (sleep 2 seconds)")
    task_id = await submit_task(io_task, duration_seconds=2)
    print(f"  Submitted: {task_id}\n")
    task_ids.append(("io_task(2s)", task_id))

    # ========================================================================
    # Section 6: Error Handling & Retries
    # ========================================================================
    print("\n📌 Section 6: Error Handling & Retries")
    print("-" * 80)

    print("Task 13: Unreliable task (50% success rate, will retry)")
    task_id = await submit_task(unreliable_task, success_rate=0.5)
    print(f"  Submitted: {task_id}\n")
    task_ids.append(("unreliable_task(50%)", task_id))

    print("Task 14: Unreliable task (80% success rate)")
    task_id = await submit_task(unreliable_task, success_rate=0.8)
    print(f"  Submitted: {task_id}\n")
    task_ids.append(("unreliable_task(80%)", task_id))

    print("Task 15: Task with custom retries")
    task_id = await submit_task(task_with_custom_retries)
    print(f"  Submitted: {task_id}\n")
    task_ids.append(("task_with_custom_retries()", task_id))

    print("Task 16: Validation task (valid)")
    task_id = await submit_task(validation_task, value=42)
    print(f"  Submitted: {task_id}\n")
    task_ids.append(("validation_task(42)", task_id))

    print("Task 17: Validation task (invalid - negative)")
    task_id = await submit_task(validation_task, value=-5)
    print(f"  Submitted: {task_id}\n")
    task_ids.append(("validation_task(-5) [ERROR]", task_id))

    # ========================================================================
    # Section 7: Real-World Tasks
    # ========================================================================
    print("\n📌 Section 7: Real-World Scenarios")
    print("-" * 80)

    print("Task 18: Send email (notification)")
    task_id = await submit_task(
        send_email,
        to="alice@example.com",
        subject="Welcome",
        body="Welcome to our platform!",
    )
    print(f"  Submitted: {task_id}\n")
    task_ids.append(("send_email(alice@...)", task_id))

    print("Task 19: Generate report (PDF)")
    task_id = await submit_task(generate_report, report_type="PDF", include_charts=True)
    print(f"  Submitted: {task_id}\n")
    task_ids.append(("generate_report(PDF)", task_id))

    print("Task 20: Database operation (insert)")
    task_id = await submit_task(database_task, operation="insert")
    print(f"  Submitted: {task_id}\n")
    task_ids.append(("database_task(insert)", task_id))

    print("Task 21: Database operation (update)")
    task_id = await submit_task(database_task, operation="update")
    print(f"  Submitted: {task_id}\n")
    task_ids.append(("database_task(update)", task_id))

    # ========================================================================
    # Section 8: Performance Tests
    # ========================================================================
    print("\n📌 Section 8: Performance Tests")
    print("-" * 80)

    print("Task 22: CPU-intensive work (100K iterations)")
    task_id = await submit_task(cpu_work, iterations=100000)
    print(f"  Submitted: {task_id}\n")
    task_ids.append(("cpu_work(100K)", task_id))

    print("Task 23: Memory allocation (5MB)")
    task_id = await submit_task(memory_task, size_mb=5)
    print(f"  Submitted: {task_id}\n")
    task_ids.append(("memory_task(5MB)", task_id))

    # ========================================================================
    # Summary
    # ========================================================================
    print("\n" + "=" * 80)
    print(f"✅ Submitted {len(task_ids)} tasks")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Start the worker in another terminal:")
    print("   tasklib-worker --task-module examples.tasks")
    print("\n2. Monitor task progress:")
    print("   python -m examples.monitor_example")
    print("\n3. Save task IDs for monitoring (shown below)")
    print("\n" + "=" * 80)

    return task_ids


async def main() -> None:
    """Main entry point."""
    # Get database URL
    db_url = os.getenv("DATABASE_URL", "postgresql://tasklib:tasklib_pass@localhost:5432/tasklib")

    # Initialize TaskLib
    config = Config(database_url=db_url)
    await init(config)  # pyrefly: ignore

    # Submit all tasks
    try:
        task_ids = await submit_all_tasks()

        # Save task IDs to file for later monitoring
        with open("examples/task_ids.txt", "w") as f:
            for name, task_id in task_ids:
                f.write(f"{task_id}  {name}\n")

        print("\n📝 Task IDs saved to: examples/task_ids.txt")
        print("\nYou can now run monitor_example.py to check progress:")
        print("  python -m examples.monitor_example")

    except Exception as e:
        print(f"\n❌ Error submitting tasks: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
