# Error Handling

How TaskLib handles errors and retries.

## Automatic Retries

Failed tasks retry automatically:

```python
@task(max_retries=3)
def risky_task() -> str:
    # If this fails, it retries 3 times
    return requests.get("https://api.example.com").json()
```

## Exponential Backoff

Retries use exponential backoff:
- Retry 1: +5 seconds
- Retry 2: +10 seconds
- Retry 3: +20 seconds

## Checking for Errors

```python
from tasklib import get_task, has_error, is_failed

task = get_task(task_id)
if has_error(task):
    print(f"Error: {task.error}")
    print(f"Attempts: {task.retry_count}/{task.max_retries}")
```

See [Full Guide](../../FINAL_SUMMARY.md) for advanced patterns.
