"""TaskLib CLI main entrypoint."""

import logging

import click
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("tasklib")


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


@click.group()
@click.version_option()
def main() -> None:
    """TaskLib: Simple, durable task queue for PostgreSQL."""
    pass


# Import commands to register them with the main group
from . import init_cli, submit_cli, worker_cli  # noqa: E402, F401
