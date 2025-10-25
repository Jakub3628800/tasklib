"""Custom exceptions for tasklib."""


class TaskLibError(Exception):
    """Base exception for tasklib."""


class TaskNotFound(TaskLibError):
    """Task not found in database."""


class TaskAlreadyRegistered(TaskLibError):
    """Task already registered with that name."""


class TaskExecutionError(TaskLibError):
    """Error during task execution."""


class TaskTimeoutError(TaskLibError):
    """Task execution exceeded timeout."""


class TaskLockError(TaskLibError):
    """Error acquiring task lock."""
