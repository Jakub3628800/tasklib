"""Example TaskLib tasks demonstrating various features."""

import random
import time

from tasklib import task


@task
def hello_world() -> str:
    """Simple hello world task."""
    message = "Hello, World!"
    print(message)
    return message


@task
def simple_add(a: int, b: int) -> int:
    """Simple task: add two numbers."""
    print(f"Adding {a} + {b}")
    result = a + b
    print(f"Result: {result}")
    return result


@task
def greet(name: str, greeting: str = "Hello") -> str:
    """Task with default parameter."""
    result = f"{greeting}, {name}!"
    print(result)
    return result


@task
def process_text(text: str) -> dict:
    """Process text and return statistics."""
    print(f"Processing: {text[:50]}...")
    result = {
        "length": len(text),
        "words": len(text.split()),
        "uppercase": sum(1 for c in text if c.isupper()),
        "lowercase": sum(1 for c in text if c.islower()),
    }
    print(f"Stats: {result}")
    return result


@task(timeout_seconds=5)
def io_task(duration_seconds: float) -> dict:
    """Simulate I/O operation with delay."""
    print(f"Simulating I/O for {duration_seconds} seconds...")
    start = time.time()
    time.sleep(duration_seconds)
    elapsed = time.time() - start
    print(f"I/O completed in {elapsed:.2f}s")
    return {"duration": elapsed}


@task(max_retries=3)
def unreliable_task(success_rate: float = 0.5) -> str:
    """Task that randomly fails (good for testing retries)."""
    if random.random() < success_rate:
        print("Task succeeded")
        return "Success!"
    else:
        print("Task failed, will retry...")
        raise RuntimeError("Random failure (will retry)")


@task(max_retries=2)
def task_with_custom_retries() -> str:
    """Task with custom retry count."""
    attempt = random.randint(1, 3)
    if attempt > 2:
        print("Task failed after 2 retries")
        raise RuntimeError("Permanent failure")
    else:
        print(f"Success on attempt {attempt}")
        return f"Succeeded after {attempt} attempts"


@task
def validation_task(value: int) -> bool:
    """Task that validates input."""
    if not isinstance(value, int):
        raise TypeError(f"Expected int, got {type(value)}")
    if value < 0:
        raise ValueError("Value must be non-negative")
    print(f"Validated value: {value}")
    return True


@task
def database_task(operation: str) -> dict:
    """Simulate database operation."""
    print(f"Executing database operation: {operation}")
    if operation == "insert":
        return {"inserted": 1, "id": 42}
    elif operation == "update":
        return {"updated": 5}
    elif operation == "delete":
        return {"deleted": 3}
    else:
        raise ValueError(f"Unknown operation: {operation}")


@task
def batch_process(items: list) -> dict:
    """Process a batch of items."""
    print(f"Processing batch of {len(items)} items")
    results = []
    for item in items:
        processed = item.upper() if isinstance(item, str) else str(item)
        results.append(processed)
    print(f"Processed {len(results)} items")
    return {"count": len(results), "items": results}


@task
def calculate_statistics(data: list[float]) -> dict:
    """Calculate statistics on data."""
    print(f"Calculating statistics for {len(data)} data points")
    if not data:
        raise ValueError("Data list cannot be empty")

    return {
        "count": len(data),
        "sum": sum(data),
        "mean": sum(data) / len(data),
        "min": min(data),
        "max": max(data),
    }


@task
def send_email(to: str, subject: str, body: str = "") -> dict:
    """Simulate sending an email."""
    print(f"Sending email to {to}")
    print(f"Subject: {subject}")
    if body:
        print(f"Body: {body[:100]}...")
    return {"to": to, "subject": subject, "sent": True}


@task
def generate_report(report_type: str, include_charts: bool = False) -> dict:
    """Generate a report."""
    print(f"Generating {report_type} report (charts: {include_charts})")
    time.sleep(0.5)  # Simulate work
    return {
        "type": report_type,
        "pages": random.randint(5, 20),
        "charts": include_charts,
        "generated_at": time.time(),
    }


@task
def cpu_work(iterations: int = 1000000) -> dict:
    """CPU-intensive task."""
    print(f"Performing {iterations} iterations...")
    result = 0
    for i in range(iterations):
        result += i % 7
    print(f"Computation result: {result}")
    return {"iterations": iterations, "result": result}


@task
def memory_task(size_mb: int = 10) -> dict:
    """Task that allocates memory."""
    print(f"Allocating {size_mb}MB of memory...")
    data = [random.random() for _ in range(size_mb * 100000)]
    print(f"Allocated {len(data)} floats")
    return {"size_mb": size_mb, "items": len(data)}
