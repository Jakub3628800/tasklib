"""Run a tasklib worker to execute tasks from the queue."""

import asyncio
import logging

from tasklib import TaskWorker, Config

# Import tasks so they're registered

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def main():
    """Run worker."""
    db_url = "postgresql://postgres:postgres@localhost:5432/tasklib_test"

    config = Config(
        database_url=db_url,
        max_retries=3,
        base_retry_delay_seconds=1.0,
        lock_timeout_seconds=5,
        worker_id="worker-1",  # Give worker a name
    )

    worker = TaskWorker(config, concurrency=4, poll_interval_seconds=1.0)

    print("Starting worker... (Ctrl+C to stop)")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
