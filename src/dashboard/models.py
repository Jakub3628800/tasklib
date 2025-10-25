from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

# Import Task model from tasklib
from tasklib.db.models import Task


# Pydantic models for API responses
class TaskResponse(BaseModel):
    id: UUID
    name: str
    state: str
    scheduled_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    kwargs: dict
    result: Optional[dict]
    error: Optional[str]
    retry_count: int
    max_retries: int
    worker_id: Optional[str]
    priority: int
    tags: dict

    class Config:
        from_attributes = True


class TaskStats(BaseModel):
    total: int
    pending: int
    running: int
    completed: int
    failed: int
    failed_permanent: int


class WorkerStats(BaseModel):
    worker_id: str
    locked_tasks: int
    earliest_lock_expires: Optional[datetime]
