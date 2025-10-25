"""Pytest configuration and fixtures."""

import asyncio

import pytest
from testcontainers.postgres import PostgresContainer  # type: ignore[import-not-found]


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")


@pytest.fixture(scope="session")
def postgres_container():
    """Provide PostgreSQL container for integration tests."""
    container = PostgresContainer(
        image="postgres:17",
        username="tasklib",
        password="tasklib_pass",
        dbname="tasklib",
    )
    with container as postgres:
        yield postgres


@pytest.fixture
def database_url(postgres_container):
    """Provide database URL for integration tests."""
    # Convert psycopg2 URL to psycopg3 (psycopg) URL
    url = postgres_container.get_connection_url()
    # Replace the driver from psycopg2 to psycopg
    return url.replace("postgresql+psycopg2://", "postgresql+psycopg://")


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
