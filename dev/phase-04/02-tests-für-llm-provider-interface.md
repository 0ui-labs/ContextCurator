I have created the following plan after thorough exploration and analysis of the codebase. Follow the below plan verbatim. Trust the files and references. Do not re-verify what's written in the plan. Explore only when absolutely necessary. First implement all the proposed file changes and then I'll review all the changes together at the end.

## Observations

The codebase follows strict TDD with 100% coverage requirements, frozen dataclasses, comprehensive Google-style docstrings, and multiple test classes grouping related functionality. The existing `file:tests/unit/core/test_core.py` only validates empty `__all__` exports. The `file:src/codemap/core/llm.py` module doesn't exist yet, indicating pure TDD workflow where tests drive implementation. Coverage excludes `NotImplementedError` (line 51 in `file:pyproject.toml`), allowing stubs without breaking coverage.

## Approach

Create `file:tests/unit/core/test_llm.py` following established patterns from `file:tests/unit/scout/test_tree.py`: multiple test classes (`TestMockProvider`, `TestProviderFactory`, `TestProtocolConformance`, `TestCerebrasStub`), Arrange-Act-Assert structure, full type hints, and comprehensive docstrings. Tests will validate `MockProvider` returns deterministic responses, factory dispatches correctly, protocol typing works with mypy, and Cerebras stub raises `NotImplementedError`. Update `file:tests/unit/core/test_core.py` to verify new exports in `__all__`.

## Implementation Steps

### 1. Create Test File Structure

Create `file:tests/unit/core/test_llm.py` with module docstring explaining test coverage scope (LLM provider interface, mock implementation, factory function, protocol conformance).

### 2. Implement TestMockProvider Class

**Test Class:** `TestMockProvider`

- **test_mock_provider_returns_string**: Verify `MockProvider().send(system="...", user="...")` returns `str` type
- **test_mock_provider_deterministic_output**: Verify repeated calls with same inputs return identical output
- **test_mock_provider_ignores_input_content**: Verify output is independent of `system` and `user` parameter values (mock behavior)
- **test_mock_provider_returns_gitignore_format**: Verify output contains gitignore-style patterns (e.g., `node_modules/`, `*.pyc`)
- **test_mock_provider_multiline_response**: Verify output contains multiple lines separated by newlines

### 3. Implement TestProviderFactory Class

**Test Class:** `TestProviderFactory`

- **test_get_provider_default_returns_mock**: Verify `get_provider()` without arguments returns `MockProvider` instance
- **test_get_provider_mock_explicit**: Verify `get_provider("mock")` returns `MockProvider` instance
- **test_get_provider_mock_type_check**: Verify returned instance has `send` method with correct signature
- **test_get_provider_invalid_name_raises_error**: Verify `get_provider("invalid")` raises `ValueError` with descriptive message
- **test_get_provider_case_sensitive**: Verify `get_provider("Mock")` raises `ValueError` (case-sensitive matching)

### 4. Implement TestCerebrasStub Class

**Test Class:** `TestCerebrasStub`

- **test_get_provider_cerebras_returns_instance**: Verify `get_provider("cerebras")` returns an object (not None)
- **test_cerebras_provider_send_raises_not_implemented**: Verify calling `.send()` on Cerebras provider raises `NotImplementedError`
- **test_cerebras_provider_has_send_method**: Verify Cerebras provider has `send` attribute (protocol conformance)

### 5. Implement TestProtocolConformance Class

**Test Class:** `TestProtocolConformance`

- **test_mock_provider_conforms_to_protocol**: Use `isinstance()` check with `typing.Protocol` to verify `MockProvider` implements `LLMProvider`
- **test_protocol_has_send_method**: Verify `LLMProvider` protocol defines `send(system: str, user: str) -> str` signature
- **test_factory_return_type_annotation**: Verify `get_provider` has correct return type annotation (`LLMProvider`)

### 6. Update Existing Core Tests

Modify `file:tests/unit/core/test_core.py`:

- Update `test_core_module_exports_empty_all` to verify `core.__all__` contains `["LLMProvider", "MockProvider", "CerebrasProvider", "get_provider"]` (or adjust based on actual exports)
- Add `test_core_module_imports_llm_components` to verify `from codemap.core import LLMProvider, get_provider` works without errors

### 7. Test Organization and Documentation

- Add comprehensive module docstring explaining test structure
- Group tests logically with descriptive class names
- Use descriptive test method names following `test_<component>_<behavior>_<expected_result>` pattern
- Include inline comments for complex assertions
- Ensure all test methods have type hints (`-> None`)

## Expected Test Structure

```
tests/unit/core/test_llm.py
├── Module docstring
├── Imports (typing, pytest, codemap.core.llm)
├── TestMockProvider (5 tests)
├── TestProviderFactory (5 tests)
├── TestCerebrasStub (3 tests)
└── TestProtocolConformance (3 tests)
```

## Coverage Considerations

- All code paths in `MockProvider.send()` must be tested
- Factory function must test all branches (mock, cerebras, invalid)
- Protocol conformance ensures type safety without runtime overhead
- `NotImplementedError` in Cerebras stub is excluded from coverage (line 51 in `file:pyproject.toml`)
- Total: 16 tests ensuring 100% coverage of testable code

## Dependencies

- No new dependencies required
- Uses existing `pytest` framework
- Leverages `typing.Protocol` from standard library
- Follows patterns from `file:tests/unit/scout/test_tree.py`