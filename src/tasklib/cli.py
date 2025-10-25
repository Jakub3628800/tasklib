"""TaskLib worker CLI."""

import asyncio
import logging
import signal
import sys
from typing import Optional

import click
import yaml

from tasklib import Config, init, TaskWorker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("tasklib")


class WorkerContext:
    """Context for managing worker lifecycle."""

    def __init__(self, worker: TaskWorker):
        self.worker = worker
        self.running = True

    async def run(self) -> None:
        """Run worker with graceful shutdown support."""
        loop = asyncio.get_event_loop()

        def handle_shutdown(signum: int, frame: object) -> None:
            logger.info("Received shutdown signal, gracefully stopping...")
            self.running = False

        loop.add_signal_handler(signal.SIGTERM, handle_shutdown)
        loop.add_signal_handler(signal.SIGINT, handle_shutdown)

        try:
            await self.worker.run()
        except KeyboardInterrupt:
            logger.info("Interrupted, shutting down...")


def load_config_file(config_path: str) -> dict:
    """Load YAML configuration file."""
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            return config or {}
    except FileNotFoundError as e:
        raise click.ClickException(f"Config file not found: {config_path}") from e
    except yaml.YAMLError as e:
        raise click.ClickException(f"Invalid YAML in config file: {e}") from e


def import_task_modules(modules: list[str]) -> None:
    """Import task modules to register tasks."""
    for module_name in modules:
        try:
            __import__(module_name)
            logger.debug(f"Imported task module: {module_name}")
        except ImportError as e:
            raise click.ClickException(f"Failed to import task module '{module_name}': {e}")


@click.command()
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
@click.version_option()
def main(
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

    if task_modules:
        logger.info(f"Importing task modules: {', '.join(task_modules)}")
        import_task_modules(task_modules)
    else:
        logger.warning("No task modules imported. Tasks may not be registered. Use --task-module to specify modules.")

    config_kwargs: dict = {
        "database_url": final_db_url,
    }
    if worker_id:
        config_kwargs["worker_id"] = worker_id
    elif "worker" in config_data and "id" in config_data["worker"]:
        config_kwargs["worker_id"] = config_data["worker"]["id"]

    if concurrency is not None:
        config_kwargs["concurrency"] = concurrency
    elif "worker" in config_data and "concurrency" in config_data["worker"]:
        config_kwargs["concurrency"] = config_data["worker"]["concurrency"]

    if poll_interval is not None:
        config_kwargs["poll_interval_seconds"] = poll_interval
    elif "worker" in config_data and "poll_interval_seconds" in config_data["worker"]:
        config_kwargs["poll_interval_seconds"] = config_data["worker"]["poll_interval_seconds"]

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

    logger.info("Starting TaskLib worker...")
    logger.info(f"  Worker ID: {cfg.worker_id}")
    logger.info(f"  Concurrency: {cfg.concurrency}")
    logger.info(f"  Poll interval: {cfg.poll_interval_seconds}s")

    asyncio.run(_run_worker(cfg))


async def _run_worker(config: Config) -> None:
    """Initialize and run the worker."""
    try:
        await init(config)
        worker = TaskWorker(config)
        await worker.run()
    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
