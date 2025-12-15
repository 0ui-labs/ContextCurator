I have created the following plan after thorough exploration and analysis of the codebase. Follow the below plan verbatim. Trust the files and references. Do not re-verify what's written in the plan. Explore only when absolutely necessary. First implement all the proposed file changes and then I'll review all the changes together at the end.

## Observations

The `file:src/codemap/core/llm.py` module defines a `LLMProvider` Protocol with a synchronous `send()` method, along with `MockProvider` and `CerebrasProvider` implementations. The current implementation uses synchronous patterns throughout. The Protocol pattern is well-structured with comprehensive docstrings. The `MockProvider` is used for deterministic testing and returns a fixed gitignore-pattern string. Type hints use `Protocol` from `typing` module.

## Approach

Convert the `LLMProvider` Protocol and `MockProvider` to async patterns by changing method signatures to `async def`, updating return type hints to use `str` (no changes needed as async functions still return the same types), and updating all docstrings to reflect the asynchronous nature. The `CerebrasProvider` will remain untouched as it's handled in a subsequent phase. This follows the TDD RED phase approach where we update the interface first, causing dependent code to fail until implementations catch up.

## Implementation Steps

### 1. Update LLMProvider Protocol to async

**File**: `file:src/codemap/core/llm.py`

- Change line 23 from `def send(self, system: str, user: str) -> str:` to `async def send(self, system: str, user: str) -> str:`
- Update the docstring at line 24-32 to indicate the method is asynchronous:
  - Change line 24 from `"""Sendet Prompts an LLM und erhält Antwort."""` to `"""Sendet Prompts asynchron an LLM und erhält Antwort."""`
  - Add a note in the docstring mentioning this is an async method that must be awaited
- Verify type hints remain correct (they should, as async functions return the same types)

### 2. Update MockProvider.send() to async

**File**: `file:src/codemap/core/llm.py`

- Change line 52 from `def send(self, system: str, user: str) -> str:` to `async def send(self, system: str, user: str) -> str:`
- Update the docstring at line 53-66:
  - Change line 53 from `"""Gibt einen deterministischen String im gitignore-Format zurück."""` to `"""Gibt asynchron einen deterministischen String im gitignore-Format zurück."""`
  - Add a note that this is an async method that must be awaited, even though it doesn't perform I/O
- Keep the return statement at line 67 unchanged: `return "node_modules/\ndist/\n.venv/"`
- Verify the `# noqa: ARG002` comment remains on the method signature line

### 3. Update class-level docstrings

**File**: `file:src/codemap/core/llm.py`

- Update `LLMProvider` class docstring (lines 14-21):
  - Change line 20 from `send: Sendet System- und User-Prompts an LLM, gibt Antwort zurück.` to `send: Sendet asynchron System- und User-Prompts an LLM, gibt Antwort zurück.`
- Update `MockProvider` class docstring (lines 37-50):
  - Add a note in the class docstring mentioning that the `send()` method is async and must be awaited

### 4. Verify type hints and imports

**File**: `file:src/codemap/core/llm.py`

- Verify that no additional imports are needed for async support (Python's `async def` is built-in)
- Confirm that the `Protocol` import from `typing` (line 8) supports async methods (it does)
- Ensure return type hints remain `-> str` for both methods (no changes needed)
- Verify that the `get_provider()` factory function return type `-> LLMProvider` remains valid

### 5. Leave CerebrasProvider untouched

**File**: `file:src/codemap/core/llm.py`

- Do NOT modify `CerebrasProvider` class (lines 70-142) in this phase
- Do NOT modify the `get_provider()` factory function (lines 145-207)
- These will be handled in subsequent phases by other engineers

## Expected Outcome

After this phase, the `LLMProvider` Protocol and `MockProvider` will have async signatures. The `CerebrasProvider` will remain synchronous (causing a protocol violation that will be fixed in the next phase). All docstrings will accurately reflect the asynchronous nature of the methods. Type hints will remain correct. This creates the RED phase of TDD where tests will fail until implementations are updated.