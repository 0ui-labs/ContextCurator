I have created the following plan after thorough exploration and analysis of the codebase. Follow the below plan verbatim. Trust the files and references. Do not re-verify what's written in the plan. Explore only when absolutely necessary. First implement all the proposed file changes and then I'll review all the changes together at the end.

## Observations

The `test_advisor.py` file contains 46 test methods across 6 test classes. Currently, all tests are synchronous. The file includes a `TestMockProvider` test-double class and multiple inline provider classes within individual tests. Based on the async refactoring of `StructureAdvisor.analyze()` and `LLMProvider.send()`, 20 test methods that invoke `analyze()` require async conversion, while 26 introspection-only tests (checking docstrings, type hints, existence) remain synchronous. The `pyproject.toml` currently lacks `asyncio_mode` configuration for pytest.

## Approach

Following strict TDD RED phase principles, convert all tests that exercise the `analyze()` method to async by adding `@pytest.mark.asyncio` decorators, changing signatures to `async def`, and using `await` for all `analyze()` calls. Update `TestMockProvider` and all inline provider classes to async. Add `asyncio_mode = "auto"` to `pyproject.toml` for automatic async test handling. Import `AsyncMock` for coroutine-compatible mocking. This intentionally breaks tests to validate the async implementation, ensuring failures like "coroutine was never awaited" surface before the GREEN phase.

## Implementation Steps

### 1. Configure pytest for Async Test Support

**File:** `file:pyproject.toml`

Add `asyncio_mode = "auto"` to the `[tool.pytest.ini_options]` section (after line 43, before the closing of the section):

```toml
[tool.pytest.ini_options]
addopts = [
    "--cov=src/codemap",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--strict-markers",
    "--strict-config",
    "-ra"
]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"  # Add this line
```

This enables pytest-asyncio to automatically detect and run async test functions without requiring explicit event loop fixtures.

---

### 2. Add AsyncMock Import

**File:** `file:tests/unit/scout/test_advisor.py`

Add `AsyncMock` import to line 11 (after existing imports):

```python
from unittest.mock import AsyncMock
```

This provides async-compatible mock objects for coroutine methods.

---

### 3. Convert TestMockProvider to Async

**File:** `file:tests/unit/scout/test_advisor.py`

**Location:** Lines 14-62 (TestMockProvider class)

Convert the `send()` method to async:

- Change line 45 from `def send(self, system: str, user: str) -> str:` to `async def send(self, system: str, user: str) -> str:`
- Update docstring (lines 46-58) to mention async nature and awaiting requirement
- No changes to method body (lines 59-61) - return statement remains synchronous

---

### 4. Convert Inline Provider Classes to Async

**File:** `file:tests/unit/scout/test_advisor.py`

Convert all inline provider classes within test methods to async. These are located in:

| Test Method | Lines | Provider Class | Action |
|------------|-------|----------------|--------|
| `test_analyze_with_clean_response` | 150-152 | `CleanProvider` | Change `def send` to `async def send` |
| `test_analyze_strips_markdown_code_blocks_with_language` | 178-180 | `MarkdownProvider` | Change `def send` to `async def send` |
| `test_analyze_strips_markdown_code_blocks_without_language` | 208-210 | `MarkdownProvider` | Change `def send` to `async def send` |
| `test_analyze_filters_prefix_text` | 235-237 | `PrefixProvider` | Change `def send` to `async def send` |
| `test_analyze_filters_empty_lines` | 264-266 | `EmptyLinesProvider` | Change `def send` to `async def send` |
| `test_analyze_accepts_simple_filenames_without_pattern_chars` | 293-295 | `SimpleNameProvider` | Change `def send` to `async def send` |
| `test_analyze_empty_response_returns_empty_list` | 321-323 | `EmptyProvider` | Change `def send` to `async def send` |
| `test_analyze_whitespace_only_returns_empty_list` | 346-348 | `WhitespaceProvider` | Change `def send` to `async def send` |
| `test_analyze_complex_response_with_markdown_and_prefix` | 371-380 | `ComplexProvider` | Change `def send` to `async def send` |
| `test_analyze_normalizes_bullet_list_with_dash` | 410-412 | `BulletDashProvider` | Change `def send` to `async def send` |
| `test_analyze_normalizes_bullet_list_with_asterisk` | 440-442 | `BulletAsteriskProvider` | Change `def send` to `async def send` |
| `test_analyze_normalizes_numbered_list` | 470-472 | `NumberedListProvider` | Change `def send` to `async def send` |
| `test_analyze_filters_comment_lines` | 502-504 | `CommentProvider` | Change `def send` to `async def send` |
| `test_analyze_mixed_formatting` | 532-541 | `MixedFormattingProvider` | Change `def send` to `async def send` |
| `test_analyze_filters_empty_bullet_points` | 571-573 | `EmptyBulletProvider` | Change `def send` to `async def send` |
| `test_analyze_returns_empty_list_on_provider_value_error` | 605-609 | `ErrorProvider` | Change `def send` to `async def send` |
| `test_analyze_uses_system_prompt` | 638-642 | `CaptureProvider` | Change `def send` to `async def send` |
| `test_analyze_user_prompt_includes_tree_string` | 666-670 | `CaptureProvider` | Change `def send` to `async def send` |
| `test_analyze_user_prompt_format` | 696-700 | `CaptureProvider` | Change `def send` to `async def send` |

For each provider class, only change the method signature - no changes to method bodies.

---

### 5. Convert Test Methods in TestStructureAdvisorAnalyzeMethod to Async

**File:** `file:tests/unit/scout/test_advisor.py`

**Location:** Lines 130-626 (TestStructureAdvisorAnalyzeMethod class)

Convert all 17 test methods to async:

1. Add `@pytest.mark.asyncio` decorator above each test method
2. Change `def test_*` to `async def test_*`
3. Replace `result = advisor.analyze(report)` with `result = await advisor.analyze(report)`

**Test methods to convert:**

- `test_analyze_with_clean_response` (line 145)
- `test_analyze_strips_markdown_code_blocks_with_language` (line 173)
- `test_analyze_strips_markdown_code_blocks_without_language` (line 203)
- `test_analyze_filters_prefix_text` (line 230)
- `test_analyze_filters_empty_lines` (line 259)
- `test_analyze_accepts_simple_filenames_without_pattern_chars` (line 288)
- `test_analyze_empty_response_returns_empty_list` (line 316)
- `test_analyze_whitespace_only_returns_empty_list` (line 341)
- `test_analyze_complex_response_with_markdown_and_prefix` (line 366)
- `test_analyze_normalizes_bullet_list_with_dash` (line 405)
- `test_analyze_normalizes_bullet_list_with_asterisk` (line 435)
- `test_analyze_normalizes_numbered_list` (line 465)
- `test_analyze_filters_comment_lines` (line 497)
- `test_analyze_mixed_formatting` (line 527)
- `test_analyze_filters_empty_bullet_points` (line 566)
- `test_analyze_returns_empty_list_on_provider_value_error` (line 595)

**Example transformation:**

```python
# Before
def test_analyze_with_clean_response(self) -> None:
    """Test analyze with clean response (no markdown, no prefix)."""
    # ... setup code ...
    result = advisor.analyze(report)
    # ... assertions ...

# After
@pytest.mark.asyncio
async def test_analyze_with_clean_response(self) -> None:
    """Test analyze with clean response (no markdown, no prefix)."""
    # ... setup code ...
    result = await advisor.analyze(report)
    # ... assertions ...
```

**Note:** The test `test_analyze_method_exists` (line 133) remains synchronous as it only checks method existence.

---

### 6. Convert Test Methods in TestStructureAdvisorPromptConstruction to Async

**File:** `file:tests/unit/scout/test_advisor.py`

**Location:** Lines 628-719 (TestStructureAdvisorPromptConstruction class)

Convert all 3 test methods to async:

1. Add `@pytest.mark.asyncio` decorator above each test method
2. Change `def test_*` to `async def test_*`
3. Replace `advisor.analyze(report)` with `await advisor.analyze(report)`

**Test methods to convert:**

- `test_analyze_uses_system_prompt` (line 631)
- `test_analyze_user_prompt_includes_tree_string` (line 659)
- `test_analyze_user_prompt_format` (line 689)

---

### 7. Keep Introspection Tests Synchronous

**File:** `file:tests/unit/scout/test_advisor.py`

**No changes required** for the following test classes (26 tests total):

- **TestStructureAdvisorInitialization** (lines 64-128): 5 tests - only check initialization, no `analyze()` calls
- **TestStructureAdvisorSystemPromptConstant** (lines 721-755): 4 tests - only check constant existence/content
- **TestStructureAdvisorDocumentation** (lines 757-798): 4 tests - only check docstrings
- **TestStructureAdvisorTypeHints** (lines 800-835): 2 tests - only check type hints
- **TestStructureAdvisorAnalyzeMethod.test_analyze_method_exists** (line 133): 1 test - only checks method existence

These tests perform introspection only and don't invoke async methods.

---

### 8. Verification Checklist

After implementation, verify:

- [ ] `asyncio_mode = "auto"` added to `pyproject.toml`
- [ ] `AsyncMock` imported in test file
- [ ] `TestMockProvider.send()` is `async def`
- [ ] All 19 inline provider classes have `async def send()`
- [ ] All 20 test methods have `@pytest.mark.asyncio` decorator
- [ ] All 20 test methods are `async def`
- [ ] All 20 test methods use `await advisor.analyze()`
- [ ] 26 introspection tests remain synchronous
- [ ] Running `pytest tests/unit/scout/test_advisor.py` produces failures (RED phase)

---

## Expected Test Failures (RED Phase)

After implementation, tests will fail with errors like:

- `RuntimeWarning: coroutine 'TestMockProvider.send' was never awaited`
- `TypeError: object str can't be used in 'await' expression`
- `AssertionError` due to coroutine objects instead of expected string results

These failures confirm the async conversion is complete and tests are ready for the GREEN phase implementation.

---

## Summary Table

| Component | Total Tests | Async Conversion | Remain Sync |
|-----------|-------------|------------------|-------------|
| TestMockProvider | 1 class | 1 method | 0 |
| Inline Providers | 19 classes | 19 methods | 0 |
| TestStructureAdvisorInitialization | 5 | 0 | 5 |
| TestStructureAdvisorAnalyzeMethod | 17 | 16 | 1 |
| TestStructureAdvisorPromptConstruction | 3 | 3 | 0 |
| TestStructureAdvisorSystemPromptConstant | 4 | 0 | 4 |
| TestStructureAdvisorDocumentation | 4 | 0 | 4 |
| TestStructureAdvisorTypeHints | 2 | 0 | 2 |
| **Total** | **46** | **20** | **26** |