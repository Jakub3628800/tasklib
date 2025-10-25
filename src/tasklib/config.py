"""Configuration for tasklib."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """TaskLib configuration."""

    database_url: str
    """PostgreSQL connection URL (psycopg format)."""

    max_retries: int = 3
    """Default max retries for tasks."""

    base_retry_delay_seconds: float = 5.0
    """Base delay for exponential backoff (5 seconds)."""

    retry_backoff_multiplier: float = 2.0
    """Exponential backoff multiplier (5s -> 10s -> 20s -> ...)."""

    lock_timeout_seconds: int = 600
    """How long a worker can lock a task before it's considered dead (10 minutes)."""

    default_task_timeout_seconds: Optional[int] = None
    """Default timeout for task execution in seconds (None = no timeout)."""

    worker_id: Optional[str] = None
    """Worker ID (auto-generated if not set). Used for locking."""
