# Codemap

A professional Python project template with strict TDD enforcement and automatic documentation

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](htmlcov/index.html)

## Overview

Codemap is a greenfield Python project demonstrating best practices for Test-Driven Development, type safety, and automated documentation generation.

**Key Features:**

- 🧪 **Strict TDD:** 100% code coverage enforced via pytest-cov
- 🔒 **Type Safety:** mypy in strict mode catches type errors
- 📚 **Auto Documentation:** MkDocs Material with mkdocstrings generates API docs from docstrings
- 🎨 **Code Quality:** ruff for linting and formatting
- 📦 **Modern Layout:** src-based package structure for better test isolation

## Installation

**Prerequisites:**
- Python >= 3.11

**Setup:**

1. Clone the repository:
```bash
git clone <repo-url>
cd codemap
```

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
```bash
# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

4. Install dependencies:
```bash
pip install -r requirements-dev.txt
```

## Quick Start

**Run tests:**
```bash
pytest
```

**View coverage report:**
```bash
# Mac
open htmlcov/index.html

# Windows
start htmlcov/index.html

# Linux
xdg-open htmlcov/index.html
```

**Build documentation:**
```bash
mkdocs build
```

**Serve documentation locally:**
```bash
mkdocs serve
```
Then open http://127.0.0.1:8000 in your browser.

**Import the package:**
```python
from codemap import __version__
print(__version__)
```

## Verify Setup

Run the automated verification script to ensure everything is configured correctly:

```bash
python setup_check.py
```

This script installs dependencies, runs all quality checks, and builds documentation to ensure the project is correctly configured.

## Project Structure

```
codemap/
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

## Documentation

For detailed API documentation, see [the docs](./docs/index.md) or run `mkdocs serve`.

For development workflow, see [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

MIT License
