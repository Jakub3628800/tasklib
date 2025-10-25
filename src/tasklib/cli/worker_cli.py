"""TaskLib worker command."""

import asyncio
import logging
import sys
from typing import Optional

import click

from tasklib import Config, init, TaskWorker

from .main import import_task_modules, load_config_file, main

logger = logging.getLogger("tasklib")


@main.command()
@click.option(
    "--db-url",
    envvar="DATABASE_URL",
    help="PostgreSQL database URL",
    metavar="URL",
)
@click.option(
    "--config",
    type=click.Path(exists=True),
    help="Path to tasklib.yaml config file",
    metavar="PATH",
)
@click.option(
    "--task-module",
    multiple=True,
    help="Task module to import (can be used multiple times)",
    metavar="MODULE",
)
@click.option(
    "--worker-id",
    default=None,
    help="Worker ID (auto-generated if not provided)",
    metavar="ID",
)
@click.option(
    "--concurrency",
    type=int,
    default=None,
    help="Number of concurrent tasks to execute",
    metavar="N",
)
@click.option(
    "--poll-interval",
    type=float,
    default=None,
    help="Poll interval in seconds",
    metavar="SECONDS",
)
@click.option(
    "--max-retries",
    type=int,
    default=None,
    help="Default max retries for tasks",
    metavar="N",
)
@click.option(
    "--base-retry-delay",
    type=float,
    default=None,
    help="Base retry delay in seconds",
    metavar="SECONDS",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    default="INFO",
    help="Logging level",
)
def worker(
    db_url: Optional[str],
    config: Optional[str],
    task_module: tuple[str, ...],
    worker_id: Optional[str],
    concurrency: Optional[int],
    poll_interval: Optional[float],
    max_retries: Optional[int],
    base_retry_delay: Optional[float],
    log_level: str,
) -> None:
    """Run TaskLib worker.

    Configuration priority: CLI flags > config file > environment variables > defaults.
    """
    logging.getLogger("tasklib").setLevel(log_level)

    config_data: dict = {}
    if config:
        config_data = load_config_file(config)
        logger.info(f"Loaded config from {config}")

    final_db_url = db_url or config_data.get("database", {}).get("url")
    if not final_db_url:
        raise click.ClickException("DATABASE_URL not provided. Use --db-url flag or DATABASE_URL env var")

    task_modules = list(task_module)
    if not task_modules and config:
        task_modules = config_data.get("tasks", {}).get("modules", [])

    if not task_modules:
        raise click.ClickException(
            "No task modules provided. Use --task-module to specify at least one module.\n"
            "Example: tasklib worker --db-url postgresql+psycopg://... --task-module myapp.tasks"
        )

    logger.info(f"Importing task modules: {', '.join(task_modules)}")
    import_task_modules(task_modules)

    # Build Config with only Config-specific parameters
    config_kwargs: dict = {
        "database_url": final_db_url,
    }
    if worker_id:
        config_kwargs["worker_id"] = worker_id
    elif "worker" in config_data and "id" in config_data["worker"]:
        config_kwargs["worker_id"] = config_data["worker"]["id"]

    if max_retries is not None:
        config_kwargs["max_retries"] = max_retries
    elif "retry" in config_data and "max_retries" in config_data["retry"]:
        config_kwargs["max_retries"] = config_data["retry"]["max_retries"]

    if base_retry_delay is not None:
        config_kwargs["base_retry_delay_seconds"] = base_retry_delay
    elif "retry" in config_data and "base_delay_seconds" in config_data["retry"]:
        config_kwargs["base_retry_delay_seconds"] = config_data["retry"]["base_delay_seconds"]

    try:
        cfg = Config(**config_kwargs)
    except Exception as e:
        raise click.ClickException(f"Invalid configuration: {e}")

    # Worker-specific parameters
    worker_concurrency = concurrency or (config_data.get("worker", {}).get("concurrency") if config else None) or 1
    worker_poll_interval = (
        poll_interval or (config_data.get("worker", {}).get("poll_interval_seconds") if config else None) or 1.0
    )

    logger.info("Starting TaskLib worker...")
    logger.info(f"  Worker ID: {cfg.worker_id}")
    logger.info(f"  Concurrency: {worker_concurrency}")
    logger.info(f"  Poll interval: {worker_poll_interval}s")
    logger.info(f"  Task modules: {', '.join(task_modules)}")

    asyncio.run(_run_worker(cfg, worker_concurrency, worker_poll_interval))


async def _run_worker(config: Config, concurrency: int, poll_interval: float) -> None:
    """Initialize and run the worker."""
    try:
        init(config)  # init() is not async
        worker = TaskWorker(config, concurrency=concurrency, poll_interval_seconds=poll_interval)
        await worker.run()
    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        sys.exit(1)
