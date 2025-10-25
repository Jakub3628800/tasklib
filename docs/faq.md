# Frequently Asked Questions

## General

### What is TaskLib?

TaskLib is a simple, durable task queue for PostgreSQL. It lets you define tasks with a decorator, queue them for later execution, and run workers to process them.

Think "Celery but simpler" - 500 lines of code instead of 50,000.

### Why PostgreSQL and not Redis/RabbitMQ?

PostgreSQL is:
- Already in many projects
- ACID compliant (durable)
- Simpler to operate
- No additional infrastructure needed
- Good performance for typical workloads

RabbitMQ/Redis are better for extreme throughput, but PostgreSQL is simpler for most use cases.

### Can I use this in production?

Yes! TaskLib is:
- Fully tested (45+ test cases)
- Used for async task execution
- Handles failures gracefully
- Multi-worker safe

Start small, monitor, scale as needed.

### How is this different from Celery?

| Aspect | TaskLib | Celery |
|--------|---------|--------|
| Setup | PostgreSQL | Redis/RabbitMQ + Celery |
| LOC | ~500 | ~50,000 |
| Learning curve | 15 min | Days |
| Flexibility | Limited | Unlimited |
| Perfect for | Simple tasks | Enterprise systems |

Choose TaskLib if simplicity matters. Choose Celery for advanced features.

## Tasks

### Can tasks be async?

Not in v1. They're sync functions executed in a thread pool.

v2 will add async support.

### Can I call other tasks from a task?

Yes, just submit them:

```python
@task
def task_a() -> str:
    # Submit another task
    task_id = await tasklib.submit_task(task_b)
    return f"Spawned {task_id}"

@task
def task_b() -> str:
    return "done"
```

### Can I pass complex objects?

Objects must be JSON-serializable (Pydantic validates this).

```python
@task
def process(data: dict) -> dict:
    return data

# ✅ Works
await submit_task(process, data={"key": "value"})

# ❌ Doesn't work - not JSON-serializable
class MyClass:
    pass

await submit_task(process, data=MyClass())  # ValueError
```

### What about task chaining?

Chain manually:

```python
@task
def task_a() -> dict:
    result = {"step": 1}
    # Submit next task with result from this one
    await tasklib.submit_task(task_b, data=result)
    return result
```

Formal chaining (task_a → task_b → task_c) is not supported in v1.

### How do I timeout a task?

```python
@task(timeout_seconds=30)
def long_task() -> str:
    # If this takes > 30 seconds, it's killed
    return "done"
```

## Workers

### Do I need multiple workers?

No, but they help with:
- Parallelism (multiple tasks at once)
- High availability (one worker dies, others continue)
- Horizontal scaling (add more workers as needed)

Start with one worker, scale up as needed.

### How many workers do I need?

Start with 1-2. Monitor:
- CPU usage (if high, add workers)
- Queue depth (if growing, add workers)
- Task latency (if slow, add workers)

Rule of thumb: 1 worker per CPU core.

### Can workers be on different machines?

Yes! All workers read from the same PostgreSQL database.

```python
# machine1.py
worker = TaskWorker(config)
await worker.run()

# machine2.py (same database URL)
worker = TaskWorker(config)
await worker.run()

# Both workers process tasks from the same queue
```

### What if a worker dies?

Task lock times out after `lock_timeout_seconds` (default 10 min).

Other workers pick up stale tasks automatically.

No manual intervention needed.

## Retries

### How do retries work?

Failed tasks retry with exponential backoff:

```
Fail → Wait 5s → Retry 1
Fail → Wait 10s → Retry 2
Fail → Wait 20s → Retry 3
Fail → Give up (max retries exceeded)
```

### Can I customize retry behavior?

```python
@task(max_retries=5)  # More retries
def retry_many() -> str:
    pass

config = Config(
    base_retry_delay_seconds=10.0,  # Longer delays
    retry_backoff_multiplier=3.0,   # Faster growth
)
```

### Can I manually retry a task?

Not yet. You can:

1. Update the task in the database directly
2. Resubmit the task

In v2, there will be a `retry_task()` function.

## Deployment

### How do I deploy this?

1. Install `uv add tasklib`
2. Run migrations (Alembic or SQL)
3. Initialize in your app: `tasklib.init(config)`
4. Define tasks with `@task`
5. Run worker process

### Can I run on Kubernetes?

Yes! Create two deployments:

```yaml
# app-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: app
        image: myapp:latest

---
# worker-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-worker
spec:
  replicas: 3  # Scale workers independently
  template:
    spec:
      containers:
      - name: worker
        image: myapp-worker:latest
        command: ["python", "worker.py"]
```

### How do I scale?

Vertical: Increase concurrency
```python
worker = TaskWorker(config, concurrency=8)  # More parallel tasks
```

Horizontal: Add more worker processes/machines
```python
# machine1, machine2, machine3...
worker = TaskWorker(config, concurrency=4)
```

## Monitoring

### How do I check task status?

```python
from tasklib import get_task, is_completed

task = get_task(task_id)
print(f"State: {task.state}")
print(f"Result: {task.result}")
```

Or query directly:
```sql
SELECT id, name, state, result, error FROM tasks WHERE id = 'xyz';
```

### How do I monitor worker health?

```sql
-- See what each worker is doing
SELECT worker_id, COUNT(*) as locked_tasks
FROM tasks
WHERE state = 'running'
GROUP BY worker_id;

-- See stuck tasks
SELECT id, name, locked_until
FROM tasks
WHERE state = 'running'
AND locked_until < NOW();
```

### How do I clean up old tasks?

```sql
-- Delete completed tasks older than 30 days
DELETE FROM tasks
WHERE state = 'completed'
AND completed_at < NOW() - INTERVAL '30 days';
```

## Troubleshooting

### Tasks not executing

1. Check PostgreSQL is running
2. Check `tasklib.init()` was called
3. Check workers are running
4. Check task `scheduled_at <= NOW()`

### Task stuck in "running"

Worker probably died. Wait for `locked_until` to expire (default 10 min).

Or manually release:

```sql
UPDATE tasks
SET state = 'pending', worker_id = NULL, locked_until = NULL
WHERE state = 'running'
AND locked_until < NOW();
```

### Task failing with validation error

Type mismatch in parameters:

```python
@task
def my_task(count: int) -> int:
    return count

# ✅ Correct
await submit_task(my_task, count=5)

# ❌ Wrong
await submit_task(my_task, count="5")  # str, not int
```

## Contributing

Have questions? Check the [Contributing](contributing.md) guide.

Want to add features? See [Contributing](contributing.md).

---

**More questions?** Open an issue on GitHub.
