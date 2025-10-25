# TaskLib Examples

Comprehensive examples demonstrating TaskLib features and usage.

## Overview

This directory contains a complete example application showing:

- ✅ **Task Definition** - Various types of tasks
- ✅ **Task Submission** - Submitting tasks with different options
- ✅ **Task Monitoring** - Checking task status and results
- ✅ **Error Handling** - Retries and failure scenarios
- ✅ **Real-World Scenarios** - Email, reports, database operations

## Files

### `tasks.py`
Defines 18 example tasks demonstrating:

- **Simple tasks**: Addition, greeting, text processing
- **I/O tasks**: Simulated database and network operations
- **Error handling**: Tasks with retries, validation errors
- **Complex tasks**: Batch processing, statistics, reports
- **Performance tests**: CPU and memory intensive tasks

### `submit_example.py`
Submits 23 different tasks showing:

- Immediate execution
- Delayed execution (`delay_seconds`)
- Task priority (`priority`)
- Task tags (`tags`)
- Multiple parameters
- Various task types
- Error scenarios

### `monitor_example.py`
Monitors submitted tasks with:

- One-time status check
- Continuous monitoring until completion
- Detailed task information
- Results and errors display
- Summary statistics

### `example.yaml`
Configuration file for the worker with:

- Database connection
- Worker settings (concurrency, poll interval)
- Retry configuration
- Task modules to import
- Logging settings

## Quick Start

### Step 1: Setup PostgreSQL

Start PostgreSQL (if not already running):

```bash
docker-compose up postgres
```

Or if PostgreSQL is running locally on localhost:5432 with credentials:
- User: `tasklib`
- Password: `tasklib_pass`
- Database: `tasklib`

### Step 2: Run Migration

```bash
alembic upgrade head
```

Or use the raw SQL migration:

```bash
psql -d tasklib -f migrations/001_add_tasks_table.sql
```

### Step 3: Open Multiple Terminals

#### Terminal 1: Start the Worker

Option A - Using config file:
```bash
tasklib-worker --config examples/example.yaml
```

Option B - Using command-line arguments:
```bash
export DATABASE_URL=postgresql://tasklib:tasklib_pass@localhost:5432/tasklib
tasklib-worker --task-module examples.tasks
```

**Expected output:**
```
2024-10-25 10:30:45 - tasklib - INFO - Starting TaskLib worker...
2024-10-25 10:30:45 - tasklib - INFO -   Worker ID: abc-123-uuid
2024-10-25 10:30:45 - tasklib - INFO -   Concurrency: 2
2024-10-25 10:30:45 - tasklib - INFO -   Poll interval: 0.5s
2024-10-25 10:30:45 - tasklib - INFO - Importing task modules: examples.tasks
```

#### Terminal 2: Submit Tasks

```bash
python -m examples.submit_example
```

**Expected output:**
```
================================================================================
TaskLib Example: Submitting Tasks
================================================================================

📌 Section 1: Simple Tasks
--------------------------------------------------------------------------------
Task 1: Simple addition (immediate)
  Submitted: 550e8400-e29b-41d4-a716-446655440000

Task 2: Greeting with default parameter
  Submitted: 6ba7b810-9dad-11d1-80b4-00c04fd430c8
...
```

The script will:
- Submit 23 different tasks
- Show their IDs
- Save IDs to `examples/task_ids.txt`

#### Terminal 3: Monitor Tasks

```bash
python -m examples.monitor_example
```

**Choose monitoring mode:**
```
TaskLib Monitoring Options:
1. One-time status check (default)
2. Continuous monitoring (until complete)

Choose option (1 or 2): 1
```

**Expected output:**
```
================================================================================
TaskLib Example: Monitor Tasks
================================================================================

SUMMARY
--------------------------------------------------------------------------------
Total tasks:     23
  ⏳ Pending:    15
  ⚙️  Running:    2
  ✅ Completed:  6
  ❌ Failed:     0

Results stored: 6
Errors logged:  0

DETAILED TASK INFORMATION
================================================================================

✅ COMPLETED TASKS (6)
--------------------------------------------------------------------------------

[1] Task ID: 550e8400-e29b-41d4-a716-446655440000
  Name:      simple_add
  State:     completed
  Created:   2024-10-25 10:30:45.123456
  Completed: 2024-10-25 10:30:45.456789
  Status:    ✅ COMPLETED
  Result:    8
```

## Example Task Types

### 1. Simple Tasks

```bash
# Add two numbers
simple_add(a=5, b=3)  →  Result: 8

# Greeting with optional parameter
greet(name="Alice")  →  Result: "Hello, Alice!"
greet(name="Bob", greeting="Hi")  →  Result: "Hi, Bob!"
```

### 2. Delayed Tasks

```bash
# Task executes after 5 seconds
simple_add(a=100, b=200, delay_seconds=5)

# Task is scheduled for future execution
submit_task(..., delay_seconds=60)
```

### 3. Priority Tasks

```bash
# High priority (execute sooner)
simple_add(a=10, b=10, priority=10)

# Low priority (execute later)
simple_add(a=1, b=1, priority=1)
```

### 4. Tasks with Retries

```bash
# Automatically retries on failure (50% success rate)
unreliable_task(success_rate=0.5)

# Retries with exponential backoff:
# Attempt 1 fails  →  delay 2s  →  Attempt 2 fails  →  delay 4s  →  Attempt 3
```

### 5. Complex Tasks

```bash
# Process text and return statistics
process_text(text="Hello World")  →  {length: 11, words: 2, uppercase: 2, ...}

# Batch process items
batch_process(items=["apple", "banana", "cherry"])  →  {count: 3, items: [...]}

# Calculate statistics
calculate_statistics(data=[1.5, 2.7, 3.2, ...])  →  {sum: 10, mean: 2.5, ...}
```

### 6. Real-World Tasks

```bash
# Send email notification
send_email(to="alice@example.com", subject="Welcome")

# Generate report
generate_report(report_type="PDF", include_charts=True)

# Database operations
database_task(operation="insert")
database_task(operation="update")
database_task(operation="delete")
```

## Monitoring Tasks

### View Task Status

From Python:

```python
from tasklib import get_task, is_completed, has_result

task = await get_task(task_id)
print(f"State: {task.state}")          # pending, running, completed, failed
print(f"Result: {task.result}")        # Task return value
print(f"Error: {task.error}")          # Exception traceback if failed
print(f"Retries: {task.retry_count}/{task.max_retries}")
print(f"Is done: {is_completed(task)}")
print(f"Has result: {has_result(task)}")
```

### List All Tasks

```python
from tasklib import list_tasks

# Get recent tasks
recent = list_tasks(limit=10)

# Get completed tasks
completed = list_tasks(state="completed", limit=100)

# Get failed tasks
failed = list_tasks(state="failed", limit=100)

for task in completed:
    print(f"{task.name}: {task.result}")
```

### Query Tasks from Database

```bash
# Connect to PostgreSQL
psql -d tasklib

# Show all tasks
SELECT id, name, state, created_at FROM tasks ORDER BY created_at DESC;

# Show completed tasks with results
SELECT id, name, result FROM tasks WHERE state = 'completed';

# Show failed tasks with errors
SELECT id, name, error FROM tasks WHERE state = 'failed';
```

## Performance Characteristics

With the example configuration:

| Metric | Value |
|--------|-------|
| Concurrency | 2 |
| Poll Interval | 0.5s |
| Task Submission | ~100+ tasks/sec |
| Task Execution | Depends on task type |
| Simple tasks | <10ms each |
| I/O tasks | 1-2 seconds |
| CPU tasks | 100ms-1s |
| Batch tasks | 10-100ms |

## Expected Results

After running the example:

- ✅ **23 tasks submitted** in ~2 seconds
- ⚙️ **Worker processes** 2 tasks concurrently
- ✅ **Simple tasks complete** almost immediately
- ⏳ **Delayed tasks** execute after their delay
- 🔄 **Unreliable tasks** may retry due to random failures
- ❌ **Validation tasks** show error handling
- 📊 **All results stored** in PostgreSQL

## Troubleshooting

### Worker won't start

```
Error: DATABASE_URL not provided
```

Make sure to set DATABASE_URL or use `--db-url`:

```bash
export DATABASE_URL=postgresql://tasklib:tasklib_pass@localhost:5432/tasklib
tasklib-worker --task-module examples.tasks
```

### Tasks not executing

Check:
1. Worker is running
2. Database is accessible
3. Migration was run
4. Task modules are imported

From worker terminal, enable debug logging:

```bash
tasklib-worker --task-module examples.tasks --log-level DEBUG
```

### Connection refused

PostgreSQL is not running:

```bash
# Start with Docker
docker-compose up postgres

# Or verify local connection
psql -h localhost -U tasklib -d tasklib
```

### Tasks failing with import errors

Ensure you're in the right directory and examples.tasks can be imported:

```bash
# From project root
python -c "from examples.tasks import simple_add; print('OK')"
```

## Next Steps

1. **Modify tasks.py** - Add your own task definitions
2. **Customize config** - Adjust concurrency, retry settings
3. **Integrate with API** - Submit tasks from your FastAPI/Django app
4. **Deploy** - Run worker in production with Docker/systemd/K8s
5. **Monitor** - Check task status and results
6. **Scale** - Run multiple workers for parallelism

## See Also

- [Running Workers](../docs/guides/workers.md)
- [Task Definition Guide](../docs/guides/task-definition.md)
- [Task Submission Guide](../docs/guides/task-submission.md)
- [Error Handling Guide](../docs/guides/error-handling.md)
- [Monitoring Guide](../docs/guides/monitoring.md)
