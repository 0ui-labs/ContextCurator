I have created the following plan after thorough exploration and analysis of the codebase. Follow the below plan verbatim. Trust the files and references. Do not re-verify what's written in the plan. Explore only when absolutely necessary. First implement all the proposed file changes and then I'll review all the changes together at the end.

## Observations

The codebase follows strict TDD with 100% coverage requirements, frozen dataclasses for immutability (`FileEntry`, `CodeNode`), and comprehensive test patterns using pytest. Dependencies (`networkx>=3.0.0`, `orjson>=3.9.0`) are already installed. The `graph` module doesn't exist yet—this is the initial RED phase. Existing tests demonstrate class-based organization, descriptive docstrings, `tmp_path` fixtures for file I/O, and thorough edge case coverage including error conditions.

## Approach

Create test-first structure following established patterns: `tests/unit/graph/` directory with `__init__.py` and `test_manager.py`. Implement four core test classes covering `GraphManager` functionality: basic node operations, hierarchy relationships, persistence (save/load roundtrip with orjson), and graph statistics. Tests will fail initially (RED phase) since `GraphManager` implementation is incomplete. Use `FileEntry` and `CodeNode` from existing models, `tmp_path` for file operations, and verify NetworkX graph structure through node/edge queries.

## Implementation Steps

### 1. Create Test Directory Structure

Create `tests/unit/graph/` directory with empty `__init__.py` file to make it a Python package, following the pattern used in `file:tests/unit/scout/` and `file:tests/unit/mapper/`.

### 2. Create Test File with Imports and Fixtures

Create `file:tests/unit/graph/test_manager.py` with:

- Standard imports: `pytest`, `pathlib.Path`, `dataclasses.FrozenInstanceError`
- Module imports: `GraphManager` from `codemap.graph.manager`, `FileEntry` from `codemap.scout.models`, `CodeNode` from `codemap.mapper.models`
- NetworkX import for graph inspection: `import networkx as nx`
- No custom fixtures needed initially (use pytest's built-in `tmp_path`)

### 3. Implement TestGraphManagerBasic Class

Create test class with methods:

**`test_graphmanager_initialization`**
- Instantiate `GraphManager()`
- Assert `manager.graph` is a `nx.DiGraph` instance
- Assert graph is empty: `manager.graph.number_of_nodes() == 0`

**`test_add_file_creates_node`**
- Create `FileEntry` with `path=Path("src/main.py")`, `size=1024`, `token_est=256`
- Call `manager.add_file(entry)`
- Assert node exists: `"src/main.py" in manager.graph.nodes`
- Assert node attributes: `manager.graph.nodes["src/main.py"]["type"] == "file"`, `["size"] == 1024`, `["token_est"] == 256`

**`test_add_file_with_relative_path`**
- Create `FileEntry` with relative path `Path("utils/helper.py")`
- Call `manager.add_file(entry)`
- Assert node ID is string representation: `"utils/helper.py" in manager.graph.nodes`

### 4. Implement TestGraphManagerHierarchy Class

Create test class for code node relationships:

**`test_add_code_node_creates_hierarchy`**
- Add file node first: `manager.add_file(FileEntry(Path("src/app.py"), 512, 128))`
- Create `CodeNode(type="function", name="calculate", start_line=10, end_line=15)`
- Call `manager.add_node("src/app.py", node)`
- Assert code node exists: `"src/app.py::calculate" in manager.graph.nodes`
- Assert node attributes: `manager.graph.nodes["src/app.py::calculate"]["type"] == "function"`, `["name"] == "calculate"`, `["start_line"] == 10`, `["end_line"] == 15`
- Assert CONTAINS edge exists: `manager.graph.has_edge("src/app.py", "src/app.py::calculate")`
- Assert edge label: `manager.graph.edges["src/app.py", "src/app.py::calculate"]["label"] == "CONTAINS"`

**`test_add_multiple_code_nodes_same_file`**
- Add file node
- Add two code nodes (function and class) to same file
- Assert both nodes exist with correct IDs: `"file::function_name"`, `"file::class_name"`
- Assert both have CONTAINS edges from file node

**`test_add_dependency_creates_import_edge`**
- Add two file nodes: `"src/main.py"`, `"src/utils.py"`
- Call `manager.add_dependency("src/main.py", "src/utils.py")`
- Assert IMPORTS edge exists: `manager.graph.has_edge("src/main.py", "src/utils.py")`
- Assert edge label: `manager.graph.edges["src/main.py", "src/utils.py"]["label"] == "IMPORTS"`

### 5. Implement TestGraphManagerPersistence Class

Create test class for save/load operations:

**`test_save_creates_file`**
- Create `GraphManager`, add file node
- Call `manager.save(tmp_path / "graph.json")`
- Assert file exists: `(tmp_path / "graph.json").exists()`
- Assert file is not empty: `(tmp_path / "graph.json").stat().st_size > 0`

**`test_save_and_load_roundtrip`**
- Create `GraphManager`, add file node and code node with CONTAINS edge
- Save to `tmp_path / "graph.json"`
- Create new `GraphManager` instance
- Call `manager2.load(tmp_path / "graph.json")`
- Assert node counts match: `manager2.graph.number_of_nodes() == manager.graph.number_of_nodes()`
- Assert edge counts match: `manager2.graph.number_of_edges() == manager.graph.number_of_edges()`
- Assert specific nodes exist with correct attributes
- Assert edges exist with correct labels

**`test_load_nonexistent_file_raises_error`**
- Create `GraphManager`
- Assert `manager.load(Path("nonexistent.json"))` raises `FileNotFoundError`

**`test_save_and_load_preserves_graph_structure`**
- Build complex graph: 3 files, 5 code nodes, 2 dependencies
- Save and load
- Assert all nodes preserved
- Assert all edges preserved with correct labels
- Assert node attributes preserved (type, size, name, etc.)

### 6. Implement TestGraphManagerStats Class

Create test class for graph statistics:

**`test_graph_stats_empty_graph`**
- Create `GraphManager`
- Assert `manager.graph_stats == {"nodes": 0, "edges": 0}`

**`test_graph_stats_with_nodes`**
- Add 3 file nodes
- Assert `manager.graph_stats == {"nodes": 3, "edges": 0}`

**`test_graph_stats_with_edges`**
- Add 2 file nodes, 1 dependency edge
- Assert `manager.graph_stats == {"nodes": 2, "edges": 1}`

**`test_graph_stats_complex_graph`**
- Build graph with files, code nodes, and dependencies
- Assert stats reflect correct counts

### 7. Add Edge Case Tests

Add methods to appropriate test classes:

**`test_add_file_duplicate_path`** (in TestGraphManagerBasic)
- Add same file twice
- Assert node count is 1 (no duplicates)
- Assert attributes are from latest add (or first, depending on implementation choice)

**`test_add_node_without_parent_file`** (in TestGraphManagerHierarchy)
- Attempt to add code node without adding file first
- Assert either: (a) raises `ValueError`, or (b) creates orphan node (document expected behavior)

**`test_load_invalid_json`** (in TestGraphManagerPersistence)
- Write invalid JSON to file
- Assert `manager.load(path)` raises appropriate error (e.g., `ValueError`, `orjson.JSONDecodeError`)

**`test_save_to_readonly_directory`** (in TestGraphManagerPersistence)
- Create readonly directory (if possible on platform)
- Assert `manager.save(readonly_path / "graph.json")` raises `PermissionError` or `OSError`

### 8. Verify Test Structure

Ensure all tests follow established patterns:
- Each test method has descriptive docstring
- Tests use AAA pattern (Arrange, Act, Assert)
- Assertions are specific and clear
- Use `tmp_path` fixture for file operations
- Import only necessary symbols
- No test implementation details leak into production code

## Expected Outcome

All tests will **FAIL** (RED phase) because:
- `GraphManager.add_file()` method not implemented
- `GraphManager.add_node()` method not implemented
- `GraphManager.add_dependency()` method not implemented
- `GraphManager.save()` method not implemented
- `GraphManager.load()` method not implemented
- `GraphManager.graph_stats` property not implemented

This is the correct TDD state—tests define the contract before implementation.

## Test Execution Command

```bash
pytest tests/unit/graph/test_manager.py -v
```

Expected output: All tests fail with `AttributeError` or `NotImplementedError`.