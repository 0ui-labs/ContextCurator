I have created the following plan after thorough exploration and analysis of the codebase. Follow the below plan verbatim. Trust the files and references. Do not re-verify what's written in the plan. Explore only when absolutely necessary. First implement all the proposed file changes and then I'll review all the changes together at the end.

## Observations

The existing `test_resolve_external_import()` in `file:tests/unit/engine/test_builder.py` (lines 1096-1137) currently asserts that external imports like `os`, `pathlib`, and `pytest` create NO edges—this test will fail after the implementation changes. The test suite follows a consistent pattern: create temp files, build graph, reset edges for isolation, call `_resolve_and_add_import()`, then assert edge/node existence. The `GraphManager` uses string node IDs and supports arbitrary node types via attributes. External nodes should use ID format `external::{module_name}` with `type="external_module"` attribute.

## Approach

Transform the existing external import test from negative assertions (no edges) to positive assertions (external nodes + edges exist), then add comprehensive coverage for additional external modules (networkx, openai). Follow the established TDD pattern: arrange temp files → build graph → test `_resolve_and_add_import()` in isolation → assert node attributes and edge relationships. Group tests logically within `TestResolveAndAddImport` class to maintain cohesion with existing import resolution tests.

## Implementation Steps

### 1. Update Existing External Import Test

**File:** `file:tests/unit/engine/test_builder.py`

**Location:** Lines 1096-1137 (`test_resolve_external_import()`)

**Changes:**

- **Rename test** to `test_resolve_external_import_creates_external_nodes()` for clarity
- **Update docstring** to reflect new behavior: "Validates that MapBuilder creates virtual external nodes with type='external_module' and IMPORTS edges for stdlib/third-party imports"
- **Replace negative assertions** (no edges) with positive assertions:
  - Assert `external::os` node exists in graph: `assert "external::os" in graph_manager.graph.nodes`
  - Assert node has correct type: `assert graph_manager.graph.nodes["external::os"]["type"] == "external_module"`
  - Assert IMPORTS edge exists: `assert graph_manager.graph.has_edge("main.py", "external::os")`
  - Assert edge relationship: `assert graph_manager.graph.edges["main.py", "external::os"]["relationship"] == "IMPORTS"`
- **Repeat assertions** for `external::pathlib` and `external::pytest`
- **Remove** the edge count comparison (`edges_before` vs `edges_after`) since edges are now expected

### 2. Add Comprehensive External Module Test

**File:** `file:tests/unit/engine/test_builder.py`

**Location:** After `test_resolve_external_import_creates_external_nodes()` (around line 1138)

**New Test:** `test_resolve_multiple_external_modules()`

**Structure:**

```
def test_resolve_multiple_external_modules(self, tmp_path: Path) -> None:
    """Test _resolve_and_add_import() with multiple external modules (networkx, openai).
    
    Validates that MapBuilder correctly handles multiple external imports
    in a single file, creating distinct external nodes for each module
    and establishing separate IMPORTS edges.
    """
```

**Implementation:**

- **Arrange:** Create `main.py` with imports: `import networkx`, `import openai`, `from typing import Dict`
- **Build graph** and get `graph_manager`
- **Act:** Call `_resolve_and_add_import()` for each module: `"networkx"`, `"openai"`, `"typing"`
- **Assert for each external module:**
  - Node exists: `"external::networkx"`, `"external::openai"`, `"external::typing"`
  - Node type is `"external_module"`
  - IMPORTS edge exists from `"main.py"` to external node
  - Edge relationship is `"IMPORTS"`

### 3. Add Idempotency Test for External Modules

**File:** `file:tests/unit/engine/test_builder.py`

**Location:** After `test_resolve_multiple_external_modules()`

**New Test:** `test_resolve_external_import_idempotent()`

**Structure:**

```
def test_resolve_external_import_idempotent(self, tmp_path: Path) -> None:
    """Test _resolve_and_add_import() with duplicate external imports.
    
    Validates that calling _resolve_and_add_import() multiple times
    with the same external module is idempotent: only one node and
    one edge are created, with no errors or duplicates.
    """
```

**Implementation:**

- **Arrange:** Create `main.py` with `import os`
- **Build graph** and get `graph_manager`
- **Act:** Call `_resolve_and_add_import()` for `"os"` **three times**
- **Assert:**
  - Only one `external::os` node exists
  - Only one IMPORTS edge from `"main.py"` to `"external::os"`
  - Node count matches expected (file node + external node = 2)
  - Edge count matches expected (1 IMPORTS edge)

### 4. Add Mixed Internal/External Import Test

**File:** `file:tests/unit/engine/test_builder.py`

**Location:** After `test_resolve_external_import_idempotent()`

**New Test:** `test_resolve_mixed_internal_external_imports()`

**Structure:**

```
def test_resolve_mixed_internal_external_imports(self, tmp_path: Path) -> None:
    """Test _resolve_and_add_import() with both internal and external imports.
    
    Validates that MapBuilder correctly handles files with mixed imports:
    internal modules resolve to file nodes, external modules create
    external nodes, and both types of edges coexist in the graph.
    """
```

**Implementation:**

- **Arrange:** 
  - Create `utils.py` with a function
  - Create `main.py` with `import os` and `from utils import helper`
- **Build graph** and reset edges for isolation
- **Act:** 
  - Call `_resolve_and_add_import()` for `"os"` (external)
  - Call `_resolve_and_add_import()` for `"utils"` (internal)
- **Assert:**
  - Internal edge: `main.py` → `utils.py` (relationship="IMPORTS")
  - External node: `external::os` exists with `type="external_module"`
  - External edge: `main.py` → `external::os` (relationship="IMPORTS")
  - Total edges from `main.py` is 2

### 5. Verify No Warnings Logged for External Imports

**File:** `file:tests/unit/engine/test_builder.py`

**Location:** After `test_resolve_mixed_internal_external_imports()`

**New Test:** `test_resolve_external_import_no_warnings()`

**Structure:**

```
def test_resolve_external_import_no_warnings(self, tmp_path: Path, caplog) -> None:
    """Test _resolve_and_add_import() logs no warnings for external imports.
    
    Validates that external imports are treated as normal behavior,
    not error conditions, and no warnings are logged to the logger.
    """
```

**Implementation:**

- **Arrange:** Create `main.py` with `import os`
- **Build graph** with `caplog` at WARNING level
- **Act:** Call `_resolve_and_add_import()` for `"os"`
- **Assert:**
  - No warning messages in `caplog.records`
  - External node and edge created successfully
  - Specifically check no messages containing "os", "external", "unresolved"

---

## Test Execution Order

Run tests in this sequence to verify implementation:

1. `test_resolve_external_import_creates_external_nodes()` - Core functionality
2. `test_resolve_multiple_external_modules()` - Multiple externals
3. `test_resolve_external_import_idempotent()` - Duplicate handling
4. `test_resolve_mixed_internal_external_imports()` - Integration with internal imports
5. `test_resolve_external_import_no_warnings()` - Logging behavior

## Expected Test Coverage

These tests will cover:
- External node creation with correct ID format (`external::{name}`)
- Node attribute validation (`type="external_module"`)
- IMPORTS edge creation from source file to external node
- Edge relationship attribute (`relationship="IMPORTS"`)
- Idempotency of external import resolution
- Coexistence of internal and external imports
- No warnings/errors logged for external modules
- Multiple external modules (os, pathlib, pytest, networkx, openai, typing)