I have created the following plan after thorough exploration and analysis of the codebase. Follow the below plan verbatim. Trust the files and references. Do not re-verify what's written in the plan. Explore only when absolutely necessary. First implement all the proposed file changes and then I'll review all the changes together at the end.

## Observations

The codebase follows strict TDD with 100% coverage requirements (`pyproject.toml` line 46). Existing test files demonstrate comprehensive patterns: multiple test classes per module (`TestGraphManagerBasic`, `TestGraphManagerHierarchy`, etc.), AAA structure, `tmp_path` fixtures for filesystem operations, and extensive edge case coverage (permission errors via mocking, invalid inputs, empty cases). The `MapBuilder` will orchestrate four components (`FileWalker`, `ContentReader`, `ParserEngine`, `GraphManager`) that each have distinct error modes: `FileWalker` handles OS errors silently, `ContentReader` raises `ContentReadError`, `ParserEngine` raises `ValueError` for unsupported languages, and `GraphManager` validates node existence.

## Approach

Extend `file:tests/unit/engine/test_builder.py` with comprehensive test coverage organized into six test classes mirroring patterns from `file:tests/unit/graph/test_manager.py` and `file:tests/unit/scout/test_walker.py`. Tests will verify the integration test (already implemented), edge cases (parsing/read errors, empty folders, invalid syntax), boundary cases (large structures, circular imports), error handling (invalid root, partial failures), and coverage completeness (all branches, logging). Use `tmp_path` fixtures to create realistic file structures, `pytest.raises` for error validation, and `unittest.mock.patch` for simulating failures. Verify 100% coverage with `pytest --cov=src/codemap/engine`, run `mypy --strict src/codemap/engine` and `ruff check src/codemap/engine` to ensure type safety and code quality. Finally, enhance docstrings in `file:src/codemap/engine/builder.py` following the Architecture/Example/Threading pattern from `file:src/codemap/graph/manager.py`.

## Implementation Steps

### 1. Create Test Class Structure in `file:tests/unit/engine/test_builder.py`

Organize tests into six classes following patterns from `file:tests/unit/graph/test_manager.py`:

- **`TestMapBuilderInitialization`**: Verify `MapBuilder()` instantiates without arguments, initializes internal components (`FileWalker`, `ContentReader`, `ParserEngine`, `GraphManager`), and has a `build` method
- **`TestMapBuilderBasicIntegration`**: Keep existing integration test (`test_build_creates_complete_graph`) that validates end-to-end workflow with `main.py` importing `utils.py`
- **`TestMapBuilderEdgeCases`**: Test error resilience
  - `test_build_with_invalid_python_syntax`: Create file with syntax error (e.g., `def foo(`), verify build continues, graph has file node but no code nodes for that file, uses `caplog` to verify warning logged
  - `test_build_with_read_error`: Mock `ContentReader.read_file` to raise `ContentReadError`, verify build continues for other files
  - `test_build_with_empty_folder`: Create empty directory, verify `build()` returns empty graph (0 nodes, 0 edges)
  - `test_build_with_binary_file`: Create `.pyc` file (ignored by walker) or mock read to raise binary error, verify graceful handling
  - `test_build_with_unsupported_file_mixed`: Create `.py` and `.txt` files, verify only `.py` processed
- **`TestMapBuilderBoundaryCases`**: Test scalability and complex scenarios
  - `test_build_with_many_files`: Create 50+ Python files with functions, verify all processed correctly (check node count)
  - `test_build_with_circular_imports`: Create `a.py` (imports `b`) and `b.py` (imports `a`), verify both IMPORTS edges exist, no infinite loop
  - `test_build_with_deep_nesting`: Create 10-level nested directories with files, verify all discovered and processed
  - `test_build_with_many_imports`: Create file with 20+ import statements, verify all captured as code nodes and dependencies resolved
- **`TestMapBuilderErrorHandling`**: Test invalid inputs and failure modes
  - `test_build_with_nonexistent_root`: Call `build(Path("/nonexistent"))`, verify `ValueError` raised with message "does not exist"
  - `test_build_with_file_as_root`: Create file, call `build(file_path)`, verify `ValueError` raised with message "not a directory"
  - `test_build_with_partial_failures`: Create 3 files where 1 has syntax error, verify graph has 2 file nodes with code nodes, 1 file node without code nodes
  - `test_build_with_no_python_files`: Create directory with only `.txt` files, verify empty graph returned
- **`TestMapBuilderImportResolution`**: Test import dependency detection
  - `test_build_resolves_relative_imports`: Create `pkg/__init__.py`, `pkg/a.py` (imports `pkg.b`), `pkg/b.py`, verify IMPORTS edge from `a` to `b`
  - `test_build_ignores_external_imports`: Create file importing `os`, `sys`, verify no IMPORTS edges to external modules
  - `test_build_resolves_dotted_imports`: Create `utils/helper.py`, `main.py` (imports `utils.helper`), verify IMPORTS edge
  - `test_build_handles_missing_import_target`: Create `main.py` importing `nonexistent`, verify no IMPORTS edge, warning logged

### 2. Implement Helper Functions for Test Data Creation

Add reusable fixtures and helpers at module level in `file:tests/unit/engine/test_builder.py`:

```python
def create_python_file(path: Path, content: str) -> None:
    """Helper to create Python file with content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def create_package(root: Path, name: str, files: dict[str, str]) -> None:
    """Helper to create Python package with multiple files."""
    pkg_dir = root / name
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    for filename, content in files.items():
        (pkg_dir / filename).write_text(content, encoding="utf-8")
```

### 3. Add Logging Verification Tests

Use `pytest`'s `caplog` fixture to verify error logging (pattern from `file:tests/unit/scout/test_walker.py` lines 791-938):

- Import `logging` and use `caplog.set_level(logging.WARNING)`
- After `build()` call, assert `"Failed to" in caplog.text` or similar
- Verify specific file paths appear in log messages for failed files

### 4. Verify 100% Coverage

Run coverage analysis and add tests for uncovered branches:

```bash
pytest tests/unit/engine/test_builder.py --cov=src/codemap/engine/builder --cov-report=term-missing
```

Ensure all branches covered:
- `build()` method: root validation, file iteration, read errors, parse errors, import resolution
- Import resolution: module-to-path conversion, file existence checks, external module filtering
- Error handling: try/except blocks for read and parse failures

### 5. Run Type Checking and Linting

Execute strict type checking and linting per `pyproject.toml` configuration:

```bash
mypy --strict src/codemap/engine/builder.py tests/unit/engine/test_builder.py
ruff check src/codemap/engine/builder.py tests/unit/engine/test_builder.py
```

Fix any issues:
- Type annotations for all parameters and return values
- No `Any` types without justification
- Import sorting per ruff rules
- Line length ≤100 characters

### 6. Enhance Docstrings in `file:src/codemap/engine/builder.py`

Follow comprehensive docstring pattern from `file:src/codemap/graph/manager.py` (lines 21-80):

**Class Docstring** - Add sections:
- **Architecture**: Describe component orchestration (FileWalker → ContentReader → ParserEngine → GraphManager)
- **Performance**: Note scalability limits (e.g., "Optimized for small to medium codebases up to ~10,000 files")
- **Thread Safety**: State "NOT thread-safe, create separate instances per thread"
- **Error Handling**: Explain per-file error isolation with logging
- **Example**: Complete workflow showing initialization, build call, graph inspection, save/load

**Method Docstrings** - Enhance `build()`:
- Add detailed Args section with root validation requirements
- Add Returns section describing GraphManager state
- Add Raises section listing ValueError conditions
- Add Example showing typical usage with assertions

**Import Resolution Documentation**:
- Document module-to-path conversion logic (dotted name → `/`, append `.py`)
- Explain external module filtering (only intra-project imports)
- Note limitations (no `__init__.py` inference, no package resolution)

### 7. Add Module-Level Docstring

Create comprehensive module docstring in `file:src/codemap/engine/builder.py`:

```python
"""Code mapping orchestration engine.

This module provides the MapBuilder class for end-to-end code graph construction,
orchestrating file discovery, content reading, parsing, and graph building.

Key Components:
    - FileWalker: Discovers Python files with ignore pattern support
    - ContentReader: Reads file content with encoding fallback
    - ParserEngine: Extracts code structure via tree-sitter
    - GraphManager: Builds and persists relationship graph

Typical Usage:
    >>> from pathlib import Path
    >>> from codemap.engine import MapBuilder
    >>> 
    >>> builder = MapBuilder()
    >>> graph_manager = builder.build(Path("src"))
    >>> print(graph_manager.graph_stats)
    {'nodes': 42, 'edges': 38}
"""
```

### 8. Create Coverage Report and Verify 100%

Generate HTML coverage report for detailed analysis:

```bash
pytest tests/unit/engine/ --cov=src/codemap/engine --cov-report=html
```

Open `htmlcov/index.html` and verify:
- All lines in `builder.py` are green (covered)
- All branches in conditionals are covered (both True/False paths)
- No yellow or red lines indicating partial or missing coverage

### 9. Document Test Organization

Add comprehensive module docstring to `file:tests/unit/engine/test_builder.py`:

```python
"""Unit tests for engine.builder module.

This module contains comprehensive tests for the MapBuilder class,
covering integration, edge cases, boundary cases, and error handling.

Test Organization:
    - TestMapBuilderInitialization: Basic instantiation and interface
    - TestMapBuilderBasicIntegration: End-to-end workflow validation
    - TestMapBuilderEdgeCases: Error resilience (syntax errors, read failures)
    - TestMapBuilderBoundaryCases: Scalability (many files, deep nesting)
    - TestMapBuilderErrorHandling: Invalid inputs and failure modes
    - TestMapBuilderImportResolution: Dependency detection accuracy

Coverage: 100% of builder.py (lines, branches, error paths)
"""
```

## Test Execution Verification

| Test Class | Test Count | Coverage Target |
|------------|-----------|----------------|
| `TestMapBuilderInitialization` | 3 | Constructor, component initialization |
| `TestMapBuilderBasicIntegration` | 1 | End-to-end happy path |
| `TestMapBuilderEdgeCases` | 5 | Error resilience, empty cases |
| `TestMapBuilderBoundaryCases` | 4 | Scalability, complex scenarios |
| `TestMapBuilderErrorHandling` | 4 | Invalid inputs, partial failures |
| `TestMapBuilderImportResolution` | 4 | Dependency detection logic |
| **Total** | **21** | **100% coverage** |

## Quality Checklist

- [ ] All 21 tests pass with `pytest tests/unit/engine/test_builder.py`
- [ ] Coverage report shows 100% for `src/codemap/engine/builder.py`
- [ ] `mypy --strict src/codemap/engine` passes with no errors
- [ ] `ruff check src/codemap/engine` passes with no warnings
- [ ] Docstrings include Architecture, Performance, Thread Safety, Example sections
- [ ] All test methods have descriptive docstrings explaining what they verify
- [ ] Error messages in assertions are clear and actionable
- [ ] No hardcoded paths (use `tmp_path` fixture consistently)