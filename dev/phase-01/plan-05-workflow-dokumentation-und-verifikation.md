I have created the following plan after thorough exploration and analysis of the codebase. Follow the below plan verbatim. Trust the files and references. Do not re-verify what's written in the plan. Explore only when absolutely necessary. First implement all the proposed file changes and then I'll review all the changes together at the end.

## Observations

The project has completed its technical foundation (src layout, strict tooling in `pyproject.toml`, MkDocs infrastructure, and initial TDD proof-of-concept tests). The final phase requires **developer-facing documentation** to onboard contributors, enforce the TDD workflow, and provide verification scripts. This completes the "ready to code" greenfield setup by documenting the established conventions and quality gates.

## Approach

Create three key files that serve distinct purposes: `CONTRIBUTING.md` as the **TDD workflow bible** (Red-Green-Refactor cycle with tool commands), `README.md` as the **project landing page** (overview, installation, quick start, links to MkDocs), and `setup_check.py` as an **automated verification script** (installs deps, runs pytest with coverage, builds docs, validates 100% coverage). This approach ensures contributors understand the strict TDD philosophy before writing code, provides a single entry point for new users, and offers a one-command health check for the entire toolchain.

## Implementation Steps

### 1. Create CONTRIBUTING.md - TDD Workflow Documentation

Create `file:CONTRIBUTING.md` in the project root with the following sections:

**Header Section:**
- Title: "Contributing to Codemap"
- Subtitle emphasizing strict TDD philosophy
- Statement: "This project follows **strict Test-Driven Development (TDD)**. All code must be test-first, and coverage must remain at 100%."

**TDD Workflow Section:**
- **Step 1 - Red Phase:** Write the test first in `tests/unit/` or `tests/integration/`, run `pytest` (must fail with clear error)
- **Step 2 - Green Phase:** Implement minimal code in `src/codemap/` to make test pass, run `pytest` again (must pass)
- **Step 3 - Refactor Phase:** Improve code quality while keeping tests green, verify coverage stays at 100%
- **Step 4 - Quality Gates:** Run `mypy src/` (no type errors), `ruff check src/ tests/` (no linting issues), `ruff format src/ tests/` (consistent formatting)

**Development Commands Section:**
- Install dependencies: `pip install -r requirements-dev.txt`
- Run tests with coverage: `pytest` (uses `pyproject.toml` defaults for `--cov` flags)
- Check coverage report: Open `htmlcov/index.html` in browser
- Type checking: `mypy src/`
- Linting: `ruff check src/ tests/`
- Auto-fix linting: `ruff check --fix src/ tests/`
- Format code: `ruff format src/ tests/`
- Build docs: `mkdocs build`
- Serve docs locally: `mkdocs serve` (opens at http://127.0.0.1:8000)

**Coverage Requirements Section:**
- Explain `fail_under=100` in `pyproject.toml`
- List excluded patterns (pragma: no cover, `if __name__ == "__main__":`, abstract methods)
- Guidance: If coverage drops below 100%, identify missing tests via `htmlcov/index.html` or terminal output

**Pull Request Checklist:**
- [ ] All tests pass (`pytest`)
- [ ] Coverage is 100% (`pytest` shows no missing lines)
- [ ] Type checking passes (`mypy src/`)
- [ ] Linting passes (`ruff check src/ tests/`)
- [ ] Code is formatted (`ruff format src/ tests/`)
- [ ] Documentation updated (if adding new modules/functions)
- [ ] Commit messages follow conventional commits (optional but recommended)

### 2. Create README.md - Project Landing Page

Create `file:README.md` in the project root with the following structure:

**Header:**
- Project title: "# Codemap"
- Tagline: "A professional Python project template with strict TDD enforcement and automatic documentation"
- Badges (optional): Python version, License, Coverage (placeholder for future CI)

**Overview Section:**
- Brief description: "Codemap is a greenfield Python project demonstrating best practices for Test-Driven Development, type safety, and automated documentation generation."
- Key features list:
  - 🧪 **Strict TDD:** 100% code coverage enforced via pytest-cov
  - 🔒 **Type Safety:** mypy in strict mode catches type errors
  - 📚 **Auto Documentation:** MkDocs Material with mkdocstrings generates API docs from docstrings
  - 🎨 **Code Quality:** ruff for linting and formatting
  - 📦 **Modern Layout:** src-based package structure for better test isolation

**Installation Section:**
- Prerequisites: Python >=3.11
- Clone repository: `git clone <repo-url>` (placeholder)
- Create virtual environment: `python -m venv venv`
- Activate venv: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
- Install dependencies: `pip install -r requirements-dev.txt`

**Quick Start Section:**
- Run tests: `pytest`
- View coverage: `open htmlcov/index.html` (Mac) or `start htmlcov/index.html` (Windows)
- Build documentation: `mkdocs build`
- Serve documentation: `mkdocs serve` then open http://127.0.0.1:8000
- Example: Import the package in Python REPL: `from codemap import __version__; print(__version__)`

**Project Structure Section:**
- Visual tree showing key directories and files:
  ```
  ContextCurator/
  ├── src/codemap/          # Main package
  │   ├── __init__.py       # Package version
  │   └── core/             # Core modules
  ├── tests/                # Test suite
  │   ├── unit/             # Unit tests
  │   └── conftest.py       # Pytest fixtures
  ├── docs/                 # Documentation source
  │   ├── index.md          # Home page
  │   └── api.md            # API reference
  ├── pyproject.toml        # Central configuration
  ├── mkdocs.yml            # Docs configuration
  └── requirements-dev.txt  # Development dependencies
  ```

**Documentation Section:**
- Link to full documentation: "For detailed API documentation, see [the docs](./docs/index.md) or run `mkdocs serve`"
- Link to contributing guide: "For development workflow, see [CONTRIBUTING.md](./CONTRIBUTING.md)"

**License Section:**
- Placeholder: "MIT License" or "See LICENSE file" (add actual license if needed)

### 3. Create setup_check.py - Automated Verification Script

Create `file:setup_check.py` in the project root as a Python script that verifies the entire toolchain:

**Script Structure:**

**Imports:**
- `subprocess`, `sys`, `pathlib`

**Function: `run_command(cmd: list[str], description: str) -> bool`:**
- Execute command using `subprocess.run()` with `capture_output=True`
- Print description with emoji (✓ for success, ✗ for failure)
- Return True if returncode == 0, else print stderr and return False

**Function: `main() -> int`:**
- Print header: "🔍 Codemap Setup Verification"
- **Step 1:** Check Python version (>= 3.11) using `sys.version_info`
- **Step 2:** Install dependencies: `run_command(["pip", "install", "-r", "requirements-dev.txt"], "Installing dependencies")`
- **Step 3:** Run pytest: `run_command(["pytest"], "Running tests with coverage")`
- **Step 4:** Check coverage threshold: Parse `htmlcov/index.html` or use `coverage report --fail-under=100`
- **Step 5:** Run mypy: `run_command(["mypy", "src/"], "Type checking with mypy")`
- **Step 6:** Run ruff check: `run_command(["ruff", "check", "src/", "tests/"], "Linting with ruff")`
- **Step 7:** Build docs: `run_command(["mkdocs", "build", "--strict"], "Building documentation")`
- Print summary: "✅ All checks passed! Project is ready to code." or "❌ Some checks failed. See errors above."
- Return 0 if all passed, else 1

**Entry Point:**
- `if __name__ == "__main__": sys.exit(main())`

**Usage Instructions (add to README.md):**
- Add section "Verify Setup" with command: `python setup_check.py`
- Explain: "This script installs dependencies, runs all quality checks, and builds documentation to ensure the project is correctly configured."

### 4. Optional: Create setup_check.sh - Shell Script Alternative

Create `file:setup_check.sh` in the project root as a Bash script (for Unix-like systems):

**Script Content:**
- Shebang: `#!/bin/bash`
- Set strict mode: `set -euo pipefail`
- Echo header: "🔍 Codemap Setup Verification"
- Check Python version: `python --version`
- Install deps: `pip install -r requirements-dev.txt`
- Run pytest: `pytest`
- Run mypy: `mypy src/`
- Run ruff: `ruff check src/ tests/`
- Build docs: `mkdocs build --strict`
- Echo success: "✅ All checks passed!"
- Make executable: `chmod +x setup_check.sh`

**Usage:** `./setup_check.sh`

### 5. Update docs/index.md - Link to Contributing Guide

Enhance `file:docs/index.md` with a new section:

**Contributing Section (add after Quick Start):**
- Heading: "## Contributing"
- Text: "This project follows strict Test-Driven Development. Before contributing, please read our [Contributing Guide](../CONTRIBUTING.md) to understand the TDD workflow and quality requirements."
- Link to GitHub issues (placeholder): "Check out [open issues](https://github.com/your-org/codemap/issues) for tasks to work on."

### 6. Final Verification Checklist

After creating all files, verify:
- [ ] `CONTRIBUTING.md` exists with complete TDD workflow (Red-Green-Refactor)
- [ ] `README.md` exists with installation, quick start, and project structure
- [ ] `setup_check.py` exists and is executable (`python setup_check.py` runs successfully)
- [ ] Optional: `setup_check.sh` exists and is executable (`chmod +x setup_check.sh`)
- [ ] `docs/index.md` links to `CONTRIBUTING.md`
- [ ] All commands in documentation are tested and work (pytest, mypy, ruff, mkdocs)
- [ ] Running `python setup_check.py` passes all checks (green output)

## Summary

This phase completes the greenfield setup by providing comprehensive developer documentation. `CONTRIBUTING.md` enforces the TDD workflow with clear Red-Green-Refactor steps and tool commands. `README.md` serves as the project landing page with installation and quick start instructions. `setup_check.py` automates verification of the entire toolchain (dependencies, tests, coverage, type checking, linting, docs build). Together, these files ensure new contributors understand the strict quality standards and can verify their setup with a single command, making the project truly "ready to code" with TDD enforcement baked in from day one.