from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy import Column, String, DateTime, Integer, JSON, Text, create_engine
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Task(Base):
    __tablename__ = "tasks"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    name = Column(String, nullable=False, index=True)
    state = Column(String, nullable=False, index=True)
    scheduled_at = Column(DateTime, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False)
    args = Column(JSON, nullable=False, default={})
    kwargs = Column(JSON, nullable=False, default={})
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False)
    next_retry_at = Column(DateTime, nullable=True)
    worker_id = Column(String, nullable=True)
    locked_until = Column(DateTime, nullable=True, index=True)
    timeout_seconds = Column(Integer, nullable=True)
    priority = Column(Integer, nullable=False, default=0, index=True)
    tags = Column(JSON, nullable=False, default={})


# Pydantic models for API responses
class TaskResponse(BaseModel):
    id: UUID
    name: str
    state: str
    scheduled_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    args: dict
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
