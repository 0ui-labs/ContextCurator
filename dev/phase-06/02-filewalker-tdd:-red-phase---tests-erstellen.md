I have created the following plan after thorough exploration and analysis of the codebase. Follow the below plan verbatim. Trust the files and references. Do not re-verify what's written in the plan. Explore only when absolutely necessary. First implement all the proposed file changes and then I'll review all the changes together at the end.

## Observations

The codebase follows strict TDD practices with 100% coverage requirement. Existing test file `file:tests/unit/scout/test_tree.py` demonstrates comprehensive test patterns: multiple test classes for organization, AAA pattern with clear comments, `tmp_path` fixture usage, and thorough edge case coverage. The `file:src/codemap/scout/tree.py` shows how `pathspec` is used for pattern matching with `.gitignore` style patterns. The project uses `pathspec` library (already in dependencies) for pattern matching, and has constants for default ignores.

## Approach

Create `file:tests/unit/scout/test_walker.py` following the established test patterns from `test_tree.py`. Organize tests into logical classes mirroring the four required test scenarios plus additional edge cases for 100% coverage. Use `tmp_path` fixture to create test file structures, verify `FileEntry` objects are returned with correct metadata (path, size, token_est), and ensure pattern matching works correctly. Tests will fail initially (RED phase) since `FileWalker` and `FileEntry` don't exist yet.

## Implementation Steps

### 1. Create Test File Structure

Create `file:tests/unit/scout/test_walker.py` with necessary imports:
- Import `Path` from `pathlib`
- Import `pytest` for fixtures and assertions
- Import `FileEntry` from `codemap.scout.models` (will fail until implemented)
- Import `FileWalker` from `codemap.scout.walker` (will fail until implemented)
- Add module docstring explaining test coverage

### 2. Implement TestFileWalkerBasic Class

Create first test class with core functionality tests:

**test_walker_returns_file_entries**
- Create 2-3 dummy files in `tmp_path` using `write_text()`
- Instantiate `FileWalker()` and call `walk(tmp_path, [])`
- Assert result is `list[FileEntry]`
- Assert length matches number of files created
- Assert each entry has correct attributes (path, size, token_est)

**test_walker_empty_directory**
- Call `walk()` on empty `tmp_path`
- Assert returns empty list

**test_walker_single_file**
- Create one file with known content
- Verify single `FileEntry` returned with correct metadata

### 3. Implement TestFileWalkerPatterns Class

Create test class for pattern matching:

**test_walker_respects_patterns**
- Create `test.tmp` and `main.py` files in `tmp_path`
- Call `walk(tmp_path, ["*.tmp"])`
- Assert only `main.py` appears in results
- Assert `test.tmp` is excluded

**test_walker_respects_multiple_patterns**
- Create files: `test.log`, `debug.tmp`, `main.py`
- Pass patterns `["*.log", "*.tmp"]`
- Assert only `main.py` in results

**test_walker_respects_directory_patterns**
- Create `node_modules/` directory with files inside
- Pass pattern `["node_modules/"]`
- Assert directory and its contents excluded

### 4. Implement TestFileWalkerDefaultIgnores Class

Create test class for default ignore behavior:

**test_walker_respects_default_ignores**
- Create `.git/`, `.venv/`, `__pycache__/` directories with files
- Create `main.py` file
- Call `walk(tmp_path, [])`
- Assert none of the default ignored directories appear
- Assert `main.py` appears

**test_walker_ignores_git_directory**
- Create `.git/config` file
- Create `README.md` file
- Assert only `README.md` in results

**test_walker_ignores_venv_directory**
- Create `.venv/lib/python.py` nested structure
- Create `src/main.py`
- Assert only `src/main.py` in results

**test_walker_ignores_pycache_directory**
- Create `__pycache__/module.pyc`
- Create `module.py`
- Assert only `module.py` in results

### 5. Implement TestFileWalkerMetadata Class

Create test class for metadata calculation:

**test_walker_calculates_metadata**
- Create file with known content (e.g., 100 bytes)
- Get `FileEntry` from walk results
- Assert `size` equals `stat().st_size`
- Assert `token_est` equals `size // 4` (integer division)

**test_walker_token_estimation_formula**
- Create multiple files with different sizes
- Verify each has `token_est = size // 4`

**test_walker_relative_paths**
- Create nested structure: `src/utils/helper.py`
- Verify `path` attribute is relative to root
- Assert path equals `Path("src/utils/helper.py")`

### 6. Implement TestFileWalkerSorting Class

Create test class for alphabetical sorting:

**test_walker_sorts_alphabetically**
- Create files: `zebra.py`, `alpha.py`, `beta.py`
- Verify results are sorted by path name
- Assert order: alpha, beta, zebra

**test_walker_sorts_nested_files**
- Create nested structure with multiple files
- Verify all results sorted alphabetically including nested paths

### 7. Implement TestFileWalkerEdgeCases Class

Create test class for error handling and edge cases:

**test_walker_handles_permission_error**
- Use `monkeypatch` to mock `stat()` raising `PermissionError`
- Verify walker continues gracefully, skipping unreadable files
- Assert other files still processed

**test_walker_handles_deep_nesting**
- Create 10-level deep nested structure
- Create file at deepest level
- Verify file is found and included

**test_walker_handles_special_characters**
- Create files with dashes, underscores, dots in names
- Verify all files correctly processed

**test_walker_nonexistent_path**
- Pass non-existent path to `walk()`
- Expect appropriate error handling (either exception or empty list)

### 8. Test Organization and Documentation

- Add comprehensive module docstring explaining test coverage
- Use clear AAA pattern (Arrange, Act, Assert) with comments
- Group related tests into classes
- Ensure each test has descriptive docstring
- Follow naming convention: `test_<component>_<behavior>`

### 9. Verification

Run tests to confirm RED phase:
- Execute `pytest tests/unit/scout/test_walker.py`
- Verify all tests fail with import errors or missing implementation
- Confirm test file has no syntax errors
- Ensure test structure follows project conventions

## Expected Test Structure

```
tests/unit/scout/test_walker.py
├── TestFileWalkerBasic (3-4 tests)
├── TestFileWalkerPatterns (3-4 tests)
├── TestFileWalkerDefaultIgnores (4 tests)
├── TestFileWalkerMetadata (3 tests)
├── TestFileWalkerSorting (2 tests)
└── TestFileWalkerEdgeCases (4-5 tests)
```

Total: ~20-25 tests ensuring comprehensive coverage for subsequent GREEN phase implementation.