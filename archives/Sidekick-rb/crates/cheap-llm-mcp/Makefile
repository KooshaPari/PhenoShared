.PHONY: install test lint fmt fmt-check verify doctor clean

install:
	python3 -m pip install -e ".[dev]"

test:
	python3 -m pytest -q

lint:
	ruff check src/ tests/

fmt:
	ruff format src/ tests/

fmt-check:
	ruff format --check src/ tests/

verify: lint fmt-check test
	@echo "✓ lint + format + tests all green"

doctor:
	cheap-llm doctor

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} +
