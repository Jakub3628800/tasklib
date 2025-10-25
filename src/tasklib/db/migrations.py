"""Database migrations for TaskLib.

This module handles database schema creation and migrations.
Currently uses SQLAlchemy's metadata.create_all() for schema management.
Future versions can integrate with Alembic for more sophisticated migrations.
"""

from sqlmodel import Session, create_engine

from .models import Task


def init_database(database_url: str) -> None:
    """Initialize database schema.

    Creates all tables defined in the ORM models if they don't exist.

    Args:
        database_url: PostgreSQL connection URL

    Example:
        init_database("postgresql+psycopg://user:pass@localhost/dbname")
    """
    engine = create_engine(database_url, echo=False)
    Task.metadata.create_all(engine)


def create_session(database_url: str) -> Session:
    """Create a new database session.

    Args:
        database_url: PostgreSQL connection URL

    Returns:
        SQLModel Session for database operations
    """
    engine = create_engine(database_url, echo=False)
    return Session(engine)
