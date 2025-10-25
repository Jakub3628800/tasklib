"""Core tasklib functionality: task decorator and submit_task."""

import inspect
from datetime import datetime, timedelta
from typing import Any, Callable, Optional
from uuid import UUID

from pydantic import ValidationError, create_model
from sqlmodel import Session, create_engine, select

from .config import Config
from .db import Task
from .exceptions import TaskAlreadyRegistered, TaskExecutionError, TaskNotFound

_task_registry: dict[str, tuple[Callable, dict]] = {}
_config: Optional[Config] = None
_engine: Optional[object] = None


def init(config: Config) -> None:
    """Initialize tasklib with configuration."""
    global _config, _engine

    _config = config
    _engine = create_engine(config.database_url, echo=False)
    Task.metadata.create_all(_engine)


def task(
    func: Optional[Callable] = None,
    *,
    max_retries: Optional[int] = None,
    timeout_seconds: Optional[int] = None,
) -> Callable:
    """
    Decorator to register a task.

    Args:
        func: The function to register
        max_retries: Max retries for this task (overrides config default)
        timeout_seconds: Timeout for execution (seconds)

    Example:
        @task
        def send_email(to: str, subject: str) -> bool:
            ...

        @task(max_retries=5, timeout_seconds=30)
        def process_image(image_path: str) -> str:
            ...
    """

    def decorator(f: Callable) -> Callable:
        if f.__name__ in _task_registry:
            raise TaskAlreadyRegistered(f"Task '{f.__name__}' already registered")

        sig = inspect.signature(f)
        fields: dict[str, Any] = {}

        for param_name, param in sig.parameters.items():
            if param.annotation == inspect.Parameter.empty:
                fields[param_name] = (Any, ...)
            else:
                if param.default == inspect.Parameter.empty:
                    fields[param_name] = (param.annotation, ...)
                else:
                    fields[param_name] = (param.annotation, param.default)

        params_model = create_model(f"{f.__name__}Params", **fields)

        _task_registry[f.__name__] = (
            f,
            {
                "max_retries": max_retries,
                "timeout_seconds": timeout_seconds,
                "signature": sig,
                "params_model": params_model,
            },
        )

        return f

    if func is None:
        return decorator
    else:
        return decorator(func)


async def submit_task(
    func: Callable,
    *,
    delay_seconds: int = 0,
    max_retries: Optional[int] = None,
    timeout_seconds: Optional[int] = None,
    priority: int = 0,
    tags: Optional[dict] = None,
    **kwargs,
) -> UUID:
    """
    Submit a task to the queue.

    Args:
        func: The function to execute (must be decorated with @task)
        delay_seconds: Delay before execution (seconds)
        max_retries: Override task's max_retries
        timeout_seconds: Override task's timeout
        priority: Task priority (higher = process first)
        tags: Metadata tags for filtering
        **kwargs: Arguments to pass to the function

    Returns:
        Task UUID

    Example:
        task_id = await submit_task(send_email, delay_seconds=60, to="user@example.com", subject="Hi")
    """
    if _config is None or _engine is None:
        raise RuntimeError("tasklib not initialized. Call tasklib.init(config) first.")

    task_name = func.__name__
    if task_name not in _task_registry:
        raise TaskNotFound(f"Task '{task_name}' not registered. Use @task decorator.")

    registered_func, metadata = _task_registry[task_name]
    params_model = metadata["params_model"]

    try:
        validated_params = params_model(**kwargs)
        validated_kwargs = validated_params.model_dump()
    except ValidationError as e:
        raise TaskExecutionError(f"Invalid arguments for task '{task_name}': {e.json()}")

    final_max_retries = max_retries if max_retries is not None else metadata["max_retries"]
    if final_max_retries is None:
        final_max_retries = _config.max_retries

    final_timeout = timeout_seconds if timeout_seconds is not None else metadata["timeout_seconds"]
    if final_timeout is None:
        final_timeout = _config.default_task_timeout_seconds

    scheduled_at = datetime.utcnow() + timedelta(seconds=delay_seconds)

    db_task = Task(
        name=task_name,
        kwargs=validated_kwargs,
        args={},
        state="pending",
        scheduled_at=scheduled_at,
        max_retries=final_max_retries,
        timeout_seconds=final_timeout,
        priority=priority,
        tags=tags or {},
    )

    with Session(_engine) as session:
        session.add(db_task)
        session.commit()
        session.refresh(db_task)
        task_id = db_task.id

    return task_id


def get_task(task_id: UUID) -> Optional[Task]:
    """Get task by ID."""
    if _engine is None:
        raise RuntimeError("tasklib not initialized. Call tasklib.init(config) first.")

    with Session(_engine) as session:
        statement = select(Task).where(Task.id == task_id)
        return session.exec(statement).first()


def list_tasks(
    state: Optional[str] = None,
    name: Optional[str] = None,
    limit: int = 100,
) -> list[Task]:
    """
    List tasks with optional filtering.

    Args:
        state: Filter by state (pending, running, completed, failed)
        name: Filter by task name
        limit: Max results

    Returns:
        List of tasks
    """
    if _engine is None:
        raise RuntimeError("tasklib not initialized. Call tasklib.init(config) first.")

    with Session(_engine) as session:
        statement = select(Task)

        if state:
            statement = statement.where(Task.state == state)
        if name:
            statement = statement.where(Task.name == name)

        statement = statement.limit(limit)
        return session.exec(statement).all()


def get_registered_tasks() -> dict[str, tuple[Callable, dict]]:
    """Get all registered tasks."""
    return _task_registry.copy()


def is_pending(task: Task) -> bool:
    """Check if task is waiting to execute."""
    return task.state == "pending"


def is_running(task: Task) -> bool:
    """Check if task is currently executing."""
    return task.state == "running"


def is_completed(task: Task) -> bool:
    """Check if task completed successfully."""
    return task.state == "completed"


def is_failed(task: Task) -> bool:
    """Check if task failed (permanently or temporarily)."""
    return task.state == "failed"


def has_result(task: Task) -> bool:
    """Check if task has a result value."""
    return task.result is not None


def has_error(task: Task) -> bool:
    """Check if task has an error."""
    return task.error is not None


def is_terminal(task: Task) -> bool:
    """Check if task is in a terminal state (cannot change anymore)."""
    if task.state == "completed":
        return True
    return task.state == "failed" and task.retry_count >= task.max_retries
