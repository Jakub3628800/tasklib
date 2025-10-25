# Running Workers

Learn how to run TaskLib workers with the `tasklib-worker` command.

## Quick Start

The simplest way to run a worker:

```bash
export DATABASE_URL=postgresql://user:pass@localhost/tasklib
tasklib-worker --task-module myapp.tasks
```

That's it! The worker is now:
- ✅ Polling PostgreSQL for tasks
- ✅ Executing registered tasks
- ✅ Handling retries automatically
- ✅ Logging results to the database

## Command Line Usage

### Basic Command

```bash
tasklib-worker [OPTIONS]
```

### Required Options

**`--task-module`**

Specify which Python modules to import to register tasks. Can be used multiple times:

```bash
tasklib-worker --task-module myapp.tasks --task-module myapp.admin.tasks
```

**Database Configuration** (one of):
- `--db-url` flag: `tasklib-worker --db-url postgresql://...`
- `DATABASE_URL` env var: `export DATABASE_URL=postgresql://...`

### Optional Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--worker-id` | Auto-generated UUID | Worker identifier for logs/monitoring |
| `--concurrency` | 4 | Number of concurrent tasks to execute |
| `--poll-interval` | 1 | Poll frequency in seconds |
| `--max-retries` | 3 | Default max retries for tasks |
| `--base-retry-delay` | 5.0 | Initial retry delay in seconds |
| `--config` | - | Path to YAML config file |
| `--log-level` | INFO | DEBUG, INFO, WARNING, ERROR, CRITICAL |

## Configuration Methods

### Method 1: Environment Variables (Simplest)

```bash
export DATABASE_URL=postgresql://user:pass@localhost/tasklib
tasklib-worker --task-module myapp.tasks
```

### Method 2: Command-Line Flags

```bash
tasklib-worker \
  --db-url postgresql://user:pass@localhost/tasklib \
  --worker-id worker-1 \
  --concurrency 4 \
  --task-module myapp.tasks
```

### Method 3: Config File (Most Flexible)

Create `tasklib.yaml`:

```yaml
database:
  url: postgresql://user:pass@localhost/tasklib

worker:
  id: worker-1
  concurrency: 4
  poll_interval_seconds: 1

retry:
  max_retries: 3
  base_delay_seconds: 5.0

tasks:
  modules:
    - myapp.tasks
    - myapp.admin.tasks

logging:
  level: INFO
```

Run with config file:

```bash
tasklib-worker --config tasklib.yaml
```

### Configuration Priority

```
CLI flags > Config file > Environment variables > Defaults
```

## Real-World Examples

### Single Worker

```bash
export DATABASE_URL=postgresql://localhost/tasklib
tasklib-worker --task-module myapp.tasks --worker-id worker-1
```

### Multiple Workers

Run in separate terminals/processes/containers:

```bash
# Terminal 1
tasklib-worker --task-module myapp.tasks --worker-id worker-1

# Terminal 2
tasklib-worker --task-module myapp.tasks --worker-id worker-2

# Terminal 3
tasklib-worker --task-module myapp.tasks --worker-id worker-3
```

All workers coordinate through PostgreSQL locking - no duplicate execution.

### High-Concurrency Worker

```bash
tasklib-worker \
  --task-module myapp.tasks \
  --concurrency 16 \
  --worker-id worker-high-concurrency
```

### With Verbose Logging

```bash
tasklib-worker \
  --task-module myapp.tasks \
  --log-level DEBUG
```

## Integration with Docker

### Using Docker Compose

Add to `docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: tasklib
      POSTGRES_USER: tasklib
      POSTGRES_PASSWORD: tasklib_pass

  worker:
    build: .
    environment:
      DATABASE_URL: postgresql://tasklib:tasklib_pass@postgres/tasklib
    command: tasklib-worker --task-module myapp.tasks
    depends_on:
      - postgres
```

Run:

```bash
docker-compose up worker
```

## Graceful Shutdown

The worker handles `SIGTERM` gracefully:

```bash
# Worker finishes current tasks then exits
kill -TERM <worker-pid>

# Or with Ctrl+C
Ctrl+C
```

## Troubleshooting

### "DATABASE_URL not provided"

Make sure to set the database URL:

```bash
export DATABASE_URL=postgresql://...
tasklib-worker --task-module myapp.tasks
```

### "Failed to import task module"

Check that the module path is correct:

```bash
# ✅ Correct: Python module path
tasklib-worker --task-module myapp.tasks
```

### "No task modules imported"

The worker needs to know which modules contain your tasks:

```bash
# ✅ Specify modules
tasklib-worker --task-module myapp.tasks
```

## Next Steps

- [Task Definition Guide](./task-definition.md) - Define tasks with `@task`
- [Task Submission Guide](./task-submission.md) - Submit tasks from your app
- [Error Handling Guide](./error-handling.md) - Handle failures and retries
