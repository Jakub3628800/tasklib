# Monitoring Tasks

How to monitor task status and health.

## Get Task Status

```python
from tasklib import get_task, is_completed

task = get_task(task_id)
print(f"State: {task.state}")
print(f"Result: {task.result}")
print(f"Error: {task.error}")
```

## SQL Queries

```sql
-- All tasks by state
SELECT state, COUNT(*) FROM tasks GROUP BY state;

-- Task performance
SELECT name, AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))
FROM tasks WHERE state='completed' GROUP BY name;

-- Stuck tasks
SELECT id, name FROM tasks WHERE state='running' AND locked_until < NOW();
```

See [Database Schema](../schema/database.md) for more queries.
