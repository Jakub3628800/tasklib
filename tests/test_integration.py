"""Integration tests for tasklib with real PostgreSQL."""

import asyncio
import os
import time
from uuid import UUID

import pytest

import tasklib


# Use PostgreSQL from docker-compose (or fallback to default)
DB_URL = os.getenv("DATABASE_URL", "postgresql://tasklib:tasklib_pass@localhost:5432/tasklib")


@pytest.fixture
def config():
    """Create config for integration tests."""
    return tasklib.Config(
        database_url=DB_URL,
        max_retries=2,
        base_retry_delay_seconds=0.1,
        lock_timeout_seconds=5,
    )


@pytest.fixture
def init_db(config):
    """Initialize database for tests."""
    tasklib.init(config)
    # Clear any existing tasks
    from sqlmodel import Session, delete, create_engine
    from tasklib.models import Task

    engine = create_engine(DB_URL)
    with Session(engine) as session:
        session.exec(delete(Task))
        session.commit()

    yield config

    # Cleanup
    with Session(engine) as session:
        session.exec(delete(Task))
        session.commit()


class TestTaskSubmissionAndExecution:
    """Test submitting and executing real tasks."""

    @pytest.mark.asyncio
    async def test_submit_and_execute_simple_task(self, init_db, config):
        """Test basic task submission and execution."""

        @tasklib.task
        def add(a: int, b: int) -> int:
            return a + b

        # Submit task
        task_id = await tasklib.submit_task(add, a=5, b=3)
        assert isinstance(task_id, UUID)

        # Verify it's in DB as pending
        task = tasklib.get_task(task_id)
        assert task is not None
        assert tasklib.is_pending(task)
        assert task.name == "add"
        assert task.kwargs == {"a": 5, "b": 3}

        # Run worker to execute
        worker = tasklib.TaskWorker(config, concurrency=1, poll_interval_seconds=0.1)

        # Run for 1 second (enough to execute one task)
        async def run_worker():
            try:
                await asyncio.wait_for(worker.run(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        await run_worker()

        # Verify task completed
        completed_task = tasklib.get_task(task_id)
        assert tasklib.is_completed(completed_task)
        assert completed_task.result == {"value": 8}

    @pytest.mark.asyncio
    async def test_delayed_task_execution(self, init_db, config):
        """Test that delayed tasks don't execute immediately."""

        @tasklib.task
        def hello(name: str) -> str:
            return f"Hello {name}!"

        # Submit with 10 second delay
        task_id = await tasklib.submit_task(hello, delay_seconds=10, name="Alice")

        # Check immediately - should still be pending
        task = tasklib.get_task(task_id)
        assert tasklib.is_pending(task)

        # scheduled_at should be in the future
        from datetime import datetime

        assert task.scheduled_at > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_task_with_custom_config(self, init_db, config):
        """Test task with custom retry and timeout."""

        @tasklib.task(max_retries=5, timeout_seconds=30)
        def custom_task() -> str:
            return "ok"

        task_id = await tasklib.submit_task(custom_task)
        task = tasklib.get_task(task_id)

        assert task.max_retries == 5
        assert task.timeout_seconds == 30

    @pytest.mark.asyncio
    async def test_task_with_priority(self, init_db, config):
        """Test task priority ordering."""

        @tasklib.task
        def task_func() -> str:
            return "ok"

        # Submit tasks with different priorities
        low_priority = await tasklib.submit_task(task_func, priority=1)
        high_priority = await tasklib.submit_task(task_func, priority=100)

        # List tasks - high priority should be first
        tasks = tasklib.list_tasks()
        task_ids = [t.id for t in tasks]
        high_idx = task_ids.index(high_priority)
        low_idx = task_ids.index(low_priority)
        assert high_idx < low_idx


class TestTaskFailureAndRetry:
    """Test failure handling and retries."""

    @pytest.mark.asyncio
    async def test_task_failure_with_retry(self, init_db, config):
        """Test that failed tasks are retried."""

        call_count = 0

        @tasklib.task(max_retries=2)
        def flaky_task() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("First attempt fails")
            return "success"

        # Submit task
        task_id = await tasklib.submit_task(flaky_task)

        # Run worker - should execute and fail
        worker = tasklib.TaskWorker(config, concurrency=1, poll_interval_seconds=0.1)

        async def run_worker(duration=2.0):
            try:
                await asyncio.wait_for(worker.run(), timeout=duration)
            except asyncio.TimeoutError:
                pass

        # First run - task fails but is marked for retry
        await run_worker(duration=1.0)

        task = tasklib.get_task(task_id)
        assert tasklib.is_failed(task)
        assert task.retry_count == 1
        assert task.next_retry_at is not None

        # Second run - wait for retry and retry
        await asyncio.sleep(0.2)  # Wait for retry time
        await run_worker(duration=1.0)

        # Should now be completed
        task = tasklib.get_task(task_id)
        assert tasklib.is_completed(task)
        assert task.result == {"value": "success"}

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, init_db, config):
        """Test that tasks fail permanently after max retries."""

        @tasklib.task(max_retries=1)
        def always_fails() -> str:
            raise RuntimeError("Always fails")

        task_id = await tasklib.submit_task(always_fails)

        worker = tasklib.TaskWorker(config, concurrency=1, poll_interval_seconds=0.1)

        async def run_worker(duration=1.0):
            try:
                await asyncio.wait_for(worker.run(), timeout=duration)
            except asyncio.TimeoutError:
                pass

        # Run until task is exhausted
        for _ in range(5):
            await run_worker(duration=0.5)
            await asyncio.sleep(0.2)

        task = tasklib.get_task(task_id)
        # Should be failed and max retries reached
        assert tasklib.is_failed(task)
        assert task.retry_count >= task.max_retries
        assert tasklib.is_terminal(task)
        assert tasklib.has_error(task)

    @pytest.mark.asyncio
    async def test_task_timeout(self, init_db, config):
        """Test that tasks timeout if they take too long."""

        @tasklib.task(timeout_seconds=1)
        def slow_task() -> str:
            time.sleep(5)  # Takes 5 seconds
            return "should not reach here"

        task_id = await tasklib.submit_task(slow_task)

        worker = tasklib.TaskWorker(config, concurrency=1, poll_interval_seconds=0.1)

        async def run_worker():
            try:
                await asyncio.wait_for(worker.run(), timeout=3.0)
            except asyncio.TimeoutError:
                pass

        await run_worker()

        task = tasklib.get_task(task_id)
        # Should be failed due to timeout
        assert tasklib.is_failed(task)
        assert "timeout" in task.error.lower()


class TestPydanticValidation:
    """Test Pydantic validation of task parameters."""

    @pytest.mark.asyncio
    async def test_type_validation(self, init_db, config):
        """Test that Pydantic validates types."""

        @tasklib.task
        def typed_task(x: int, name: str) -> str:
            return f"{x}:{name}"

        # Valid submission
        task_id = await tasklib.submit_task(typed_task, x=5, name="test")
        task = tasklib.get_task(task_id)
        assert task.kwargs == {"x": 5, "name": "test"}

    @pytest.mark.asyncio
    async def test_invalid_type_rejected(self, init_db, config):
        """Test that invalid types are rejected at submit time."""

        @tasklib.task
        def typed_task(x: int) -> int:
            return x * 2

        # This should raise validation error - string instead of int
        with pytest.raises(tasklib.TaskLibError):
            await tasklib.submit_task(typed_task, x="not an int")

    @pytest.mark.asyncio
    async def test_missing_required_param(self, init_db, config):
        """Test that missing required parameters are rejected."""

        @tasklib.task
        def required_param_task(x: int, y: int) -> int:
            return x + y

        # Missing y parameter
        with pytest.raises(tasklib.TaskLibError):
            await tasklib.submit_task(required_param_task, x=5)

    @pytest.mark.asyncio
    async def test_optional_params(self, init_db, config):
        """Test optional parameters with defaults."""

        @tasklib.task
        def optional_param_task(x: int, y: int = 10) -> int:
            return x + y

        # Only x provided
        task_id = await tasklib.submit_task(optional_param_task, x=5)
        task = tasklib.get_task(task_id)
        assert task.kwargs == {"x": 5, "y": 10}


class TestMultiWorker:
    """Test behavior with multiple workers."""

    @pytest.mark.asyncio
    async def test_multiple_workers_same_task(self, init_db, config):
        """Test that multiple workers process tasks concurrently."""

        execution_times = []

        @tasklib.task
        def concurrent_task(n: int) -> int:
            execution_times.append(n)
            time.sleep(0.2)  # Simulate work
            return n * 2

        # Submit 4 tasks
        task_ids = []
        for i in range(4):
            task_id = await tasklib.submit_task(concurrent_task, n=i)
            task_ids.append(task_id)

        # Run 2 workers concurrently
        worker1 = tasklib.TaskWorker(config, concurrency=2, poll_interval_seconds=0.1)
        worker2 = tasklib.TaskWorker(config, concurrency=2, poll_interval_seconds=0.1)

        async def run_worker(worker):
            try:
                await asyncio.wait_for(worker.run(), timeout=2.0)
            except asyncio.TimeoutError:
                pass

        # Run both workers
        await asyncio.gather(run_worker(worker1), run_worker(worker2))

        # All tasks should be completed
        for task_id in task_ids:
            task = tasklib.get_task(task_id)
            assert tasklib.is_completed(task)


class TestTaskMonitoring:
    """Test task listing and filtering."""

    @pytest.mark.asyncio
    async def test_list_by_state(self, init_db, config):
        """Test listing tasks by state."""

        @tasklib.task
        def simple() -> str:
            return "ok"

        # Submit a few tasks
        for _ in range(3):
            await tasklib.submit_task(simple)

        # All should be pending
        pending_tasks = tasklib.list_tasks(state="pending")
        assert len(pending_tasks) >= 3

    @pytest.mark.asyncio
    async def test_list_by_name(self, init_db, config):
        """Test listing tasks by name."""

        @tasklib.task
        def task_a() -> str:
            return "a"

        @tasklib.task
        def task_b() -> str:
            return "b"

        await tasklib.submit_task(task_a)
        await tasklib.submit_task(task_b)

        # Filter by name
        a_tasks = tasklib.list_tasks(name="task_a")
        b_tasks = tasklib.list_tasks(name="task_b")

        assert all(t.name == "task_a" for t in a_tasks)
        assert all(t.name == "task_b" for t in b_tasks)

    @pytest.mark.asyncio
    async def test_result_helpers(self, init_db, config):
        """Test result state helper functions."""

        @tasklib.task
        def result_helper_task() -> str:
            return "done"

        task_id = await tasklib.submit_task(result_helper_task)
        task = tasklib.get_task(task_id)

        assert tasklib.is_pending(task)
        assert not tasklib.is_completed(task)
        assert not tasklib.has_result(task)
        assert not tasklib.has_error(task)

        # Execute
        worker = tasklib.TaskWorker(config, concurrency=1, poll_interval_seconds=0.1)

        async def run_worker():
            try:
                await asyncio.wait_for(worker.run(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        await run_worker()

        # Check completed state
        task = tasklib.get_task(task_id)
        assert tasklib.is_completed(task)
        assert tasklib.has_result(task)
        assert not tasklib.has_error(task)


class TestRegistration:
    """Test task registration."""

    def test_register_unregistered_task_fails(self, init_db):
        """Test that unregistered tasks can't be submitted."""

        async def unregistered_task() -> str:
            return "nope"

        with pytest.raises(tasklib.TaskLibError):
            asyncio.run(tasklib.submit_task(unregistered_task))

    def test_duplicate_registration_fails(self, init_db):
        """Test that duplicate task names can't be registered."""

        @tasklib.task
        def duplicate() -> str:
            return "first"

        with pytest.raises(tasklib.TaskLibError):

            @tasklib.task
            def duplicate() -> str:
                return "second"
