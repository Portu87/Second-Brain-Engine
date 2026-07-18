.PHONY: install lint format typecheck test check

install:
	python -m pip install -e ".[dev]"

lint:
	ruff check .
	ruff format --check .

format:
	ruff check --fix .
	ruff format .

typecheck:
	mypy src

test:
	pytest --cov=second_brain_engine --cov-report=term-missing

check: lint typecheck test
