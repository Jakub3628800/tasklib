.PHONY: serve serve-reload build clean help

help:
	@echo "TaskLib Documentation"
	@echo ""
	@echo "Available commands:"
	@echo "  make serve        - Serve docs on http://localhost:8000"
	@echo "  make serve-reload - Serve with auto-reload on file changes"
	@echo "  make build        - Build static site"
	@echo "  make clean        - Remove build artifacts"

serve:
	uv run mkdocs serve -f mkdocs.yml --dev-addr localhost:8000

serve-reload:
	uv run mkdocs serve -f mkdocs.yml --dev-addr localhost:8000

build:
	uv run mkdocs build -f mkdocs.yml

clean:
	rm -rf site/
