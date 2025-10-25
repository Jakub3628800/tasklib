"""SQLModel schema for tasks."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Column, Field, JSON, SQLModel


class Task(SQLModel, table=True):
    """Task model stored in PostgreSQL."""

    __tablename__ = "tasks"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    name: str = Field(index=True)
    args: dict = Field(default_factory=dict, sa_column=Column(JSON))
    kwargs: dict = Field(default_factory=dict, sa_column=Column(JSON))

    state: str = Field(default="pending", index=True)
    result: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    error: Optional[str] = None

    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    next_retry_at: Optional[datetime] = Field(default=None, index=True)

    scheduled_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    worker_id: Optional[str] = None
    locked_until: Optional[datetime] = Field(default=None, index=True)

    timeout_seconds: Optional[int] = None
    priority: int = Field(default=0, index=True)
    tags: dict = Field(default_factory=dict, sa_column=Column(JSON))

    class Config:  # pyrefly: ignore
        """SQLModel config."""

        arbitrary_types_allowed = True
