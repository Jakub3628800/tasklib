"""Simple test tasks for demonstration."""

from tasklib import task


@task
def hello() -> str:
    """Simple hello task."""
    return "Hello, TaskLib!"


@task
def add_numbers(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@task(max_retries=2)
def send_notification(message: str) -> dict:
    """Send a notification."""
    return {"sent": True, "message": message}
