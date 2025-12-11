# Codemap

A strict Test-Driven Development (TDD) Python project for code mapping and analysis.

## Welcome

Codemap is a powerful tool designed for code mapping and analysis, built with a strict Test-Driven Development approach. Every line of code is written test-first, ensuring 100% test coverage and robust, maintainable software.

This project serves as both a practical tool and a demonstration of rigorous software engineering practices, where quality and reliability are paramount.

## Key Features

- **Strict Test-Driven Development**: 100% test coverage enforced - no code ships without tests
- **Type Safety**: Full type annotations with mypy strict mode enabled
- **Modern Tooling**: Built with pytest for testing, ruff for linting, and mkdocs-material for documentation
- **Automatic API Documentation**: Comprehensive API docs generated from code and docstrings

## Getting Started

### Installation

Install the project in development mode with all dependencies:

```bash
pip install -r requirements-dev.txt
```

### Running Tests

Execute the test suite to verify everything is working:

```bash
pytest
```

### API Reference

For detailed information about the codebase, see the [API Reference](api.md) section.

## Philosophy

Codemap follows a strict TDD workflow:

**Red → Green → Refactor**

1. **Red**: Write a failing test that defines the desired functionality
2. **Green**: Write the minimal code necessary to make the test pass
3. **Refactor**: Improve the code while keeping tests green

In this project, **untested code is considered broken code**. No feature, bug fix, or refactoring is complete without corresponding tests that verify its behavior.

For detailed information about our development workflow, contribution guidelines, and testing standards, please refer to `CONTRIBUTING.md`.

## Contributing

This project follows strict Test-Driven Development. Before contributing, please read our **Contributing Guide** (`CONTRIBUTING.md` in the project root) to understand the TDD workflow and quality requirements.

Check out the project's issue tracker for tasks to work on.
