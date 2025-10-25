# Task Definition

Learn how to define tasks with TaskLib.

## Basic Task

```python
from tasklib import task

@task
def send_email(to: str, subject: str) -> bool:
    """Send an email. Parameters are Pydantic-validated."""
    # Your code
    return True
```

## Task with Type Hints

```python
@task
def process_data(data: dict, count: int) -> dict:
    """Process data with type validation."""
    return {"processed": len(data) * count}
```

## Task with Options

```python
@task(max_retries=5, timeout_seconds=30)
def slow_task(path: str) -> str:
    """
    Task with custom retry and timeout settings.

    - max_retries: Try up to 5 times if fails
    - timeout_seconds: Abort if takes > 30 seconds
    """
    # Your code
    return f"processed_{path}"
```

## Supported Types

TaskLib uses Pydantic for validation. All Python types are supported:

```python
@task
def full_example(
    name: str,                      # Required string
    age: int = 30,                  # Optional with default
    tags: list[str] = None,         # Optional list
    config: dict = None,            # Optional dict
    count: int = 1,                 # Optional int with default
) -> dict:
    """Fully typed task."""
    return {"processed": count}
```

## Return Values

Tasks can return any JSON-serializable value:

```python
@task
def various_returns() -> None:
    return None  # OK

@task
def returns_bool() -> bool:
    return True

@task
def returns_dict() -> dict:
    return {"key": "value", "count": 42}

@task
def returns_list() -> list:
    return [1, 2, 3]

@task
def returns_str() -> str:
    return "done"
```

## Exceptions

All exceptions are captured and retried:

```python
@task(max_retries=3)
def risky_task() -> str:
    # If this raises, it will retry 3 times
    # Full traceback is stored in DB for debugging
    return requests.get("https://api.example.com").json()
```

## Task Registration

Tasks **must** be defined with `@task` decorator:

```python
# ✅ Correct
@task
def my_task():
    pass

# ❌ Wrong - not registered
def undecorated_task():
    pass

await submit_task(undecorated_task)  # TaskLibError: not registered
```

## Naming

Task names are derived from function names:

```python
@task
def send_email(to: str) -> bool:
    pass

# Task name: "send_email"
# Can submit by function reference:
await submit_task(send_email, to="...")
```

## Module Organization

```python
# tasks.py
from tasklib import task

@task
def email_task(to: str) -> bool:
    return True

@task
def process_task(data: dict) -> dict:
    return data

# app.py
from tasks import email_task, process_task

# Tasks are registered when imported
await submit_task(email_task, to="...")
await submit_task(process_task, data={})
```

## Best Practices

1. **Use type hints** - Enables Pydantic validation
2. **Keep tasks focused** - One task, one responsibility
3. **Make idempotent** - Task may execute multiple times
4. **Handle errors** - Let them propagate for retry
5. **Keep small** - Prefer small, fast tasks
6. **Document** - Add docstrings

## Example: Email Task

```python
@task(max_retries=3, timeout_seconds=10)
def send_password_reset_email(
    user_id: int,
    email: str,
    reset_token: str
) -> bool:
    """
    Send password reset email.

    Will retry up to 3 times if SMTP fails.
    Must complete within 10 seconds.
    """
    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(f"Reset: {reset_token}")
    msg["Subject"] = "Password Reset"
    msg["To"] = email

    smtp = smtplib.SMTP("localhost")
    smtp.send_message(msg)
    smtp.quit()

    return True
```

## Next Steps

- **[Task Submission](task-submission.md)** - How to queue tasks
- **[Running Workers](workers.md)** - Execute tasks
- **[Error Handling](error-handling.md)** - Handle failures
