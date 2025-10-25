.PHONY: help install test test-unit test-integration db-up db-down lint format check

help:
	@echo "tasklib - Simple, durable task queue for PostgreSQL"
	@echo ""
	@echo "Available commands:"
	@echo "  make install          Install dependencies"
	@echo "  make db-up            Start PostgreSQL (docker-compose)"
	@echo "  make db-down          Stop PostgreSQL"
	@echo "  make test             Run all tests"
	@echo "  make test-unit        Run unit tests only (no DB required)"
	@echo "  make test-integration Run integration tests (requires DB)"
	@echo "  make lint             Run linting"
	@echo "  make format           Format code"
	@echo "  make check            Run all checks (lint + tests)"

install:
	uv sync --extra dev

db-up:
	docker-compose up -d
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 5

db-down:
	docker-compose down

test: db-up
	uv run pytest tests/ -v

test-unit:
	uv run pytest tests/test_core.py -v

test-integration: db-up
	uv run pytest tests/test_integration.py -v

lint:
	uv run ruff check src/ tests/ examples/

format:
	uv run ruff format src/ tests/ examples/

check: lint test
	@echo "All checks passed!"

format-check:
	uv run ruff format --check src/ tests/ examples/
