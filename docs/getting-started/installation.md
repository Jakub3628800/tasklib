# Installation

## Requirements

- **Python:** 3.12 or higher
- **PostgreSQL:** 12 or higher
- **pip or uv:** Package manager

## Install TaskLib

### Using pip

```bash
pip install tasklib
```

### Using uv

```bash
uv add tasklib
```

### From Source

```bash
git clone https://github.com/your-org/tasklib.git
cd tasklib
uv sync
```

## Set Up PostgreSQL

### Local Development

```bash
# With Docker
docker run -d \
  -e POSTGRES_USER=tasklib \
  -e POSTGRES_PASSWORD=tasklib_pass \
  -e POSTGRES_DB=tasklib \
  -p 5432:5432 \
  postgres:15

# Or use docker-compose
docker-compose up -d
```

### Connection URL

```
postgresql://user:password@localhost:5432/database
```

## Verify Installation

```python
import tasklib

print(tasklib.__version__)  # Should print: 0.1.0

# Check imports
from tasklib import task, submit_task, Config, TaskWorker

print("✅ TaskLib installed successfully!")
```

## Next Steps

- **[Quick Start](quick-start.md)** - Create your first task in 5 minutes
- **[Your First Task](first-task.md)** - Step-by-step walkthrough

## Troubleshooting

### "ModuleNotFoundError: No module named 'tasklib'"

```bash
# Reinstall
pip install --upgrade tasklib

# Or verify installation
pip show tasklib
```

### "psycopg.OperationalError: connection failed"

```bash
# Check PostgreSQL is running
psql -U tasklib -d tasklib -c "SELECT 1;"

# Or via Docker
docker-compose ps
```

### "relation \"tasks\" does not exist"

Run migrations:

```python
import tasklib

config = tasklib.Config(database_url="postgresql://...")
tasklib.init(config)  # Creates tables automatically
```

Or use Alembic:

```bash
alembic upgrade head
```

## Development Setup

For contributors:

```bash
# Clone repo
git clone <url>
cd tasklib

# Install with dev dependencies
uv sync --extra dev

# Start PostgreSQL
docker-compose up -d

# Run tests
make test
```
