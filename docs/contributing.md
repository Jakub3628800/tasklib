# Contributing to TaskLib

We love contributions! This document explains how to contribute to TaskLib.

## Getting Started

### Prerequisites

- Python 3.13+
- PostgreSQL 13+
- `uv` package manager

### Setup Development Environment

```bash
git clone https://github.com/your-org/tasklib.git
cd tasklib
uv sync --extra dev
```

### Start PostgreSQL

```bash
docker-compose up
```

## Development Workflow

### Running Tests

```bash
# Run all tests
make test

# Run only unit tests
make test-unit

# Run only integration tests
make test-integration
```

### Code Quality

```bash
# Check code style
make lint

# Format code
make format

# Run both checks and tests
make check
```

### Building Documentation

```bash
cd docs
make install
make serve
```

Documentation will be available at `http://localhost:8000`

## Making Changes

### Code Changes

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes
3. Add tests for new functionality
4. Run `make check` to ensure code quality
5. Commit with a clear message: `git commit -m "Add feature description"`
6. Push and create a pull request

### Documentation Changes

1. Edit files in the `docs/` directory
2. Follow existing markdown style
3. Test locally with `make serve`
4. Commit and push

## Testing Guidelines

- Write unit tests in `tests/test_core.py` for isolated functionality
- Write integration tests in `tests/test_integration.py` for full workflows
- Aim for >80% code coverage
- Use meaningful test names that describe what is being tested

## Code Style

TaskLib follows PEP 8 with some preferences:

- Use type hints for all functions
- Use docstrings for public APIs
- Maximum line length: 88 characters (enforced by ruff)
- Use async/await for I/O operations

The `ruff` formatter and linter will enforce these automatically when you run `make format` and `make lint`.

## Commit Messages

- Keep messages short and descriptive
- Use imperative mood ("Add feature" not "Added feature")
- Reference issues if applicable: "Fix #123"

Example:
```
Add retry backoff configuration option

Allows users to customize exponential backoff multiplier for task retries.
```

## Submitting Pull Requests

1. **Title**: Clear, concise description of changes
2. **Description**:
   - What problem does this solve?
   - How does it work?
   - Any breaking changes?
3. **Tests**: Include tests for new functionality
4. **Documentation**: Update docs for user-facing changes
5. **Review**: Address review comments and discussions

## Areas for Contribution

- **Bug fixes**: Check open issues
- **Performance improvements**: Profile and optimize
- **Documentation**: Improve guides and examples
- **Examples**: Add real-world usage examples
- **Tests**: Increase coverage
- **Features**: Propose enhancements in issues first

## Questions?

- Open an issue for bugs or feature requests
- Check [FAQ](./faq.md) for common questions
- Read [Architecture Overview](./design.md) to understand the system

## License

By contributing to TaskLib, you agree that your contributions will be licensed under the MIT License.

Thank you for contributing to TaskLib!
