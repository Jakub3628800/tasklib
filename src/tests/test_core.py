"""Tests for tasklib core functionality."""

import pytest
from uuid import UUID

import tasklib
from tasklib import Config, task


@pytest.fixture
def config():
    """Create test config."""
    return Config(
        database_url="sqlite:///:memory:",  # In-memory for testing
        max_retries=2,
        base_retry_delay_seconds=0.1,
    )


@pytest.fixture(autouse=True)
def clear_task_registry():
    """Clear task registry before each test."""
    from tasklib.core import _task_registry

    _task_registry.clear()
    yield
    _task_registry.clear()


@pytest.fixture
def init_tasklib(config):
    """Initialize tasklib for testing."""
    tasklib.init(config)
    yield
    # Cleanup would go here


class TestTaskDecorator:
    """Test task decorator."""

    @pytest.mark.unit
    def test_register_task(self, init_tasklib):
        """Test registering a task."""

        @task
        def my_task(x: int) -> int:
            return x * 2

        registered = tasklib.get_registered_tasks()
        assert "my_task" in registered

    @pytest.mark.unit
    def test_duplicate_task_name(self, init_tasklib):
        """Test that duplicate task names raise error."""

        @task
        def duplicate():
            pass

        with pytest.raises(tasklib.TaskLibError):

            @task
            def duplicate():
                pass

    @pytest.mark.unit
    def test_task_with_options(self, init_tasklib):
        """Test task with custom options."""

        @task(max_retries=5, timeout_seconds=30)
        def my_task():
            pass

        registered = tasklib.get_registered_tasks()
        func, meta = registered["my_task"]
        assert meta["max_retries"] == 5
        assert meta["timeout_seconds"] == 30


class TestSubmitTask:
    """Test task submission."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_submit_task(self, init_tasklib):
        """Test submitting a task."""

        @task
        def simple_task(x: int) -> int:
            return x * 2

        task_id = await tasklib.submit_task(simple_task, x=5)

        assert isinstance(task_id, UUID)

        # Verify task was created
        t = tasklib.get_task(task_id)
        assert t is not None
        assert t.name == "simple_task"
        assert t.kwargs == {"x": 5}
        assert t.state == "pending"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_submit_with_delay(self, init_tasklib):
        """Test submitting task with delay."""

        @task
        def delayed_task():
            pass

        task_id = await tasklib.submit_task(delayed_task, delay_seconds=10)
        t = tasklib.get_task(task_id)
        assert t is not None

        # Verify scheduled_at is in the future
        from datetime import datetime

        assert t.scheduled_at > datetime.utcnow()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_submit_unregistered_task(self, init_tasklib):
        """Test submitting unregistered task raises error."""

        def unregistered():
            pass

        with pytest.raises(tasklib.TaskLibError):
            await tasklib.submit_task(unregistered)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_submit_with_invalid_args(self, init_tasklib):
        """Test submitting task with invalid arguments."""

        @task
        def typed_task(x: int, y: str) -> str:
            return f"{x}:{y}"

        # Missing required argument
        with pytest.raises(tasklib.TaskLibError):
            await tasklib.submit_task(typed_task, x=5)


class TestTaskListing:
    """Test task listing and filtering."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_tasks(self, init_tasklib):
        """Test listing tasks."""

        @task
        def task1():
            pass

        @task
        def task2():
            pass

        # Submit some tasks
        await tasklib.submit_task(task1)
        await tasklib.submit_task(task2)

        tasks = tasklib.list_tasks()
        assert len(tasks) >= 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_by_state(self, init_tasklib):
        """Test listing tasks by state."""

        @task
        def my_task():
            pass

        task_id = await tasklib.submit_task(my_task)

        # Check pending state
        pending = tasklib.list_tasks(state="pending")
        assert any(t.id == task_id for t in pending)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_by_name(self, init_tasklib):
        """Test listing tasks by name."""

        @task
        def my_named_task():
            pass

        await tasklib.submit_task(my_named_task)

        tasks = tasklib.list_tasks(name="my_named_task")
        assert all(t.name == "my_named_task" for t in tasks)


class TestConfiguration:
    """Test configuration."""

    @pytest.mark.unit
    def test_config_creation(self):
        """Test creating config."""
        config = Config(
            database_url="postgresql://localhost/test",
            max_retries=5,
            base_retry_delay_seconds=2.0,
        )

        assert config.database_url == "postgresql://localhost/test"
        assert config.max_retries == 5
        assert config.base_retry_delay_seconds == 2.0

    @pytest.mark.unit
    def test_config_defaults(self):
        """Test config defaults."""
        config = Config(database_url="postgresql://localhost/test")

        assert config.max_retries == 3
        assert config.base_retry_delay_seconds == 5.0
        assert config.retry_backoff_multiplier == 2.0
        assert config.lock_timeout_seconds == 600
