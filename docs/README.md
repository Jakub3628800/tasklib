# Documentation

Complete TaskLib documentation organized by topic.

## Structure

```
docs/
├── index.md                     # Main documentation home
├── getting-started/
│   ├── installation.md          # Install TaskLib
│   ├── quick-start.md           # 5-minute quick start
│   └── first-task.md            # Step-by-step first task
├── guides/
│   ├── task-definition.md       # How to define tasks
│   ├── task-submission.md       # How to submit tasks
│   ├── workers.md               # Running workers
│   ├── monitoring.md            # Monitor task status
│   ├── error-handling.md        # Handle failures
│   └── testing.md               # Testing guide
├── api/
│   ├── core.md                  # Core API reference
│   ├── configuration.md         # Config options
│   ├── worker.md                # Worker class reference
│   └── exceptions.md            # Exception reference
├── schema/
│   ├── database.md              # Database schema
│   ├── task-states.md           # Task lifecycle
│   └── migrations.md            # Database migrations
├── examples/
│   ├── simple.md                # Simple example
│   ├── fastapi.md               # FastAPI integration
│   └── django.md                # Django integration
├── architecture/
│   ├── design.md                # Architecture & design
│   └── specification.md         # Full specification
├── faq.md                       # Frequently asked questions
├── contributing.md              # Contributing guide
└── Makefile                     # Documentation build
```

## Build & Serve

```bash
# Install dependencies
cd docs
make install

# Serve locally (http://localhost:8000)
make serve

# Build static site
make build

# Clean build
make clean
```

## Navigation

- **[Home](index.md)** - Start here
- **[Installation](getting-started/installation.md)** - Get started
- **[Quick Start](getting-started/quick-start.md)** - 5 minutes
- **[API Reference](api/core.md)** - Complete API
- **[Examples](examples/simple.md)** - Code examples
- **[FAQ](faq.md)** - Common questions

## Publishing

### GitHub Pages

```bash
# Build docs
make build

# Push to gh-pages branch
git checkout --orphan gh-pages
git add site/
git commit -m "Deploy docs"
git push origin gh-pages

# Configure in GitHub Settings:
# Pages → Branch: gh-pages → Root
```

### Netlify

1. Push to GitHub
2. Connect repo to Netlify
3. Build command: `cd docs && make build`
4. Publish directory: `site`

### Read the Docs

1. Import project at readthedocs.org
2. Select GitHub repo
3. Auto-builds on push

## Content Guidelines

- Use clear, practical examples
- Include both simple and advanced topics
- Keep code snippets runnable
- Link between related pages
- Update frequently

## Dependencies

- mkdocs - Documentation generator
- mkdocs-material - Material Design theme

Install with:

```bash
pip install mkdocs mkdocs-material
```

## Questions?

See [FAQ](faq.md) or check [Contributing](contributing.md) guide.
