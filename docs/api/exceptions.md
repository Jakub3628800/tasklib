# Exceptions Reference

TaskLib exception classes.

```python
from tasklib import TaskLibError
```

## Exception Hierarchy

```
TaskLibError
├── TaskNotFound
├── TaskAlreadyRegistered
├── TaskExecutionError
├── TaskTimeoutError
└── TaskLockError
```

## Usage

```python
try:
    await tasklib.submit_task(unregistered_func)
except tasklib.TaskLibError:
    print("Error submitting task")
```

See [Error Handling](../guides/error-handling.md) for patterns.
