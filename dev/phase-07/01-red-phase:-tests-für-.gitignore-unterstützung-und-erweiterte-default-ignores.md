I have created the following plan after thorough exploration and analysis of the codebase. Follow the below plan verbatim. Trust the files and references. Do not re-verify what's written in the plan. Explore only when absolutely necessary. First implement all the proposed file changes and then I'll review all the changes together at the end.

## Observations

The existing `test_walker.py` follows strict TDD patterns with comprehensive test coverage organized into logical test classes. The `FileWalker` currently uses only three default ignores (`.git`, `.venv`, `__pycache__`) and does NOT read local `.gitignore` files. The `TreeGenerator` in `tree.py` already has `.gitignore` reading logic via `_load_gitignore()` method, which can serve as a reference pattern. Tests use pytest's `tmp_path` fixture and follow consistent arrange-act-assert structure.

## Approach

Add two new test methods to the `TestFileWalkerDefaultIgnores` class in `file:tests/unit/scout/test_walker.py`. These tests will initially FAIL (RED phase) because the required functionality doesn't exist yet. The first test verifies `.gitignore` file reading, while the second validates comprehensive polyglot default ignores. Both tests follow existing patterns: create test files/directories in `tmp_path`, invoke `walker.walk()`, and assert on the returned `FileEntry` list.

## Implementation Steps

### 1. Add `test_walker_reads_local_gitignore` to TestFileWalkerDefaultIgnores class

**Location**: After `test_walker_ignores_pycache_directory` (around line 269)

**Test structure**:
- Create `.gitignore` file in `tmp_path` with content `local_ignore.txt`
- Create two files: `local_ignore.txt` and `should_pass.txt`
- Instantiate `FileWalker()` and call `walk(tmp_path, [])` with empty ignore_patterns
- Assert `should_pass.txt` IS in results (verify file exists in returned list)
- Assert `local_ignore.txt` is NOT in results (verify gitignore exclusion works)
- Use list comprehension `[entry.path for entry in result]` to extract paths for assertions

**Expected behavior**: Test will FAIL because `walker.walk()` doesn't read `.gitignore` yet

### 2. Add `test_walker_ignores_common_junk_polyglot` to TestFileWalkerDefaultIgnores class

**Location**: After the new `test_walker_reads_local_gitignore` test

**Test structure**:
- Create four directories representing different language ecosystems:
  - `node_modules` (JavaScript/Node.js) with `node_modules/package.json`
  - `wp-admin` (PHP/WordPress) with `wp-admin/admin.php`
  - `.dart_tool` (Dart/Flutter) with `.dart_tool/package_config.json`
  - `target` (Rust/Java) with `target/debug.log`
- Create a valid file `main.py` in root to verify walker still works
- Instantiate `FileWalker()` and call `walk(tmp_path, [])`
- Assert `main.py` IS in results
- Assert NONE of the junk directories appear in results using path string checks
- Use loop to verify: `for path in paths: assert not str(path).startswith("node_modules")` (repeat for each junk dir)

**Expected behavior**: Test will FAIL because `DEFAULT_IGNORES` only contains 3 entries, not the comprehensive polyglot list

### 3. Test Implementation Details

**Naming conventions**: Follow existing pattern `test_walker_<action>_<scenario>`

**Assertions style**: 
- Use `assert len(result) == expected_count` for count verification
- Use `assert Path("filename") in paths` for inclusion checks
- Use `assert Path("filename") not in paths` for exclusion checks
- Extract paths list: `paths = [entry.path for entry in result]`

**File content**: Use simple strings like `"content"` or `"dummy"` - content doesn't matter for these tests

**Directory structure**: Use `Path.mkdir()` for directories, `Path.write_text()` for files

### 4. Integration with Existing Test Suite

**Class placement**: Both tests belong in `TestFileWalkerDefaultIgnores` class (lines 187-269) since they test ignore functionality

**Test order**: Place after existing default ignore tests to maintain logical grouping

**Fixtures**: Use standard `tmp_path: Path` fixture from pytest, consistent with all other tests

**No mocking needed**: These are integration tests that verify actual file system operations