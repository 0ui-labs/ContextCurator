"""Unit tests for graph.manager module.

This module contains comprehensive tests for the GraphManager class,
following strict TDD RED phase - all tests define the expected API contract
and will fail until implementation is complete.
"""

from pathlib import Path

import networkx as nx
import pytest

from codemap.graph import GraphManager
from codemap.mapper.models import CodeNode
from codemap.scout.models import FileEntry


class TestGraphModuleExports:
    """Test suite for graph module exports."""

    def test_graph_manager_is_exported(self) -> None:
        """Test GraphManager is exported from codemap.graph."""
        # GraphManager should be importable from the graph package
        assert GraphManager is not None
        assert callable(GraphManager)

    def test_graph_module_all_contains_graph_manager(self) -> None:
        """Test __all__ contains GraphManager export."""
        from codemap import graph

        assert hasattr(graph, "__all__")
        assert "GraphManager" in graph.__all__


class TestGraphManagerInitialization:
    """Test suite for GraphManager initialization."""

    def test_graph_manager_exists(self) -> None:
        """Test GraphManager class exists."""
        assert GraphManager is not None
        assert isinstance(GraphManager, type)

    def test_graph_manager_instantiates_without_arguments(self) -> None:
        """Test GraphManager() creates instance without arguments."""
        manager = GraphManager()
        assert isinstance(manager, GraphManager)

    def test_initialized_graph_manager_has_empty_graph(self) -> None:
        """Test initialized GraphManager has empty graph (0 nodes, 0 edges)."""
        manager = GraphManager()
        graph = manager.graph

        assert graph.number_of_nodes() == 0
        assert graph.number_of_edges() == 0


class TestGraphProperty:
    """Test suite for GraphManager.graph property."""

    def test_graph_property_exists(self) -> None:
        """Test graph property exists."""
        manager = GraphManager()
        assert hasattr(manager, "graph")

    def test_graph_property_returns_digraph(self) -> None:
        """Test graph property returns NetworkX DiGraph."""
        manager = GraphManager()
        graph = manager.graph

        assert isinstance(graph, nx.DiGraph)

    def test_graph_property_returns_same_object(self) -> None:
        """Test graph property returns the same graph object (read-only access)."""
        manager = GraphManager()

        # Access property multiple times
        graph1 = manager.graph
        graph2 = manager.graph

        # Should be the same object
        assert graph1 is graph2

    def test_graph_property_is_typed_as_string_digraph(self) -> None:
        """Test graph property is correctly typed for type checkers."""
        manager = GraphManager()
        graph = manager.graph

        # Verify it's a DiGraph that can be used with string node identifiers
        assert isinstance(graph, nx.DiGraph)

        # The graph should accept string node identifiers (per type hint)
        graph.add_node("test_node")
        assert "test_node" in graph.nodes()


class TestGraphManagerBasic:
    """Test suite for GraphManager basic node operations."""

    def test_graphmanager_initialization(self) -> None:
        """Test GraphManager initializes with empty DiGraph."""
        manager = GraphManager()

        assert isinstance(manager.graph, nx.DiGraph)
        assert manager.graph.number_of_nodes() == 0

    def test_add_file_creates_node(self) -> None:
        """Test add_file creates a node with correct attributes."""
        manager = GraphManager()
        entry = FileEntry(path=Path("src/main.py"), size=1024, token_est=256)

        manager.add_file(entry)

        assert "src/main.py" in manager.graph.nodes
        assert manager.graph.nodes["src/main.py"]["type"] == "file"
        assert manager.graph.nodes["src/main.py"]["size"] == 1024
        assert manager.graph.nodes["src/main.py"]["token_est"] == 256

    def test_add_file_with_relative_path(self) -> None:
        """Test add_file handles relative paths correctly."""
        manager = GraphManager()
        entry = FileEntry(path=Path("utils/helper.py"), size=512, token_est=128)

        manager.add_file(entry)

        assert "utils/helper.py" in manager.graph.nodes

    def test_add_file_duplicate_path(self) -> None:
        """Test add_file with duplicate path does not create duplicate nodes."""
        manager = GraphManager()
        entry1 = FileEntry(path=Path("src/main.py"), size=1024, token_est=256)
        entry2 = FileEntry(path=Path("src/main.py"), size=2048, token_est=512)

        manager.add_file(entry1)
        manager.add_file(entry2)

        # Should have only one node
        assert manager.graph.number_of_nodes() == 1
        # Attributes should be from the latest add
        assert manager.graph.nodes["src/main.py"]["size"] == 2048
        assert manager.graph.nodes["src/main.py"]["token_est"] == 512


class TestGraphManagerHierarchy:
    """Test suite for GraphManager hierarchy and relationship operations."""

    def test_add_code_node_creates_hierarchy(self) -> None:
        """Test add_node creates code node with CONTAINS edge from file."""
        manager = GraphManager()
        manager.add_file(FileEntry(Path("src/app.py"), 512, 128))
        node = CodeNode(type="function", name="calculate", start_line=10, end_line=15)

        manager.add_node("src/app.py", node)

        # Assert code node exists with correct ID
        assert "src/app.py::calculate" in manager.graph.nodes
        # Assert node attributes
        assert manager.graph.nodes["src/app.py::calculate"]["type"] == "function"
        assert manager.graph.nodes["src/app.py::calculate"]["name"] == "calculate"
        assert manager.graph.nodes["src/app.py::calculate"]["start_line"] == 10
        assert manager.graph.nodes["src/app.py::calculate"]["end_line"] == 15
        # Assert CONTAINS edge exists
        assert manager.graph.has_edge("src/app.py", "src/app.py::calculate")
        assert (
            manager.graph.edges["src/app.py", "src/app.py::calculate"]["relationship"]
            == "CONTAINS"
        )

    def test_add_multiple_code_nodes_same_file(self) -> None:
        """Test add_node creates multiple nodes with correct edges."""
        manager = GraphManager()
        manager.add_file(FileEntry(Path("src/models.py"), 1024, 256))
        func_node = CodeNode(
            type="function", name="process_data", start_line=5, end_line=10
        )
        class_node = CodeNode(type="class", name="DataModel", start_line=15, end_line=30)

        manager.add_node("src/models.py", func_node)
        manager.add_node("src/models.py", class_node)

        # Both nodes exist
        assert "src/models.py::process_data" in manager.graph.nodes
        assert "src/models.py::DataModel" in manager.graph.nodes
        # Both have CONTAINS edges from file
        assert manager.graph.has_edge("src/models.py", "src/models.py::process_data")
        assert manager.graph.has_edge("src/models.py", "src/models.py::DataModel")
        assert (
            manager.graph.edges["src/models.py", "src/models.py::process_data"]["relationship"]
            == "CONTAINS"
        )
        assert (
            manager.graph.edges["src/models.py", "src/models.py::DataModel"]["relationship"]
            == "CONTAINS"
        )

    def test_add_dependency_creates_import_edge(self) -> None:
        """Test add_dependency creates IMPORTS edge between files."""
        manager = GraphManager()
        manager.add_file(FileEntry(Path("src/main.py"), 512, 128))
        manager.add_file(FileEntry(Path("src/utils.py"), 256, 64))

        manager.add_dependency("src/main.py", "src/utils.py")

        assert manager.graph.has_edge("src/main.py", "src/utils.py")
        assert (
            manager.graph.edges["src/main.py", "src/utils.py"]["relationship"] == "IMPORTS"
        )

    def test_add_node_without_parent_file_raises_error(self) -> None:
        """Test add_node without parent file raises ValueError."""
        manager = GraphManager()
        node = CodeNode(type="function", name="orphan", start_line=1, end_line=5)

        with pytest.raises(ValueError):
            manager.add_node("nonexistent.py", node)

    def test_add_node_to_non_file_node_raises_error(self) -> None:
        """Test add_node to a non-file node raises ValueError."""
        manager = GraphManager()
        # Add a file and a code node first
        manager.add_file(FileEntry(Path("src/app.py"), 512, 128))
        func_node = CodeNode(type="function", name="main", start_line=1, end_line=5)
        manager.add_node("src/app.py", func_node)

        # Try to add a code node to another code node (not a file)
        nested_node = CodeNode(type="function", name="nested", start_line=2, end_line=3)

        with pytest.raises(ValueError):
            manager.add_node("src/app.py::main", nested_node)

    def test_add_node_duplicate_updates_attributes(self) -> None:
        """Test add_node with duplicate name updates attributes."""
        manager = GraphManager()
        manager.add_file(FileEntry(Path("src/app.py"), 512, 128))

        # Add code node first time
        node1 = CodeNode(type="function", name="process", start_line=5, end_line=10)
        manager.add_node("src/app.py", node1)

        # Add same code node with different line numbers
        node2 = CodeNode(type="function", name="process", start_line=12, end_line=20)
        manager.add_node("src/app.py", node2)

        # Should have only one code node (plus the file node)
        assert manager.graph.number_of_nodes() == 2
        # Attributes should be from the latest add
        assert manager.graph.nodes["src/app.py::process"]["start_line"] == 12
        assert manager.graph.nodes["src/app.py::process"]["end_line"] == 20

    def test_add_dependency_duplicate_ignored(self) -> None:
        """Test add_dependency with duplicate edge does not create duplicates."""
        manager = GraphManager()
        manager.add_file(FileEntry(Path("src/main.py"), 512, 128))
        manager.add_file(FileEntry(Path("src/utils.py"), 256, 64))

        # Add dependency twice
        manager.add_dependency("src/main.py", "src/utils.py")
        manager.add_dependency("src/main.py", "src/utils.py")

        # Should have only one edge
        assert manager.graph.number_of_edges() == 1
        assert manager.graph.has_edge("src/main.py", "src/utils.py")

    def test_add_dependency_without_source_node(self) -> None:
        """Test add_dependency raises ValueError when source node doesn't exist.

        Source validation should remain strict - only target nodes are created lazily.
        This ensures the importing file exists in the graph before creating dependencies.

        Tests two scenarios:
        1. Source missing, target exists -> ValueError
        2. Source missing, target also missing -> ValueError (source checked first)
        """
        manager = GraphManager()
        manager.add_file(FileEntry(Path("src/utils.py"), 256, 64))

        # Scenario 1: Source missing, target exists
        with pytest.raises(ValueError, match="Source node.*not found"):
            manager.add_dependency("nonexistent.py", "src/utils.py")

        # Scenario 2: Both source and target missing - source validation fails first
        with pytest.raises(ValueError, match="Source node.*not found"):
            manager.add_dependency("nonexistent.py", "also_nonexistent.py")

    def test_add_dependency_without_target_node(self) -> None:
        """Test add_dependency creates target node lazily when it doesn't exist.

        When target_file_id does not exist in the graph, add_dependency should:
        1. Create the target node automatically (lazy creation)
        2. Create the IMPORTS edge from source to target
        3. The lazy-created node should have no attributes except its ID

        This allows adding dependencies to external modules without pre-creating nodes.
        """
        manager = GraphManager()
        manager.add_file(FileEntry(Path("src/main.py"), 512, 128))

        # Add dependency to non-existent target - should create it lazily
        manager.add_dependency("src/main.py", "external::os")

        # Assert target node was created
        assert "external::os" in manager.graph.nodes

        # Assert IMPORTS edge was created
        assert manager.graph.has_edge("src/main.py", "external::os")
        assert (
            manager.graph.edges["src/main.py", "external::os"]["relationship"] == "IMPORTS"
        )

        # Assert lazy-created node has no attributes (except implicit ID)
        # NetworkX nodes always have the node_id, but should have no other attributes
        node_attrs = dict(manager.graph.nodes["external::os"])
        assert len(node_attrs) == 0, f"Lazy node should have no attributes, got: {node_attrs}"

    def test_add_dependency_lazy_node_idempotent(self) -> None:
        """Test add_dependency is idempotent for lazy-created target nodes.

        Calling add_dependency multiple times with the same source and target
        (where target is lazy-created) should:
        1. Create the target node only once
        2. Create only one IMPORTS edge
        3. Not add any attributes to the lazy-created node
        """
        manager = GraphManager()
        manager.add_file(FileEntry(Path("src/main.py"), 512, 128))

        # Call add_dependency twice with same source and lazy target
        manager.add_dependency("src/main.py", "external::idempotent")
        manager.add_dependency("src/main.py", "external::idempotent")

        # Should have exactly 2 nodes: source file + lazy target
        assert manager.graph.number_of_nodes() == 2
        assert "external::idempotent" in manager.graph.nodes

        # Should have exactly 1 IMPORTS edge
        assert manager.graph.number_of_edges() == 1
        assert manager.graph.has_edge("src/main.py", "external::idempotent")
        assert (
            manager.graph.edges["src/main.py", "external::idempotent"]["relationship"]
            == "IMPORTS"
        )

        # Lazy-created node should still have no attributes
        node_attrs = dict(manager.graph.nodes["external::idempotent"])
        assert len(node_attrs) == 0, f"Lazy node should have no attributes, got: {node_attrs}"

    def test_lazy_node_can_be_enriched_later(self) -> None:
        """Test lazy-created nodes can be enriched with attributes later.

        After lazy creation, the node should be accessible via direct graph
        access to add attributes like type, name, or other metadata.
        """
        manager = GraphManager()
        manager.add_file(FileEntry(Path("src/main.py"), 512, 128))

        # Create lazy node via add_dependency
        manager.add_dependency("src/main.py", "external::requests")

        # Verify it exists with no attributes
        assert "external::requests" in manager.graph.nodes
        assert len(dict(manager.graph.nodes["external::requests"])) == 0

        # Enrich the node with attributes using direct graph access
        manager.graph.nodes["external::requests"]["type"] = "external_module"
        manager.graph.nodes["external::requests"]["name"] = "requests"
        manager.graph.nodes["external::requests"]["source"] = "pip"

        # Verify enrichment worked
        assert manager.graph.nodes["external::requests"]["type"] == "external_module"
        assert manager.graph.nodes["external::requests"]["name"] == "requests"
        assert manager.graph.nodes["external::requests"]["source"] == "pip"

    def test_multiple_lazy_nodes_for_same_target(self) -> None:
        """Test multiple files can add dependencies to the same lazy-created target.

        When multiple source files import the same external module, the target
        node should only be created once, with all IMPORTS edges pointing to it.
        """
        manager = GraphManager()
        manager.add_file(FileEntry(Path("src/main.py"), 512, 128))
        manager.add_file(FileEntry(Path("src/utils.py"), 256, 64))
        manager.add_file(FileEntry(Path("src/models.py"), 768, 192))

        # All files import the same external module
        manager.add_dependency("src/main.py", "external::json")
        manager.add_dependency("src/utils.py", "external::json")
        manager.add_dependency("src/models.py", "external::json")

        # Should have 3 file nodes + 1 lazy external node = 4 nodes
        assert manager.graph.number_of_nodes() == 4

        # Should have 3 IMPORTS edges to the same target
        assert manager.graph.number_of_edges() == 3
        assert manager.graph.has_edge("src/main.py", "external::json")
        assert manager.graph.has_edge("src/utils.py", "external::json")
        assert manager.graph.has_edge("src/models.py", "external::json")

        # Lazy node should still have no attributes
        assert len(dict(manager.graph.nodes["external::json"])) == 0

    def test_lazy_node_creation_with_existing_node(self) -> None:
        """Test add_dependency doesn't overwrite existing target node.

        If the target node already exists (e.g., a real file), lazy creation
        should not modify its attributes. The edge should be created normally.
        """
        manager = GraphManager()
        manager.add_file(FileEntry(Path("src/main.py"), 512, 128))
        manager.add_file(FileEntry(Path("src/utils.py"), 256, 64))

        # Verify target node has attributes before add_dependency
        assert manager.graph.nodes["src/utils.py"]["type"] == "file"
        assert manager.graph.nodes["src/utils.py"]["size"] == 256

        # Add dependency - should not modify existing node
        manager.add_dependency("src/main.py", "src/utils.py")

        # Verify attributes are preserved
        assert manager.graph.nodes["src/utils.py"]["type"] == "file"
        assert manager.graph.nodes["src/utils.py"]["size"] == 256
        assert manager.graph.nodes["src/utils.py"]["token_est"] == 64

        # Verify edge was created
        assert manager.graph.has_edge("src/main.py", "src/utils.py")

    def test_add_external_module_creates_node(self) -> None:
        """Test add_external_module creates node with correct attributes.

        The method should create a node with:
        - Node ID in format "external::{module_name}"
        - Attribute type="external_module"
        - Attribute name=module_name
        """
        manager = GraphManager()

        node_id = manager.add_external_module("os")

        # Node should exist with correct ID
        assert "external::os" in manager.graph.nodes

        # Node should have correct attributes
        assert manager.graph.nodes["external::os"]["type"] == "external_module"
        assert manager.graph.nodes["external::os"]["name"] == "os"

    def test_add_external_module_returns_node_id(self) -> None:
        """Test add_external_module returns the correct node ID.

        The method should return the node ID in format "external::{module_name}".
        """
        manager = GraphManager()

        node_id = manager.add_external_module("requests")

        assert node_id == "external::requests"

    def test_add_external_module_deduplicates(self) -> None:
        """Test add_external_module deduplicates multiple calls.

        Calling add_external_module multiple times with the same module_name
        should not create duplicate nodes. The node should only be created once.
        """
        manager = GraphManager()

        # Add same module twice
        node_id1 = manager.add_external_module("json")
        node_id2 = manager.add_external_module("json")

        # Both should return the same node ID
        assert node_id1 == node_id2
        assert node_id1 == "external::json"

        # Should only have one node in graph
        assert manager.graph.number_of_nodes() == 1
        assert "external::json" in manager.graph.nodes

    def test_add_external_module_preserves_existing_attributes(self) -> None:
        """Test add_external_module does not overwrite existing node attributes.

        If a node already exists (e.g., created lazily via add_dependency),
        add_external_module should not modify its existing attributes.
        Only missing attributes should be added.
        """
        manager = GraphManager()

        # Create a lazy node first via add_dependency
        manager.add_file(FileEntry(Path("src/main.py"), 512, 128))
        manager.add_dependency("src/main.py", "external::numpy")

        # Add custom attribute to the lazy node
        manager.graph.nodes["external::numpy"]["custom_attr"] = "custom_value"

        # Call add_external_module on existing node
        node_id = manager.add_external_module("numpy")

        # Should return correct node ID
        assert node_id == "external::numpy"

        # Should have type and name attributes
        assert manager.graph.nodes["external::numpy"]["type"] == "external_module"
        assert manager.graph.nodes["external::numpy"]["name"] == "numpy"

        # Should preserve custom attribute
        assert manager.graph.nodes["external::numpy"]["custom_attr"] == "custom_value"

        # Should still have the IMPORTS edge
        assert manager.graph.has_edge("src/main.py", "external::numpy")


class TestGraphManagerPersistence:
    """Test suite for GraphManager persistence (save/load) operations."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """Test save creates file on disk."""
        manager = GraphManager()
        manager.add_file(FileEntry(Path("src/main.py"), 1024, 256))

        manager.save(tmp_path / "graph.json")

        assert (tmp_path / "graph.json").exists()
        assert (tmp_path / "graph.json").stat().st_size > 0

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        """Test save and load preserves graph structure."""
        manager = GraphManager()
        manager.add_file(FileEntry(Path("src/app.py"), 512, 128))
        node = CodeNode(type="function", name="main", start_line=1, end_line=10)
        manager.add_node("src/app.py", node)

        manager.save(tmp_path / "graph.json")

        # Load into new manager
        manager2 = GraphManager()
        manager2.load(tmp_path / "graph.json")

        # Assert counts match
        assert (
            manager2.graph.number_of_nodes() == manager.graph.number_of_nodes()
        )
        assert (
            manager2.graph.number_of_edges() == manager.graph.number_of_edges()
        )
        # Assert specific nodes exist
        assert "src/app.py" in manager2.graph.nodes
        assert "src/app.py::main" in manager2.graph.nodes
        # Assert edges exist
        assert manager2.graph.has_edge("src/app.py", "src/app.py::main")

    def test_load_nonexistent_file_raises_error(self, tmp_path: Path) -> None:
        """Test load raises FileNotFoundError for nonexistent file."""
        manager = GraphManager()

        with pytest.raises(FileNotFoundError):
            manager.load(tmp_path / "nonexistent.json")

    def test_save_and_load_preserves_graph_structure(self, tmp_path: Path) -> None:
        """Test save/load preserves complex graph structure."""
        manager = GraphManager()
        # Build complex graph: 3 files, 5 code nodes, 2 dependencies
        manager.add_file(FileEntry(Path("src/main.py"), 1024, 256))
        manager.add_file(FileEntry(Path("src/utils.py"), 512, 128))
        manager.add_file(FileEntry(Path("src/models.py"), 768, 192))

        manager.add_node(
            "src/main.py", CodeNode("function", "main", 1, 10)
        )
        manager.add_node(
            "src/main.py", CodeNode("function", "run", 12, 20)
        )
        manager.add_node(
            "src/utils.py", CodeNode("function", "helper", 1, 5)
        )
        manager.add_node(
            "src/models.py", CodeNode("class", "User", 1, 50)
        )
        manager.add_node(
            "src/models.py", CodeNode("class", "Order", 52, 100)
        )

        manager.add_dependency("src/main.py", "src/utils.py")
        manager.add_dependency("src/main.py", "src/models.py")

        manager.save(tmp_path / "graph.json")

        # Load and verify
        manager2 = GraphManager()
        manager2.load(tmp_path / "graph.json")

        # 3 files + 5 code nodes = 8 nodes
        assert manager2.graph.number_of_nodes() == 8
        # 5 CONTAINS edges + 2 IMPORTS edges = 7 edges
        assert manager2.graph.number_of_edges() == 7

        # Verify all nodes preserved
        for node_id in ["src/main.py", "src/utils.py", "src/models.py"]:
            assert node_id in manager2.graph.nodes
            assert manager2.graph.nodes[node_id]["type"] == "file"

        # Verify code nodes
        assert manager2.graph.nodes["src/main.py::main"]["type"] == "function"
        assert manager2.graph.nodes["src/models.py::User"]["type"] == "class"

        # Verify edges
        assert manager2.graph.has_edge("src/main.py", "src/utils.py")
        assert (
            manager2.graph.edges["src/main.py", "src/utils.py"]["relationship"]
            == "IMPORTS"
        )

    def test_load_invalid_json_raises_error(self, tmp_path: Path) -> None:
        """Test load raises error for invalid JSON."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{ invalid json }")

        manager = GraphManager()

        with pytest.raises((ValueError, Exception)):  # orjson.JSONDecodeError is a ValueError subclass
            manager.load(invalid_file)

    def test_load_invalid_graph_schema_raises_error(self, tmp_path: Path) -> None:
        """Test load raises ValueError for valid JSON with invalid graph schema.

        Valid JSON that does not conform to node_link_data structure (e.g., missing
        'nodes' or 'links' keys) should raise a ValueError with clear message.
        """
        invalid_schema_file = tmp_path / "invalid_schema.json"
        # Valid JSON but missing required "nodes" and "links" keys
        invalid_schema_file.write_bytes(b'{"foo": "bar", "baz": 123}')

        manager = GraphManager()

        with pytest.raises(ValueError, match="Invalid graph schema"):
            manager.load(invalid_schema_file)

    def test_save_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test save creates parent directories when they don't exist."""
        manager = GraphManager()
        manager.add_file(FileEntry(Path("src/main.py"), 1024, 256))

        # Call save with nested path where dirs don't exist
        nested_path = tmp_path / "nested" / "dir" / "graph.json"
        manager.save(nested_path)

        # Verify parent directories were created
        assert nested_path.parent.exists()
        assert nested_path.exists()
        assert nested_path.stat().st_size > 0

    def test_empty_graph_save_and_load(self, tmp_path: Path) -> None:
        """Test save and load of empty graph preserves empty state.

        A freshly initialized GraphManager with no nodes should be saveable
        and loadable, resulting in an identical empty graph.
        """
        # Save empty graph
        manager1 = GraphManager()
        graph_path = tmp_path / "empty_graph.json"
        manager1.save(graph_path)

        # Load into new manager
        manager2 = GraphManager()
        manager2.load(graph_path)

        # Both should report empty stats
        assert manager1.graph_stats == {"nodes": 0, "edges": 0}
        assert manager2.graph_stats == {"nodes": 0, "edges": 0}

    def test_save_and_load_preserves_all_attributes(self, tmp_path: Path) -> None:
        """Test save and load preserves all node and edge attributes exactly.

        All file attributes (size, token_est), code node attributes (type, name,
        start_line, end_line), and edge attributes (relationship) must be
        preserved through save/load roundtrip.
        """
        manager = GraphManager()

        # Add files with all attributes
        manager.add_file(FileEntry(Path("src/app.py"), size=2048, token_est=512))
        manager.add_file(FileEntry(Path("src/utils.py"), size=1024, token_est=256))

        # Add code nodes with all attributes
        manager.add_node("src/app.py", CodeNode("function", "main", 10, 25))
        manager.add_node("src/app.py", CodeNode("class", "AppController", 30, 100))
        manager.add_node("src/utils.py", CodeNode("function", "helper", 5, 15))

        # Add dependency
        manager.add_dependency("src/app.py", "src/utils.py")

        # Save and load
        graph_path = tmp_path / "full_graph.json"
        manager.save(graph_path)

        manager2 = GraphManager()
        manager2.load(graph_path)

        # Verify file node attributes
        assert manager2.graph.nodes["src/app.py"]["type"] == "file"
        assert manager2.graph.nodes["src/app.py"]["size"] == 2048
        assert manager2.graph.nodes["src/app.py"]["token_est"] == 512

        assert manager2.graph.nodes["src/utils.py"]["type"] == "file"
        assert manager2.graph.nodes["src/utils.py"]["size"] == 1024
        assert manager2.graph.nodes["src/utils.py"]["token_est"] == 256

        # Verify code node attributes using concrete node IDs
        assert manager2.graph.nodes["src/app.py::main"]["type"] == "function"
        assert manager2.graph.nodes["src/app.py::main"]["name"] == "main"
        assert manager2.graph.nodes["src/app.py::main"]["start_line"] == 10
        assert manager2.graph.nodes["src/app.py::main"]["end_line"] == 25

        assert manager2.graph.nodes["src/app.py::AppController"]["type"] == "class"
        assert manager2.graph.nodes["src/app.py::AppController"]["name"] == "AppController"
        assert manager2.graph.nodes["src/app.py::AppController"]["start_line"] == 30
        assert manager2.graph.nodes["src/app.py::AppController"]["end_line"] == 100

        assert manager2.graph.nodes["src/utils.py::helper"]["type"] == "function"
        assert manager2.graph.nodes["src/utils.py::helper"]["name"] == "helper"
        assert manager2.graph.nodes["src/utils.py::helper"]["start_line"] == 5
        assert manager2.graph.nodes["src/utils.py::helper"]["end_line"] == 15

        # Verify CONTAINS edge attributes
        assert manager2.graph.edges["src/app.py", "src/app.py::main"]["relationship"] == "CONTAINS"
        assert (
            manager2.graph.edges["src/app.py", "src/app.py::AppController"]["relationship"]
            == "CONTAINS"
        )
        assert (
            manager2.graph.edges["src/utils.py", "src/utils.py::helper"]["relationship"]
            == "CONTAINS"
        )

        # Verify IMPORTS edge attributes
        assert manager2.graph.edges["src/app.py", "src/utils.py"]["relationship"] == "IMPORTS"


class TestGraphManagerStats:
    """Test suite for GraphManager graph_stats property."""

    def test_graph_stats_empty_graph(self) -> None:
        """Test graph_stats returns correct stats for empty graph."""
        manager = GraphManager()

        assert manager.graph_stats == {"nodes": 0, "edges": 0}

    def test_graph_stats_with_nodes(self) -> None:
        """Test graph_stats returns correct node count."""
        manager = GraphManager()
        manager.add_file(FileEntry(Path("src/a.py"), 100, 25))
        manager.add_file(FileEntry(Path("src/b.py"), 200, 50))
        manager.add_file(FileEntry(Path("src/c.py"), 300, 75))

        assert manager.graph_stats == {"nodes": 3, "edges": 0}

    def test_graph_stats_with_edges(self) -> None:
        """Test graph_stats returns correct edge count."""
        manager = GraphManager()
        manager.add_file(FileEntry(Path("src/main.py"), 100, 25))
        manager.add_file(FileEntry(Path("src/utils.py"), 200, 50))
        manager.add_dependency("src/main.py", "src/utils.py")

        assert manager.graph_stats == {"nodes": 2, "edges": 1}

    def test_graph_stats_complex_graph(self) -> None:
        """Test graph_stats returns correct stats for complex graph."""
        manager = GraphManager()
        # 2 files
        manager.add_file(FileEntry(Path("src/main.py"), 1024, 256))
        manager.add_file(FileEntry(Path("src/utils.py"), 512, 128))
        # 3 code nodes (creates 3 CONTAINS edges)
        manager.add_node("src/main.py", CodeNode("function", "main", 1, 10))
        manager.add_node("src/main.py", CodeNode("function", "run", 12, 20))
        manager.add_node("src/utils.py", CodeNode("function", "helper", 1, 5))
        # 1 dependency (creates 1 IMPORTS edge)
        manager.add_dependency("src/main.py", "src/utils.py")

        # 2 files + 3 code nodes = 5 nodes
        # 3 CONTAINS + 1 IMPORTS = 4 edges
        assert manager.graph_stats == {"nodes": 5, "edges": 4}

    def test_load_preserves_graph_identity(self, tmp_path: Path) -> None:
        """Test load() preserves graph instance identity.

        The graph reference obtained before load() should remain valid after load(),
        pointing to the same DiGraph instance with updated content.
        """
        manager = GraphManager()
        manager.add_file(FileEntry(Path("src/initial.py"), 100, 25))

        # Get graph reference BEFORE load
        graph_before = manager.graph

        # Save to file
        manager.save(tmp_path / "graph.json")

        # Create new manager with different content and save
        manager2 = GraphManager()
        manager2.add_file(FileEntry(Path("src/loaded.py"), 200, 50))
        manager2.add_node("src/loaded.py", CodeNode("function", "foo", 1, 5))
        manager2.save(tmp_path / "graph.json")

        # Load the new content into original manager
        manager.load(tmp_path / "graph.json")

        # Get graph reference AFTER load
        graph_after = manager.graph

        # CRITICAL: Same object identity
        assert graph_before is graph_after, "load() must not replace the graph instance"

        # Content should be updated
        assert "src/loaded.py" in graph_before.nodes
        assert "src/loaded.py::foo" in graph_before.nodes
        assert "src/initial.py" not in graph_before.nodes
        assert graph_before.number_of_nodes() == 2
        assert graph_before.number_of_edges() == 1


class TestHierarchyBuilding:
    """Tests for hierarchical graph structure (project → package → file → code)."""

    def test_add_project_creates_root_node(self) -> None:
        """add_project() creates a level-0 project node."""
        manager = GraphManager()

        manager.add_project("MyProject")

        assert "project::MyProject" in manager.graph.nodes
        node = manager.graph.nodes["project::MyProject"]
        assert node["type"] == "project"
        assert node["level"] == 0
        assert node["name"] == "MyProject"

    def test_add_package_creates_package_node(self) -> None:
        """add_package() creates a package node with correct level."""
        manager = GraphManager()
        manager.add_project("MyProject")

        manager.add_package("src/auth")

        assert "src/auth" in manager.graph.nodes
        node = manager.graph.nodes["src/auth"]
        assert node["type"] == "package"
        assert node["level"] == 1
        assert node["name"] == "auth"

    def test_add_package_creates_contains_edge_to_project(self) -> None:
        """Package at root level gets CONTAINS edge from project."""
        manager = GraphManager()
        manager.add_project("MyProject")

        manager.add_package("src")

        assert manager.graph.has_edge("project::MyProject", "src")
        edge = manager.graph.edges["project::MyProject", "src"]
        assert edge["relationship"] == "CONTAINS"

    def test_nested_package_creates_contains_edge_to_parent(self) -> None:
        """Nested package gets CONTAINS edge from parent package."""
        manager = GraphManager()
        manager.add_project("MyProject")
        manager.add_package("src")

        manager.add_package("src/auth")

        assert manager.graph.has_edge("src", "src/auth")
        edge = manager.graph.edges["src", "src/auth"]
        assert edge["relationship"] == "CONTAINS"

    def test_add_package_calculates_correct_level(self) -> None:
        """All packages get level 1 regardless of nesting depth."""
        manager = GraphManager()
        manager.add_project("MyProject")
        manager.add_package("src")
        manager.add_package("src/auth")
        manager.add_package("src/auth/oauth")

        assert manager.graph.nodes["src"]["level"] == 1
        assert manager.graph.nodes["src/auth"]["level"] == 1
        assert manager.graph.nodes["src/auth/oauth"]["level"] == 1

    def test_build_hierarchy_creates_packages_from_files(self) -> None:
        """build_hierarchy() infers packages from existing file nodes."""
        manager = GraphManager()
        manager.add_file(FileEntry(Path("src/auth/login.py"), 100, 25))
        manager.add_file(FileEntry(Path("src/auth/session.py"), 100, 25))
        manager.add_file(FileEntry(Path("src/api/routes.py"), 100, 25))

        manager.build_hierarchy("MyProject")

        # Verify project and packages were created
        assert "project::MyProject" in manager.graph.nodes
        assert "src" in manager.graph.nodes
        assert "src/auth" in manager.graph.nodes
        assert "src/api" in manager.graph.nodes

        # Verify level attributes (0=project, 1=package)
        assert manager.graph.nodes["project::MyProject"]["level"] == 0
        assert manager.graph.nodes["src"]["level"] == 1
        assert manager.graph.nodes["src/auth"]["level"] == 1
        assert manager.graph.nodes["src/api"]["level"] == 1

        # Verify hierarchy edges
        assert manager.graph.has_edge("project::MyProject", "src")
        assert manager.graph.has_edge("src", "src/auth")
        assert manager.graph.has_edge("src", "src/api")
        assert manager.graph.has_edge("src/auth", "src/auth/login.py")

    def test_file_nodes_get_level_attribute(self) -> None:
        """File nodes receive level attribute based on depth."""
        manager = GraphManager()
        manager.add_file(FileEntry(Path("src/auth/login.py"), 100, 25))

        manager.build_hierarchy("MyProject")

        file_node = manager.graph.nodes["src/auth/login.py"]
        assert file_node["level"] == 2  # file = level 2

    def test_code_nodes_get_level_attribute(self) -> None:
        """Code nodes (function/class) receive level = file_level + 1."""
        manager = GraphManager()
        manager.add_file(FileEntry(Path("src/auth/login.py"), 100, 25))
        manager.add_node("src/auth/login.py", CodeNode("function", "login", 1, 10))

        manager.build_hierarchy("MyProject")

        code_node = manager.graph.nodes["src/auth/login.py::login"]
        assert code_node["level"] == 3  # function/class = level 3
