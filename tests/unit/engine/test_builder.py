"""Unit tests for engine.builder module.

This module contains comprehensive tests for the MapBuilder class,
covering integration, edge cases, boundary cases, and error handling.

Test Organization:
    - TestMapBuilderIntegration: End-to-end workflow validation with realistic
      file structures, import chains, and graph statistics verification.
    - TestMapBuilderBuild: Unit tests for build() method including valid paths,
      invalid inputs (nonexistent, file-as-root), error handling (parsing,
      content read), empty directories, and non-Python file filtering.
    - TestMapBuilderExternalImportsIntegration: Integration tests for external
      imports handling including stdlib imports, third-party modules, deduplication,
      and mixed internal/external import scenarios.
    - TestMapBuilderBoundaryCases: Scalability tests for large directory
      structures (50+ files), deep nesting (10 levels), circular imports,
      and files with many import statements.
    - TestResolveAndAddImport: Unit tests for import resolution logic covering
      simple modules, dotted names, relative imports, package imports,
      unresolved imports, and external modules (with virtual node creation).
    - TestMapBuilderFailureModeIntegration: Failure-mode tests for resilience
      to corrupt files, parser exceptions, permission errors, and mixed
      success/failure scenarios.

Coverage: 100% of builder.py (lines, branches, error paths)

Test Patterns:
    - AAA (Arrange-Act-Assert) structure throughout
    - tmp_path fixture for isolated filesystem operations
    - caplog fixture for log verification
    - unittest.mock.patch for simulating component failures
    - pytest.raises for exception validation

Component Interactions Tested:
    - FileWalker: File discovery with ignore patterns
    - ContentReader: Content reading with encoding fallback
    - ParserEngine: Code structure extraction via tree-sitter
    - GraphManager: Graph construction and persistence
"""

from pathlib import Path
from typing import Any

import pytest

from codemap.engine.builder import MapBuilder
from codemap.graph import GraphManager


class TestMapBuilderIntegration:
    """Integration test suite for MapBuilder workflow."""

    def test_build_creates_complete_graph(self, tmp_path: Path) -> None:
        """Test MapBuilder builds complete graph with all components.

        This integration test validates the entire MapBuilder workflow by
        creating a realistic temporary file structure with Python files that
        have import relationships. The test verifies that MapBuilder correctly
        orchestrates all components (FileWalker, ContentReader, ParserEngine,
        GraphManager) to produce a complete graph with:
        - File nodes for each discovered Python file
        - Code nodes for functions and classes
        - CONTAINS edges linking files to their code nodes
        - IMPORTS edges capturing import dependencies

        Assertions use attribute-based discovery to find nodes rather than
        hardcoded IDs, respecting the GraphManager API contract for node ID
        format: "{parent_file_id}::{node.name}".
        """
        # Arrange
        utils_content = '''def helper_function():
    return "helper"
'''
        main_content = '''from utils import helper_function

def main():
    result = helper_function()
    return result
'''
        (tmp_path / "utils.py").write_text(utils_content)
        (tmp_path / "main.py").write_text(main_content)

        builder = MapBuilder()

        # Act
        graph_manager = builder.build(tmp_path)

        # Collect nodes by type for flexible assertions
        # Note: Using Any for attrs dict since NetworkX returns complex attribute types
        file_nodes: dict[str, dict[str, Any]] = {}
        code_nodes: dict[str, dict[str, Any]] = {}

        for node_id, attrs in graph_manager.graph.nodes(data=True):
            if attrs.get("type") == "file":
                file_nodes[node_id] = attrs
            elif attrs.get("type") == "function":
                code_nodes[node_id] = attrs

        # Assert - File Nodes (at least 2)
        assert len(file_nodes) >= 2, f"Expected at least 2 file nodes, got {len(file_nodes)}"

        # Find main.py and utils.py nodes by checking path ends with filename
        main_file_id = next((nid for nid in file_nodes if nid.endswith("main.py")), None)
        utils_file_id = next((nid for nid in file_nodes if nid.endswith("utils.py")), None)

        assert main_file_id is not None, "main.py file node not found"
        assert utils_file_id is not None, "utils.py file node not found"

        # Verify file nodes have required metadata
        assert "size" in file_nodes[main_file_id]
        assert "token_est" in file_nodes[main_file_id]
        assert "size" in file_nodes[utils_file_id]
        assert "token_est" in file_nodes[utils_file_id]

        # Assert - Code Nodes (at least 2)
        assert len(code_nodes) >= 2, f"Expected at least 2 code nodes, got {len(code_nodes)}"

        # Find code nodes by name attribute
        helper_node_id = next(
            (nid for nid, attrs in code_nodes.items() if attrs.get("name") == "helper_function"),
            None,
        )
        main_fn_node_id = next(
            (nid for nid, attrs in code_nodes.items() if attrs.get("name") == "main"),
            None,
        )

        assert helper_node_id is not None, "helper_function code node not found"
        assert main_fn_node_id is not None, "main function code node not found"

        # Verify code nodes follow ID format "{parent_file_id}::{node.name}"
        assert "::" in helper_node_id, f"Code node ID should contain '::': {helper_node_id}"
        assert "::" in main_fn_node_id, f"Code node ID should contain '::': {main_fn_node_id}"

        # Verify code node attributes
        helper_attrs = code_nodes[helper_node_id]
        assert helper_attrs["start_line"] > 0
        assert helper_attrs["end_line"] > 0

        main_fn_attrs = code_nodes[main_fn_node_id]
        assert main_fn_attrs["start_line"] > 0
        assert main_fn_attrs["end_line"] > 0

        # Assert - CONTAINS Edges (verify relationship exists)
        assert graph_manager.graph.has_edge(utils_file_id, helper_node_id)
        assert graph_manager.graph.has_edge(main_file_id, main_fn_node_id)

        contains_edge_utils = graph_manager.graph.edges[utils_file_id, helper_node_id]
        assert contains_edge_utils["relationship"] == "CONTAINS"

        contains_edge_main = graph_manager.graph.edges[main_file_id, main_fn_node_id]
        assert contains_edge_main["relationship"] == "CONTAINS"

        # Assert - IMPORTS Edge (at least 1 from main to utils)
        assert graph_manager.graph.has_edge(main_file_id, utils_file_id), (
            f"Expected IMPORTS edge from {main_file_id} to {utils_file_id}"
        )
        imports_edge = graph_manager.graph.edges[main_file_id, utils_file_id]
        assert imports_edge["relationship"] == "IMPORTS"

        # Assert - Graph Statistics (minimum counts, not exact)
        stats = graph_manager.graph_stats
        assert stats["nodes"] >= 4, f"Expected at least 4 nodes, got {stats['nodes']}"
        assert stats["edges"] >= 3, f"Expected at least 3 edges, got {stats['edges']}"

    def test_integration_graph_statistics(self, tmp_path: Path) -> None:
        """Test MapBuilder produces correct graph statistics.

        This integration test validates that MapBuilder correctly produces
        comprehensive graph statistics including accurate node counts, edge counts,
        and relationship breakdowns. Uses a realistic project structure with
        multiple files, functions, classes, and import dependencies.

        The test verifies:
        - Total node count includes file nodes and code nodes
        - Total edge count includes CONTAINS and IMPORTS edges
        - Graph statistics are consistent with actual graph structure
        - Statistics reflect the complete orchestration workflow
        """
        # Arrange - Create a more complex project structure
        # Use 'mypackage' instead of 'pkg' (FileWalker ignores pkg for Go patterns)
        (tmp_path / "mypackage").mkdir()

        # main.py imports from utils and mypackage
        main_content = '''from utils import helper
from mypackage import func

def main():
    result = helper()
    data = func()
    return result + data
'''

        # utils.py with helper function
        utils_content = '''def helper():
    return "helper"

class UtilityClass:
    def method(self):
        pass
'''

        # mypackage/__init__.py imports from .module
        init_content = '''from .module import func
'''

        # mypackage/module.py with func
        module_content = '''def func():
    return "func"

class ModuleClass:
    pass
'''

        (tmp_path / "main.py").write_text(main_content)
        (tmp_path / "utils.py").write_text(utils_content)
        (tmp_path / "mypackage" / "__init__.py").write_text(init_content)
        (tmp_path / "mypackage" / "module.py").write_text(module_content)

        builder = MapBuilder()

        # Act
        graph_manager = builder.build(tmp_path)
        stats = graph_manager.graph_stats

        # Assert - Node counts (4 files + at least 5 code nodes)
        # Files: main.py, utils.py, mypackage/__init__.py, mypackage/module.py
        # Code nodes: main, helper, UtilityClass, func, ModuleClass (at least 5)
        assert stats["nodes"] >= 9, (
            f"Expected at least 9 nodes (4 files + 5 code nodes), got {stats['nodes']}"
        )

        # Assert - Edge counts (at least 4 CONTAINS + 2 IMPORTS edges)
        # CONTAINS: main.py->main, utils.py->helper, utils.py->UtilityClass,
        #           module.py->func, module.py->ModuleClass (5 minimum)
        # IMPORTS: main.py->utils.py, main.py->mypackage/__init__.py (2 minimum)
        assert stats["edges"] >= 6, (
            f"Expected at least 6 edges (4 CONTAINS + 2 IMPORTS), got {stats['edges']}"
        )

        # Assert - Verify specific counts by counting directly
        file_nodes = [
            node_id for node_id, attrs in graph_manager.graph.nodes(data=True)
            if attrs.get("type") == "file"
        ]
        code_nodes = [
            node_id for node_id, attrs in graph_manager.graph.nodes(data=True)
            if attrs.get("type") in ["function", "class"]
        ]
        contains_edges = [
            (src, tgt) for src, tgt, attrs in graph_manager.graph.edges(data=True)
            if attrs.get("relationship") == "CONTAINS"
        ]
        imports_edges = [
            (src, tgt) for src, tgt, attrs in graph_manager.graph.edges(data=True)
            if attrs.get("relationship") == "IMPORTS"
        ]

        assert len(file_nodes) == 4, f"Expected exactly 4 file nodes, got {len(file_nodes)}"
        assert len(code_nodes) >= 5, f"Expected at least 5 code nodes, got {len(code_nodes)}"
        assert len(contains_edges) >= 5, (
            f"Expected at least 5 CONTAINS edges, got {len(contains_edges)}"
        )
        assert len(imports_edges) >= 2, (
            f"Expected at least 2 IMPORTS edges, got {len(imports_edges)}"
        )

    def test_integration_import_chain(self, tmp_path: Path) -> None:
        """Test MapBuilder captures transitive import dependencies across multiple files.

        This integration test validates that MapBuilder correctly traces import
        chains across multiple files in a project. It creates a chain of dependencies:
        main.py -> utils.py -> helper.py

        The test verifies:
        - Direct import edges are captured (main->utils, utils->helper)
        - All files in the chain are included in the graph
        - Import resolution works across nested directory structures
        - Transitive dependencies can be queried from the graph
        """
        # Arrange - Create import chain: main -> utils -> helper
        # Use 'mypackage' instead of 'pkg' (FileWalker ignores pkg for Go patterns)
        (tmp_path / "mypackage").mkdir()

        # helper.py at bottom of chain
        helper_content = '''def base_helper():
    return "base"
'''

        # utils.py imports from helper
        utils_content = '''from mypackage.helper import base_helper

def helper():
    return base_helper() + " wrapper"
'''

        # main.py imports from utils (creates chain)
        main_content = '''from utils import helper

def main():
    return helper()
'''

        (tmp_path / "mypackage" / "helper.py").write_text(helper_content)
        (tmp_path / "utils.py").write_text(utils_content)
        (tmp_path / "main.py").write_text(main_content)

        builder = MapBuilder()

        # Act
        graph_manager = builder.build(tmp_path)

        # Assert - All files in chain are present
        file_nodes = {
            node_id: attrs for node_id, attrs in graph_manager.graph.nodes(data=True)
            if attrs.get("type") == "file"
        }

        main_file_id = next((nid for nid in file_nodes if nid.endswith("main.py")), None)
        utils_file_id = next((nid for nid in file_nodes if nid.endswith("utils.py")), None)
        helper_file_id = next(
            (nid for nid in file_nodes if nid.endswith("helper.py")), None
        )

        assert main_file_id is not None, "main.py file node not found in graph"
        assert utils_file_id is not None, "utils.py file node not found in graph"
        assert helper_file_id is not None, "helper.py file node not found in graph"

        # Assert - Direct import edges exist
        # main.py -> utils.py
        assert graph_manager.graph.has_edge(main_file_id, utils_file_id), (
            f"Expected IMPORTS edge from {main_file_id} to {utils_file_id}"
        )
        main_utils_edge = graph_manager.graph.edges[main_file_id, utils_file_id]
        assert main_utils_edge["relationship"] == "IMPORTS"

        # utils.py -> mypackage/helper.py
        assert graph_manager.graph.has_edge(utils_file_id, helper_file_id), (
            f"Expected IMPORTS edge from {utils_file_id} to {helper_file_id}"
        )
        utils_helper_edge = graph_manager.graph.edges[utils_file_id, helper_file_id]
        assert utils_helper_edge["relationship"] == "IMPORTS"

        # Assert - Transitive dependency can be queried via graph traversal
        # Using NetworkX's descendants or shortest path to verify chain
        import networkx as nx

        # Check if there's a path from main to helper (transitive dependency)
        has_path = nx.has_path(graph_manager.graph, main_file_id, helper_file_id)
        assert has_path, (
            f"Expected transitive dependency path from {main_file_id} to {helper_file_id}"
        )

        # Verify the path is exactly 2 hops (main->utils->helper)
        path = nx.shortest_path(graph_manager.graph, main_file_id, helper_file_id)
        assert len(path) == 3, (
            f"Expected path length 3 (main->utils->helper), got {len(path)}: {path}"
        )
        assert path == [main_file_id, utils_file_id, helper_file_id], (
            f"Expected path [main, utils, helper], got {path}"
        )


class TestMapBuilderBuild:
    """Unit test suite for MapBuilder.build() method."""

    def test_build_with_valid_path(self, tmp_path: Path) -> None:
        """Test build() with valid directory path returns GraphManager with correct nodes.

        Validates that MapBuilder correctly processes a valid directory structure:
        - Creates file nodes for discovered Python files
        - Extracts code nodes (functions, classes) from parsed content
        - Adds CONTAINS edges linking files to their code nodes
        - Resolves and adds IMPORTS edges for module dependencies
        """
        # Arrange
        utils_content = '''def helper():
    return "help"
'''
        main_content = '''from utils import helper

def main():
    return helper()
'''
        (tmp_path / "utils.py").write_text(utils_content)
        (tmp_path / "main.py").write_text(main_content)

        builder = MapBuilder()

        # Act
        result = builder.build(tmp_path)

        # Assert - Returns GraphManager instance
        assert isinstance(result, GraphManager)

        # Assert - Contains file nodes
        file_nodes = [
            node_id for node_id, attrs in result.graph.nodes(data=True)
            if attrs.get("type") == "file"
        ]
        assert len(file_nodes) >= 2, f"Expected at least 2 file nodes, got {len(file_nodes)}"

        # Assert - Contains code nodes (functions)
        code_nodes = [
            node_id for node_id, attrs in result.graph.nodes(data=True)
            if attrs.get("type") == "function"
        ]
        assert len(code_nodes) >= 2, f"Expected at least 2 code nodes, got {len(code_nodes)}"

        # Assert - Contains IMPORTS edges
        import_edges = [
            (src, tgt) for src, tgt, attrs in result.graph.edges(data=True)
            if attrs.get("relationship") == "IMPORTS"
        ]
        assert len(import_edges) >= 1, f"Expected at least 1 IMPORTS edge, got {len(import_edges)}"

    def test_build_with_nonexistent_path(self) -> None:
        """Test build() raises ValueError when path does not exist.

        Validates that MapBuilder properly validates input and raises
        ValueError with a clear error message when the provided path
        does not exist in the filesystem.
        """
        # Arrange
        nonexistent_path = Path("/nonexistent/path/that/does/not/exist")
        builder = MapBuilder()

        # Act & Assert
        with pytest.raises(ValueError, match="Path does not exist"):
            builder.build(nonexistent_path)

    def test_build_with_file_instead_of_directory(self, tmp_path: Path) -> None:
        """Test build() raises ValueError when path is a file, not a directory.

        Validates that MapBuilder enforces directory-only input and raises
        ValueError with a clear error message when a file path is provided
        instead of a directory path.
        """
        # Arrange
        file_path = tmp_path / "test_file.py"
        file_path.write_text("# test content")
        builder = MapBuilder()

        # Act & Assert
        with pytest.raises(ValueError, match="Path is not a directory"):
            builder.build(file_path)

    def test_build_catches_parsing_errors(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test build() logs warning and continues when ParserEngine throws exception.

        Validates that MapBuilder implements robust error handling:
        - Catches parsing exceptions from ParserEngine
        - Logs warning message with file name and error details
        - Continues processing remaining files (does not abort)
        - Returns GraphManager with successfully processed files

        Note: This test mocks ParserEngine to throw exceptions since tree-sitter
        is resilient to syntax errors and doesn't throw exceptions naturally.
        """
        # Arrange
        from unittest.mock import patch

        # Create two valid files
        valid1_content = '''def valid_function():
    return "valid1"
'''
        valid2_content = '''def another_function():
    return "valid2"
'''
        (tmp_path / "valid1.py").write_text(valid1_content)
        (tmp_path / "problematic.py").write_text(valid2_content)

        builder = MapBuilder()

        # Mock ParserEngine to throw exception for problematic.py
        original_parse = builder._parser.parse_file

        def mock_parse(path: Path, content: str) -> list[object]:
            if "problematic" in str(path):
                raise ValueError("Simulated parser error for testing")
            return list(original_parse(path, content))

        # Act
        import logging
        with patch.object(builder._parser, "parse_file", side_effect=mock_parse):
            with caplog.at_level(logging.WARNING):
                result = builder.build(tmp_path)

        # Assert - Warning was logged for problematic.py
        assert len(caplog.records) > 0, "Expected warning to be logged for parsing error"
        warning_messages = [
            record.message for record in caplog.records
            if record.levelname == "WARNING"
        ]
        assert any("problematic.py" in msg for msg in warning_messages), \
            "Expected warning message to mention problematic.py"

        # Assert - GraphManager is still returned (partial success)
        assert isinstance(result, GraphManager)

        # Assert - Valid file was processed (despite problematic file failing)
        file_nodes = [
            node_id for node_id, attrs in result.graph.nodes(data=True)
            if attrs.get("type") == "file"
        ]
        assert len(file_nodes) >= 1, "Expected at least valid1.py to be processed"

    def test_build_catches_content_read_errors(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test build() logs warning and continues when ContentReader throws ContentReadError.

        Validates that MapBuilder handles file reading errors gracefully:
        - Catches ContentReadError from ContentReader
        - Logs warning message with file name and error details
        - Continues processing remaining files
        - Returns GraphManager with successfully processed files
        """
        # Arrange

        # Create valid file
        valid_content = '''def valid_function():
    return "valid"
'''
        (tmp_path / "valid.py").write_text(valid_content)

        # Create binary file with .py extension (will cause read error)
        binary_file = tmp_path / "binary.py"
        binary_file.write_bytes(b'\x00\x01\x02\x03\x04\x05')

        builder = MapBuilder()

        # Act
        import logging
        with caplog.at_level(logging.WARNING):
            result = builder.build(tmp_path)

        # Assert - Warning was logged for binary file
        assert len(caplog.records) > 0, "Expected warning to be logged for content read error"
        warning_messages = [
            record.message for record in caplog.records
            if record.levelname == "WARNING"
        ]
        assert any("binary.py" in msg for msg in warning_messages), \
            "Expected warning message to mention binary.py"

        # Assert - GraphManager is still returned
        assert isinstance(result, GraphManager)

        # Assert - Valid file was processed
        file_nodes = [
            node_id for node_id, attrs in result.graph.nodes(data=True)
            if attrs.get("type") == "file"
        ]
        assert len(file_nodes) >= 1, "Expected at least valid.py to be processed"

    def test_build_empty_directory(self, tmp_path: Path) -> None:
        """Test build() with empty directory returns GraphManager with empty graph.

        Validates that MapBuilder handles edge case of empty directory:
        - Does not raise exceptions
        - Returns GraphManager instance
        - Graph contains zero nodes (no files discovered)
        - Graph contains zero edges (no relationships)
        """
        # Arrange
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        builder = MapBuilder()

        # Act
        result = builder.build(empty_dir)

        # Assert - Returns GraphManager instance
        assert isinstance(result, GraphManager)

        # Assert - Graph is empty
        stats = result.graph_stats
        assert stats["nodes"] == 0, f"Expected 0 nodes in empty directory, got {stats['nodes']}"
        assert stats["edges"] == 0, f"Expected 0 edges in empty directory, got {stats['edges']}"

    def test_build_skips_non_python_files(self, tmp_path: Path) -> None:
        """Test build() skips non-Python files (.txt, .md, etc).

        Validates that MapBuilder correctly skips non-Python files:
        - File nodes are created for all discovered files (including non-Python)
        - Code nodes are only extracted from Python files
        - Non-Python files do not cause errors or warnings
        """
        # Arrange
        py_content = '''def python_function():
    return "python"
'''
        txt_content = "This is a text file"
        md_content = "# Markdown File\nThis is markdown content"

        (tmp_path / "script.py").write_text(py_content)
        (tmp_path / "readme.txt").write_text(txt_content)
        (tmp_path / "docs.md").write_text(md_content)

        builder = MapBuilder()

        # Act
        result = builder.build(tmp_path)

        # Assert - All files are discovered and have file nodes
        file_nodes = [
            node_id for node_id, attrs in result.graph.nodes(data=True)
            if attrs.get("type") == "file"
        ]
        assert len(file_nodes) == 3, f"Expected 3 file nodes (all files), got {len(file_nodes)}"

        # Assert - Only Python file has code nodes
        code_nodes = [
            node_id for node_id, attrs in result.graph.nodes(data=True)
            if attrs.get("type") == "function"
        ]
        assert len(code_nodes) == 1, (
            f"Expected 1 code node (only from .py file), got {len(code_nodes)}"
        )

        # Verify the code node is from the Python file
        python_code_node = next(
            (nid for nid, attrs in result.graph.nodes(data=True)
             if attrs.get("name") == "python_function"),
            None
        )
        assert python_code_node is not None, "Expected python_function code node"
        assert "script.py" in python_code_node, "Expected code node to be from script.py"


class TestMapBuilderExternalImportsIntegration:
    """Integration tests for external imports handling in MapBuilder.

    Tests verify end-to-end behavior when building projects with external imports.
    """

    def test_build_creates_external_nodes_for_stdlib_imports(self, tmp_path: Path) -> None:
        """Test MapBuilder.build() creates external nodes for stdlib imports in the graph.

        Integration test validating that the complete build workflow:
        - Discovers external imports (os, sys, pathlib, etc.) during parsing
        - Creates virtual external nodes for each unique external module
        - Adds IMPORTS edges from files to external nodes
        - No warnings or errors are logged for external imports
        """
        # Arrange
        main_content = '''import os
import sys
from pathlib import Path

def main():
    print(os.getcwd())
    return sys.version
'''
        utils_content = '''import os
from typing import List

def helper() -> List[str]:
    return os.listdir('.')
'''
        (tmp_path / "main.py").write_text(main_content)
        (tmp_path / "utils.py").write_text(utils_content)

        builder = MapBuilder()

        # Act
        graph_manager = builder.build(tmp_path)

        # Assert - External nodes were created
        external_nodes = {
            node_id: attrs for node_id, attrs in graph_manager.graph.nodes(data=True)
            if attrs.get("type") == "external_module"
        }

        # Expected external modules (os is deduplicated)
        expected_modules = ["os", "sys", "pathlib", "typing"]
        for module_name in expected_modules:
            expected_node_id = f"external::{module_name}"
            assert expected_node_id in external_nodes, \
                f"Expected external node '{expected_node_id}' to be created"

            attrs = external_nodes[expected_node_id]
            assert attrs["name"] == module_name, \
                f"Expected name='{module_name}', got '{attrs['name']}'"

        # Assert - IMPORTS edges exist
        # main.py should import: os, sys, pathlib
        assert graph_manager.graph.has_edge("main.py", "external::os")
        assert graph_manager.graph.has_edge("main.py", "external::sys")
        assert graph_manager.graph.has_edge("main.py", "external::pathlib")

        # utils.py should import: os, typing
        assert graph_manager.graph.has_edge("utils.py", "external::os")
        assert graph_manager.graph.has_edge("utils.py", "external::typing")

        # Assert - Only ONE external::os node (deduplication)
        os_nodes = [nid for nid in external_nodes if nid == "external::os"]
        assert len(os_nodes) == 1, "Expected exactly 1 external::os node (deduplication)"

    def test_build_handles_mixed_internal_and_external_imports(self, tmp_path: Path) -> None:
        """Test MapBuilder.build() correctly handles mix of internal and external imports.

        Integration test validating that when a file has both internal (project)
        and external (stdlib/third-party) imports, both are resolved correctly:
        - Internal imports create IMPORTS edges to project files
        - External imports create IMPORTS edges to virtual external nodes
        - Graph statistics reflect both types of imports
        """
        # Arrange
        utils_content = '''def helper():
    return "help"
'''
        main_content = '''import os
from utils import helper

def main():
    result = helper()
    return os.path.join(result, "path")
'''
        (tmp_path / "utils.py").write_text(utils_content)
        (tmp_path / "main.py").write_text(main_content)

        builder = MapBuilder()

        # Act
        graph_manager = builder.build(tmp_path)

        # Assert - File nodes exist
        file_nodes = [
            node_id for node_id, attrs in graph_manager.graph.nodes(data=True)
            if attrs.get("type") == "file"
        ]
        assert "main.py" in file_nodes
        assert "utils.py" in file_nodes

        # Assert - External node exists
        external_nodes = [
            node_id for node_id, attrs in graph_manager.graph.nodes(data=True)
            if attrs.get("type") == "external_module"
        ]
        assert "external::os" in external_nodes

        # Assert - Both IMPORTS edges exist from main.py
        # To internal file
        assert graph_manager.graph.has_edge("main.py", "utils.py"), \
            "Expected IMPORTS edge from main.py to utils.py (internal)"
        # To external module
        assert graph_manager.graph.has_edge("main.py", "external::os"), \
            "Expected IMPORTS edge from main.py to external::os (external)"

        # Verify edge types
        internal_edge = graph_manager.graph.edges["main.py", "utils.py"]
        assert internal_edge["relationship"] == "IMPORTS"

        external_edge = graph_manager.graph.edges["main.py", "external::os"]
        assert external_edge["relationship"] == "IMPORTS"

        # Assert - Graph statistics include external nodes
        stats = graph_manager.graph_stats
        # At least: 2 file nodes + 1 external node + 2 code nodes = 5 nodes
        assert stats["nodes"] >= 5, f"Expected at least 5 nodes, got {stats['nodes']}"
        # At least: 2 CONTAINS edges + 2 IMPORTS edges = 4 edges
        assert stats["edges"] >= 4, f"Expected at least 4 edges, got {stats['edges']}"


class TestMapBuilderBoundaryCases:
    """Boundary case tests for MapBuilder scalability and complex scenarios.

    Tests verify that MapBuilder handles:
    - Large directory structures with many files
    - Deeply nested directory hierarchies
    - Circular import dependencies between modules
    """

    def test_build_handles_large_directory_structure(self, tmp_path: Path) -> None:
        """Test MapBuilder handles large directory structures with many files.

        Creates 50+ Python files across multiple nested directories and verifies:
        - All files are discovered and added as file nodes
        - All code nodes (functions/classes) are extracted
        - Build completes without errors or excessive runtime
        - Graph statistics reflect the expected structure
        """
        # Arrange - Create 60 Python files across 6 directories (10 files each)
        num_dirs = 6
        files_per_dir = 10
        total_files = num_dirs * files_per_dir

        for dir_idx in range(num_dirs):
            # Create nested directory structure: level1/level2/...
            if dir_idx == 0:
                current_dir = tmp_path
            else:
                current_dir = tmp_path / f"pkg_{dir_idx}"
                current_dir.mkdir(parents=True, exist_ok=True)
                # Add __init__.py for packages
                (current_dir / "__init__.py").write_text("")

            for file_idx in range(files_per_dir):
                file_content = f'''def func_{dir_idx}_{file_idx}():
    """Function {file_idx} in directory {dir_idx}."""
    return {dir_idx * 100 + file_idx}

class Class_{dir_idx}_{file_idx}:
    """Class {file_idx} in directory {dir_idx}."""
    pass
'''
                (current_dir / f"module_{file_idx}.py").write_text(file_content)

        builder = MapBuilder()

        # Act
        graph_manager = builder.build(tmp_path)

        # Assert - All files discovered
        file_nodes = [
            node_id for node_id, attrs in graph_manager.graph.nodes(data=True)
            if attrs.get("type") == "file"
        ]
        # 60 module files + 5 __init__.py files = 65 total
        assert len(file_nodes) >= total_files, (
            f"Expected at least {total_files} file nodes, got {len(file_nodes)}"
        )

        # Assert - Code nodes extracted (2 per file: 1 function + 1 class)
        code_nodes = [
            node_id for node_id, attrs in graph_manager.graph.nodes(data=True)
            if attrs.get("type") in ["function", "class"]
        ]
        expected_code_nodes = total_files * 2  # Each file has 1 function + 1 class
        assert len(code_nodes) >= expected_code_nodes, (
            f"Expected at least {expected_code_nodes} code nodes, got {len(code_nodes)}"
        )

        # Assert - Graph statistics are reasonable
        stats = graph_manager.graph_stats
        assert stats["nodes"] >= total_files + expected_code_nodes, (
            f"Expected at least {total_files + expected_code_nodes} total nodes"
        )
        assert stats["edges"] >= expected_code_nodes, (
            f"Expected at least {expected_code_nodes} CONTAINS edges"
        )

    def test_build_handles_deep_nesting(self, tmp_path: Path) -> None:
        """Test MapBuilder handles deeply nested directory structures.

        Creates a 10-level deep directory hierarchy with Python files at each
        level and verifies all files are discovered and processed correctly.
        """
        # Arrange - Create 10-level deep nested structure
        nesting_depth = 10
        current_dir = tmp_path

        for level in range(nesting_depth):
            # Create __init__.py at each level
            (current_dir / "__init__.py").write_text(f"# Level {level}")

            # Create a module at each level
            module_content = f'''def level_{level}_func():
    """Function at nesting level {level}."""
    return {level}
'''
            (current_dir / f"module_level_{level}.py").write_text(module_content)

            # Go deeper
            current_dir = current_dir / f"subpkg_{level}"
            current_dir.mkdir(exist_ok=True)

        # Create final file at deepest level
        (current_dir / "__init__.py").write_text("# Deepest level")
        (current_dir / "deepest.py").write_text("def deepest(): return 'bottom'")

        builder = MapBuilder()

        # Act
        graph_manager = builder.build(tmp_path)

        # Assert - All levels discovered
        file_nodes = [
            node_id for node_id, attrs in graph_manager.graph.nodes(data=True)
            if attrs.get("type") == "file"
        ]
        # 10 __init__.py + 10 module files + 1 final __init__.py + 1 deepest.py = 22
        assert len(file_nodes) >= 20, (
            f"Expected at least 20 file nodes for deep nesting, got {len(file_nodes)}"
        )

        # Assert - Deepest file was found
        deepest_found = any("deepest.py" in node_id for node_id in file_nodes)
        assert deepest_found, "Expected deepest.py to be discovered"

        # Assert - Code nodes from all levels
        code_nodes = [
            node_id for node_id, attrs in graph_manager.graph.nodes(data=True)
            if attrs.get("type") == "function"
        ]
        # At least 10 level functions + 1 deepest function
        assert len(code_nodes) >= 11, (
            f"Expected at least 11 function nodes, got {len(code_nodes)}"
        )

    def test_build_handles_circular_imports(self, tmp_path: Path) -> None:
        """Test MapBuilder handles circular imports without recursion errors.

        Creates two files that import each other (a.py imports b, b.py imports a)
        and verifies:
        - Build completes without infinite loops or recursion errors
        - Both IMPORTS edges are present in the graph
        - Both files have their code nodes extracted
        """
        # Arrange - Create circular import scenario
        a_content = '''from b import func_b

def func_a():
    """Function in module a."""
    return func_b() + "_from_a"
'''
        b_content = '''from a import func_a

def func_b():
    """Function in module b."""
    return "b"
'''
        (tmp_path / "a.py").write_text(a_content)
        (tmp_path / "b.py").write_text(b_content)

        builder = MapBuilder()

        # Act - Should complete without recursion error or infinite loop
        graph_manager = builder.build(tmp_path)

        # Assert - Both files discovered
        file_nodes = {
            node_id: attrs for node_id, attrs in graph_manager.graph.nodes(data=True)
            if attrs.get("type") == "file"
        }
        a_file_id = next((nid for nid in file_nodes if nid.endswith("a.py")), None)
        b_file_id = next((nid for nid in file_nodes if nid.endswith("b.py")), None)

        assert a_file_id is not None, "Expected a.py file node"
        assert b_file_id is not None, "Expected b.py file node"

        # Assert - Both IMPORTS edges exist (circular dependency)
        assert graph_manager.graph.has_edge(a_file_id, b_file_id), (
            f"Expected IMPORTS edge from {a_file_id} to {b_file_id}"
        )
        assert graph_manager.graph.has_edge(b_file_id, a_file_id), (
            f"Expected IMPORTS edge from {b_file_id} to {a_file_id}"
        )

        # Verify edge types
        edge_a_to_b = graph_manager.graph.edges[a_file_id, b_file_id]
        assert edge_a_to_b["relationship"] == "IMPORTS"

        edge_b_to_a = graph_manager.graph.edges[b_file_id, a_file_id]
        assert edge_b_to_a["relationship"] == "IMPORTS"

        # Assert - Both functions extracted
        code_nodes = [
            attrs.get("name") for _, attrs in graph_manager.graph.nodes(data=True)
            if attrs.get("type") == "function"
        ]
        assert "func_a" in code_nodes, "Expected func_a in graph"
        assert "func_b" in code_nodes, "Expected func_b in graph"

    def test_build_handles_many_imports(self, tmp_path: Path) -> None:
        """Test MapBuilder handles files with many import statements.

        Creates a file with 20+ imports to other modules in the project
        and verifies all import dependencies are captured.
        """
        # Arrange - Create 20 utility modules
        num_utils = 20
        for i in range(num_utils):
            util_content = f'''def util_func_{i}():
    """Utility function {i}."""
    return {i}
'''
            (tmp_path / f"util_{i}.py").write_text(util_content)

        # Create main file that imports all utilities
        import_lines = [f"from util_{i} import util_func_{i}" for i in range(num_utils)]
        main_content = "\n".join(import_lines) + f'''

def main():
    """Main function using all utilities."""
    return {num_utils}
'''
        (tmp_path / "main.py").write_text(main_content)

        builder = MapBuilder()

        # Act
        graph_manager = builder.build(tmp_path)

        # Assert - Main file has IMPORTS edges to all utilities
        file_nodes = {
            node_id for node_id, attrs in graph_manager.graph.nodes(data=True)
            if attrs.get("type") == "file"
        }
        main_file_id = next((nid for nid in file_nodes if nid.endswith("main.py")), None)
        assert main_file_id is not None, "Expected main.py file node"

        # Count IMPORTS edges from main.py
        imports_edges = [
            (src, tgt) for src, tgt, attrs in graph_manager.graph.edges(data=True)
            if src == main_file_id and attrs.get("relationship") == "IMPORTS"
        ]
        assert len(imports_edges) >= num_utils, (
            f"Expected at least {num_utils} IMPORTS edges from main.py, "
            f"got {len(imports_edges)}"
        )


class TestResolveAndAddImport:
    """Unit test suite for MapBuilder._resolve_and_add_import() method."""

    def test_resolve_simple_module_name(self, tmp_path: Path) -> None:
        """Test _resolve_and_add_import() with simple module name in same directory.

        Validates that MapBuilder correctly resolves a simple import (e.g., "utils")
        by checking for a file in the same directory as the source file
        (e.g., "utils.py") and adds a dependency edge if found.
        """
        # Arrange
        utils_content = '''def helper():
    return "help"
'''
        main_content = '''from utils import helper

def main():
    return helper()
'''
        (tmp_path / "utils.py").write_text(utils_content)
        (tmp_path / "main.py").write_text(main_content)

        builder = MapBuilder()
        graph_manager = builder.build(tmp_path)

        # Get the graph manager used by builder
        builder._graph = graph_manager

        # Get file IDs (relative paths as used in graph)
        main_file_id = "main.py"
        utils_file_id = "utils.py"

        # Reset edges to test method in isolation
        if graph_manager.graph.has_edge(main_file_id, utils_file_id):
            graph_manager.graph.remove_edge(main_file_id, utils_file_id)

        # Act - Pass relative path as source_file (Path object)
        builder._resolve_and_add_import(tmp_path, Path("main.py"), "utils")

        # Assert - Dependency edge was added
        assert graph_manager.graph.has_edge(main_file_id, utils_file_id), \
            f"Expected IMPORTS edge from {main_file_id} to {utils_file_id}"
        edge_attrs = graph_manager.graph.edges[main_file_id, utils_file_id]
        assert edge_attrs["relationship"] == "IMPORTS"

    def test_resolve_dotted_module_name(self, tmp_path: Path) -> None:
        """Test _resolve_and_add_import() with dotted module name.

        Validates that MapBuilder correctly resolves dotted import names
        (e.g., "codemap.scout.walker") by converting to path format
        (e.g., "codemap/scout/walker.py") and adds dependency if file exists.
        """
        # Arrange
        # Create directory structure: codemap/scout/walker.py
        (tmp_path / "codemap").mkdir()
        (tmp_path / "codemap" / "scout").mkdir()
        walker_content = '''class FileWalker:
    pass
'''
        (tmp_path / "codemap" / "scout" / "walker.py").write_text(walker_content)

        main_content = '''from codemap.scout.walker import FileWalker

def main():
    pass
'''
        (tmp_path / "main.py").write_text(main_content)

        builder = MapBuilder()
        graph_manager = builder.build(tmp_path)

        # Get the graph manager used by builder
        builder._graph = graph_manager

        # Get file IDs (relative paths as used in graph)
        main_file_id = "main.py"
        walker_file_id = "codemap/scout/walker.py"

        # Reset edges to test method in isolation
        if graph_manager.graph.has_edge(main_file_id, walker_file_id):
            graph_manager.graph.remove_edge(main_file_id, walker_file_id)

        # Act - Pass relative path as source_file (Path object)
        builder._resolve_and_add_import(tmp_path, Path("main.py"), "codemap.scout.walker")

        # Assert - Dependency edge was added
        assert graph_manager.graph.has_edge(main_file_id, walker_file_id), \
            f"Expected IMPORTS edge from {main_file_id} to {walker_file_id}"
        edge_attrs = graph_manager.graph.edges[main_file_id, walker_file_id]
        assert edge_attrs["relationship"] == "IMPORTS"

    def test_resolve_relative_import_same_dir(self, tmp_path: Path) -> None:
        """Test _resolve_and_add_import() with relative import from same folder.

        Validates that MapBuilder correctly resolves imports relative to the
        source file's directory by checking source_file.parent for the module.
        """
        # Arrange
        # Create package structure (use 'mypackage' instead of 'pkg' which is ignored for Go)
        (tmp_path / "mypackage").mkdir()
        module1_content = '''def func1():
    pass
'''
        module2_content = '''from module1 import func1

def func2():
    func1()
'''
        (tmp_path / "mypackage" / "module1.py").write_text(module1_content)
        (tmp_path / "mypackage" / "module2.py").write_text(module2_content)

        builder = MapBuilder()
        graph_manager = builder.build(tmp_path)

        # Get the graph manager used by builder
        builder._graph = graph_manager

        # Get file IDs (relative paths as used in graph)
        module2_file_id = "mypackage/module2.py"
        module1_file_id = "mypackage/module1.py"

        # Reset edges to test method in isolation
        if graph_manager.graph.has_edge(module2_file_id, module1_file_id):
            graph_manager.graph.remove_edge(module2_file_id, module1_file_id)

        # Act - Pass relative path as source_file (Path object)
        builder._resolve_and_add_import(tmp_path, Path("mypackage/module2.py"), "module1")

        # Assert - Dependency edge was added
        assert graph_manager.graph.has_edge(module2_file_id, module1_file_id), \
            f"Expected IMPORTS edge from {module2_file_id} to {module1_file_id}"
        edge_attrs = graph_manager.graph.edges[module2_file_id, module1_file_id]
        assert edge_attrs["relationship"] == "IMPORTS"

    def test_resolve_package_import(self, tmp_path: Path) -> None:
        """Test _resolve_and_add_import() with package import (__init__.py).

        Validates that MapBuilder correctly resolves package imports by
        checking for __init__.py files in the package directory.
        """
        # Arrange
        # Create package structure (use 'mypackage' instead of 'pkg' which is ignored for Go)
        (tmp_path / "mypackage").mkdir()
        init_content = '''def package_func():
    pass
'''
        (tmp_path / "mypackage" / "__init__.py").write_text(init_content)

        main_content = '''from mypackage import package_func

def main():
    package_func()
'''
        (tmp_path / "main.py").write_text(main_content)

        builder = MapBuilder()
        graph_manager = builder.build(tmp_path)

        # Get the graph manager used by builder
        builder._graph = graph_manager

        # Get file IDs (relative paths as used in graph)
        main_file_id = "main.py"
        pkg_init_file_id = "mypackage/__init__.py"

        # Reset edges to test method in isolation
        if graph_manager.graph.has_edge(main_file_id, pkg_init_file_id):
            graph_manager.graph.remove_edge(main_file_id, pkg_init_file_id)

        # Act - Pass relative path as source_file (Path object)
        builder._resolve_and_add_import(tmp_path, Path("main.py"), "mypackage")

        # Assert - Dependency edge was added to __init__.py
        assert graph_manager.graph.has_edge(main_file_id, pkg_init_file_id), \
            f"Expected IMPORTS edge from {main_file_id} to {pkg_init_file_id}"
        edge_attrs = graph_manager.graph.edges[main_file_id, pkg_init_file_id]
        assert edge_attrs["relationship"] == "IMPORTS"

    def test_resolve_unresolved_import_silent(self, tmp_path: Path) -> None:
        """Test _resolve_and_add_import() with import to non-existent file.

        Validates that MapBuilder silently skips imports that cannot be resolved
        to files in the project (e.g., typos, not-yet-created modules):
        - No exception is raised
        - No dependency edge is added
        - Logs no error/warning (silent skip)
        """
        # Arrange
        main_content = '''from nonexistent import something

def main():
    pass
'''
        (tmp_path / "main.py").write_text(main_content)

        builder = MapBuilder()
        graph_manager = builder.build(tmp_path)

        # Get the graph manager used by builder
        builder._graph = graph_manager

        # Get file ID (relative path as used in graph)
        main_file_id = "main.py"

        # Count edges before
        edges_before = list(graph_manager.graph.edges(main_file_id))

        # Act - Should not raise exception - Pass relative path as source_file
        builder._resolve_and_add_import(tmp_path, Path("main.py"), "nonexistent")

        # Assert - No new edges added
        edges_after = list(graph_manager.graph.edges(main_file_id))
        assert len(edges_after) == len(edges_before), \
            "Expected no new edges for unresolved import"

    def test_resolve_external_import_creates_virtual_node(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test _resolve_and_add_import() creates virtual external nodes for stdlib/third-party imports.

        Validates that MapBuilder creates virtual external module nodes for external
        imports (e.g., "os", "pathlib", "pytest") that are not part of the scanned project:
        - No exception is raised
        - A virtual node with ID 'external::{module_name}' is created
        - The node has type='external_module' and name=module_name
        - An IMPORTS edge is created from source file to external node
        - No warnings or errors are logged
        """
        # Arrange
        main_content = '''import os
from pathlib import Path
import pytest

def main():
    pass
'''
        (tmp_path / "main.py").write_text(main_content)

        builder = MapBuilder()
        graph_manager = builder.build(tmp_path)

        # Get the graph manager used by builder
        builder._graph = graph_manager

        # Get file ID (relative path as used in graph)
        main_file_id = "main.py"

        # Reset graph to test method in isolation with fresh state
        # Remove both edges AND nodes to ensure _resolve_and_add_import() creates them
        external_modules = ["os", "pathlib", "pytest"]
        for module_name in external_modules:
            external_node_id = f"external::{module_name}"
            if graph_manager.graph.has_edge(main_file_id, external_node_id):
                graph_manager.graph.remove_edge(main_file_id, external_node_id)
            if external_node_id in graph_manager.graph.nodes:
                graph_manager.graph.remove_node(external_node_id)

        # Act - Should create external nodes and IMPORTS edges
        # Pass relative path as source_file
        import logging
        with caplog.at_level(logging.WARNING):
            builder._resolve_and_add_import(tmp_path, Path("main.py"), "os")
            builder._resolve_and_add_import(tmp_path, Path("main.py"), "pathlib")
            builder._resolve_and_add_import(tmp_path, Path("main.py"), "pytest")

        # Assert - No warnings logged for external modules
        warning_messages = [
            record.message for record in caplog.records
            if record.levelname == "WARNING"
        ]
        assert len(warning_messages) == 0, \
            f"Expected no warnings for external imports, got: {warning_messages}"

        # Assert - External nodes were created
        external_nodes = {
            node_id: attrs for node_id, attrs in graph_manager.graph.nodes(data=True)
            if attrs.get("type") == "external_module"
        }

        expected_external_nodes = ["external::os", "external::pathlib", "external::pytest"]
        for expected_node in expected_external_nodes:
            assert expected_node in external_nodes, \
                f"Expected external node '{expected_node}' to be created"

            # Verify node attributes
            attrs = external_nodes[expected_node]
            module_name = expected_node.replace("external::", "")
            assert attrs["name"] == module_name, \
                f"Expected external node name to be '{module_name}', got '{attrs['name']}'"

        # Assert - IMPORTS edges were created from main.py to external nodes
        # Filter edges to only count IMPORTS edges to exactly these three target nodes
        imports_to_external = [
            (u, v) for u, v in graph_manager.graph.edges(main_file_id)
            if v in expected_external_nodes
            and graph_manager.graph.edges[u, v].get("relationship") == "IMPORTS"
        ]
        assert len(imports_to_external) == 3, \
            f"Expected 3 IMPORTS edges to external nodes, got {len(imports_to_external)}"

        for expected_node in expected_external_nodes:
            assert graph_manager.graph.has_edge(main_file_id, expected_node), \
                f"Expected IMPORTS edge from {main_file_id} to {expected_node}"
            edge_attrs = graph_manager.graph.edges[main_file_id, expected_node]
            assert edge_attrs["relationship"] == "IMPORTS", \
                f"Expected IMPORTS relationship, got {edge_attrs['relationship']}"

    def test_resolve_external_import_deduplication(self, tmp_path: Path) -> None:
        """Test that same external module imported from multiple files creates only ONE external node.

        Validates that MapBuilder deduplicates external module nodes when the same
        external module is imported from multiple files:
        - Only one external node is created for each unique external module
        - Each importing file has its own IMPORTS edge to the shared external node
        """
        # Arrange
        main_content = '''import os
def main():
    pass
'''
        utils_content = '''import os
def helper():
    pass
'''
        (tmp_path / "main.py").write_text(main_content)
        (tmp_path / "utils.py").write_text(utils_content)

        builder = MapBuilder()
        graph_manager = builder.build(tmp_path)

        # Get the graph manager used by builder
        builder._graph = graph_manager

        # Act - Import 'os' from both files
        builder._resolve_and_add_import(tmp_path, Path("main.py"), "os")
        builder._resolve_and_add_import(tmp_path, Path("utils.py"), "os")

        # Assert - Only ONE external::os node exists
        external_nodes = [
            node_id for node_id, attrs in graph_manager.graph.nodes(data=True)
            if attrs.get("type") == "external_module" and node_id == "external::os"
        ]
        assert len(external_nodes) == 1, \
            f"Expected exactly 1 external::os node, got {len(external_nodes)}"

        # Assert - Both files have IMPORTS edges to the same external node
        assert graph_manager.graph.has_edge("main.py", "external::os"), \
            "Expected IMPORTS edge from main.py to external::os"
        assert graph_manager.graph.has_edge("utils.py", "external::os"), \
            "Expected IMPORTS edge from utils.py to external::os"

    def test_resolve_external_dotted_import(self, tmp_path: Path) -> None:
        """Test _resolve_and_add_import() with dotted external imports (e.g., os.path).

        Validates that MapBuilder creates external nodes for dotted external imports:
        - Creates node with ID 'external::os.path' (preserves dots)
        - Node has type='external_module' and name='os.path'
        - IMPORTS edge is created from source file to external node
        """
        # Arrange
        main_content = '''from os.path import join
def main():
    pass
'''
        (tmp_path / "main.py").write_text(main_content)

        builder = MapBuilder()
        graph_manager = builder.build(tmp_path)

        # Get the graph manager used by builder
        builder._graph = graph_manager

        main_file_id = "main.py"

        # Act
        builder._resolve_and_add_import(tmp_path, Path("main.py"), "os.path")

        # Assert - External node created with dotted name
        expected_node_id = "external::os.path"
        assert expected_node_id in graph_manager.graph.nodes, \
            f"Expected external node '{expected_node_id}' to be created"

        # Verify node attributes
        attrs = graph_manager.graph.nodes[expected_node_id]
        assert attrs["type"] == "external_module", \
            f"Expected type='external_module', got '{attrs['type']}'"
        assert attrs["name"] == "os.path", \
            f"Expected name='os.path', got '{attrs['name']}'"

        # Assert - IMPORTS edge created
        assert graph_manager.graph.has_edge(main_file_id, expected_node_id), \
            f"Expected IMPORTS edge from {main_file_id} to {expected_node_id}"
        edge_attrs = graph_manager.graph.edges[main_file_id, expected_node_id]
        assert edge_attrs["relationship"] == "IMPORTS"

    def test_resolve_multiple_external_modules(self, tmp_path: Path) -> None:
        """Test _resolve_and_add_import() with multiple external modules (networkx, openai).

        Validates that MapBuilder correctly handles multiple external imports
        in a single file, creating distinct external nodes for each module
        and establishing separate IMPORTS edges.
        """
        # Arrange
        main_content = '''import networkx
import openai
from typing import Dict

def main():
    pass
'''
        (tmp_path / "main.py").write_text(main_content)

        builder = MapBuilder()
        graph_manager = builder.build(tmp_path)

        # Get the graph manager used by builder
        builder._graph = graph_manager

        main_file_id = "main.py"

        # Reset graph to test method in isolation with fresh state
        # Remove both edges AND nodes to ensure _resolve_and_add_import() creates them
        external_modules = ["networkx", "openai", "typing"]
        for module_name in external_modules:
            external_node_id = f"external::{module_name}"
            if graph_manager.graph.has_edge(main_file_id, external_node_id):
                graph_manager.graph.remove_edge(main_file_id, external_node_id)
            if external_node_id in graph_manager.graph.nodes:
                graph_manager.graph.remove_node(external_node_id)

        # Act - Call _resolve_and_add_import() for each module
        builder._resolve_and_add_import(tmp_path, Path("main.py"), "networkx")
        builder._resolve_and_add_import(tmp_path, Path("main.py"), "openai")
        builder._resolve_and_add_import(tmp_path, Path("main.py"), "typing")

        # Assert - External nodes were created for each module
        for module_name in external_modules:
            external_node_id = f"external::{module_name}"

            # Node exists
            assert external_node_id in graph_manager.graph.nodes, \
                f"Expected external node '{external_node_id}' to be created"

            # Node has correct type
            attrs = graph_manager.graph.nodes[external_node_id]
            assert attrs["type"] == "external_module", \
                f"Expected type='external_module' for {external_node_id}, got '{attrs['type']}'"

            # IMPORTS edge exists
            assert graph_manager.graph.has_edge(main_file_id, external_node_id), \
                f"Expected IMPORTS edge from {main_file_id} to {external_node_id}"

            # Edge has correct relationship
            edge_attrs = graph_manager.graph.edges[main_file_id, external_node_id]
            assert edge_attrs["relationship"] == "IMPORTS", \
                f"Expected IMPORTS relationship for edge to {external_node_id}"

    def test_resolve_external_import_idempotent(self, tmp_path: Path) -> None:
        """Test _resolve_and_add_import() with duplicate external imports.

        Validates that calling _resolve_and_add_import() multiple times
        with the same external module is idempotent: only one node and
        one edge are created, with no errors or duplicates.
        """
        # Arrange
        main_content = '''import os

def main():
    pass
'''
        (tmp_path / "main.py").write_text(main_content)

        builder = MapBuilder()
        graph_manager = builder.build(tmp_path)

        # Get the graph manager used by builder
        builder._graph = graph_manager

        main_file_id = "main.py"
        external_node_id = "external::os"

        # Reset edges to test method in isolation
        if graph_manager.graph.has_edge(main_file_id, external_node_id):
            graph_manager.graph.remove_edge(main_file_id, external_node_id)
        if external_node_id in graph_manager.graph.nodes:
            graph_manager.graph.remove_node(external_node_id)

        # Act - Call _resolve_and_add_import() for "os" THREE times
        builder._resolve_and_add_import(tmp_path, Path("main.py"), "os")
        builder._resolve_and_add_import(tmp_path, Path("main.py"), "os")
        builder._resolve_and_add_import(tmp_path, Path("main.py"), "os")

        # Assert - Only ONE external::os node exists
        external_nodes = [
            node_id for node_id, attrs in graph_manager.graph.nodes(data=True)
            if node_id == external_node_id
        ]
        assert len(external_nodes) == 1, \
            f"Expected exactly 1 external::os node after 3 calls, got {len(external_nodes)}"

        # Assert - Only ONE IMPORTS edge from main.py to external::os
        edges_to_external = [
            (u, v) for u, v in graph_manager.graph.edges()
            if u == main_file_id and v == external_node_id
        ]
        assert len(edges_to_external) == 1, \
            f"Expected exactly 1 IMPORTS edge after 3 calls, got {len(edges_to_external)}"

        # Assert - Node has correct type
        attrs = graph_manager.graph.nodes[external_node_id]
        assert attrs["type"] == "external_module", \
            f"Expected type='external_module', got '{attrs['type']}'"

    def test_resolve_mixed_internal_external_imports(self, tmp_path: Path) -> None:
        """Test _resolve_and_add_import() with both internal and external imports.

        Validates that MapBuilder correctly handles files with mixed imports:
        internal modules resolve to file nodes, external modules create
        external nodes, and both types of edges coexist in the graph.
        """
        # Arrange
        utils_content = '''def helper():
    pass
'''
        main_content = '''import os
from utils import helper

def main():
    helper()
'''
        (tmp_path / "utils.py").write_text(utils_content)
        (tmp_path / "main.py").write_text(main_content)

        builder = MapBuilder()
        graph_manager = builder.build(tmp_path)

        # Get the graph manager used by builder
        builder._graph = graph_manager

        main_file_id = "main.py"
        utils_file_id = "utils.py"
        external_node_id = "external::os"

        # Reset edges to test method in isolation
        if graph_manager.graph.has_edge(main_file_id, utils_file_id):
            graph_manager.graph.remove_edge(main_file_id, utils_file_id)
        if graph_manager.graph.has_edge(main_file_id, external_node_id):
            graph_manager.graph.remove_edge(main_file_id, external_node_id)

        # Act - Resolve both external and internal imports
        builder._resolve_and_add_import(tmp_path, Path("main.py"), "os")
        builder._resolve_and_add_import(tmp_path, Path("main.py"), "utils")

        # Assert - Internal edge: main.py → utils.py
        assert graph_manager.graph.has_edge(main_file_id, utils_file_id), \
            f"Expected IMPORTS edge from {main_file_id} to {utils_file_id} (internal)"
        internal_edge_attrs = graph_manager.graph.edges[main_file_id, utils_file_id]
        assert internal_edge_attrs["relationship"] == "IMPORTS", \
            "Expected IMPORTS relationship for internal import"

        # Assert - External node exists with correct type
        assert external_node_id in graph_manager.graph.nodes, \
            f"Expected external node '{external_node_id}' to be created"
        external_attrs = graph_manager.graph.nodes[external_node_id]
        assert external_attrs["type"] == "external_module", \
            f"Expected type='external_module', got '{external_attrs['type']}'"

        # Assert - External edge: main.py → external::os
        assert graph_manager.graph.has_edge(main_file_id, external_node_id), \
            f"Expected IMPORTS edge from {main_file_id} to {external_node_id} (external)"
        external_edge_attrs = graph_manager.graph.edges[main_file_id, external_node_id]
        assert external_edge_attrs["relationship"] == "IMPORTS", \
            "Expected IMPORTS relationship for external import"

        # Assert - Total IMPORTS edges from main.py is 2 (ignore CONTAINS edges to functions)
        imports_edges_from_main = [
            (u, v) for u, v in graph_manager.graph.edges(main_file_id)
            if graph_manager.graph.edges[u, v].get("relationship") == "IMPORTS"
        ]
        assert len(imports_edges_from_main) == 2, \
            f"Expected 2 IMPORTS edges from main.py (1 internal + 1 external), got {len(imports_edges_from_main)}"

    def test_resolve_dotted_package_import_from_root(self, tmp_path: Path) -> None:
        """Test _resolve_and_add_import() with dotted package import from root.

        Validates that MapBuilder correctly resolves dotted package imports
        (e.g., "codemap.scout") to __init__.py files in nested directories
        by converting to path format (e.g., "codemap/scout/__init__.py").
        This tests lines 169-170 in builder.py.
        """
        # Arrange
        # Create directory structure: codemap/scout/__init__.py
        (tmp_path / "codemap").mkdir()
        (tmp_path / "codemap" / "scout").mkdir()
        init_content = '''def scout_func():
    pass
'''
        (tmp_path / "codemap" / "scout" / "__init__.py").write_text(init_content)

        main_content = '''from codemap.scout import scout_func

def main():
    pass
'''
        (tmp_path / "main.py").write_text(main_content)

        builder = MapBuilder()
        graph_manager = builder.build(tmp_path)

        # Get the graph manager used by builder
        builder._graph = graph_manager

        # Get file IDs (relative paths as used in graph)
        main_file_id = "main.py"
        init_file_id = "codemap/scout/__init__.py"

        # Reset edges to test method in isolation
        if graph_manager.graph.has_edge(main_file_id, init_file_id):
            graph_manager.graph.remove_edge(main_file_id, init_file_id)

        # Act - Pass relative path as source_file (Path object)
        builder._resolve_and_add_import(tmp_path, Path("main.py"), "codemap.scout")

        # Assert - Dependency edge was added to __init__.py
        assert graph_manager.graph.has_edge(main_file_id, init_file_id), \
            f"Expected IMPORTS edge from {main_file_id} to {init_file_id}"
        edge_attrs = graph_manager.graph.edges[main_file_id, init_file_id]
        assert edge_attrs["relationship"] == "IMPORTS"


class TestMapBuilderFailureModeIntegration:
    """Failure-mode integration test suite for MapBuilder resilience.

    This test suite validates that MapBuilder handles error conditions gracefully
    and continues processing remaining files when encountering:
    - Corrupt or binary files with .py extension
    - Files with invalid Python syntax
    - Files with permission errors
    - Mixed scenarios with both valid and invalid files

    All tests verify that:
    - Warnings are logged for failed files
    - Processing continues for remaining files
    - Valid files are successfully added to the graph
    """

    def test_integration_corrupt_file_continues(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test MapBuilder logs warning and continues when encountering binary file.

        Validates that MapBuilder handles corrupt files (binary data with .py extension)
        gracefully by:
        - Logging a WARNING level message for the corrupt file
        - Continuing to process remaining valid files
        - Successfully building graph with valid files only
        """
        # Arrange
        valid_content = '''def valid_function():
    return "valid"
'''
        (tmp_path / "valid.py").write_text(valid_content)

        # Create binary file with .py extension (corrupt file)
        binary_file = tmp_path / "corrupt.py"
        binary_file.write_bytes(b'\x00\x01\x02\x03\x04\x05\xff\xfe')

        builder = MapBuilder()

        # Act
        import logging
        with caplog.at_level(logging.WARNING):
            graph_manager = builder.build(tmp_path)

        # Assert - Warning was logged for corrupt file
        assert len(caplog.records) > 0, "Expected warning to be logged for corrupt file"
        warning_messages = [
            record.message for record in caplog.records
            if record.levelname == "WARNING"
        ]
        assert any("corrupt.py" in msg for msg in warning_messages), \
            "Expected warning message to mention corrupt.py"

        # Assert - Valid file was processed successfully
        file_nodes = [
            node_id for node_id, attrs in graph_manager.graph.nodes(data=True)
            if attrs.get("type") == "file"
        ]
        # Should have at least valid.py (corrupt.py is also discovered but fails content read)
        assert len(file_nodes) >= 1, "Expected at least valid.py to be processed"

        # Verify valid.py has code nodes
        code_nodes = [
            node_id for node_id, attrs in graph_manager.graph.nodes(data=True)
            if attrs.get("type") == "function" and "valid.py" in node_id
        ]
        assert len(code_nodes) >= 1, "Expected valid.py to have code nodes"

    def test_integration_parser_exception_continues(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test MapBuilder logs warning and continues when parser raises exception.

        Validates that MapBuilder handles parser exceptions gracefully by:
        - Logging a WARNING level message when parsing fails
        - Continuing to process remaining valid files
        - Successfully building graph with valid files only

        Note: Since tree-sitter is resilient and doesn't naturally throw exceptions,
        this test mocks the parser to simulate a parsing error.
        """
        # Arrange
        from unittest.mock import patch

        valid1_content = '''def first_function():
    return "first"
'''
        valid2_content = '''def second_function():
    return "second"
'''
        (tmp_path / "valid1.py").write_text(valid1_content)
        (tmp_path / "problematic.py").write_text("def broken")  # Will be forced to fail via mock
        (tmp_path / "valid2.py").write_text(valid2_content)

        builder = MapBuilder()

        # Mock ParserEngine to throw exception for problematic.py
        original_parse = builder._parser.parse_file

        def mock_parse(path: Path, content: str) -> list[object]:
            if "problematic" in str(path):
                raise ValueError("Simulated parser exception for testing")
            return list(original_parse(path, content))

        # Act
        import logging
        with patch.object(builder._parser, "parse_file", side_effect=mock_parse):
            with caplog.at_level(logging.WARNING):
                graph_manager = builder.build(tmp_path)

        # Assert - Warning was logged for problematic.py
        assert len(caplog.records) > 0, "Expected warning to be logged for parser exception"
        warning_messages = [
            record.message for record in caplog.records
            if record.levelname == "WARNING"
        ]
        assert any("problematic.py" in msg for msg in warning_messages), \
            "Expected warning message to mention problematic.py"

        # Assert - Valid files were processed successfully
        code_nodes = [
            node_id for node_id, attrs in graph_manager.graph.nodes(data=True)
            if attrs.get("type") == "function"
        ]
        # Should have at least 2 code nodes (first_function and second_function)
        assert len(code_nodes) >= 2, f"Expected at least 2 code nodes, got {len(code_nodes)}"

        # Verify specific functions are present
        function_names = [attrs.get("name") for _, attrs in graph_manager.graph.nodes(data=True)
                         if attrs.get("type") == "function"]
        assert "first_function" in function_names, "Expected first_function to be in graph"
        assert "second_function" in function_names, "Expected second_function to be in graph"

    def test_integration_permission_error_continues(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test MapBuilder logs warning and continues when file has no read permissions.

        Validates that MapBuilder handles permission errors gracefully by:
        - Logging a WARNING level message for files without read permissions
        - Continuing to process remaining accessible files
        - Successfully building graph with accessible files only

        Note: Permission tests may behave differently on different platforms.
        This test is skipped on Windows where permission handling differs.
        """
        # Arrange
        import platform
        if platform.system() == "Windows":
            pytest.skip("Permission tests unreliable on Windows")

        valid_content = '''def accessible_function():
    return "accessible"
'''
        (tmp_path / "accessible.py").write_text(valid_content)

        # Create file and remove read permissions
        restricted_file = tmp_path / "restricted.py"
        restricted_file.write_text("def restricted(): pass")
        import os
        os.chmod(restricted_file, 0o000)  # Remove all permissions

        builder = MapBuilder()

        # Act
        import logging
        try:
            with caplog.at_level(logging.WARNING):
                graph_manager = builder.build(tmp_path)

            # Assert - Warning was logged for restricted file
            assert len(caplog.records) > 0, "Expected warning for permission error"
            warning_messages = [
                record.message for record in caplog.records
                if record.levelname == "WARNING"
            ]
            assert any("restricted.py" in msg for msg in warning_messages), \
                "Expected warning message to mention restricted.py"

            # Assert - Accessible file was processed successfully
            code_nodes = [
                node_id for node_id, attrs in graph_manager.graph.nodes(data=True)
                if attrs.get("type") == "function" and "accessible.py" in node_id
            ]
            assert len(code_nodes) >= 1, "Expected accessible.py to have code nodes"

            # Verify accessible_function is present
            function_names = [
                attrs.get("name") for _, attrs in graph_manager.graph.nodes(data=True)
                if attrs.get("type") == "function"
            ]
            assert "accessible_function" in function_names, \
                "Expected accessible_function to be in graph"

        finally:
            # Restore permissions for cleanup
            os.chmod(restricted_file, 0o644)

    def test_integration_mixed_success_failure(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test MapBuilder handles mix of valid and invalid files correctly.

        Validates that MapBuilder processes a realistic mixed scenario with:
        - Multiple valid Python files
        - Binary/corrupt files with .py extension
        - Files that cause parser errors (via mocking)

        Verifies that:
        - All errors are logged with WARNING level
        - All valid files are successfully processed and added to graph
        - Graph contains correct nodes and edges for valid files only
        - Import relationships between valid files are preserved
        """
        # Arrange
        from unittest.mock import patch

        # Valid files with import relationship
        helper_content = '''def helper():
    return "help"
'''
        main_content = '''from helper import helper

def main():
    return helper()
'''
        utils_content = '''class UtilityClass:
    def method(self):
        pass
'''

        (tmp_path / "helper.py").write_text(helper_content)
        (tmp_path / "main.py").write_text(main_content)
        (tmp_path / "utils.py").write_text(utils_content)

        # Create corrupt binary file
        corrupt_file = tmp_path / "corrupt.py"
        corrupt_file.write_bytes(b'\x00\xff\xfe\xfd')

        # Create file that will trigger parser error (via mock)
        (tmp_path / "parser_error.py").write_text("def will_fail(): pass")

        builder = MapBuilder()

        # Mock ParserEngine to throw exception for parser_error.py
        original_parse = builder._parser.parse_file

        def mock_parse(path: Path, content: str) -> list[object]:
            if "parser_error" in str(path):
                raise ValueError("Simulated parser error for testing")
            return list(original_parse(path, content))

        # Act
        import logging
        with patch.object(builder._parser, "parse_file", side_effect=mock_parse):
            with caplog.at_level(logging.WARNING):
                graph_manager = builder.build(tmp_path)

        # Assert - Multiple warnings were logged (corrupt.py and parser_error.py)
        assert len(caplog.records) >= 2, (
            f"Expected at least 2 warnings, got {len(caplog.records)}"
        )
        warning_messages = [
            record.message for record in caplog.records
            if record.levelname == "WARNING"
        ]
        assert any("corrupt.py" in msg for msg in warning_messages), \
            "Expected warning for corrupt.py"
        assert any("parser_error.py" in msg for msg in warning_messages), \
            "Expected warning for parser_error.py"

        # Assert - All valid files are in graph
        file_nodes = {
            node_id: attrs for node_id, attrs in graph_manager.graph.nodes(data=True)
            if attrs.get("type") == "file"
        }

        # Find valid file nodes
        helper_file_id = next((nid for nid in file_nodes if nid.endswith("helper.py")), None)
        main_file_id = next((nid for nid in file_nodes if nid.endswith("main.py")), None)
        utils_file_id = next((nid for nid in file_nodes if nid.endswith("utils.py")), None)

        assert helper_file_id is not None, "Expected helper.py file node in graph"
        assert main_file_id is not None, "Expected main.py file node in graph"
        assert utils_file_id is not None, "Expected utils.py file node in graph"

        # Assert - Code nodes from valid files are present
        code_nodes = [
            node_id for node_id, attrs in graph_manager.graph.nodes(data=True)
            if attrs.get("type") in ["function", "class"]
        ]
        assert len(code_nodes) >= 3, f"Expected at least 3 code nodes, got {len(code_nodes)}"

        # Verify specific code elements are present
        function_names = [attrs.get("name") for _, attrs in graph_manager.graph.nodes(data=True)
                         if attrs.get("type") in ["function", "class"]]
        assert "helper" in function_names, "Expected helper function in graph"
        assert "main" in function_names, "Expected main function in graph"
        assert "UtilityClass" in function_names, "Expected UtilityClass in graph"

        # Assert - Import relationship between valid files is preserved
        assert graph_manager.graph.has_edge(main_file_id, helper_file_id), \
            f"Expected IMPORTS edge from {main_file_id} to {helper_file_id}"
        imports_edge = graph_manager.graph.edges[main_file_id, helper_file_id]
        assert imports_edge["relationship"] == "IMPORTS", \
            "Expected IMPORTS relationship between main.py and helper.py"

        # Assert - Graph statistics reflect only valid files
        stats = graph_manager.graph_stats
        # At least 3 file nodes + 3 code nodes = 6 nodes minimum
        assert stats["nodes"] >= 6, f"Expected at least 6 nodes, got {stats['nodes']}"
        # At least 3 CONTAINS edges + 1 IMPORTS edge = 4 edges minimum
        assert stats["edges"] >= 4, f"Expected at least 4 edges, got {stats['edges']}"
