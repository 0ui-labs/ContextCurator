I have created the following plan after thorough exploration and analysis of the codebase. Follow the below plan verbatim. Trust the files and references. Do not re-verify what's written in the plan. Explore only when absolutely necessary. First implement all the proposed file changes and then I'll review all the changes together at the end.

## Observations

The codebase follows strict TDD with 100% coverage enforcement (`pyproject.toml` line 44). Currently, `file:src/codemap/scout/walker.py` is **completely empty** and `tests/unit/scout/test_walker.py` **does not exist**. The `FileEntry` dataclass exists in `file:src/codemap/scout/models.py` with `path`, `size`, and `token_est` attributes. The `TreeGenerator` in `file:src/codemap/scout/tree.py` provides a proven pattern for pathspec-based filtering, OSError handling, and alphabetical sorting that should be mirrored in `FileWalker`.

## Approach

Since no implementation or tests exist yet, this plan covers the complete TDD cycle: **RED** (create failing tests), **GREEN** (implement to pass tests), and **REFACTOR** (verify 100% coverage). The `FileWalker` will use `pathspec` for gitignore-style pattern matching, default ignores (`.git`, `.venv`, `__pycache__`), `Path.rglob("*")` for efficient traversal, `stat().st_size` for metadata, token estimation (`size // 4`), and alphabetical sorting. This mirrors `TreeGenerator`'s architecture for consistency.

---

## Implementation Steps

### Phase 1: RED - Create Comprehensive Test Suite

Create `tests/unit/scout/test_walker.py` with the following test structure:

#### Test Class: `TestFileWalkerBasic`
- **`test_walker_returns_file_entries`**: Create 2 dummy files (`a.py`, `b.txt`), call `walker.walk(tmp_path, [])`, assert returns `list[FileEntry]` with 2 entries, verify each has `path`, `size`, `token_est` attributes
- **`test_walker_empty_directory`**: Call `walk()` on empty `tmp_path`, assert returns empty list `[]`
- **`test_walker_single_file`**: Create `README.md`, assert returns 1 `FileEntry` with correct `path` (relative to root)
- **`test_walker_nested_structure`**: Create `src/main.py` and `tests/test_main.py`, assert returns 2 entries with relative paths `Path("src/main.py")` and `Path("tests/test_main.py")`

#### Test Class: `TestFileWalkerPatterns`
- **`test_walker_respects_patterns`**: Pass `ignore_patterns=["*.tmp"]`, create `test.tmp` and `main.py`, assert only `main.py` in results
- **`test_walker_respects_multiple_patterns`**: Pass `["*.log", "*.tmp"]`, create `app.log`, `cache.tmp`, `main.py`, assert only `main.py` returned
- **`test_walker_respects_directory_patterns`**: Pass `["node_modules/"]`, create `node_modules/package.json` and `src/main.py`, assert only `src/main.py` returned
- **`test_walker_respects_wildcard_patterns`**: Pass `["test_*.py"]`, create `test_unit.py`, `test_integration.py`, `main.py`, assert only `main.py` returned

#### Test Class: `TestFileWalkerDefaultIgnores`
- **`test_walker_respects_default_ignores`**: Create `.git/config`, `.venv/lib/python.py`, `__pycache__/module.pyc`, `main.py`, assert only `main.py` returned (no patterns passed)
- **`test_walker_ignores_git_directory`**: Create `.git/HEAD`, `src/main.py`, assert `.git` never scanned
- **`test_walker_ignores_venv_directory`**: Create `.venv/bin/python`, `main.py`, assert `.venv` excluded
- **`test_walker_ignores_pycache_directory`**: Create `__pycache__/cache.pyc`, `module.py`, assert `__pycache__` excluded

#### Test Class: `TestFileWalkerMetadata`
- **`test_walker_calculates_metadata`**: Create file with known content (e.g., `"x" * 100`), assert `size == 100` and `token_est == 25` (100 // 4)
- **`test_walker_calculates_size_correctly`**: Create 3 files with sizes 50, 200, 1000 bytes, assert each `FileEntry.size` matches
- **`test_walker_calculates_token_estimation`**: Verify formula `token_est = size // 4` for multiple files (0 bytes → 0 tokens, 17 bytes → 4 tokens, 100 bytes → 25 tokens)
- **`test_walker_handles_empty_files`**: Create empty file (0 bytes), assert `size == 0` and `token_est == 0`

#### Test Class: `TestFileWalkerSorting`
- **`test_walker_sorts_alphabetically`**: Create `zebra.py`, `alpha.py`, `beta.py`, assert result order is `[alpha.py, beta.py, zebra.py]` by comparing `entry.path` strings
- **`test_walker_sorts_nested_files`**: Create `src/z.py`, `src/a.py`, `tests/b.py`, assert sorted as `[src/a.py, src/z.py, tests/b.py]`
- **`test_walker_sorting_is_deterministic`**: Run `walk()` twice on same structure, assert identical order both times

#### Test Class: `TestFileWalkerEdgeCases`
- **`test_walker_invalid_root_raises_error`**: Pass non-existent path, assert raises `ValueError` with message "does not exist"
- **`test_walker_file_as_root_raises_error`**: Pass file path instead of directory, assert raises `ValueError` with message "not a directory"
- **`test_walker_handles_permission_errors`**: Use `monkeypatch` to mock `Path.stat()` raising `OSError`, assert walker continues gracefully (skips file, no crash)
- **`test_walker_handles_deep_nesting`**: Create 10-level nested structure (`a/b/c/.../j/file.py`), assert file found with correct relative path
- **`test_walker_ignores_directories_only_files`**: Create `src/` directory and `main.py` file, assert only `main.py` in results (directories not included)
- **`test_walker_handles_special_characters`**: Create files with dashes, underscores, dots (`file-name.py`, `file_name.py`, `file.name.py`), assert all found

**Test Patterns:**
- Use `tmp_path` fixture for isolated file system
- Follow AAA pattern (Arrange, Act, Assert)
- Import: `from codemap.scout.walker import FileWalker` and `from codemap.scout.models import FileEntry`
- Use descriptive docstrings matching `test_tree.py` style
- Tests should **fail** initially (RED phase) because `FileWalker` doesn't exist yet

---

### Phase 2: GREEN - Implement FileWalker

Create `file:src/codemap/scout/walker.py`:

#### Module Structure
```
"""File walker for inventory generation.

Scans directories and returns FileEntry objects with metadata.
"""

from pathlib import Path
import pathspec
from codemap.scout.models import FileEntry

# Default directories to always ignore
DEFAULT_IGNORES: list[str] = [".git", ".venv", "__pycache__"]
```

#### Class: `FileWalker`

**Method: `walk(self, root: Path, ignore_patterns: list[str]) -> list[FileEntry]`**

**Implementation Logic:**

1. **Input Validation:**
   - Check `root.exists()`, raise `ValueError("Path does not exist: {root}")` if False
   - Check `root.is_dir()`, raise `ValueError("Path is not a directory: {root}")` if False

2. **Pattern Compilation:**
   - Combine `ignore_patterns` with `DEFAULT_IGNORES`: `all_patterns = DEFAULT_IGNORES + ignore_patterns`
   - Compile using `pathspec.PathSpec.from_lines("gitwildmatch", all_patterns)`

3. **File Traversal:**
   - Use `root.rglob("*")` to iterate all paths recursively
   - For each path:
     - Skip if `path.is_dir()` (only collect files)
     - Calculate relative path: `relative_path = path.relative_to(root)`
     - Normalize for pathspec: `pattern_path = str(relative_path).replace("\\", "/")`
     - Check if ignored: `if spec.match_file(pattern_path): continue`
     - Wrap in `try/except OSError` to handle permission errors gracefully (skip file on error)
     - Get metadata: `size = path.stat().st_size`
     - Calculate tokens: `token_est = size // 4`
     - Create `FileEntry(path=relative_path, size=size, token_est=token_est)`
     - Append to results list

4. **Sorting:**
   - Sort results: `results.sort(key=lambda e: str(e.path))`

5. **Return:**
   - Return `list[FileEntry]`

**Error Handling:**
- Wrap `path.stat()` in `try/except OSError` to skip files with permission issues
- Wrap `path.rglob()` iteration in `try/except OSError` to handle unreadable directories

**Key Implementation Details:**
- Use `Path.rglob("*")` for performance (more efficient than `os.walk` for filtering)
- Normalize backslashes to forward slashes for cross-platform pathspec matching
- Use integer division `//` for token estimation (not float division)
- Ensure relative paths are used (not absolute)
- Match `TreeGenerator` patterns for consistency

---

### Phase 3: Export FileWalker

Update `file:src/codemap/scout/__init__.py`:

- Add import: `from codemap.scout.walker import FileWalker`
- Update `__all__`: Add `"FileWalker"` to the list (maintain alphabetical order: `["FileEntry", "FileWalker", "StructureAdvisor", "TreeGenerator", "TreeReport"]`)

---

### Phase 4: Run Tests and Verify Coverage

#### Execute Test Suite
Run from project root:
```bash
pytest tests/unit/scout/test_walker.py -v
```

Expected outcome: All tests should **pass** (GREEN phase complete)

#### Verify 100% Coverage
Run coverage analysis:
```bash
pytest --cov=src/codemap/scout/walker --cov-report=term-missing tests/unit/scout/test_walker.py
```

**Coverage Requirements:**
- `walker.py` must show **100% coverage** (all lines, all branches)
- Check for missing lines in coverage report
- If coverage < 100%, identify untested code paths

**Common Coverage Gaps to Check:**
- Error handling branches (OSError exceptions)
- Edge cases (empty directory, single file)
- Both branches of conditional statements
- Default ignores vs custom patterns

#### Run Full Test Suite
Verify no regressions:
```bash
pytest --cov=src/codemap
```

Expected: All tests pass, overall coverage remains 100%

---

### Phase 5: REFACTOR - Code Quality and Coverage Verification

#### Coverage Analysis
If coverage < 100%, add missing tests:
- **Untested error paths:** Add tests for `OSError` during `stat()` or `rglob()`
- **Untested branches:** Check if all `if` statements have both True/False cases tested
- **Edge cases:** Verify empty patterns list, empty directory, single file scenarios

#### Code Quality Checks

**Run Type Checking:**
```bash
mypy src/codemap/scout/walker.py
```
Expected: No type errors (strict mode enabled in `pyproject.toml`)

**Run Linting:**
```bash
ruff check src/codemap/scout/walker.py
```
Expected: No linting errors

**Run Formatting:**
```bash
ruff format src/codemap/scout/walker.py
```

#### Refactoring Opportunities

**Check for Code Duplication:**
- Compare `walker.py` with `tree.py` for shared logic
- If pattern compilation logic is identical, consider extracting to shared utility (future refactor, not required now)

**Verify Consistency:**
- Ensure `walker.py` uses same error handling pattern as `tree.py` (silent OSError handling)
- Ensure same pathspec usage pattern (gitwildmatch, forward slash normalization)
- Ensure same default ignores (`.git`, `.venv`, `__pycache__`)

**Documentation:**
- Verify docstrings follow project style (see `tree.py` for reference)
- Ensure class and method docstrings explain purpose, args, returns, raises

#### Final Verification

**Run Complete Test Suite with Coverage:**
```bash
pytest --cov=src/codemap --cov-report=term-missing --cov-report=html
```

**Success Criteria:**
- ✅ All tests pass (no failures, no errors)
- ✅ `walker.py` shows 100% coverage
- ✅ Overall project coverage remains 100%
- ✅ No type errors from mypy
- ✅ No linting errors from ruff
- ✅ HTML coverage report shows no missing lines in `walker.py`

**Review HTML Coverage Report:**
```bash
open htmlcov/index.html  # macOS
```
Navigate to `walker.py`, verify all lines are green (covered)

---

## Summary

This plan implements `FileWalker` following strict TDD:

1. **RED Phase:** Create 20+ comprehensive tests covering basic functionality, pattern matching, default ignores, metadata calculation, sorting, and edge cases
2. **GREEN Phase:** Implement `FileWalker.walk()` using pathspec, Path.rglob(), error handling, and alphabetical sorting
3. **Export Phase:** Add `FileWalker` to `__init__.py` for public API
4. **Verification Phase:** Run pytest with coverage to confirm all tests pass
5. **REFACTOR Phase:** Verify 100% coverage, run type checking and linting, ensure code quality

The implementation mirrors `TreeGenerator` patterns for consistency, uses proven pathspec techniques, and maintains the project's strict quality standards.