"""TaskLib submit-task command."""

import asyncio
import logging
from typing import Optional

import click

from tasklib import Config, init

from .main import import_task_modules, load_config_file, main

logger = logging.getLogger("tasklib")


@main.command()
@click.argument("task_name")
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
    required=True,
    help="Task module to import (required)",
    metavar="MODULE",
)
@click.option(
    "--arg",
    multiple=True,
    help="Task argument as key=value (can be used multiple times)",
    metavar="KEY=VALUE",
)
@click.option(
    "--delay",
    type=int,
    default=0,
    help="Delay task execution by N seconds",
    metavar="SECONDS",
)
def submit_task_cmd(
    task_name: str,
    db_url: Optional[str],
    config: Optional[str],
    task_module: tuple[str, ...],
    arg: tuple[str, ...],
    delay: int,
) -> None:
    """Submit a task for execution.

    TASK_NAME should be the function name, e.g. 'hello' or 'add_numbers'

    Examples:
        tasklib submit-task hello --task-module tasklib.test_tasks
        tasklib submit-task add_numbers --task-module tasklib.test_tasks --arg a=5 --arg b=3
    """
    config_data: dict = {}
    if config:
        config_data = load_config_file(config)
        logger.info(f"Loaded config from {config}")

    final_db_url = db_url or config_data.get("database", {}).get("url")
    if not final_db_url:
        raise click.ClickException("DATABASE_URL not provided. Use --db-url flag or DATABASE_URL env var")

    task_modules = list(task_module)
    if task_modules:
        logger.info(f"Importing task modules: {', '.join(task_modules)}")
        import_task_modules(task_modules)
    else:
        raise click.ClickException("At least one task module required. Use --task-module to specify.")

    try:
        cfg = Config(database_url=final_db_url)
    except Exception as e:
        raise click.ClickException(f"Invalid configuration: {e}")

    kwargs = {}
    for arg_str in arg:
        if "=" not in arg_str:
            raise click.ClickException(f"Invalid argument format: {arg_str}. Use key=value")
        key, value = arg_str.split("=", 1)

        try:
            kwargs[key] = int(value)
        except ValueError:
            try:
                kwargs[key] = float(value)
            except ValueError:
                if value.lower() in ("true", "false"):
                    kwargs[key] = value.lower() == "true"
                else:
                    kwargs[key] = value

    async def submit():
        init(cfg)

        from tasklib import submit_task as submit_func
        from tasklib.core import _task_registry

        if task_name not in _task_registry:
            raise click.ClickException(
                f"Task '{task_name}' not found. Available tasks: {', '.join(_task_registry.keys()) or 'none'}"
            )

        func, _ = _task_registry[task_name]

        task_id = await submit_func(func, delay_seconds=delay, **kwargs)
        return task_id

    try:
        task_id = asyncio.run(submit())
        click.secho(f"Task submitted: {task_id}", fg="green")
        click.echo(f"   Task: {task_name}")
        if kwargs:
            click.echo(f"   Args: {kwargs}")
        if delay:
            click.echo(f"   Delay: {delay}s")
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Failed to submit task: {e}")
