.PHONY: test test-unit test-integration uvlock db-up db-down run

db-up:
	docker compose up -d
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 5

db-down:
	docker compose down

test: db-up
	uv run pytest src/tests/ -v

test-unit:
	uv run pytest src/tests/test_core.py -v

test-integration: db-up
	uv run pytest src/tests/test_integration.py -v

uvlock:
	uv lock

run: %
	uv run --isolated tasklib $(filter-out run,$(MAKECMDGOALS))

%:
	@true
