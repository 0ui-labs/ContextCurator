I have created the following plan after thorough exploration and analysis of the codebase. Follow the below plan verbatim. Trust the files and references. Do not re-verify what's written in the plan. Explore only when absolutely necessary. First implement all the proposed file changes and then I'll review all the changes together at the end.

## Observations

The codebase follows strict TDD practices with 100% coverage requirements. `CerebrasProvider` currently exists as a stub raising `NotImplementedError`. The project already uses `unittest.mock` for testing external dependencies (seen in `file:tests/unit/test_setup_check.py`). The `LLMProvider` protocol defines a simple interface with a `send(system, user)` method returning a string. The `StructureAdvisor` class demonstrates how providers are used via dependency injection.

## Approach

Replace the `CerebrasProvider` stub with a real implementation using the OpenAI Python client configured for Cerebras API. Use environment variable `CEREBRAS_API_KEY` for authentication, failing fast with `ValueError` if not set. Implement the `send()` method to make actual API calls with `temperature=0.2` for deterministic responses. Update tests to use `unittest.mock.patch` to mock the OpenAI client, testing initialization and send logic without real API calls, maintaining 100% coverage following existing project patterns.

## Implementation Steps

### Phase 1: Update CerebrasProvider Implementation

**File: `file:src/codemap/core/llm.py`**

1. **Add imports at the top of the file:**
   - Import `os` module for environment variable access
   - Import `OpenAI` class from `openai` package

2. **Replace the entire `CerebrasProvider` class (lines 67-102):**
   - Update class docstring to reflect real implementation instead of stub
   - Implement `__init__` method:
     - Read `CEREBRAS_API_KEY` from `os.environ.get("CEREBRAS_API_KEY")`
     - If API key is `None` or empty string, raise `ValueError("CEREBRAS_API_KEY environment variable not set")`
     - Initialize `self.client = OpenAI(api_key=api_key, base_url="https://api.cerebras.ai/v1")`
     - Set `self.model = "llama3.1-70b"`
   - Implement `send(self, system: str, user: str) -> str` method:
     - Add `# pragma: no cover` comment on the method definition line
     - Call `response = self.client.chat.completions.create(model=self.model, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}], temperature=0.2)`
     - Return `response.choices[0].message.content`
   - Update docstrings:
     - Class docstring: Describe real Cerebras API integration, mention API key requirement, base URL, and model used
     - `__init__` docstring: Document that it reads `CEREBRAS_API_KEY` environment variable and raises `ValueError` if not set
     - `send` docstring: Document that it makes real API calls to Cerebras, mention temperature setting, and that it's marked with pragma: no cover

### Phase 2: Update Test Suite

**File: `file:tests/unit/core/test_llm.py`**

1. **Add import at the top:**
   - Add `from unittest.mock import MagicMock, patch` to imports section

2. **Update `TestCerebrasProvider` class (lines 264-358):**

   - **Replace `test_cerebras_provider_init_no_parameters` (lines 282-288):**
     - Rename to `test_cerebras_provider_init_requires_api_key`
     - Use `@patch.dict(os.environ, {"CEREBRAS_API_KEY": "test-key"}, clear=True)` decorator
     - Use `@patch("codemap.core.llm.OpenAI")` decorator
     - Test that provider can be instantiated when API key is set
     - Verify OpenAI client is initialized with correct parameters (api_key, base_url)
     - Verify model is set to "llama3.1-70b"

   - **Add new test `test_cerebras_provider_init_missing_api_key`:**
     - Use `@patch.dict(os.environ, {}, clear=True)` to ensure no API key
     - Test that instantiation raises `ValueError` with message "CEREBRAS_API_KEY environment variable not set"

   - **Add new test `test_cerebras_provider_init_empty_api_key`:**
     - Use `@patch.dict(os.environ, {"CEREBRAS_API_KEY": ""}, clear=True)`
     - Test that instantiation raises `ValueError` with message "CEREBRAS_API_KEY environment variable not set"

   - **Replace `test_cerebras_provider_send_raises_not_implemented_error` (lines 315-326):**
     - Rename to `test_cerebras_provider_send_calls_openai_api`
     - Use `@patch.dict(os.environ, {"CEREBRAS_API_KEY": "test-key"}, clear=True)` decorator
     - Use `@patch("codemap.core.llm.OpenAI")` decorator
     - Mock the OpenAI client's `chat.completions.create` method to return a mock response
     - Mock response structure: `response.choices[0].message.content = "mocked response"`
     - Call `provider.send("system prompt", "user prompt")`
     - Verify `chat.completions.create` was called with correct parameters (model, messages, temperature)
     - Verify returned value is "mocked response"
     - Note: This test verifies the integration logic without making real API calls

   - **Update `test_cerebras_provider_conforms_to_protocol` (lines 328-336):**
     - Add `@patch.dict(os.environ, {"CEREBRAS_API_KEY": "test-key"}, clear=True)` decorator
     - Add `@patch("codemap.core.llm.OpenAI")` decorator
     - Keep existing assertions

   - **Update `test_cerebras_provider_has_docstring` (lines 337-345):**
     - Update assertion to check for "cerebras" and "api" in docstring (not "stub")

   - **Update `test_cerebras_provider_send_has_docstring` (lines 347-357):**
     - Update assertion to check for "api" or "cerebras" in docstring (not "notimplementederror")

3. **Update `TestGetProviderFactory` class:**

   - **Update `test_get_provider_cerebras_returns_cerebras_provider` (lines 390-398):**
     - Add `@patch.dict(os.environ, {"CEREBRAS_API_KEY": "test-key"}, clear=True)` decorator
     - Add `@patch("codemap.core.llm.OpenAI")` decorator
     - Keep existing assertions

   - **Update `test_get_provider_returned_cerebras_raises_not_implemented` (lines 500-508):**
     - Rename to `test_get_provider_returned_cerebras_works_with_mock`
     - Add `@patch.dict(os.environ, {"CEREBRAS_API_KEY": "test-key"}, clear=True)` decorator
     - Add `@patch("codemap.core.llm.OpenAI")` decorator
     - Mock the OpenAI client to return a test response
     - Call `provider.send("system", "user")` and verify it returns the mocked response
     - Remove the NotImplementedError assertion

   - **Update `test_factory_returns_protocol_conformant_provider` (lines 510-532):**
     - Add `@patch.dict(os.environ, {"CEREBRAS_API_KEY": "test-key"}, clear=True)` decorator
     - Add `@patch("codemap.core.llm.OpenAI")` decorator for the cerebras_provider section
     - Mock the OpenAI client to return a test response
     - Replace the NotImplementedError assertion with a successful call verification

### Testing Strategy

```mermaid
sequenceDiagram
    participant Test as Test Suite
    participant Mock as unittest.mock
    participant Provider as CerebrasProvider
    participant OpenAI as OpenAI Client (Mocked)
    
    Test->>Mock: @patch.dict(os.environ)
    Test->>Mock: @patch("codemap.core.llm.OpenAI")
    Test->>Provider: __init__()
    Provider->>Mock: os.environ.get("CEREBRAS_API_KEY")
    Mock-->>Provider: "test-key"
    Provider->>OpenAI: OpenAI(api_key, base_url)
    OpenAI-->>Provider: client instance (mocked)
    Test->>Provider: send("system", "user")
    Provider->>OpenAI: chat.completions.create(...)
    OpenAI-->>Provider: mocked response
    Provider-->>Test: "mocked response"
    Test->>Test: Assert correct parameters used
```

### Key Implementation Details

| Component | Detail | Rationale |
|-----------|--------|-----------|
| API Key Source | `os.environ.get("CEREBRAS_API_KEY")` | Standard practice for sensitive credentials |
| Error Handling | Raise `ValueError` if key missing/empty | Fail fast with clear error message |
| Base URL | `https://api.cerebras.ai/v1` | Cerebras API endpoint |
| Model | `llama3.1-70b` | As specified in requirements |
| Temperature | `0.2` | Low temperature for precise, deterministic responses |
| Coverage Strategy | `# pragma: no cover` on send method | Avoid real API calls in tests while maintaining 100% coverage |
| Test Mocking | `unittest.mock.patch` | Mock OpenAI client following existing project patterns |

### Files Modified

- `file:src/codemap/core/llm.py` - Replace stub with real implementation
- `file:tests/unit/core/test_llm.py` - Update tests to mock OpenAI client instead of expecting NotImplementedError