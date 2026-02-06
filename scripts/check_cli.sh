#!/bin/bash
set -e

echo "Running type checks..."
mypy --strict src/codemap/cli/

echo "Running linter..."
ruff check src/codemap/cli/ tests/unit/cli/

echo "Checking formatting..."
ruff format --check src/codemap/cli/ tests/unit/cli/

echo "Running tests..."
pytest tests/unit/cli/ -v

echo "Checking coverage..."
pytest --cov=src/codemap/cli --cov-report=term-missing --cov-fail-under=100

echo "All checks passed!"
