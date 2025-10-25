# Core API Reference

Main TaskLib API functions.

## Initialization

```python
from tasklib import Config, init

config = Config(database_url="postgresql://...")
init(config)
```

See [Configuration](configuration.md) for all options.

## Task Decorator

```python
from tasklib import task

@task
def my_task(param: str) -> str:
    return f"done: {param}"

@task(max_retries=5, timeout_seconds=30)
def advanced_task(param: str) -> str:
    return param
```

## Task Submission

```python
from tasklib import submit_task

task_id = await submit_task(
    my_task,
    param="hello",
    delay_seconds=60,
    priority=0,
    tags={},
)
```

## Task Monitoring

```python
from tasklib import get_task, list_tasks

task = get_task(task_id)
tasks = list_tasks(state="pending", name="my_task")
```

See [Configuration](configuration.md) for detailed API.
