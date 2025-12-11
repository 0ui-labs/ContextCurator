# Contributing to Codemap

**Strict Test-Driven Development (TDD) Philosophy**

This project follows **strict Test-Driven Development (TDD)**. All code must be test-first, and coverage must remain at 100%.

## TDD Workflow

### Red-Green-Refactor Cycle

#### Step 1 - Red Phase: Write the Test First

Write the test first in `tests/unit/` or `tests/integration/`, then run `pytest`. The test **must fail** with a clear error message showing what functionality is missing.

```bash
pytest
```

Expected result: Test fails (Red Phase)

#### Step 2 - Green Phase: Implement Minimal Code

Implement the minimal code necessary in `src/codemap/` to make the test pass. Run `pytest` again to verify the test passes.

```bash
pytest
```

Expected result: Test passes (Green Phase)

#### Step 3 - Refactor Phase: Improve Code Quality

Improve code quality, readability, and structure while keeping all tests green. Verify coverage stays at 100%.

```bash
pytest
```

Expected result: All tests pass, coverage remains 100%

#### Step 4 - Quality Gates: Run All Checks

Before committing, ensure all quality gates pass:

- Type checking: `mypy src/` (no type errors)
- Linting: `ruff check src/ tests/` (no linting issues)
- Formatting: `ruff format src/ tests/` (consistent formatting)

## Development Commands

### Installation

Install all development dependencies:

```bash
pip install -r requirements-dev.txt
```

### Testing

Run tests with coverage:

```bash
pytest
```

This uses the configuration in `pyproject.toml` which automatically enables coverage reporting with `--cov=src/codemap --cov-report=term-missing --cov-report=html` and strict test discovery.

Check detailed coverage report:

```bash
open htmlcov/index.html  # macOS
# or
start htmlcov/index.html  # Windows
# or
xdg-open htmlcov/index.html  # Linux
```

### Code Quality

Type checking:

```bash
mypy src/
```

Linting:

```bash
ruff check src/ tests/
```

Auto-fix linting issues:

```bash
ruff check --fix src/ tests/
```

Format code:

```bash
ruff format src/ tests/
```

### Documentation

Build documentation:

```bash
mkdocs build
```

Serve documentation locally:

```bash
mkdocs serve
```

Then open http://127.0.0.1:8000 in your browser.

## Coverage Requirements

This project enforces **100% code coverage** via the `fail_under=100` setting in `pyproject.toml`. The pytest run will fail if coverage drops below 100%.

### Excluded Patterns

The following patterns are excluded from coverage requirements:

- Lines marked with `# pragma: no cover`
- `if __name__ == "__main__":` blocks
- Abstract methods (methods decorated with `@abstractmethod`)
- String representation methods (`def __repr__` and `def __str__`)
- Defensive assertions (`raise AssertionError` and `raise NotImplementedError`)
- Type checking blocks (`if TYPE_CHECKING:`)

### Identifying Missing Coverage

If coverage drops below 100%, identify the missing tests by:

1. Checking the terminal output for uncovered line numbers
2. Opening `htmlcov/index.html` in your browser to see a visual report
3. Looking for red-highlighted lines in the HTML report

## Pull Request Checklist

Before submitting a pull request, ensure:

- [ ] All tests pass (`pytest`)
- [ ] Coverage is 100% (`pytest` shows no missing lines)
- [ ] Type checking passes (`mypy src/`)
- [ ] Linting passes (`ruff check src/ tests/`)
- [ ] Code is formatted (`ruff format src/ tests/`)
- [ ] Documentation updated (if adding new modules/functions)
- [ ] Commit messages follow [conventional commits](https://www.conventionalcommits.org/) format (optional but recommended): `feat:`, `fix:`, `docs:`, `refactor:`, etc.

## Questions?

If you have questions about the TDD workflow or contribution process, please open an issue for discussion.
