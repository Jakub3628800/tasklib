import os
import json
from typing import Optional
from uuid import UUID
from datetime import datetime
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, desc, func, and_
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

from models import Base, Task, TaskResponse, TaskStats, WorkerStats

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/tasklib")
DASHBOARD_MODE = os.getenv("DASHBOARD_MODE", "readonly").lower()  # readonly or readwrite

if DASHBOARD_MODE not in ("readonly", "readwrite"):
    raise ValueError("DASHBOARD_MODE must be 'readonly' or 'readwrite'")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI(
    title="TaskLib Dashboard API",
    description="Real-time task monitoring and management API with ReDoc documentation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


def check_write_mode():
    """Raise exception if dashboard is in readonly mode"""
    if DASHBOARD_MODE == "readonly":
        raise HTTPException(status_code=403, detail="Dashboard is in read-only mode")


@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    """Serve the dashboard HTML"""
    return get_dashboard_html()


@app.get("/api/tasks", response_model=list[TaskResponse])
def list_tasks(
    state: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    worker_id: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    priority_min: Optional[int] = Query(None),
    retry_count_min: Optional[int] = Query(None),
    created_after: Optional[str] = Query(None),
    created_before: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
):
    """
    Get tasks with filtering options.

    Query parameters:
    - state: Filter by state (pending, running, completed, failed)
    - name: Filter by task name (substring match)
    - worker_id: Filter by worker ID
    - tag: Filter by tag key (JSON key existence)
    - priority_min: Filter by minimum priority
    - retry_count_min: Filter by minimum retry count
    - created_after: Filter tasks created after this date (ISO format)
    - created_before: Filter tasks created before this date (ISO format)
    """
    from datetime import datetime as dt

    with get_db() as db:
        query = db.query(Task)

        if state:
            query = query.filter(Task.state == state)
        if name:
            query = query.filter(Task.name.ilike(f"%{name}%"))
        if worker_id:
            query = query.filter(Task.worker_id == worker_id)
        if priority_min is not None:
            query = query.filter(Task.priority >= priority_min)
        if retry_count_min is not None:
            query = query.filter(Task.retry_count >= retry_count_min)
        if created_after:
            query = query.filter(Task.created_at >= dt.fromisoformat(created_after.replace("Z", "+00:00")))
        if created_before:
            query = query.filter(Task.created_at <= dt.fromisoformat(created_before.replace("Z", "+00:00")))

        # Order by created_at descending
        query = query.order_by(desc(Task.created_at))

        tasks = query.limit(limit).offset(offset).all()

        return [TaskResponse.from_orm(task) for task in tasks]


@app.get("/api/stats", response_model=TaskStats)
def get_stats(
    created_after: Optional[str] = Query(None),
    created_before: Optional[str] = Query(None),
):
    """Get overall task statistics with optional time filtering"""
    from datetime import datetime as dt

    with get_db() as db:
        query = db.query(Task)

        # Apply time filters if provided
        if created_after:
            query = query.filter(Task.created_at >= dt.fromisoformat(created_after.replace("Z", "+00:00")))
        if created_before:
            query = query.filter(Task.created_at <= dt.fromisoformat(created_before.replace("Z", "+00:00")))

        total = query.count()
        pending = query.filter(Task.state == "pending").count()
        running = query.filter(Task.state == "running").count()
        completed = query.filter(Task.state == "completed").count()
        failed = query.filter(Task.state == "failed").count()
        failed_permanent = query.filter(and_(Task.state == "failed", Task.retry_count >= Task.max_retries)).count()

        return TaskStats(
            total=total,
            pending=pending,
            running=running,
            completed=completed,
            failed=failed,
            failed_permanent=failed_permanent,
        )


@app.get("/api/workers", response_model=list[WorkerStats])
def get_workers():
    """Get worker status"""
    with get_db() as db:
        workers = (
            db.query(
                Task.worker_id,
                func.count(Task.id).label("locked_tasks"),
                func.min(Task.locked_until).label("earliest_lock_expires"),
            )
            .filter(and_(Task.state == "running", Task.worker_id.isnot(None)))
            .group_by(Task.worker_id)
            .all()
        )

        return [
            WorkerStats(
                worker_id=w[0],
                locked_tasks=w[1],
                earliest_lock_expires=w[2],
            )
            for w in workers
        ]


@app.get("/api/task/{task_id}", response_model=TaskResponse)
def get_task(task_id: str):
    """Get a specific task by ID"""
    with get_db() as db:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return TaskResponse.from_orm(task)


@app.get("/api/mode")
def get_mode():
    """Get dashboard mode (readonly or readwrite)"""
    return {"mode": DASHBOARD_MODE}


@app.patch("/api/tasks/{task_id}/cancel")
def cancel_task(task_id: str):
    """Cancel a pending task"""
    check_write_mode()

    try:
        task_uuid = UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID")

    with get_db() as db:
        task = db.query(Task).filter(Task.id == task_uuid).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if task.state != "pending":
            raise HTTPException(status_code=400, detail=f"Can only cancel pending tasks, current state: {task.state}")

        task.state = "cancelled"
        db.add(task)
        db.commit()
        db.refresh(task)

        return TaskResponse.from_orm(task)


@app.post("/api/tasks", response_model=TaskResponse)
def create_task(
    name: str = Query(...),
    args: Optional[str] = Query(None),
    kwargs: Optional[str] = Query(None),
    priority: int = Query(0),
):
    """Create a new task"""
    check_write_mode()

    import json
    from uuid import uuid4

    try:
        task_args = json.loads(args) if args else {}
        task_kwargs = json.loads(kwargs) if kwargs else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in args or kwargs")

    with get_db() as db:
        new_task = Task(
            id=uuid4(),
            name=name,
            args=task_args,
            kwargs=task_kwargs,
            state="pending",
            priority=priority,
            scheduled_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.add(new_task)
        db.commit()
        db.refresh(new_task)

        return TaskResponse.from_orm(new_task)


def get_dashboard_html():
    """Generate the dashboard HTML with modern design"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TaskLib Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --primary: #83a598;
            --primary-dark: #689d6a;
            --bg: #1d2021;
            --bg-card: #282828;
            --text: #ebdbb2;
            --text-secondary: #a89984;
            --border: #3c3836;
            --pending: #fabd2f;
            --running: #b8bb26;
            --completed: #83a598;
            --failed: #fb4934;
        }

        html {
            scroll-behavior: smooth;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 20px;
        }

        .time-picker-section {
            margin-bottom: 24px;
        }

        .time-picker-container {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 20px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            align-items: flex-end;
        }

        /* Header */
        header {
            background: var(--bg-card);
            border-bottom: 1px solid var(--border);
            padding: 16px 0;
            margin-bottom: 16px;
        }

        header h1 {
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 4px;
        }

        header p {
            color: var(--text-secondary);
            font-size: 12px;
        }

        /* Stats Grid */
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 12px;
            margin-bottom: 24px;
        }

        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 16px;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .stat-card:hover {
            border-color: var(--primary);
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.1);
        }

        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--primary), #8b5cf6);
        }

        .stat-card.pending::before { background: var(--pending); }
        .stat-card.running::before { background: var(--running); }
        .stat-card.completed::before { background: var(--completed); }
        .stat-card.failed::before { background: var(--failed); }

        .stat-label {
            font-size: 10px;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.4px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }


        .stat-number {
            font-size: 22px;
            font-weight: 700;
            color: var(--text);
        }

        /* Main Content */
        .main-content {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 20px;
        }

        .section-title {
            font-size: 14px;
            font-weight: 700;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* Filters */
        .filters {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 12px;
            padding-bottom: 16px;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--border);
        }

        .filter-group {
            display: flex;
            flex-direction: column;
        }

        .filter-group label {
            font-size: 11px;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.4px;
            margin-bottom: 6px;
        }

        .filter-group input,
        .filter-group select {
            padding: 8px 10px;
            border: 1px solid var(--border);
            border-radius: 6px;
            font-size: 13px;
            background: var(--bg);
            color: var(--text);
            transition: all 0.2s ease;
            font-family: inherit;
        }

        .filter-group input::placeholder {
            color: var(--text-secondary);
        }

        .filter-group input:focus,
        .filter-group select:focus {
            outline: none;
            border-color: var(--primary);
            background: var(--bg);
            box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
        }

        .filter-actions {
            grid-column: 1 / -1;
            display: flex;
            gap: 12px;
        }

        button {
            padding: 8px 14px;
            border: none;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .btn-primary {
            background: var(--primary);
            color: white;
        }

        .btn-primary:hover {
            background: var(--primary-dark);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
        }

        .btn-secondary {
            background: var(--bg);
            color: var(--text);
            border: 1px solid var(--border);
        }

        .btn-secondary:hover {
            background: var(--border);
            border-color: var(--text-secondary);
        }

        /* Tasks Table */
        .tasks-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }

        .tasks-table thead {
            border-bottom: 2px solid var(--border);
        }

        .tasks-table th {
            padding: 10px 12px;
            text-align: left;
            font-weight: 600;
            font-size: 11px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.4px;
        }

        .tasks-table td {
            padding: 10px 12px;
            border-bottom: 1px solid var(--border);
            font-size: 12px;
        }

        .tasks-table tbody tr {
            transition: all 0.2s ease;
        }

        .tasks-table tbody tr:hover {
            background: var(--bg);
        }

        .task-name {
            font-weight: 600;
            color: var(--primary);
            display: block;
            margin-bottom: 4px;
        }

        .task-id {
            font-size: 12px;
            color: var(--text-secondary);
            font-family: 'Monaco', 'Courier New', monospace;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 600;
            width: fit-content;
        }

        .status-badge::before {
            content: '●';
            font-size: 8px;
        }

        .status-pending {
            background: rgba(245, 158, 11, 0.1);
            color: var(--pending);
        }

        .status-running {
            background: rgba(16, 185, 129, 0.1);
            color: var(--running);
        }

        .status-completed {
            background: rgba(59, 130, 246, 0.1);
            color: var(--completed);
        }

        .status-failed {
            background: rgba(239, 68, 68, 0.1);
            color: var(--failed);
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: var(--text-secondary);
        }

        .error {
            background: rgba(239, 68, 68, 0.1);
            color: var(--failed);
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid var(--failed);
        }

        .pagination {
            display: flex;
            gap: 12px;
            align-items: center;
            justify-content: center;
            margin-top: 32px;
        }

        input[type="date"] {
            padding: 8px 10px;
            border: 1px solid var(--border);
            border-radius: 6px;
            font-size: 13px;
            background: var(--bg);
            color: var(--text);
            transition: all 0.2s ease;
            font-family: inherit;
        }

        input[type="date"]:focus,
        input[type="datetime-local"]:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(131, 165, 152, 0.1);
        }

        input[type="datetime-local"] {
            padding: 8px 10px;
            border: 1px solid var(--border);
            border-radius: 6px;
            font-size: 13px;
            background: var(--bg);
            color: var(--text);
            transition: all 0.2s ease;
            font-family: inherit;
        }

        /* Workers Section */
        .workers-section {
            margin-top: 24px;
            padding-top: 16px;
            border-top: 1px solid var(--border);
        }

        .workers-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
            gap: 12px;
            margin-top: 12px;
        }

        .worker-card {
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 14px;
            transition: all 0.2s ease;
        }

        .worker-card:hover {
            border-color: var(--primary);
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.1);
        }

        .worker-card h4 {
            font-size: 11px;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.4px;
            margin-bottom: 8px;
        }

        .worker-id {
            font-size: 12px;
            font-weight: 600;
            color: var(--primary);
            font-family: 'Monaco', 'Courier New', monospace;
            word-break: break-all;
            margin-bottom: 10px;
            padding: 6px 8px;
            background: var(--bg-card);
            border-radius: 4px;
            border: 1px solid var(--border);
        }

        .worker-info {
            font-size: 11px;
            color: var(--text-secondary);
            margin: 5px 0;
            display: flex;
            justify-content: space-between;
        }

        .worker-info strong {
            color: var(--text);
            font-weight: 600;
        }

        /* Responsive */
        @media (max-width: 768px) {
            header {
                padding: 24px 0;
                margin-bottom: 24px;
            }

            header h1 {
                font-size: 24px;
            }

            .stats {
                grid-template-columns: repeat(2, 1fr);
                gap: 16px;
                margin-bottom: 24px;
            }

            .main-content {
                padding: 20px;
            }

            .filters {
                grid-template-columns: 1fr;
                gap: 16px;
                margin-bottom: 24px;
            }

            .tasks-table {
                font-size: 12px;
            }

            .tasks-table th,
            .tasks-table td {
                padding: 12px;
            }

            .workers-grid {
                grid-template-columns: 1fr;
            }
        }

        /* Modal Styles */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.7);
            animation: fadeIn 0.3s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        .modal.show {
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .modal-content {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            max-width: 800px;
            width: 90%;
            max-height: 90vh;
            overflow-y: auto;
            padding: 24px;
            position: relative;
            animation: slideIn 0.3s ease;
        }

        @keyframes slideIn {
            from {
                transform: translateY(-50px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border);
        }

        .modal-header h2 {
            font-size: 20px;
            font-weight: 700;
            color: var(--text);
            margin: 0;
        }

        .modal-close {
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 24px;
            cursor: pointer;
            padding: 0;
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: color 0.2s ease;
        }

        .modal-close:hover {
            color: var(--text);
        }

        .detail-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }

        .detail-section {
            margin-bottom: 20px;
        }

        .detail-label {
            font-size: 10px;
            font-weight: 700;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.4px;
            margin-bottom: 8px;
        }

        .detail-value {
            font-size: 13px;
            color: var(--text);
            word-break: break-all;
            padding: 8px;
            background: var(--bg);
            border-radius: 6px;
            border: 1px solid var(--border);
            font-family: 'Monaco', 'Courier New', monospace;
        }

        .detail-value.text {
            font-family: inherit;
        }

        .detail-value.json {
            max-height: 200px;
            overflow-y: auto;
            white-space: pre-wrap;
        }

        .detail-row {
            grid-column: 1 / -1;
        }

        .clickable-row {
            cursor: pointer;
        }

        .clickable-row:hover {
            background: var(--border) !important;
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h1>Task Dashboard</h1>
                    <p>Real-time task monitoring and management</p>
                </div>
                <div style="display: flex; gap: 16px; align-items: center;">
                    <a href="/redoc" target="_blank" style="padding: 8px 14px; background: var(--primary); color: white; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: 600; transition: all 0.2s ease;" onmouseover="this.style.background='var(--primary-dark)'" onmouseout="this.style.background='var(--primary)'">
                        📚 API Docs
                    </a>
                    <div id="mode-badge" style="padding: 8px 16px; border-radius: 8px; font-size: 12px; font-weight: 600;">
                        Loading...
                    </div>
                </div>
            </div>
        </div>
    </header>

    <div class="container">
        <div class="time-picker-section">
            <div class="time-picker-container">
                <div class="filter-group">
                    <label for="filter-relative-time">Time Range</label>
                    <select id="filter-relative-time" onchange="updateAbsoluteDates()">
                        <option value="">All Time</option>
                        <option value="1h">Last 1 Hour</option>
                        <option value="6h">Last 6 Hours</option>
                        <option value="24h">Last 24 Hours</option>
                        <option value="7d">Last 7 Days</option>
                        <option value="30d">Last 30 Days</option>
                    </select>
                </div>

                <div class="filter-group">
                    <label for="filter-time-from">From</label>
                    <input type="datetime-local" id="filter-time-from" onchange="applyTimeFilter()">
                </div>

                <div class="filter-group">
                    <label for="filter-time-to">To</label>
                    <input type="datetime-local" id="filter-time-to" onchange="applyTimeFilter()">
                </div>

                <button class="btn-secondary" onclick="clearTimeFilter()" style="align-self: flex-end; margin-bottom: 0;">Clear</button>
            </div>
        </div>

        <div class="stats" id="stats">
            <div class="stat-card">
                <div class="stat-label">
                    Total Tasks
                </div>
                <div class="stat-number" id="stat-total">0</div>
            </div>
            <div class="stat-card pending">
                <div class="stat-label">
                    Pending
                </div>
                <div class="stat-number" id="stat-pending">0</div>
            </div>
            <div class="stat-card running">
                <div class="stat-label">
                    Running
                </div>
                <div class="stat-number" id="stat-running">0</div>
            </div>
            <div class="stat-card completed">
                <div class="stat-label">
                    Completed
                </div>
                <div class="stat-number" id="stat-completed">0</div>
            </div>
            <div class="stat-card failed">
                <div class="stat-label">
                    Failed
                </div>
                <div class="stat-number" id="stat-failed">0</div>
            </div>
            <div class="stat-card failed">
                <div class="stat-label">
                    Permanent
                </div>
                <div class="stat-number" id="stat-failed-permanent">0</div>
            </div>
        </div>

        <div id="create-task-section" class="main-content" style="display: none; margin-bottom: 24px;">
            <h2 class="section-title">Create New Task</h2>
            <div class="filters">
                <div class="filter-group">
                    <label for="create-task-name">Task Name *</label>
                    <input type="text" id="create-task-name" placeholder="e.g., send_email, process_data">
                </div>

                <div class="filter-group">
                    <label for="create-task-priority">Priority</label>
                    <input type="number" id="create-task-priority" placeholder="0" min="0" value="0">
                </div>

                <div class="filter-group">
                    <label for="create-task-args">Args (JSON)</label>
                    <input type="text" id="create-task-args" placeholder='{}' value="{}">
                </div>

                <div class="filter-group">
                    <label for="create-task-kwargs">Kwargs (JSON)</label>
                    <input type="text" id="create-task-kwargs" placeholder='{}' value="{}">
                </div>

                <div class="filter-actions">
                    <button class="btn-primary" onclick="createTask()">Create Task</button>
                    <button class="btn-secondary" onclick="clearCreateForm()">Reset</button>
                </div>
            </div>
            <div id="create-error-message"></div>
        </div>

        <div class="main-content">
            <h2 class="section-title">Filter Tasks</h2>

            <div class="filters">
                <div class="filter-group">
                    <label for="filter-state">State</label>
                    <select id="filter-state">
                        <option value="">All States</option>
                        <option value="pending">Pending</option>
                        <option value="running">Running</option>
                        <option value="completed">Completed</option>
                        <option value="failed">Failed</option>
                    </select>
                </div>

                <div class="filter-group">
                    <label for="filter-name">Task Name</label>
                    <input type="text" id="filter-name" placeholder="Search tasks...">
                </div>

                <div class="filter-group">
                    <label for="filter-worker">Worker ID</label>
                    <input type="text" id="filter-worker" placeholder="Filter by worker...">
                </div>

                <div class="filter-group">
                    <label for="filter-priority">Min Priority</label>
                    <input type="number" id="filter-priority" placeholder="0" min="0">
                </div>

                <div class="filter-group">
                    <label for="filter-retries">Min Retries</label>
                    <input type="number" id="filter-retries" placeholder="0" min="0">
                </div>

                <div class="filter-actions">
                    <button class="btn-primary" onclick="loadTasks()">Search</button>
                    <button class="btn-secondary" onclick="clearFilters()">Reset</button>
                </div>
            </div>

            <div id="error-message"></div>

            <h2 class="section-title">Tasks</h2>
            <div id="tasks-container" class="loading">Loading tasks...</div>

            <div id="workers-section" class="workers-section" style="display: none;">
                <h2 class="section-title">Active Workers</h2>
                <div id="workers-container" class="workers-grid"></div>
            </div>
        </div>
    </div>

    <!-- Task Detail Modal -->
    <div id="task-detail-modal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modal-task-name"></h2>
                <button class="modal-close" onclick="closeTaskModal()">✕</button>
            </div>
            <div class="detail-grid" id="modal-task-details"></div>
        </div>
    </div>

    <script>
        let currentOffset = 0;
        const LIMIT = 50;

        function updateAbsoluteDates() {
            const relative = document.getElementById('filter-relative-time').value;
            const now = new Date();
            let from = new Date();

            if (relative === '1h') from.setHours(from.getHours() - 1);
            else if (relative === '6h') from.setHours(from.getHours() - 6);
            else if (relative === '24h') from.setDate(from.getDate() - 1);
            else if (relative === '7d') from.setDate(from.getDate() - 7);
            else if (relative === '30d') from.setDate(from.getDate() - 30);
            else {
                document.getElementById('filter-time-from').value = '';
                document.getElementById('filter-time-to').value = '';
                return;
            }

            // Format as datetime-local (YYYY-MM-DDTHH:mm)
            document.getElementById('filter-time-from').value = from.toISOString().slice(0, 16);
            document.getElementById('filter-time-to').value = now.toISOString().slice(0, 16);

            applyTimeFilter();
        }

        function applyTimeFilter() {
            loadStats();
            loadTasks();
        }

        function getTimeParams() {
            const from = document.getElementById('filter-time-from').value;
            const to = document.getElementById('filter-time-to').value;
            const params = {};

            if (from) {
                const fromDate = new Date(from);
                params.created_after = fromDate.toISOString();
            }
            if (to) {
                const toDate = new Date(to);
                params.created_before = toDate.toISOString();
            }

            return params;
        }

        async function loadStats() {
            try {
                const timeParams = getTimeParams();
                const params = new URLSearchParams(timeParams);
                const response = await fetch(`/api/stats?${params}`);
                const stats = await response.json();

                document.getElementById('stat-total').textContent = stats.total;
                document.getElementById('stat-pending').textContent = stats.pending;
                document.getElementById('stat-running').textContent = stats.running;
                document.getElementById('stat-completed').textContent = stats.completed;
                document.getElementById('stat-failed').textContent = stats.failed;
                document.getElementById('stat-failed-permanent').textContent = stats.failed_permanent;
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }

        async function loadTasks(offset = 0) {
            currentOffset = offset;
            const state = document.getElementById('filter-state').value;
            const name = document.getElementById('filter-name').value;
            const worker_id = document.getElementById('filter-worker').value;
            const priority_min = document.getElementById('filter-priority').value;
            const retry_count_min = document.getElementById('filter-retries').value;

            const params = new URLSearchParams();
            if (state) params.append('state', state);
            if (name) params.append('name', name);
            if (worker_id) params.append('worker_id', worker_id);
            if (priority_min) params.append('priority_min', priority_min);
            if (retry_count_min) params.append('retry_count_min', retry_count_min);

            // Add time parameters
            const timeParams = getTimeParams();
            if (timeParams.created_after) params.append('created_after', timeParams.created_after);
            if (timeParams.created_before) params.append('created_before', timeParams.created_before);

            params.append('limit', LIMIT);
            params.append('offset', offset);

            try {
                document.getElementById('error-message').innerHTML = '';
                document.getElementById('tasks-container').innerHTML = '<div class="loading">Loading tasks...</div>';

                const response = await fetch(`/api/tasks?${params}`);
                if (!response.ok) throw new Error('Failed to load tasks');

                const tasks = await response.json();
                renderTasks(tasks);
            } catch (error) {
                document.getElementById('error-message').innerHTML = `<div class="error">Error: ${error.message}</div>`;
                document.getElementById('tasks-container').innerHTML = '';
            }
        }

        function renderTasks(tasks) {
            if (tasks.length === 0) {
                document.getElementById('tasks-container').innerHTML = '<div class="loading">No tasks found</div>';
                return;
            }

            let html = '<table class="tasks-table"><thead><tr>';
            html += '<th>Task Name</th>';
            html += '<th>State</th>';
            html += '<th>Created</th>';
            html += '<th>Started</th>';
            html += '<th>Completed</th>';
            html += '<th>Worker</th>';
            html += '<th>Retries</th>';
            html += '<th>Priority</th>';
            if (window.dashboardMode === 'readwrite') {
                html += '<th>Actions</th>';
            }
            html += '</tr></thead><tbody>';

            tasks.forEach(task => {
                const stateClass = `status-${task.state}`;
                const stateEmoji = {
                    pending: '⏳',
                    running: '⚙️',
                    completed: '✅',
                    failed: '❌'
                }[task.state] || '•';

                html += `<tr class="clickable-row" onclick="openTaskModal('${task.id}')">`;
                html += `<td><span class="task-name">${escapeHtml(task.name)}</span><span class="task-id">${task.id.substring(0, 12)}...</span></td>`;
                html += `<td><span class="status-badge ${stateClass}">${task.state}</span></td>`;
                html += `<td>${formatDate(task.created_at)}</td>`;
                html += `<td>${task.started_at ? formatDate(task.started_at) : '–'}</td>`;
                html += `<td>${task.completed_at ? formatDate(task.completed_at) : '–'}</td>`;
                html += `<td style="font-family: monospace; font-size: 12px;">${task.worker_id ? task.worker_id.substring(0, 8) : '–'}</td>`;
                html += `<td>${task.retry_count}/${task.max_retries}</td>`;
                html += `<td>${task.priority}</td>`;
                if (window.dashboardMode === 'readwrite') {
                    let actions = '';
                    if (task.state === 'pending') {
                        actions += `<button class="btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="event.stopPropagation(); cancelTask('${task.id}')">Cancel</button>`;
                    }
                    html += `<td>${actions || '–'}</td>`;
                }
                html += '</tr>';
            });

            html += '</tbody></table>';

            if (tasks.length === LIMIT) {
                html += '<div class="pagination">';
                if (currentOffset > 0) {
                    html += `<button class="btn-primary" onclick="loadTasks(${currentOffset - LIMIT})">← Previous</button>`;
                }
                html += `<button class="btn-primary" onclick="loadTasks(${currentOffset + LIMIT})">Next →</button>`;
                html += '</div>';
            }

            document.getElementById('tasks-container').innerHTML = html;
        }

        async function loadWorkers() {
            try {
                const response = await fetch('/api/workers');
                const workers = await response.json();

                if (workers.length === 0) {
                    document.getElementById('workers-section').style.display = 'none';
                    return;
                }

                document.getElementById('workers-section').style.display = 'block';

                let html = '';
                workers.forEach(worker => {
                    html += '<div class="worker-card">';
                    html += `<h4>Worker</h4>`;
                    html += `<div class="worker-id">${worker.worker_id}</div>`;
                    html += `<div class="worker-info">`;
                    html += `  <span>Locked Tasks</span>`;
                    html += `  <strong>${worker.locked_tasks}</strong>`;
                    html += `</div>`;
                    if (worker.earliest_lock_expires) {
                        html += `<div class="worker-info">`;
                        html += `  <span>Lock Expires</span>`;
                        html += `  <strong>${formatDate(worker.earliest_lock_expires)}</strong>`;
                        html += `</div>`;
                    }
                    html += '</div>';
                });

                document.getElementById('workers-container').innerHTML = html;
            } catch (error) {
                console.error('Error loading workers:', error);
            }
        }

        function formatDate(dateString) {
            const date = new Date(dateString);
            return date.toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function clearTimeFilter() {
            document.getElementById('filter-relative-time').value = '';
            document.getElementById('filter-time-from').value = '';
            document.getElementById('filter-time-to').value = '';
            applyTimeFilter();
        }

        function clearFilters() {
            document.getElementById('filter-state').value = '';
            document.getElementById('filter-name').value = '';
            document.getElementById('filter-worker').value = '';
            document.getElementById('filter-priority').value = '';
            document.getElementById('filter-retries').value = '';
            clearTimeFilter();
        }

        async function loadMode() {
            try {
                const response = await fetch('/api/mode');
                const data = await response.json();
                window.dashboardMode = data.mode;

                const badge = document.getElementById('mode-badge');
                if (data.mode === 'readwrite') {
                    badge.textContent = '✏️ Read & Write';
                    badge.style.background = 'rgba(59, 130, 246, 0.2)';
                    badge.style.color = 'var(--primary)';
                    document.getElementById('create-task-section').style.display = 'block';
                } else {
                    badge.textContent = '👁️ Read Only';
                    badge.style.background = 'rgba(107, 114, 128, 0.2)';
                    badge.style.color = 'var(--text-secondary)';
                    document.getElementById('create-task-section').style.display = 'none';
                }
            } catch (error) {
                console.error('Error loading mode:', error);
            }
        }

        async function createTask() {
            const name = document.getElementById('create-task-name').value.trim();
            if (!name) {
                document.getElementById('create-error-message').innerHTML = '<div class="error">Task name is required</div>';
                return;
            }

            const argsText = document.getElementById('create-task-args').value;
            const kwargsText = document.getElementById('create-task-kwargs').value;
            const priority = document.getElementById('create-task-priority').value;

            const params = new URLSearchParams({
                name: name,
                args: argsText,
                kwargs: kwargsText,
                priority: priority
            });

            try {
                const response = await fetch(`/api/tasks?${params}`, {
                    method: 'POST'
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to create task');
                }

                const task = await response.json();
                document.getElementById('create-error-message').innerHTML = '<div class="error" style="background: rgba(59, 130, 246, 0.1); color: var(--primary); border-left-color: var(--primary);">✓ Task created successfully</div>';
                clearCreateForm();
                setTimeout(() => {
                    loadTasks();
                    loadStats();
                }, 500);
            } catch (error) {
                document.getElementById('create-error-message').innerHTML = `<div class="error">Error: ${error.message}</div>`;
            }
        }

        function clearCreateForm() {
            document.getElementById('create-task-name').value = '';
            document.getElementById('create-task-priority').value = '0';
            document.getElementById('create-task-args').value = '{}';
            document.getElementById('create-task-kwargs').value = '{}';
            document.getElementById('create-error-message').innerHTML = '';
        }

        async function openTaskModal(taskId) {
            try {
                const response = await fetch(`/api/task/${taskId}`);
                if (!response.ok) throw new Error('Failed to load task');

                const task = await response.json();
                displayTaskDetail(task);

                const modal = document.getElementById('task-detail-modal');
                modal.classList.add('show');
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }

        function closeTaskModal() {
            const modal = document.getElementById('task-detail-modal');
            modal.classList.remove('show');
        }

        function displayTaskDetail(task) {
            document.getElementById('modal-task-name').textContent = task.name;

            let html = '';

            // Task ID
            html += '<div class="detail-section">';
            html += '<div class="detail-label">Task ID</div>';
            html += `<div class="detail-value">${task.id}</div>`;
            html += '</div>';

            // State
            html += '<div class="detail-section">';
            html += '<div class="detail-label">State</div>';
            html += `<div class="detail-value text"><span class="status-badge status-${task.state}">${task.state}</span></div>`;
            html += '</div>';

            // Priority
            html += '<div class="detail-section">';
            html += '<div class="detail-label">Priority</div>';
            html += `<div class="detail-value text">${task.priority}</div>`;
            html += '</div>';

            // Worker ID
            html += '<div class="detail-section">';
            html += '<div class="detail-label">Worker ID</div>';
            html += `<div class="detail-value">${task.worker_id ? task.worker_id : '–'}</div>`;
            html += '</div>';

            // Retry Count
            html += '<div class="detail-section">';
            html += '<div class="detail-label">Retries</div>';
            html += `<div class="detail-value text">${task.retry_count}/${task.max_retries}</div>`;
            html += '</div>';

            // Created At
            html += '<div class="detail-section">';
            html += '<div class="detail-label">Created At</div>';
            html += `<div class="detail-value text">${formatDate(task.created_at)}</div>`;
            html += '</div>';

            // Scheduled At
            html += '<div class="detail-section">';
            html += '<div class="detail-label">Scheduled At</div>';
            html += `<div class="detail-value text">${formatDate(task.scheduled_at)}</div>`;
            html += '</div>';

            // Started At
            html += '<div class="detail-section">';
            html += '<div class="detail-label">Started At</div>';
            html += `<div class="detail-value text">${task.started_at ? formatDate(task.started_at) : '–'}</div>`;
            html += '</div>';

            // Completed At
            html += '<div class="detail-section">';
            html += '<div class="detail-label">Completed At</div>';
            html += `<div class="detail-value text">${task.completed_at ? formatDate(task.completed_at) : '–'}</div>`;
            html += '</div>';

            // Args
            html += '<div class="detail-section detail-row">';
            html += '<div class="detail-label">Arguments</div>';
            html += `<div class="detail-value json">${JSON.stringify(task.args, null, 2)}</div>`;
            html += '</div>';

            // Kwargs
            html += '<div class="detail-section detail-row">';
            html += '<div class="detail-label">Keyword Arguments</div>';
            html += `<div class="detail-value json">${JSON.stringify(task.kwargs, null, 2)}</div>`;
            html += '</div>';

            // Tags
            html += '<div class="detail-section detail-row">';
            html += '<div class="detail-label">Tags</div>';
            html += `<div class="detail-value json">${JSON.stringify(task.tags, null, 2)}</div>`;
            html += '</div>';

            // Result
            if (task.result) {
                html += '<div class="detail-section detail-row">';
                html += '<div class="detail-label">Result</div>';
                html += `<div class="detail-value json">${JSON.stringify(task.result, null, 2)}</div>`;
                html += '</div>';
            }

            // Error
            if (task.error) {
                html += '<div class="detail-section detail-row">';
                html += '<div class="detail-label">Error</div>';
                html += `<div class="detail-value json" style="color: var(--failed);">${escapeHtml(task.error)}</div>`;
                html += '</div>';
            }

            // Mock Logs section
            html += '<div class="detail-section detail-row">';
            html += '<div class="detail-label">Logs</div>';
            html += '<div class="detail-value json" style="color: var(--text-secondary);">';
            html += '[2024-10-25 10:23:45] Task started\n';
            html += '[2024-10-25 10:23:46] Processing input data...\n';
            html += '[2024-10-25 10:23:47] Validation passed\n';
            html += '[2024-10-25 10:23:48] Executing main logic...\n';
            html += '[2024-10-25 10:23:49] Writing results to database\n';
            html += '[2024-10-25 10:23:50] Task completed successfully';
            html += '</div>';
            html += '</div>';

            document.getElementById('modal-task-details').innerHTML = html;
        }

        async function cancelTask(taskId) {
            if (!confirm('Are you sure you want to cancel this task?')) {
                return;
            }

            try {
                const response = await fetch(`/api/tasks/${taskId}/cancel`, {
                    method: 'PATCH'
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to cancel task');
                }

                loadTasks();
                loadStats();
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }

        // Close modal when clicking outside
        document.getElementById('task-detail-modal').addEventListener('click', function(event) {
            if (event.target === this) {
                closeTaskModal();
            }
        });

        // Initial load
        loadMode();
        loadStats();
        loadTasks();
        loadWorkers();

        // Refresh stats and workers every 5 seconds
        setInterval(() => {
            loadStats();
            loadWorkers();
        }, 5000);
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8696"))
    uvicorn.run(app, host="0.0.0.0", port=port)
