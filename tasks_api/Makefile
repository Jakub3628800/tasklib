.PHONY: help install run dev-db stop clean

help:
	@echo "TaskLib Dashboard API - Makefile"
	@echo ""
	@echo "Commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make run        - Run the dashboard API (port 8989)"
	@echo "  make dev-db     - Start PostgreSQL in Docker for development"
	@echo "  make stop       - Stop the development database"
	@echo "  make clean      - Clean up Docker containers and cache"

install:
	pip install -r requirements.txt

run:
	python app.py

dev-db:
	@echo "Starting PostgreSQL..."
	docker run -d \
		--name tasklib-postgres \
		-e POSTGRES_DB=tasklib \
		-e POSTGRES_PASSWORD=postgres \
		-p 5432:5432 \
		postgres:15-alpine
	@echo "PostgreSQL started at localhost:5432"
	@echo "Database: tasklib, User: postgres, Password: postgres"
	@echo "Connection string: postgresql://postgres:postgres@localhost:5432/tasklib"

stop:
	@echo "Stopping PostgreSQL..."
	docker stop tasklib-postgres || true
	docker rm tasklib-postgres || true
	@echo "Done"

clean: stop
	@echo "Cleaning up..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".DS_Store" -delete
	@echo "Clean complete"
