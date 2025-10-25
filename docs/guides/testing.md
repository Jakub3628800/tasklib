# Testing

How to test tasks with TaskLib.

## Unit Tests (No Database)

```python
import pytest
from tasklib import task

@task
def my_task(x: int) -> int:
    return x * 2

def test_task_definition():
    assert my_task(5) == 10
```

## Integration Tests (With Database)

```python
import pytest
import tasklib

@pytest.fixture
def init_db():
    config = tasklib.Config(database_url="postgresql://...")
    tasklib.init(config)
    yield config

@pytest.mark.asyncio
async def test_task_execution(init_db):
    task_id = await tasklib.submit_task(my_task, x=5)

    worker = tasklib.TaskWorker(init_db)
    # Run worker...

    task = tasklib.get_task(task_id)
    assert tasklib.is_completed(task)
```

See [Testing Guide](../../TEST_COVERAGE.md) for more examples.
