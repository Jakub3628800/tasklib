# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2025-10-25

### Added
- Initial release of TaskLib
- Core `@task` decorator for registering tasks
- `submit_task()` for queuing work with optional delay
- `TaskWorker` class for executing tasks with multi-worker support
- PostgreSQL SELECT FOR UPDATE locking strategy
- Exponential backoff retry logic
- Task timeout support
- Priority-based task ordering
- Metadata tags for filtering
- Task state tracking: pending, running, completed, failed
- Dead worker detection via lock timeout
- Comprehensive test suite
- Complete API documentation (README.md)
- Architecture documentation (DESIGN.md)
- Detailed specification (SPEC.md)
- Example implementations (simple.py, worker.py)
- Makefile for development tasks

### Features

#### Task Definition
- `@task` decorator with optional `max_retries` and `timeout_seconds`
- Pydantic validation of task arguments
- Type hints support

#### Task Submission
- `submit_task()` async function
- `delay_seconds` for scheduling tasks in the future
- `priority` parameter for task ordering
- `tags` for metadata and filtering
- UUID-based task IDs

#### Task Execution
- Sync function execution (async v2.0)
- Thread pool execution via asyncio
- Configurable timeouts
- Full exception traceback capture
- Exponential backoff retries (default: 5s, 10s, 20s)

#### Multi-Worker Support
- PostgreSQL SELECT FOR UPDATE for atomic task claiming
- `locked_until` timestamp for dead worker detection
- `worker_id` tracking
- Configurable lock timeout (default: 10 minutes)
- Works across multiple machines

#### Monitoring
- `get_task(task_id)` - retrieve single task status
- `list_tasks()` - filter tasks by state, name, limit
- `get_registered_tasks()` - inspect registered tasks
- Direct SQL query support via PostgreSQL

#### Database
- Single `tasks` table with comprehensive schema
- Indexed columns: state, scheduled_at, locked_until, priority, name
- JSONB support for arguments, results, metadata
- Full audit trail (created_at, started_at, completed_at)

### Not Included
- Async function support (planned for v2.0)
- Recurring/cron tasks (planned for v2.0)
- Task dependencies/chaining (planned for v2.0)
- Admin UI dashboard (planned for v2.0)
- Automatic result cleanup (intentional for v1)
- Message broker integration (PostgreSQL as queue)
- Task result expiration

### Known Limitations
- Sync functions only (v2 will add async)
- Single-table design (limits some advanced features)
- No built-in monitoring dashboard (SQL queries work)
- No automatic cleanup policy (use manual archival)

---

## Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **0.1.0** - Initial MVP release
- **0.x.x** - API subject to change
- **1.0.0** - Stable API (coming soon)

---

## Future Releases

### v0.2.0 (Planned)
- Async/await function support
- Better error context
- Task result pagination
- Performance improvements

### v1.0.0 (Planned)
- API stability guarantee
- Comprehensive error handling
- Performance optimizations
- Production hardening

### v2.0.0 (Future)
- Recurring tasks (cron-like)
- Task dependencies/chaining
- Admin API + basic UI
- Distributed tracing
- Dead letter queue
- Prometheus metrics

---

**Last Updated:** 2025-10-25
