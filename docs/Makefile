.PHONY: help serve build clean install

help:
	@echo "TaskLib Documentation Build"
	@echo ""
	@echo "Commands (using uv with --isolated):"
	@echo "  make install    Install mkdocs via uv"
	@echo "  make serve      Serve docs locally (http://localhost:8000)"
	@echo "  make build      Build static documentation"
	@echo "  make clean      Remove build artifacts"
	@echo ""
	@echo "Deploy:"
	@echo "  GitHub Pages:   Push to gh-pages branch"
	@echo "  Netlify:        Connect repo to Netlify"
	@echo "  ReadTheDocs:    Import repo to Read the Docs"

install:
	cd .. && uv pip install --isolated mkdocs mkdocs-material

serve:
	cd .. && uv run --isolated mkdocs serve

build:
	cd .. && uv run --isolated mkdocs build --site-dir site

clean:
	rm -rf ../site
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

.DEFAULT_GOAL := help
