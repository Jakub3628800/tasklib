# Database Migrations

Adding tasks table to existing database.

## Alembic Migration

```bash
cp ../migrations/001_add_tasks_table.py \
   your_project/alembic/versions/

alembic upgrade head
```

## Raw SQL

```bash
psql -d your_db -f ../migrations/001_add_tasks_table.sql
```

See [MIGRATIONS.md](../../MIGRATIONS.md) for detailed instructions.
