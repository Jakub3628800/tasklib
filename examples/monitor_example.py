"""Example: Monitor and check task status.

This script demonstrates how to monitor submitted tasks and check their status.

Usage:

    # Terminal 1: Start the worker
    tasklib-worker --task-module examples.tasks

    # Terminal 2: Submit tasks
    python -m examples.submit_example

    # Terminal 3: Monitor (this script)
    python -m examples.monitor_example
"""

import asyncio
import os
import sys
from datetime import datetime

# Add parent directory to path to import tasklib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tasklib import (
    Config,
    get_task,
    has_error,
    has_result,
    init,
    is_completed,
    is_failed,
    is_pending,
    is_running,
)


def format_result(value, max_len=50):
    """Format a value for display."""
    if value is None:
        return "None"
    s = str(value)
    if len(s) > max_len:
        return s[:max_len] + "..."
    return s


def print_task_details(task, index=None):
    """Print detailed information about a task."""
    prefix = f"[{index}] " if index is not None else ""

    print(f"\n{prefix}Task ID: {task.id}")
    print(f"  Name:      {task.name}")
    print(f"  State:     {task.state}")
    print(f"  Priority:  {task.priority}")

    # Timing info
    if task.created_at:
        print(f"  Created:   {task.created_at}")
    if task.scheduled_at:
        print(f"  Scheduled: {task.scheduled_at}")
    if task.started_at:
        print(f"  Started:   {task.started_at}")
    if task.completed_at:
        print(f"  Completed: {task.completed_at}")

    # Retry info
    if task.retry_count > 0 or task.max_retries > 0:
        print(f"  Retries:   {task.retry_count}/{task.max_retries}")

    # Status indicators
    if is_pending(task):
        print("  Status:    ⏳ PENDING")
    elif is_running(task):
        print("  Status:    ⚙️  RUNNING")
    elif is_completed(task):
        print("  Status:    ✅ COMPLETED")
    elif is_failed(task):
        print("  Status:    ❌ FAILED")

    # Results
    if has_result(task):
        result_str = format_result(task.result, max_len=60)
        print(f"  Result:    {result_str}")

    # Errors
    if has_error(task):
        error_str = format_result(task.error, max_len=60)
        print(f"  Error:     {error_str}")

    # Tags
    if task.tags:
        print(f"  Tags:      {task.tags}")


async def monitor_specific_tasks() -> None:
    """Monitor specific tasks from task_ids.txt file."""
    task_ids_file = "examples/task_ids.txt"

    if not os.path.exists(task_ids_file):
        print(f"⚠️  Task IDs file not found: {task_ids_file}")
        print("Please run submit_example.py first:")
        print("  python -m examples.submit_example")
        return

    # Read task IDs from file
    with open(task_ids_file, "r") as f:
        lines = f.readlines()

    task_data = []
    for line in lines:
        parts = line.strip().split(None, 1)
        if len(parts) == 2:
            task_id, name = parts
            task_data.append((task_id, name))

    print("=" * 80)
    print("TaskLib Example: Monitor Tasks")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Monitoring {len(task_data)} tasks\n")

    # Fetch all task details
    tasks = []
    for task_id, name in task_data:
        try:
            task = await get_task(task_id)
            if task:
                tasks.append((name, task))
            else:
                print(f"⚠️  Task not found: {task_id}")
        except Exception as e:
            print(f"❌ Error fetching task {task_id}: {e}")

    if not tasks:
        print("No tasks to monitor")
        return

    # ========================================================================
    # Summary Statistics
    # ========================================================================
    print("\n" + "-" * 80)
    print("SUMMARY")
    print("-" * 80)

    states = {"pending": 0, "running": 0, "completed": 0, "failed": 0}
    for name, task in tasks:
        states[task.state] = states.get(task.state, 0) + 1

    print(f"Total tasks:     {len(tasks)}")
    print(f"  ⏳ Pending:    {states.get('pending', 0)}")
    print(f"  ⚙️  Running:    {states.get('running', 0)}")
    print(f"  ✅ Completed:  {states.get('completed', 0)}")
    print(f"  ❌ Failed:     {states.get('failed', 0)}")

    # Count results and errors
    with_results = sum(1 for _, t in tasks if has_result(t))
    with_errors = sum(1 for _, t in tasks if has_error(t))
    print(f"\nResults stored: {with_results}")
    print(f"Errors logged:  {with_errors}")

    # ========================================================================
    # Detailed Task Information
    # ========================================================================
    print("\n" + "=" * 80)
    print("DETAILED TASK INFORMATION")
    print("=" * 80)

    # Group by state
    by_state = {"pending": [], "running": [], "completed": [], "failed": []}
    for name, task in tasks:
        by_state[task.state].append((name, task))

    # Print pending tasks
    if by_state["pending"]:
        print(f"\n⏳ PENDING TASKS ({len(by_state['pending'])})")
        print("-" * 80)
        for i, (name, task) in enumerate(by_state["pending"], 1):
            print_task_details(task, i)

    # Print running tasks
    if by_state["running"]:
        print(f"\n⚙️  RUNNING TASKS ({len(by_state['running'])})")
        print("-" * 80)
        for i, (name, task) in enumerate(by_state["running"], 1):
            print_task_details(task, i)

    # Print completed tasks
    if by_state["completed"]:
        print(f"\n✅ COMPLETED TASKS ({len(by_state['completed'])})")
        print("-" * 80)
        for i, (name, task) in enumerate(by_state["completed"], 1):
            print_task_details(task, i)

    # Print failed tasks
    if by_state["failed"]:
        print(f"\n❌ FAILED TASKS ({len(by_state['failed'])})")
        print("-" * 80)
        for i, (name, task) in enumerate(by_state["failed"], 1):
            print_task_details(task, i)

    # ========================================================================
    # Tips
    # ========================================================================
    print("\n" + "=" * 80)
    print("TIPS")
    print("=" * 80)
    print("\n✅ All tasks completed? Check results by running again later.")
    print("   Run monitor_example.py again to see updated status.")
    print("\n⚙️  Tasks still running? Worker is processing them.")
    print("   Check worker logs: tasklib-worker --log-level DEBUG")
    print("\n❌ Tasks failed? Check error column for details.")
    print("   Some tasks may retry automatically.")
    print("\n📊 Query tasks from Python:")
    print("""
    from tasklib import list_tasks
    all_tasks = list_tasks(limit=100, state='completed')
    for task in all_tasks:
        print(f"{task.name}: {task.result}")
    """)


async def continuous_monitoring() -> None:
    """Continuously monitor tasks until all are done."""
    task_ids_file = "examples/task_ids.txt"

    if not os.path.exists(task_ids_file):
        print(f"⚠️  Task IDs file not found: {task_ids_file}")
        return

    # Read task IDs
    with open(task_ids_file, "r") as f:
        lines = f.readlines()

    task_ids = []
    for line in lines:
        parts = line.strip().split(None, 1)
        if len(parts) >= 1:
            task_ids.append(parts[0])

    print("=" * 80)
    print("TaskLib Example: Continuous Monitoring")
    print("=" * 80)
    print(f"Monitoring {len(task_ids)} tasks continuously...")
    print("(Press Ctrl+C to stop)\n")

    previous_states = {}

    try:
        while True:
            # Fetch all tasks
            tasks = []
            for task_id in task_ids:
                try:
                    task = await get_task(task_id)
                    if task:
                        tasks.append(task)
                except Exception:
                    pass

            # Check if states changed
            current_states = {t.id: t.state for t in tasks}

            # Print header
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Status Update")
            print("-" * 80)

            # Count by state
            states = {
                "pending": sum(1 for t in tasks if is_pending(t)),
                "running": sum(1 for t in tasks if is_running(t)),
                "completed": sum(1 for t in tasks if is_completed(t)),
                "failed": sum(1 for t in tasks if is_failed(t)),
            }

            print(f"⏳ Pending:   {states['pending']}")
            print(f"⚙️  Running:   {states['running']}")
            print(f"✅ Completed: {states['completed']}")
            print(f"❌ Failed:    {states['failed']}")

            # Show changes
            changes = []
            for task_id, new_state in current_states.items():
                old_state = previous_states.get(task_id)
                if old_state and old_state != new_state:
                    changes.append(f"  {task_id[:8]}... {old_state} → {new_state}")

            if changes:
                print("\nState changes:")
                for change in changes:
                    print(change)

            previous_states = current_states

            # Check if all done
            if states["pending"] == 0 and states["running"] == 0:
                print("\n" + "=" * 80)
                print("✅ All tasks completed!")
                print("=" * 80)
                break

            # Wait before next check
            await asyncio.sleep(3)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")


async def main() -> None:
    """Main entry point."""
    # Get database URL
    db_url = os.getenv("DATABASE_URL", "postgresql://tasklib:tasklib_pass@localhost:5432/tasklib")

    # Initialize TaskLib
    config = Config(database_url=db_url)
    await init(config)

    # Choose monitoring mode
    print("TaskLib Monitoring Options:")
    print("1. One-time status check (default)")
    print("2. Continuous monitoring (until complete)")
    print()

    choice = input("Choose option (1 or 2): ").strip()

    if choice == "2":
        await continuous_monitoring()
    else:
        await monitor_specific_tasks()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
