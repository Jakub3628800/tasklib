# TaskLib Dashboard API

A simple FastAPI application that provides a beautiful web dashboard for monitoring TaskLib tasks.

## Setup

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configuration

Set the database connection via environment variable:

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/tasklib"
```

If not set, defaults to `postgresql://postgres:postgres@localhost:5432/tasklib`

### Run the Application

```bash
python app.py
```

The dashboard will be available at `http://localhost:8000`

## Features

- **Overview Dashboard**: Real-time stats on total, pending, running, completed, and failed tasks
- **Advanced Filtering**: Filter tasks by:
  - State (pending, running, completed, failed)
  - Task name (substring match)
  - Worker ID
  - Minimum priority
  - Minimum retry count
- **Task List**: View all tasks with details including:
  - Task ID and name
  - Current state (with color-coded badges)
  - Created, started, and completed timestamps
  - Worker assignment
  - Retry count vs max retries
  - Priority level
- **Worker Status**: Monitor active workers and their locked tasks
- **Auto-refresh**: Stats and worker info update every 5 seconds

## API Endpoints

### GET /
Serves the dashboard HTML

### GET /api/tasks
Get a list of tasks with optional filtering

Query parameters:
- `state`: Filter by state (pending, running, completed, failed)
- `name`: Filter by task name (substring match)
- `worker_id`: Filter by worker ID
- `priority_min`: Filter by minimum priority
- `retry_count_min`: Filter by minimum retry count
- `limit`: Number of results (default: 100, max: 1000)
- `offset`: Pagination offset (default: 0)

### GET /api/stats
Get overall task statistics

Response:
```json
{
  "total": 100,
  "pending": 10,
  "running": 5,
  "completed": 80,
  "failed": 5,
  "failed_permanent": 2
}
```

### GET /api/workers
Get active worker status

Response:
```json
[
  {
    "worker_id": "worker-uuid",
    "locked_tasks": 3,
    "earliest_lock_expires": "2025-10-25T17:30:00"
  }
]
```

### GET /api/task/{task_id}
Get details of a specific task

## Notes

- The app assumes the TaskLib schema already exists in PostgreSQL
- No schema creation is performed automatically
- All timestamps are UTC
- The dashboard is read-only (no task modification capability yet)
