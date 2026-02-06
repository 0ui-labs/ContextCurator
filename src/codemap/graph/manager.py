"""Graph manager for building and persisting code relationship graphs.

This module provides the GraphManager class for managing directed graphs
of code relationships using NetworkX.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import networkx as nx
import orjson
from networkx.readwrite import json_graph

if TYPE_CHECKING:
    from codemap.mapper.models import CodeNode
    from codemap.scout.models import FileEntry


class GraphManager:
    """Manage a directed graph of code relationships using NetworkX.

    This class provides an interface for building and persisting directed
    graphs that represent code relationships. Nodes represent files and
    code elements (classes, functions), while edges represent relationships
    (CONTAINS, IMPORTS).

    Architecture:
        - Uses networkx.DiGraph for directed relationship representation
        - Nodes represent files and code elements (classes/functions)
        - Edges represent relationships (CONTAINS, IMPORTS)
        - Persistence via networkx.node_link_data and orjson

    Performance:
        Optimized for small to medium codebases (up to ~10,000 files,
        ~50,000 code nodes). For larger codebases, consider batching
        operations or using a database-backed solution.

    Thread Safety:
        GraphManager instances are NOT thread-safe. Create separate instances
        per thread for parallel processing.

    Raises:
        ValueError: Methods may raise ValueError for invalid inputs.
        FileNotFoundError: load() raises if file does not exist.

    Example:
        Complete workflow for building and persisting a code graph::

            from pathlib import Path
            from codemap.graph import GraphManager
            from codemap.scout.models import FileEntry
            from codemap.mapper.models import CodeNode

            # Initialize manager
            manager = GraphManager()

            # Add file nodes
            manager.add_file(FileEntry(Path("src/main.py"), size=1024, token_est=256))
            manager.add_file(FileEntry(Path("src/utils.py"), size=512, token_est=128))

            # Add code nodes (functions, classes)
            manager.add_node("src/main.py", CodeNode("function", "main", 1, 10))
            manager.add_node("src/utils.py", CodeNode("function", "helper", 1, 5))

            # Add import dependency
            manager.add_dependency("src/main.py", "src/utils.py")

            # Check graph statistics
            print(manager.graph_stats)  # {"nodes": 4, "edges": 3}

            # Save to file
            manager.save(Path("graph.json"))

            # Load into new manager
            manager2 = GraphManager()
            manager2.load(Path("graph.json"))
            print(manager2.graph_stats)  # {"nodes": 4, "edges": 3}
    """

    def __init__(self) -> None:
        """Initialize GraphManager with an empty directed graph."""
        self._graph: nx.DiGraph[str] = nx.DiGraph()

    @property
    def graph(self) -> nx.DiGraph[str]:
        """Return the underlying NetworkX directed graph.

        This property provides access to the raw NetworkX DiGraph for querying
        and analysis. While direct modification is technically possible, prefer
        using GraphManager methods for modifications:

        Recommended API for modifications:
            - add_file(): Add file nodes
            - add_node(): Add code element nodes with CONTAINS edges
            - add_dependency(): Add IMPORTS edges (with lazy target creation)
            - add_external_module(): Add external module nodes

        Direct graph access is appropriate for:
            - Querying nodes and edges (iteration, filtering, analysis)
            - Reading node/edge attributes
            - Using NetworkX algorithms (shortest_path, centrality, etc.)

        Note:
            Direct modifications via graph.add_node() or graph.add_edge() bypass
            GraphManager's validation and may create inconsistent graph states.
            Use the GraphManager methods for proper encapsulation.

        Returns:
            The directed graph managed by this instance.
        """
        return self._graph

    @property
    def graph_stats(self) -> dict[str, int]:
        """Return statistics about the graph.

        Returns:
            dict[str, int]: Dictionary with keys 'nodes' and 'edges' containing
                the respective counts as integers.

        Example:
            >>> manager = GraphManager()
            >>> manager.graph_stats
            {'nodes': 0, 'edges': 0}
        """
        return {
            "nodes": self._graph.number_of_nodes(),
            "edges": self._graph.number_of_edges(),
        }

    def add_file(self, entry: FileEntry) -> None:
        """Add a file node to the graph.

        Creates a node with type='file' and the file's metadata as attributes.
        If a node with the same path already exists, its attributes are updated.

        Args:
            entry: FileEntry containing path, size, and token_est attributes.

        Returns:
            None

        Example:
            >>> manager = GraphManager()
            >>> manager.add_file(FileEntry(Path("src/main.py"), size=1024, token_est=256))
            >>> "src/main.py" in manager.graph.nodes
            True
        """
        node_id = str(entry.path)
        self._graph.add_node(
            node_id,
            type="file",
            size=entry.size,
            token_est=entry.token_est,
        )

    def add_node(self, parent_file_id: str, node: CodeNode) -> None:
        """Add a code node to the graph with a CONTAINS edge from its parent file.

        Creates a node with ID format '{parent_file_id}::{node.name}' and
        automatically adds a CONTAINS edge from the parent file to this node.
        If a node with the same ID exists, its attributes are updated.

        Args:
            parent_file_id: The file node ID (path string) that contains this
                code element. Must exist in the graph as a file node.
            node: CodeNode containing type, name, start_line, and end_line.

        Returns:
            None

        Raises:
            ValueError: If parent_file_id does not exist in graph.
            ValueError: If parent_file_id exists but is not a file node.

        Example:
            >>> manager = GraphManager()
            >>> manager.add_file(FileEntry(Path("src/app.py"), 512, 128))
            >>> manager.add_node("src/app.py", CodeNode("function", "main", 1, 10))
            >>> "src/app.py::main" in manager.graph.nodes
            True
            >>> manager.graph.has_edge("src/app.py", "src/app.py::main")
            True
        """
        if parent_file_id not in self._graph.nodes:
            raise ValueError(f"Parent file '{parent_file_id}' does not exist in graph")

        if self._graph.nodes[parent_file_id].get("type") != "file":
            raise ValueError(f"Node '{parent_file_id}' is not a file node")

        code_node_id = f"{parent_file_id}::{node.name}"
        self._graph.add_node(
            code_node_id,
            type=node.type,
            name=node.name,
            start_line=node.start_line,
            end_line=node.end_line,
        )
        self._graph.add_edge(parent_file_id, code_node_id, relationship="CONTAINS")

    def add_dependency(self, source_file_id: str, target_file_id: str) -> None:
        """Add an IMPORTS edge between two nodes.

        Creates a directed edge from source to target with relationship='IMPORTS'.
        This method can create edges between any existing nodes, not just file nodes.
        If the target node does not exist, it is created automatically with no attributes.
        If the edge already exists, it is updated (idempotent operation).

        The source node must exist and is typically a file node (type="file") representing
        the file that contains the import statement. The target node can be:
        - A file node (type="file") for internal project imports
        - An external module node (type="external_module") for third-party/stdlib imports
        - A lazily-created node with no type (will be enriched later by the caller)

        No type validation is performed on either node; only existence of the source
        node is verified.

        Note:
            All IMPORTS edges are identical regardless of whether the target is internal
            or external. There is no separate edge attribute to distinguish import types.
            To determine if an import is external, check the target node's type attribute
            (type="external_module" indicates an external import).

        Args:
            source_file_id: The node ID of the importing file (must exist in graph).
            target_file_id: The node ID being imported (created lazily if missing).

        Returns:
            None

        Raises:
            ValueError: If source_file_id does not exist in graph.

        Lazy Node Creation:
            If target_file_id does not exist in the graph, a minimal node is created
            automatically with only the node ID. This allows adding dependencies to
            external modules or forward references without pre-creating nodes. The
            caller can later enrich the node with attributes (e.g., type="external_module",
            name) using direct graph access or by calling add_file().

        Example:
            >>> manager = GraphManager()
            >>> manager.add_file(FileEntry(Path("src/main.py"), 512, 128))
            >>> # Target node doesn't exist yet - will be created lazily
            >>> manager.add_dependency("src/main.py", "external::os")
            >>> "external::os" in manager.graph.nodes
            True
            >>> manager.graph.edges["src/main.py", "external::os"]["relationship"]
            'IMPORTS'
            >>> # Enrich the lazy node with type attribute
            >>> manager.graph.nodes["external::os"]["type"] = "external_module"
        """
        if source_file_id not in self._graph.nodes:
            raise ValueError(f"Source node '{source_file_id}' not found in graph")

        # Create target node lazily if it doesn't exist
        if target_file_id not in self._graph.nodes:
            self._graph.add_node(target_file_id)

        self._graph.add_edge(source_file_id, target_file_id, relationship="IMPORTS")

    def add_external_module(self, module_name: str) -> str:
        """Add an external module node to the graph.

        Creates a node with ID format 'external::{module_name}' and attributes
        type='external_module' and name=module_name. If a node with the same ID
        already exists, it is NOT modified (deduplication). This method provides
        encapsulation for creating properly-typed external module nodes instead
        of relying on lazy node creation via add_dependency().

        Args:
            module_name: The name of the external module (e.g., 'os', 'requests').

        Returns:
            The node ID in format 'external::{module_name}'.

        Note:
            This method is idempotent and deduplicates nodes by ID. If the node
            already exists (e.g., created lazily via add_dependency()), its
            attributes are preserved and not overwritten. Only missing attributes
            are added.

        Example:
            >>> manager = GraphManager()
            >>> node_id = manager.add_external_module("os")
            >>> node_id
            'external::os'
            >>> manager.graph.nodes["external::os"]["type"]
            'external_module'
            >>> manager.graph.nodes["external::os"]["name"]
            'os'
            >>> # Calling again returns same ID and doesn't create duplicates
            >>> node_id2 = manager.add_external_module("os")
            >>> node_id2 == node_id
            True
            >>> manager.graph.number_of_nodes()
            1
        """
        node_id = f"external::{module_name}"

        # If node already exists, do NOT overwrite attributes
        if node_id in self._graph.nodes:
            # Only add missing attributes, preserve existing ones
            if "type" not in self._graph.nodes[node_id]:
                self._graph.nodes[node_id]["type"] = "external_module"
            if "name" not in self._graph.nodes[node_id]:
                self._graph.nodes[node_id]["name"] = module_name
        else:
            # Create new node with attributes
            self._graph.add_node(
                node_id,
                type="external_module",
                name=module_name,
            )

        return node_id

    def add_project(self, name: str) -> None:
        """Add a project root node (level 0) to the graph.

        Creates a node with ID format 'project::{name}' and attributes
        type='project', level=0, name=name.

        Args:
            name: Project name for display.
        """
        node_id = f"project::{name}"
        self._graph.add_node(
            node_id,
            type="project",
            level=0,
            name=name,
        )

    def add_package(self, package_path: str, project_id: str | None = None) -> None:
        """Add a package node with correct level and parent CONTAINS edge.

        Creates a node with type='package', level=len(path.parts), and name
        set to the last path segment. Automatically connects to parent package
        or project node via CONTAINS edge.

        Args:
            package_path: Relative path like 'src/auth'.
            project_id: Optional project node ID for root-level packages.
                If not provided, searches for an existing project node.
        """
        parts = Path(package_path).parts
        name = parts[-1] if parts else package_path

        self._graph.add_node(
            package_path,
            type="package",
            level=len(parts),
            name=name,
        )

        # Connect to parent
        if len(parts) > 1:
            parent_path = str(Path(*parts[:-1]))
            if parent_path in self._graph.nodes:
                self._graph.add_edge(parent_path, package_path, relationship="CONTAINS")
        else:
            # Root-level package: connect to project node
            if project_id is None:
                # Find existing project node
                for node_id, attrs in self._graph.nodes(data=True):
                    if attrs.get("type") == "project":
                        project_id = node_id
                        break
            if project_id:
                self._graph.add_edge(project_id, package_path, relationship="CONTAINS")

    def build_hierarchy(self, project_name: str) -> None:
        """Build hierarchical structure from existing file nodes.

        Creates project and package nodes, sets level attributes on all nodes,
        and establishes CONTAINS edges forming the hierarchy:
        project -> package -> file -> code.

        Args:
            project_name: Name for the project root node.
        """
        project_id = f"project::{project_name}"
        self.add_project(project_name)

        # Collect all unique directory paths from file nodes
        directories: set[str] = set()
        for node_id, attrs in self._graph.nodes(data=True):
            if attrs.get("type") == "file":
                path = Path(node_id)
                for i in range(1, len(path.parts)):
                    directories.add(str(Path(*path.parts[:i])))

        # Create package nodes sorted by depth for proper parent creation
        for dir_path in sorted(directories, key=lambda p: len(Path(p).parts)):
            self.add_package(dir_path, project_id)

        # Set level on file nodes and connect to parent package
        file_nodes = [nid for nid, a in self._graph.nodes(data=True) if a.get("type") == "file"]
        for node_id in file_nodes:
            path = Path(node_id)
            self._graph.nodes[node_id]["level"] = len(path.parts)

            if len(path.parts) > 1:
                parent_dir = str(Path(*path.parts[:-1]))
                if parent_dir in self._graph.nodes:
                    self._graph.add_edge(parent_dir, node_id, relationship="CONTAINS")
            else:
                self._graph.add_edge(project_id, node_id, relationship="CONTAINS")

        # Set level on code nodes (file_level + 1)
        for node_id, attrs in self._graph.nodes(data=True):
            if attrs.get("type") in ("function", "class"):
                file_id = node_id.split("::")[0]
                if file_id in self._graph.nodes:
                    file_level = self._graph.nodes[file_id].get("level", 0)
                    self._graph.nodes[node_id]["level"] = file_level + 1

    def save(self, path: Path) -> None:
        """Save the graph to a JSON file using orjson.

        Serializes the graph using NetworkX's node_link_data format and writes
        it to the specified path. Parent directories are created automatically
        if they don't exist.

        Args:
            path: Path object specifying where to save the graph JSON file.

        Returns:
            None

        Raises:
            OSError: If the file cannot be written (e.g., permission denied).

        Example:
            >>> manager = GraphManager()
            >>> manager.add_file(FileEntry(Path("src/main.py"), 512, 128))
            >>> manager.save(Path("output/graph.json"))  # Creates output/ if needed
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        data = json_graph.node_link_data(self._graph)
        path.write_bytes(orjson.dumps(data))

    def load(self, path: Path) -> None:
        """Load a graph from a JSON file.

        Deserializes a graph from NetworkX's node_link_data JSON format.
        Preserves the identity of the internal graph object, so external
        references obtained via the graph property remain valid after loading.

        Args:
            path: Path object specifying the JSON file to load.

        Returns:
            None

        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If the file contains syntactically invalid JSON.
            ValueError: If the JSON structure does not conform to node_link_data
                schema (e.g., missing 'nodes' or 'links' keys).

        Example:
            >>> manager = GraphManager()
            >>> graph_ref = manager.graph  # Get reference before load
            >>> manager.load(Path("graph.json"))
            >>> graph_ref is manager.graph  # Same object, updated content
            True
        """
        if not path.exists():
            raise FileNotFoundError(f"Graph file not found: {path}")

        try:
            data = orjson.loads(path.read_bytes())
        except orjson.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in graph file: {e}") from e

        # Create temporary graph from loaded data
        try:
            temp_graph: nx.DiGraph[str] = json_graph.node_link_graph(data, directed=True)
        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(f"Invalid graph schema in file: {e}") from e

        # Clear existing graph while preserving instance identity
        self._graph.clear()

        # Copy all nodes with their attributes
        for node_id, attrs in temp_graph.nodes(data=True):
            self._graph.add_node(node_id, **attrs)

        # Copy all edges with their attributes
        for source, target, attrs in temp_graph.edges(data=True):
            self._graph.add_edge(source, target, **attrs)
