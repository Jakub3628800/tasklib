"""TaskLib: Simple, durable task queue for PostgreSQL."""

from .config import Config
from .core import (
    get_registered_tasks,
    get_task,
    has_error,
    has_result,
    init,
    is_completed,
    is_failed,
    is_pending,
    is_running,
    is_terminal,
    list_tasks,
    submit_task,
    task,
)
from .exceptions import TaskLibError
from .worker import TaskWorker

__version__ = "0.1.0"
__all__ = [
    "Config",
    "init",
    "task",
    "submit_task",
    "get_task",
    "list_tasks",
    "get_registered_tasks",
    "is_pending",
    "is_running",
    "is_completed",
    "is_failed",
    "has_result",
    "has_error",
    "is_terminal",
    "TaskWorker",
    "TaskLibError",
]
