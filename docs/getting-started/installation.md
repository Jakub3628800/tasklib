# Installation

## Requirements

- Python 3.13+
- PostgreSQL 12+

## Install TaskLib

=== "pip"

    ```bash
    pip install tasklib
    ```

=== "uv"

    ```bash
    uv add tasklib
    ```

## Set Up PostgreSQL

=== "Docker"

    ```bash
    docker run -d \
      -e POSTGRES_USER=tasklib \
      -e POSTGRES_PASSWORD=tasklib_pass \
      -e POSTGRES_DB=tasklib \
      -p 5432:5432 \
      postgres:15
    ```

=== "Local"

    ```bash
    # macOS with Homebrew
    brew install postgresql@15
    brew services start postgresql@15

    # Create database
    createdb tasklib
    ```

## Verify Installation

```python
from tasklib import task, Config

config = Config(database_url="postgresql://tasklib:tasklib_pass@localhost/tasklib")
print("✅ Ready!")
```

## Next Steps

- [**Quick Start**](quick-start.md) — 5 minute walkthrough
- [**Your First Task**](first-task.md) — Step-by-step guide
