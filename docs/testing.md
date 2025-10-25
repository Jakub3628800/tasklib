# Testing TaskLib

## Quick Start

### 1. Start PostgreSQL with Docker Compose

```bash
docker-compose up -d
```

This starts PostgreSQL on `localhost:5432` with:
- Username: `tasklib`
- Password: `tasklib_pass`
- Database: `tasklib`

### 2. Install Dependencies

```bash
uv sync --extra dev
```

### 3. Run Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run only unit tests
uv run pytest tests/test_core.py -v

# Run only integration tests (requires PostgreSQL)
uv run pytest tests/test_integration.py -v

# Run with logging
uv run pytest tests/ -v -s

# Run specific test
uv run pytest tests/test_integration.py::TestTaskSubmissionAndExecution::test_submit_and_execute_simple_task -v
```

### 4. Stop PostgreSQL

```bash
docker-compose down
```

## Test Structure

### Unit Tests (`tests/test_core.py`)

- ✅ Task registration (@task decorator)
- ✅ Argument validation
- ✅ Configuration defaults
- ✅ Exception handling
- ✅ No database required

**Run:** `uv run pytest tests/test_core.py`

### Integration Tests (`tests/test_integration.py`)

Full end-to-end tests with real PostgreSQL:

- ✅ Task submission and execution
- ✅ Delayed execution
- ✅ Task failures and retries with exponential backoff
- ✅ Max retries exceeded
- ✅ Task timeouts
- ✅ Pydantic validation
- ✅ Multi-worker concurrency
- ✅ Task monitoring and filtering
- ✅ Result state helpers

**Requirements:** PostgreSQL running (via docker-compose)
**Run:** `uv run pytest tests/test_integration.py`

## Key Integration Test Scenarios

### Basic Execution

```python
@tasklib.task
def add(a: int, b: int) -> int:
    return a + b

task_id = await tasklib.submit_task(add, a=5, b=3)
worker = tasklib.TaskWorker(config, concurrency=1)
await worker.run()  # Executes task

task = tasklib.get_task(task_id)
assert tasklib.is_completed(task)
assert task.result == {"value": 8}
```

### Failure and Retry

```python
@tasklib.task(max_retries=3)
def flaky_task() -> str:
    if some_condition:
        raise ValueError("Temporary failure")
    return "success"

# Task automatically retried with exponential backoff (5s, 10s, 20s)
```

### Timeout

```python
@tasklib.task(timeout_seconds=1)
def slow_task() -> str:
    time.sleep(5)  # Will timeout
    return "never"

# Task fails due to timeout, can be retried
```

### Validation

```python
@tasklib.task
def typed_task(x: int, name: str) -> str:
    return f"{x}:{name}"

# Valid
await tasklib.submit_task(typed_task, x=5, name="test")

# Invalid - rejected at submit time
with pytest.raises(tasklib.TaskLibError):
    await tasklib.submit_task(typed_task, x="not int")
```

## Debugging

### View PostgreSQL

```bash
# Connect to database
docker-compose exec postgres psql -U tasklib -d tasklib

# See task table
SELECT id, name, state, result, error FROM tasks;

# See pending tasks
SELECT id, name, scheduled_at FROM tasks WHERE state = 'pending';
```

### Enable Worker Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
worker = tasklib.TaskWorker(config)
await worker.run()
```

### Run Pytest with Stdout

```bash
uv run pytest tests/test_integration.py -v -s
```

## Troubleshooting

### "Connection refused" to PostgreSQL

```bash
# Ensure docker-compose is running
docker-compose ps

# Restart if needed
docker-compose down
docker-compose up -d
```

### "relation \"tasks\" does not exist"

- TaskLib should auto-create tables via SQLModel
- Verify DATABASE_URL is correct
- Check PostgreSQL is up: `docker-compose logs postgres`

### Tests hang

- Worker might be looping indefinitely
- Pytest timeout will kill it after 5 minutes by default
- Use `pytest --timeout=30` to limit

### Import errors

```bash
# Reinstall with dev dependencies
uv sync --extra dev

# Verify tasklib is importable
python -c "import tasklib; print(tasklib.__version__)"
```

## CI/CD

For CI environments (GitHub Actions, etc.):

```yaml
# .github/workflows/tests.yml
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: tasklib
          POSTGRES_PASSWORD: tasklib_pass
          POSTGRES_DB: tasklib
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install uv
      - run: uv sync --extra dev
      - run: uv run pytest tests/ -v
```

## Coverage

To measure test coverage:

```bash
# Install coverage
uv pip install pytest-cov

# Run with coverage
uv run pytest tests/ --cov=src/tasklib --cov-report=html

# View report
open htmlcov/index.html
```

## Performance Testing

To stress-test tasklib:

```python
@pytest.mark.asyncio
async def test_1000_tasks(init_db, config):
    """Submit 1000 tasks and execute them."""

    @tasklib.task
    def task_func(n: int) -> int:
        return n * 2

    # Submit 1000 tasks
    task_ids = []
    start = time.time()
    for i in range(1000):
        task_id = await tasklib.submit_task(task_func, n=i)
        task_ids.append(task_id)
    submit_time = time.time() - start
    print(f"Submitted 1000 tasks in {submit_time:.2f}s")

    # Execute all with 10 workers
    workers = [
        tasklib.TaskWorker(config, concurrency=4)
        for _ in range(10)
    ]

    async def run_workers():
        await asyncio.gather(*[w.run() for w in workers])

    start = time.time()
    try:
        await asyncio.wait_for(run_workers(), timeout=30)
    except asyncio.TimeoutError:
        pass
    exec_time = time.time() - start

    # Verify all completed
    completed = sum(
        1 for task_id in task_ids
        if tasklib.is_completed(tasklib.get_task(task_id))
    )
    print(f"Executed {completed}/1000 tasks in {exec_time:.2f}s")
```

## Test Maintenance

### Add New Test

1. Create test function in `test_integration.py` or `test_core.py`
2. Use `@pytest.mark.asyncio` for async tests
3. Use `init_db` fixture for database access
4. Run: `uv run pytest tests/test_<name>.py -v`

### Update Fixtures

- `config` - TaskLib configuration
- `init_db` - Initialize DB and clear tasks

---

**Last Updated:** 2025-10-25
