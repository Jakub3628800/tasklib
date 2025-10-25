# TaskLib Developer Experience

## The Simplicity

TaskLib has **3 core things:**

1. **`@task` decorator** - mark functions as tasks
2. **`submit_task()` function** - queue them to run later
3. **`TaskWorker` class** - execute them in the background

That's it. Everything else is optional.

---

## Real Code Example

### Step 1: Import

```python
from tasklib import task, submit_task, Config, TaskWorker
```

### Step 2: Initialize (once at app startup)

```python
config = Config(database_url="postgresql://...")
tasklib.init(config)
```

### Step 3: Define a Task

```python
@task
def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email. Parameters are automatically Pydantic-validated."""
    # Your code here
    smtp = smtplib.SMTP("localhost")
    smtp.send_message(...)
    return True
```

**That's it.** Parameters are type-checked at submit time via Pydantic.

### Step 4: Submit (in your app)

```python
# In a request handler, API endpoint, etc.
task_id = await submit_task(
    send_email,
    to="user@example.com",
    subject="Welcome!",
    body="Hello..."
)
print(f"Task queued: {task_id}")
# The function runs in the background
```

### Step 5: Run Worker (separate process)

```python
# In worker.py or as a Celery-like worker command
async def main():
    config = Config(database_url="postgresql://...")
    worker = TaskWorker(config, concurrency=4)
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
```

```bash
# Run it
python worker.py
# Output: Starting TaskWorker abc-123 with concurrency=4
```

### Step 6: Monitor (optional)

```python
from tasklib import get_task, is_completed, has_result

task = get_task(task_id)
print(f"State: {task.state}")          # "pending", "running", "completed", "failed"
print(f"Is done: {is_completed(task)}")
print(f"Result: {task.result}")         # {"value": true}
```

---

## Full Integration Example

### In your FastAPI app:

```python
# app.py
from fastapi import FastAPI
import tasklib

app = FastAPI()

# Initialize at startup
@app.on_event("startup")
async def startup():
    config = tasklib.Config(database_url="postgresql://...")
    tasklib.init(config)

# Define tasks
@tasklib.task
def send_email(to: str, subject: str) -> bool:
    # Your email logic
    return True

# Use in endpoints
@app.post("/send-email")
async def send_email_endpoint(to: str, subject: str):
    task_id = await tasklib.submit_task(
        send_email,
        to=to,
        subject=subject
    )
    return {"task_id": task_id, "status": "queued"}

@app.get("/task/{task_id}")
async def get_task_status(task_id: str):
    from uuid import UUID
    task = tasklib.get_task(UUID(task_id))
    return {
        "id": task.id,
        "state": task.state,
        "result": task.result,
        "error": task.error
    }
```

### Running:

```bash
# Terminal 1: Run the app
uvicorn app:app --reload

# Terminal 2: Run the worker
python -c "
import asyncio
from tasklib import Config, TaskWorker

async def main():
    config = Config(database_url='postgresql://...')
    worker = TaskWorker(config, concurrency=4)
    await worker.run()

asyncio.run(main())
"
```

### Testing:

```bash
# Submit a task
curl -X POST "http://localhost:8000/send-email?to=user@example.com&subject=Hello"
# {"task_id": "550e8400-e29b-41d4-a716-446655440001", "status": "queued"}

# Check status
curl "http://localhost:8000/task/550e8400-e29b-41d4-a716-446655440001"
# {"id": "550e8400...", "state": "completed", "result": {"value": true}, "error": null}
```

---

## Advanced Features (Still Simple!)

### 1. Retries with Backoff

```python
@tasklib.task(max_retries=5)  # Will retry up to 5 times
def flaky_api_call() -> dict:
    return requests.get("https://api.example.com/data").json()

# If it fails:
# - Attempt 1: Immediate failure
# - Wait 5 seconds
# - Attempt 2: Fail
# - Wait 10 seconds (5 * 2^1)
# - Attempt 3: Fail
# - Wait 20 seconds (5 * 2^2)
# - ... and so on
```

### 2. Timeouts

```python
@tasklib.task(timeout_seconds=30)  # Max 30 seconds
def process_file(file_path: str) -> str:
    # If this takes > 30 seconds, task fails and retries
    return process(file_path)
```

### 3. Delayed Execution

```python
# Send welcome email in 1 hour
task_id = await tasklib.submit_task(
    send_email,
    delay_seconds=3600,  # 1 hour
    to="user@example.com",
    subject="Welcome!"
)
```

### 4. Priority

```python
# High-priority task (execute first)
await tasklib.submit_task(
    alert_admin,
    message="Disk full!",
    priority=100  # Higher number = higher priority
)

# Low-priority task (execute later)
await tasklib.submit_task(
    cleanup_logs,
    priority=-10
)
```

### 5. Metadata Tags

```python
# Add custom metadata for filtering/monitoring
await tasklib.submit_task(
    send_email,
    to="user@example.com",
    subject="Newsletter",
    tags={
        "batch": "weekly-newsletter",
        "cohort": "2025-10-25",
        "user_id": 12345
    }
)

# Query later
tasks = tasklib.list_tasks(tags={"batch": "weekly-newsletter"})
```

### 6. Check Results

```python
from tasklib import (
    get_task,
    is_pending,
    is_running,
    is_completed,
    is_failed,
    has_result,
    has_error,
    is_terminal
)

task = get_task(task_id)

if is_completed(task):
    print(f"Result: {task.result['value']}")

elif is_failed(task):
    if is_terminal(task):
        print(f"Permanently failed: {task.error}")
    else:
        print(f"Temporary failure, will retry at {task.next_retry_at}")

elif is_running(task):
    print(f"Being executed by {task.worker_id}")

elif is_pending(task):
    print(f"Waiting to execute at {task.scheduled_at}")
```

---

## Error Handling

### Valid (Pydantic validates at submit time)

```python
@tasklib.task
def greet(name: str) -> str:
    return f"Hello {name}!"

# ✅ Valid
await tasklib.submit_task(greet, name="Alice")
```

### Invalid (Rejected at submit)

```python
# ❌ Wrong type - rejected with ValidationError
try:
    await tasklib.submit_task(greet, name=123)  # name should be str
except tasklib.TaskLibError:
    print("Rejected: wrong type")

# ❌ Missing required param - rejected
try:
    await tasklib.submit_task(greet)  # missing 'name'
except tasklib.TaskLibError:
    print("Rejected: missing parameter")

# ❌ Task not registered - rejected
async def undecorated():
    return "oops"

try:
    await tasklib.submit_task(undecorated)
except tasklib.TaskLibError:
    print("Rejected: not registered with @task")
```

### Task Execution Errors (Handled Automatically)

```python
@tasklib.task(max_retries=3)
def risky_task() -> str:
    if random.random() < 0.5:
        raise ValueError("Random failure!")
    return "success"

# Submit
task_id = await tasklib.submit_task(risky_task)

# If fails:
# - Captured: task.error = "<full traceback>"
# - Scheduled: task.next_retry_at = NOW() + 5 seconds
# - Marked: task.state = "failed"
# - Queued: Will retry at next_retry_at automatically
```

---

## Comparison to Celery

| Feature | TaskLib | Celery |
|---------|---------|--------|
| **Setup** | Just PostgreSQL | Broker + Backend + Workers |
| **First Task** | 10 minutes | 1 hour |
| **Lines of Code** | ~500 | ~50,000 |
| **Dependencies** | sqlmodel, psycopg | redis/rabbitmq, kombu, vine, ... |
| **Docker Compose** | 5 lines | 15+ lines |
| **Deployment** | Simple | Complex |
| **Learn Time** | 15 minutes | Days |
| **Perfect for** | Simple async work | Enterprise systems |

---

## Production Checklist

- [ ] PostgreSQL 12+ running (cloud or self-hosted)
- [ ] tasklib installed (`uv add tasklib`)
- [ ] Migration applied (Alembic or SQL)
- [ ] `tasklib.init()` called at app startup
- [ ] Tasks defined with `@task` decorator
- [ ] Worker process running (separate from app)
- [ ] Worker configured with concurrency (typically 4-10)
- [ ] Monitoring in place (query tasks table or use helpers)
- [ ] Cleanup job for old tasks (optional)

---

## Monitoring

### Quick Status

```sql
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE state='pending') as pending,
  COUNT(*) FILTER (WHERE state='running') as running,
  COUNT(*) FILTER (WHERE state='completed') as completed,
  COUNT(*) FILTER (WHERE state='failed' AND retry_count < max_retries) as failed_retrying,
  COUNT(*) FILTER (WHERE state='failed' AND retry_count >= max_retries) as failed_permanent
FROM tasks;
```

### Performance by Task

```sql
SELECT
  name,
  COUNT(*) as executions,
  AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration_s,
  MAX(EXTRACT(EPOCH FROM (completed_at - started_at))) as max_duration_s
FROM tasks
WHERE state = 'completed'
GROUP BY name
ORDER BY avg_duration_s DESC;
```

### Worker Health

```sql
SELECT
  worker_id,
  COUNT(*) as locked_tasks,
  MIN(locked_until) as earliest_lock_expires
FROM tasks
WHERE state = 'running'
AND worker_id IS NOT NULL
GROUP BY worker_id;
```

---

## Key Takeaways

1. **Decorator pattern** - Mark functions with `@task`
2. **Type validation** - Parameters checked at submit via Pydantic
3. **Simple API** - Just `submit_task()` and `TaskWorker`
4. **Automatic retries** - Exponential backoff built-in
5. **PostgreSQL only** - Single source of truth
6. **Worker loop** - Poll, lock, execute, update DB
7. **Distributed ready** - Multiple workers, atomic locking
8. **No complexity** - No Celery config hell

---

**Start using it in 5 minutes. Scale it to 1000s of tasks. Sleep well.**

---

**Last Updated:** 2025-10-25
