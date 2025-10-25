# Task States

Task execution states and transitions.

## States

| State | Meaning | Next |
|-------|---------|------|
| pending | Waiting to execute | running |
| running | Being executed | completed or failed |
| completed | Finished successfully | terminal |
| failed | Execution failed | pending (retry) or terminal |

## Lifecycle

```
PENDING → RUNNING → COMPLETED
  ↓
FAILED → (retry?) → PENDING
  ↓
FAILED (permanent)
```

See [FINAL_SCHEMA.md](../../FINAL_SCHEMA.md) for examples.
