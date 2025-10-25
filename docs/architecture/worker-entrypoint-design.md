# Worker Entrypoint Design Ultrathink

## The Problem

Current state for a user integrating TaskLib:
1. Easy: Run migration (`alembic upgrade head`)
2. Hard: Write `worker.py` to initialize and run the worker
3. Hard: Figure out how to run it in Docker/docker-compose/systemd/K8s

**Goal**: Make it so easy that it's just ONE command, with optional configuration.

## The Vision

After running migration, user should be able to do ONE of:

```bash
# Option A: Simple env var + CLI command
export DATABASE_URL=postgresql://...
tasklib-worker

# Option B: With config file
tasklib-worker --config config.yaml

# Option C: Python module execution (no installation)
python -m tasklib.worker

# Option D: Docker (pre-built image)
docker run tasklib-worker --db-url postgresql://...

# Option E: Docker Compose (included example)
docker-compose up worker
```

**And their tasks just work.**

---

## Option 1: CLI Entry Point (RECOMMENDED PRIMARY)

### Implementation

```toml
# pyproject.toml
[project.scripts]
tasklib-worker = "tasklib.cli:main"
```

### Usage

```bash
# With environment variables
export DATABASE_URL=postgresql://localhost/tasklib
tasklib-worker

# With arguments
tasklib-worker --db-url postgresql://... --worker-id worker-1 --concurrency 4

# With config file
tasklib-worker --config tasklib.yaml

# With uv (for users without pip install)
uv run tasklib-worker
```

### Config File Support (YAML)

```yaml
# tasklib.yaml
database:
  url: postgresql://user:pass@localhost/tasklib

worker:
  id: worker-1
  concurrency: 4
  poll_interval_seconds: 1

retry:
  base_delay_seconds: 5.0
  backoff_multiplier: 2.0
  max_retries: 3

tasks:
  # Auto-import these modules to register tasks
  modules:
    - myapp.tasks
    - myapp.admin.tasks

logging:
  level: INFO
```

### Pros
- Standard Python practice (pytest, black, pip, etc. all do this)
- Works everywhere: Docker, systemd, K8s, cron, manual
- Easy to call: `tasklib-worker` or `uv run tasklib-worker`
- Flexible configuration (env vars, CLI args, config file)
- Task module discovery built-in
- Graceful shutdown on SIGTERM/SIGINT
- Clear error messages for misconfiguration

### Cons
- Requires users to `pip install tasklib` (or use `uv add tasklib`)
- Entry point needs testing

### Implementation Details

```python
# src/tasklib/cli.py
import asyncio
import sys
from pathlib import Path
from typing import Optional
import yaml
import click
from . import Config, init, TaskWorker

@click.command()
@click.option('--db-url', envvar='DATABASE_URL', help='PostgreSQL connection URL')
@click.option('--worker-id', default=None, help='Worker ID (auto-generated if not provided)')
@click.option('--concurrency', type=int, default=None, help='Number of concurrent tasks')
@click.option('--poll-interval', type=float, default=None, help='Poll interval in seconds')
@click.option('--config', type=click.Path(exists=True), help='Config file (YAML)')
@click.option('--import-modules', default=None, help='Comma-separated modules to import')
@click.option('--log-level', default='INFO', help='Logging level')
def main(db_url, worker_id, concurrency, poll_interval, config, import_modules, log_level):
    """Run TaskLib worker."""

    # Load config file if provided
    if config:
        with open(config) as f:
            cfg = yaml.safe_load(f)
        db_url = db_url or cfg.get('database', {}).get('url')
        worker_id = worker_id or cfg.get('worker', {}).get('id')
        concurrency = concurrency or cfg.get('worker', {}).get('concurrency')
        poll_interval = poll_interval or cfg.get('worker', {}).get('poll_interval_seconds')
        import_modules = import_modules or ','.join(cfg.get('tasks', {}).get('modules', []))

    # Validate
    if not db_url:
        click.echo("Error: DATABASE_URL not provided", err=True)
        sys.exit(1)

    # Import task modules
    if import_modules:
        for module_name in import_modules.split(','):
            try:
                __import__(module_name.strip())
            except ImportError as e:
                click.echo(f"Error importing {module_name}: {e}", err=True)
                sys.exit(1)

    # Initialize tasklib
    config_obj = Config(
        database_url=db_url,
        worker_id=worker_id,
        # ... other options
    )

    # Run worker
    asyncio.run(_run_worker(config_obj))

async def _run_worker(config):
    await init(config)
    worker = TaskWorker(config)
    try:
        await worker.run()
    except KeyboardInterrupt:
        click.echo("\nShutting down gracefully...")

if __name__ == '__main__':
    main()
```

---

## Option 2: Python Module Execution

### Implementation

```python
# src/tasklib/__main__.py
import asyncio
import sys
from pathlib import Path
from . import Config, init, TaskWorker
import os

async def main():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("Error: DATABASE_URL environment variable not set", file=sys.stderr)
        sys.exit(1)

    config = Config(database_url=db_url)
    await init(config)
    worker = TaskWorker(config)
    await worker.run()

if __name__ == '__main__':
    asyncio.run(main())
```

### Usage

```bash
# Standard Python
python -m tasklib

# With uv
uv run tasklib
```

### Pros
- No CLI package dependencies needed
- Works with `uv run` out of the box
- Simple implementation
- Good fallback option

### Cons
- Less discoverable than CLI
- Only supports environment variables (no config file)
- Task module import not handled

---

## Option 3: Docker Image + Docker Compose

### Implementation

```dockerfile
# Dockerfile.worker
FROM python:3.13-slim

WORKDIR /app

# Install tasklib from pip/local
RUN pip install tasklib

# Task modules should be in the container
COPY ./tasks.py /app/
COPY ./myapp /app/myapp

ENV DATABASE_URL=postgresql://localhost/tasklib
ENV WORKER_ID=worker-default

ENTRYPOINT ["tasklib-worker"]
CMD ["--import-modules", "myapp.tasks"]
```

### Docker Compose Example

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: tasklib
      POSTGRES_PASSWORD: tasklib_pass
      POSTGRES_DB: tasklib
    ports:
      - "5432:5432"

  api:
    build: .
    environment:
      DATABASE_URL: postgresql://tasklib:tasklib_pass@postgres/tasklib
    ports:
      - "8000:8000"
    command: uvicorn myapp.api:app --host 0.0.0.0

  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    environment:
      DATABASE_URL: postgresql://tasklib:tasklib_pass@postgres/tasklib
      WORKER_ID: worker-1
    depends_on:
      - postgres
    # Scale: docker-compose up -d --scale worker=3

  worker-2:
    extends: worker
    environment:
      WORKER_ID: worker-2

  worker-3:
    extends: worker
    environment:
      WORKER_ID: worker-3
```

### Pros
- Isolated environment
- Easy scaling (Docker Compose, K8s)
- Same environment everywhere
- Pre-built image available (optional)

### Cons
- Requires Docker installed
- Extra infrastructure
- Configuration still needed

---

## Option 4: Systemd Service Template

### Implementation

```ini
# tasklib-worker.service
[Unit]
Description=TaskLib Worker
After=network.target postgresql.service

[Service]
Type=simple
User=tasklib
WorkingDirectory=/opt/myapp
Environment="DATABASE_URL=postgresql://user:pass@localhost/tasklib"
Environment="WORKER_ID=worker-1"
ExecStart=/usr/local/bin/tasklib-worker
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

### Usage

```bash
sudo cp tasklib-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tasklib-worker
sudo systemctl start tasklib-worker
```

### Pros
- Native Linux integration
- Auto-restart on failure
- Multiple instances easy (worker@1.service, worker@2.service)

### Cons
- Linux-only
- Requires systemd

---

## Option 5: Kubernetes Deployment

### Implementation

```yaml
# k8s-worker.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tasklib-worker
spec:
  replicas: 3
  selector:
    matchLabels:
      app: tasklib-worker
  template:
    metadata:
      labels:
        app: tasklib-worker
    spec:
      containers:
      - name: worker
        image: myapp:latest
        command: ["tasklib-worker", "--import-modules", "myapp.tasks"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: tasklib-secrets
              key: database-url
        - name: WORKER_ID
          value: "$(HOSTNAME)"
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### Pros
- Cloud-native
- Auto-scaling
- Self-healing
- Multi-region ready

### Cons
- Requires K8s cluster
- Complex setup

---

## Option 6: Script Template (Backward Compatible)

For users who want to keep everything in their project:

```python
# ./worker.py (template provided by TaskLib)
#!/usr/bin/env python
"""
TaskLib Worker Script

Usage:
    python worker.py

Configuration via environment variables:
    DATABASE_URL: PostgreSQL connection string
    WORKER_ID: Worker identifier (auto-generated if not set)
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from tasklib import Config, init, TaskWorker

# Import your tasks here to register them
from myapp import tasks  # noqa: F401

async def main():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("Error: DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)

    config = Config(database_url=db_url)
    await init(config)
    worker = TaskWorker(config)
    await worker.run()

if __name__ == '__main__':
    asyncio.run(main())
```

### Usage

```bash
python worker.py
# Or with uv:
uv run python worker.py
```

### Pros
- Maximum flexibility
- No installation needed
- Users own the code

### Cons
- Each project maintains their own script
- Less discoverable

---

## RECOMMENDED HYBRID APPROACH

### Primary Path (Recommended)

1. **CLI Entry Point** (`tasklib-worker` command)
   - Default, easy way for most users
   - Works everywhere
   - Full configuration support

2. **Python Module** (`python -m tasklib`)
   - Fallback option
   - No CLI dependency

3. **Configuration Options**
   - Environment variables (easiest)
   - Config file (most flexible)
   - CLI arguments (for overrides)
   - Priority: CLI args > config file > env vars > defaults

4. **Docker Compose Example**
   - Provided in repository
   - Easy copy-paste for new projects

### Task Module Import Strategy

Users have 3 ways to ensure tasks are registered:

```bash
# Option A: Command-line argument
tasklib-worker --import-modules myapp.tasks,myapp.admin.tasks

# Option B: Config file
# tasklib.yaml lists modules

# Option C: Convention
# Worker auto-imports {app_module}/tasks.py if it exists
tasklib-worker --app myapp  # Imports myapp.tasks automatically
```

---

## Integration Flow (User Perspective)

### Step 1: Install
```bash
uv add tasklib
```

### Step 2: Define Tasks
```python
# myapp/tasks.py
from tasklib import task

@task
def send_email(to: str, subject: str) -> bool:
    # ...
    return True
```

### Step 3: Run Migration
```bash
alembic upgrade head
```

### Step 4: Run Worker (Pick one)

**Option A - Simplest** (Env vars + CLI)
```bash
export DATABASE_URL=postgresql://...
tasklib-worker --import-modules myapp.tasks
```

**Option B - Config file**
```yaml
# tasklib.yaml
database:
  url: postgresql://...
tasks:
  modules:
    - myapp.tasks
```
```bash
tasklib-worker --config tasklib.yaml
```

**Option C - Docker**
```bash
docker-compose up worker
```

**Option D - Python module**
```bash
python -m tasklib
```

### Step 5: Submit Tasks
```python
from myapp.tasks import send_email
await tasklib.submit_task(send_email, to="user@example.com", subject="Hello")
```

---

## Implementation Checklist

### Phase 1: CLI Entry Point (Required)
- [ ] Create `src/tasklib/cli.py` with Click
- [ ] Add entry point to `pyproject.toml`
- [ ] Support environment variables
- [ ] Support config file (YAML)
- [ ] Support command-line arguments
- [ ] Add task module import
- [ ] Add graceful shutdown (SIGTERM)
- [ ] Add logging support
- [ ] Update pyproject.toml to include Click dependency

### Phase 2: Python Module
- [ ] Create `src/tasklib/__main__.py`
- [ ] Support environment variables
- [ ] Basic task module loading

### Phase 3: Docker Support
- [ ] Create `Dockerfile.worker`
- [ ] Create example `docker-compose.yml`
- [ ] Add to documentation

### Phase 4: Documentation
- [ ] "Running the Worker" guide
- [ ] CLI reference
- [ ] Config file examples
- [ ] Docker/Compose examples
- [ ] Systemd/K8s templates

### Phase 5: Templates (Nice to have)
- [ ] Systemd service template
- [ ] K8s deployment YAML
- [ ] Script template for projects

---

## Config File Schema

```yaml
# Complete tasklib.yaml reference

# Database configuration (required)
database:
  url: postgresql://user:pass@localhost/tasklib
  # Optional: connection pool settings
  pool_size: 10
  max_overflow: 20

# Worker configuration
worker:
  id: worker-1                          # Optional, auto-generated if not set
  concurrency: 4                        # Number of concurrent tasks
  poll_interval_seconds: 1              # How often to check for tasks
  lock_timeout_seconds: 600             # Dead worker detection timeout

# Retry configuration
retry:
  base_delay_seconds: 5.0               # Initial retry delay
  backoff_multiplier: 2.0               # Exponential backoff
  max_retries: 3                        # Default max retries

# Task registration
tasks:
  modules:                              # Auto-import these modules
    - myapp.tasks
    - myapp.admin.tasks
  timeout_seconds: 300                  # Default task timeout

# Logging
logging:
  level: INFO                           # DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: simple                        # simple or json
  # Optional: log to file
  file: /var/log/tasklib/worker.log
  max_size_mb: 100
  backup_count: 5

# Optional: Monitoring/Metrics
monitoring:
  prometheus_port: 8001                 # Expose Prometheus metrics
  log_stats_interval_seconds: 60        # Log stats periodically
```

---

## Security Considerations

- [ ] Don't log database URLs/credentials
- [ ] Validate module names to prevent arbitrary imports
- [ ] Support reading secrets from env vars (for Docker)
- [ ] Support reading secrets from files (for K8s)
- [ ] Rate limiting on task execution (optional)
- [ ] Timeout enforcement on all tasks

---

## Backwards Compatibility

All options are non-breaking:
- Existing `examples/worker.py` still works
- Users who write their own worker.py still works
- New users have easier path with CLI

---

## Success Criteria

A new user can:
1. `uv add tasklib`
2. Run migration
3. Do `tasklib-worker --import-modules myapp.tasks`
4. Submit tasks and they execute

All within 5 minutes with documentation

Deployment options for all environments:
- Local development
- Docker/Docker Compose
- Systemd
- Kubernetes

---

## Recommendation

**Implement CLI Entry Point (Option 1) as primary path**

This gives users:
- Simplicity: `tasklib-worker`
- Flexibility: Config files, env vars, CLI args
- Standardization: Follows Python conventions
- Scalability: Works everywhere from laptop to K8s
- Discovery: CLI is discoverable (`tasklib-worker --help`)

Plus secondary options:
- Python -m as fallback
- Docker examples for containerized deployments
- Documentation for other platforms
