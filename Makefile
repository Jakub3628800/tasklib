.PHONY: test test-unit test-integration uvlock run

test-unit:
	uv run --extra dev pytest -m unit -v

test-integration:
	uv run --extra dev pytest -m integration -v

test:
	uv run --extra dev pytest -v

uvlock:
	uv lock

run: %
	uv run --isolated tasklib $(filter-out run,$(MAKECMDGOALS))

%:
	@true
