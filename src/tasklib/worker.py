"""Task worker implementation."""

import asyncio
import logging
import traceback
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

from sqlmodel import Session, create_engine, select

from .config import Config
from .core import _task_registry
from .db import Task
from .exceptions import TaskExecutionError, TaskTimeoutError

logger = logging.getLogger(__name__)


class TaskWorker:
    """
    Simple task worker that pulls and executes tasks from the queue.

    Example:
        config = Config(database_url="postgresql://...")
        worker = TaskWorker(config, concurrency=4)
        await worker.run()
    """

    def __init__(
        self,
        config: Config,
        concurrency: int = 1,
        poll_interval_seconds: float = 1.0,
    ):
        """
        Initialize worker.

        Args:
            config: TaskLib configuration
            concurrency: Number of concurrent tasks to execute
            poll_interval_seconds: How often to poll for new tasks (seconds)
        """
        self.config = config
        self.concurrency = concurrency
        self.poll_interval_seconds = poll_interval_seconds
        self.worker_id = config.worker_id or str(uuid.uuid4())
        self.engine = create_engine(config.database_url, echo=False)

        Task.metadata.create_all(self.engine)

        self._running_tasks: set[asyncio.Task] = set()
        self._shutdown: bool = False

    async def run(self) -> None:
        """Run the worker (blocks until shutdown)."""
        logger.info(f"Starting TaskWorker {self.worker_id} with concurrency={self.concurrency}")

        try:
            while not self._shutdown:
                for _ in range(self.concurrency - len(self._running_tasks)):
                    task = self._try_acquire_task()
                    if task is None:
                        break

                    coro = self._execute_task(task)
                    async_task = asyncio.create_task(coro)
                    self._running_tasks.add(async_task)
                    async_task.add_done_callback(lambda t: self._running_tasks.discard(t))

                await asyncio.sleep(self.poll_interval_seconds)

        except KeyboardInterrupt:
            logger.info("Received interrupt, shutting down...")
        finally:
            await self.shutdown()

    def _try_acquire_task(self) -> Optional[Task]:
        """Try to acquire and lock a task for execution using PostgreSQL SELECT FOR UPDATE."""
        try:
            with Session(self.engine) as session:  # pyrefly: ignore
                now = datetime.utcnow()
                statement = (
                    select(Task)
                    .where(Task.state.in_(["pending", "failed"]))  # pyrefly: ignore
                    .where(Task.scheduled_at <= now)
                    .where((Task.locked_until.is_(None)) | (Task.locked_until < now))  # pyrefly: ignore
                    .order_by(Task.priority.desc(), Task.created_at.asc())  # pyrefly: ignore
                    .limit(1)
                    .with_for_update()
                )

                task = session.exec(statement).first()  # pyrefly: ignore
                if task is None:
                    return None

                lock_until = now + timedelta(seconds=self.config.lock_timeout_seconds)
                task.state = "running"
                task.worker_id = self.worker_id
                task.locked_until = lock_until
                task.started_at = now
                session.add(task)  # pyrefly: ignore
                session.commit()  # pyrefly: ignore
                session.refresh(task)  # pyrefly: ignore

                return task

        except Exception as e:
            logger.error(f"Error acquiring task: {e}")
            return None

    async def _execute_task(self, task: Task) -> None:
        """Execute a single task."""
        try:
            if task.name not in _task_registry:
                raise TaskExecutionError(f"Task '{task.name}' not registered")

            func, _ = _task_registry[task.name]
            kwargs = task.kwargs or {}

            logger.info(f"Executing task {task.id} ({task.name})")

            try:
                if task.timeout_seconds:
                    result = await asyncio.wait_for(
                        self._run_sync_in_executor(func, kwargs),
                        timeout=task.timeout_seconds,
                    )
                else:
                    result = await self._run_sync_in_executor(func, kwargs)

                self._mark_completed(task, result)
                logger.info(f"Task {task.id} completed successfully")

            except asyncio.TimeoutError:
                raise TaskTimeoutError(f"Task {task.id} exceeded timeout of {task.timeout_seconds}s")

        except Exception as e:
            self._handle_failure(task, e)

    async def _run_sync_in_executor(self, func: Callable, kwargs: dict) -> object:
        """Run a sync function in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(**kwargs))  # pyrefly: ignore

    def _mark_completed(self, task: Task, result: Any) -> None:
        """Mark task as completed."""
        with Session(self.engine) as session:  # pyrefly: ignore
            db_task = session.get(Task, task.id)  # pyrefly: ignore
            if db_task:
                db_task.state = "completed"
                db_task.result = {"value": result} if result is not None else None
                db_task.completed_at = datetime.utcnow()
                db_task.locked_until = None
                db_task.worker_id = None
                session.add(db_task)  # pyrefly: ignore
                session.commit()  # pyrefly: ignore

    def _handle_failure(self, task: Task, error: Exception) -> None:
        """Handle task failure with retry logic."""
        with Session(self.engine) as session:  # pyrefly: ignore
            db_task = session.get(Task, task.id)  # pyrefly: ignore
            if not db_task:
                return

            error_msg = f"{error.__class__.__name__}: {str(error)}\n{traceback.format_exc()}"

            if db_task.retry_count < db_task.max_retries:
                retry_count = db_task.retry_count + 1
                delay = self.config.base_retry_delay_seconds * (
                    self.config.retry_backoff_multiplier ** (retry_count - 1)
                )
                next_retry = datetime.utcnow() + timedelta(seconds=delay)

                db_task.state = "failed"
                db_task.retry_count = retry_count
                db_task.next_retry_at = next_retry
                db_task.error = error_msg
                db_task.locked_until = None
                db_task.worker_id = None

                logger.warning(
                    f"Task {task.id} failed (attempt {retry_count}/{db_task.max_retries}). "
                    f"Retrying in {delay:.1f}s. Error: {error}"
                )
            else:
                db_task.state = "failed"
                db_task.error = error_msg
                db_task.completed_at = datetime.utcnow()
                db_task.locked_until = None
                db_task.worker_id = None

                logger.error(f"Task {task.id} failed permanently. Error: {error}")

            session.add(db_task)  # pyrefly: ignore
            session.commit()  # pyrefly: ignore

    async def shutdown(self) -> None:
        """Graceful shutdown."""
        self._shutdown = True
        logger.info("Waiting for running tasks to complete...")

        if self._running_tasks:
            await asyncio.gather(*self._running_tasks, return_exceptions=True)

        logger.info("Worker shutdown complete")
