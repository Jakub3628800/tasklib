"""TaskLib init command."""

import logging
from typing import Optional

import click

from tasklib import Config, init

from .main import load_config_file, main

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
    "--host",
    default="localhost",
    help="PostgreSQL host",
    metavar="HOST",
)
@click.option(
    "--port",
    type=int,
    default=5432,
    help="PostgreSQL port",
    metavar="PORT",
)
@click.option(
    "--user",
    default="tasklib",
    help="PostgreSQL username",
    metavar="USER",
)
@click.option(
    "--password",
    default="tasklib_pass",
    help="PostgreSQL password",
    metavar="PASSWORD",
)
@click.option(
    "--database",
    default="tasklib",
    help="PostgreSQL database name",
    metavar="DATABASE",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force migration if tables exist",
)
def init_cmd(
    db_url: Optional[str],
    config: Optional[str],
    host: str,
    port: int,
    user: str,
    password: str,
    database: str,
    force: bool,
) -> None:
    """Initialize TaskLib database.

    Creates the tasks table if it doesn't exist.
    If table exists, asks for confirmation before proceeding.
    """
    config_data: dict = {}
    if config:
        config_data = load_config_file(config)
        logger.info(f"Loaded config from {config}")

    # Use provided db_url or build from components
    final_db_url = db_url or config_data.get("database", {}).get("url")
    if not final_db_url:
        final_db_url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"
        logger.info(f"Connecting to {host}:{port}/{database}")

    try:
        cfg = Config(database_url=final_db_url)
    except Exception as e:
        raise click.ClickException(f"Invalid configuration: {e}")

    # Check if tables already exist
    from sqlalchemy import inspect
    from sqlalchemy import create_engine as sa_create_engine

    try:
        engine = sa_create_engine(cfg.database_url, echo=False)
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if "tasks" in tables:
            if not force:
                click.secho("⚠️  The 'tasks' table already exists", fg="yellow")
                click.echo("Database is already initialized.")
                click.echo("To override and reinitialize, run: tasklib init --force")
                return
            logger.info("Reinitializing database (--force flag used)...")
        else:
            logger.info("Initializing TaskLib database...")

        init(cfg)
        click.secho("✅ Database initialized successfully", fg="green")
        click.echo(f"   Database: {database}")
        click.echo(f"   Host: {host}:{port}")
        click.echo("   Tables: tasks")

    except Exception as e:
        raise click.ClickException(f"Database error: {e}")
