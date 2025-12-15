I have created the following plan after thorough exploration and analysis of the codebase. Follow the below plan verbatim. Trust the files and references. Do not re-verify what's written in the plan. Explore only when absolutely necessary. First implement all the proposed file changes and then I'll review all the changes together at the end.

## Observations

The test file `file:tests/unit/core/test_llm.py` contains 91 test methods across 5 test classes, all currently synchronous. Tests verify protocol definitions, type hints, docstrings, and behavior for `LLMProvider`, `MockProvider`, `CerebrasProvider`, and the `get_provider` factory. The codebase uses strict TDD with 100% coverage requirements. Tests extensively use `unittest.mock.MagicMock` and `@patch` decorators to mock the OpenAI client. The pytest configuration in `file:pyproject.toml` lacks async-specific settings.

## Approach

Following TDD RED phase principles, convert all test methods to async by adding `@pytest.mark.asyncio` decorators, changing signatures to `async def`, and adding `await` to all `send()` calls. Update mock infrastructure to use `AsyncMock` for async methods and configure return values as coroutines. Add `asyncio_mode = "auto"` to pytest configuration for automatic async test detection. This intentionally breaks tests before implementation changes, enforcing strict TDD workflow. Tests will fail with "coroutine was never awaited" errors until the actual implementation is converted to async in subsequent phases.

## Implementation Steps

### 1. Configure pytest-asyncio in pyproject.toml

Add async test mode configuration to `file:pyproject.toml` under `[tool.pytest.ini_options]`:

```toml
asyncio_mode = "auto"
```

This enables automatic detection and execution of async tests without requiring explicit event loop fixtures.

### 2. Add AsyncMock import to test file

Update imports in `file:tests/unit/core/test_llm.py` at line 14:

- Change `from unittest.mock import MagicMock, patch` to `from unittest.mock import AsyncMock, MagicMock, patch`
- This provides async-compatible mock objects for coroutine methods

### 3. Convert TestLLMProviderProtocol tests (lines 21-76)

**Tests requiring NO changes** (protocol introspection only, no async calls):
- `test_llm_provider_is_protocol` (line 24)
- `test_llm_provider_has_send_method` (line 34)
- `test_send_method_signature` (line 40)
- `test_llm_provider_has_docstring` (line 56)
- `test_send_method_has_docstring` (line 65)

These tests inspect protocol structure without calling async methods, remain synchronous.

### 4. Convert TestLLMProviderProtocolImplementation tests (lines 78-124)

**Test: `test_concrete_class_implements_protocol` (line 81)**
- Add `@pytest.mark.asyncio` decorator before method
- Change `def test_concrete_class_implements_protocol(self) -> None:` to `async def test_concrete_class_implements_protocol(self) -> None:`
- Update inner `MockLLMProvider.send()` to `async def send(self, system: str, user: str) -> str:`
- Change `result = instance.send("test_system", "test_user")` to `result = await instance.send("test_system", "test_user")`

**Tests requiring NO changes** (type hint introspection only):
- `test_protocol_enforces_return_type` (line 104)
- `test_protocol_requires_two_str_parameters` (line 113)

### 5. Convert TestMockProvider tests (lines 126-264)

**Tests requiring NO changes** (instantiation/introspection only):
- `test_mock_provider_exists` (line 129)
- `test_mock_provider_has_init` (line 138)
- `test_mock_provider_init_no_parameters` (line 144)
- `test_mock_provider_has_send_method` (line 152)
- `test_mock_provider_send_signature` (line 161)
- `test_mock_provider_has_docstring` (line 246)
- `test_mock_provider_send_has_docstring` (line 256)

**Tests requiring async conversion** (call `send()` method):

- `test_mock_provider_send_returns_deterministic_string` (line 181)
- `test_mock_provider_send_returns_gitignore_format` (line 193)
- `test_mock_provider_send_is_deterministic` (line 206)
- `test_mock_provider_send_expected_content` (line 220)
- `test_mock_provider_conforms_to_protocol` (line 233)

For each:
- Add `@pytest.mark.asyncio` decorator
- Change `def` to `async def`
- Add `await` to all `provider.send()` calls

Example for line 181:
```python
@pytest.mark.asyncio
async def test_mock_provider_send_returns_deterministic_string(self) -> None:
    provider = MockProvider()
    result = await provider.send("system prompt", "user prompt")
    assert isinstance(result, str)
    assert len(result) > 0
```

### 6. Convert TestCerebrasProvider tests (lines 266-423)

**Tests requiring NO changes** (introspection/docstring checks):
- `test_cerebras_provider_has_init` (line 280)
- `test_cerebras_provider_send_signature` (line 338)
- `test_cerebras_provider_has_docstring` (line 402)
- `test_cerebras_provider_send_has_docstring` (line 412)

**Tests requiring async conversion with AsyncMock**:

- `test_cerebras_provider_exists` (line 271)
- `test_cerebras_provider_init_requires_api_key` (line 288)
- `test_cerebras_provider_has_send_method` (line 329)
- `test_cerebras_provider_send_calls_openai_api` (line 356)
- `test_cerebras_provider_conforms_to_protocol` (line 393)

**Critical: Update mock setup for async OpenAI client**

For `test_cerebras_provider_send_calls_openai_api` (line 356):
- Add `@pytest.mark.asyncio` decorator
- Change to `async def`
- Replace `mock_client = MagicMock()` with `mock_client = AsyncMock()`
- Make `create` method return a coroutine: `mock_client.chat.completions.create = AsyncMock(return_value=mock_response)`
- Change `result = provider.send(...)` to `result = await provider.send(...)`

Example:
```python
@pytest.mark.asyncio
@patch.dict(os.environ, {"CEREBRAS_API_KEY": "test-key"}, clear=True)
@patch("codemap.core.llm.AsyncOpenAI")  # Note: patch AsyncOpenAI not OpenAI
async def test_cerebras_provider_send_calls_openai_api(self, mock_openai_cls: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_openai_cls.return_value = mock_client
    
    mock_message = MagicMock()
    mock_message.content = "mocked response"
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    provider = CerebrasProvider()
    result = await provider.send("system prompt", "user prompt")
    
    mock_client.chat.completions.create.assert_called_once_with(...)
    assert result == "mocked response"
```

**Tests requiring NO changes** (error handling, no API calls):
- `test_cerebras_provider_init_missing_api_key` (line 310)
- `test_cerebras_provider_init_empty_api_key` (line 319)

### 7. Convert TestGetProviderFactory tests (lines 426-631)

**Tests requiring NO changes** (introspection/docstring checks):
- `test_get_provider_exists` (line 429)
- `test_get_provider_return_type_annotation` (line 491)
- `test_get_provider_parameter_type_annotation` (line 500)
- `test_get_provider_has_docstring` (line 509)
- `test_get_provider_docstring_mentions_factory_pattern` (line 515)
- `test_get_provider_docstring_lists_available_providers` (line 523)
- `test_get_provider_docstring_has_examples_section` (line 533)
- `test_get_provider_docstring_has_mock_example` (line 541)
- `test_get_provider_docstring_has_cerebras_example` (line 549)

**Tests requiring async conversion**:

- `test_get_provider_default_returns_mock_provider` (line 434)
- `test_get_provider_mock_returns_mock_provider` (line 445)
- `test_get_provider_cerebras_returns_cerebras_provider` (line 457)
- `test_get_provider_returned_mock_works_correctly` (line 557)
- `test_get_provider_returned_cerebras_works_with_mock` (line 569)
- `test_factory_returns_protocol_conformant_provider` (line 594)

For each:
- Add `@pytest.mark.asyncio` decorator
- Change to `async def`
- Add `await` to all `send()` calls
- Update AsyncMock setup for Cerebras tests

**Tests requiring NO changes** (error handling, no send() calls):
- `test_get_provider_unknown_raises_value_error` (line 467)
- `test_get_provider_invalid_provider_raises_value_error` (line 478)

### 8. Update patch targets for AsyncOpenAI

All `@patch("codemap.core.llm.OpenAI")` decorators must change to `@patch("codemap.core.llm.AsyncOpenAI")` to match the async implementation:

- Line 270: `@patch("codemap.core.llm.OpenAI")` → `@patch("codemap.core.llm.AsyncOpenAI")`
- Line 287: `@patch("codemap.core.llm.OpenAI")` → `@patch("codemap.core.llm.AsyncOpenAI")`
- Line 328: `@patch("codemap.core.llm.OpenAI")` → `@patch("codemap.core.llm.AsyncOpenAI")`
- Line 355: `@patch("codemap.core.llm.OpenAI")` → `@patch("codemap.core.llm.AsyncOpenAI")`
- Line 392: `@patch("codemap.core.llm.OpenAI")` → `@patch("codemap.core.llm.AsyncOpenAI")`
- Line 456: `@patch("codemap.core.llm.OpenAI")` → `@patch("codemap.core.llm.AsyncOpenAI")`
- Line 568: `@patch("codemap.core.llm.OpenAI")` → `@patch("codemap.core.llm.AsyncOpenAI")`
- Line 593: `@patch("codemap.core.llm.OpenAI")` → `@patch("codemap.core.llm.AsyncOpenAI")`

### 9. Special handling for nested helper functions

In `test_factory_returns_protocol_conformant_provider` (line 594), the nested `use_provider` helper function must become async:

```python
async def use_provider(provider: LLMProvider) -> str:
    """Use a provider through the protocol interface."""
    return await provider.send("system prompt", "user prompt")
```

And calls to it: `result = await use_provider(mock_provider)`

## Expected Test Failures (RED Phase)

After these changes, running `pytest tests/unit/core/test_llm.py` will produce:

1. **RuntimeWarning: coroutine was never awaited** - for all async `send()` calls in the implementation
2. **TypeError: object MagicMock can't be used in 'await' expression** - for improperly mocked async methods
3. **AttributeError: 'AsyncOpenAI' has no attribute...** - if implementation still uses `OpenAI` instead of `AsyncOpenAI`

These failures confirm tests are correctly updated and implementation needs async conversion (GREEN phase).

## Summary Table

| Test Class | Total Tests | Async Conversion | No Changes |
|------------|-------------|------------------|------------|
| TestLLMProviderProtocol | 5 | 0 | 5 |
| TestLLMProviderProtocolImplementation | 3 | 1 | 2 |
| TestMockProvider | 10 | 5 | 5 |
| TestCerebrasProvider | 10 | 5 | 5 |
| TestGetProviderFactory | 18 | 6 | 12 |
| **Total** | **46** | **17** | **29** |

## Verification Checklist

- [ ] All 17 async test methods have `@pytest.mark.asyncio` decorator
- [ ] All 17 async test methods use `async def` signature
- [ ] All `send()` calls in async tests use `await`
- [ ] All `AsyncMock` instances properly configured for coroutine returns
- [ ] All 8 `@patch` decorators updated to `AsyncOpenAI`
- [ ] `asyncio_mode = "auto"` added to `pyproject.toml`
- [ ] `AsyncMock` imported in test file
- [ ] Tests fail with expected async-related errors (RED phase confirmed)