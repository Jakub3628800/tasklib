# Worker Reference

TaskWorker class API.

```python
from tasklib import TaskWorker, Config

worker = TaskWorker(
    config,
    concurrency=4,
    poll_interval_seconds=1.0,
)

await worker.run()
```

## Configuration

- `config` - TaskLib Config
- `concurrency` - Parallel tasks (default: 1)
- `poll_interval_seconds` - Poll frequency (default: 1.0)

## Methods

- `run()` - Run worker (blocks until shutdown)
- `shutdown()` - Graceful shutdown

See [Running Workers](../guides/workers.md) for examples.
