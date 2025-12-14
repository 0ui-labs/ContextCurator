"""MapBuilder for orchestrating code map construction.

This module provides the MapBuilder class which coordinates all components
to build a complete code relationship graph from a project directory.
"""

import logging
from pathlib import Path

from codemap.graph import GraphManager
from codemap.mapper.engine import ParserEngine
from codemap.mapper.reader import ContentReader, ContentReadError
from codemap.scout.walker import FileWalker

logger = logging.getLogger(__name__)


class MapBuilder:
    """Orchestrate code map building from project directory.

    MapBuilder coordinates all components (FileWalker, ContentReader, ParserEngine,
    GraphManager) to create a complete graph representation of a codebase including:
    - File nodes with metadata (size, token_est)
    - Code nodes (functions, classes) with line information
    - CONTAINS edges linking files to their code elements
    - IMPORTS edges representing module dependencies

    Example:
        >>> builder = MapBuilder()
        >>> graph_manager = builder.build(Path("/path/to/project"))
        >>> print(graph_manager.graph_stats)
        {'nodes': 10, 'edges': 15}
    """

    def __init__(self) -> None:
        """Initialize MapBuilder with component instances.

        All components are instantiated during initialization, including the
        GraphManager. The GraphManager is reinitialized on each call to build()
        to ensure a fresh graph for each analysis.
        """
        self._walker = FileWalker()
        self._reader = ContentReader()
        self._parser = ParserEngine()
        self._graph: GraphManager = GraphManager()

    def build(self, root: Path) -> GraphManager:
        """Build complete code map graph from project directory.

        Orchestrates the complete workflow:
        1. Walk directory with FileWalker to discover files
        2. Add file nodes to graph via GraphManager.add_file()
        3. Read and parse each file with ParserEngine
        4. Add code nodes via GraphManager.add_node()
        5. Resolve import dependencies and add IMPORTS edges

        Each call to build() reinitializes the internal GraphManager to ensure
        a fresh graph. The returned GraphManager is the same instance stored
        in self._graph.

        Args:
            root: Root directory of the project to analyze.

        Returns:
            GraphManager instance (self._graph) containing the complete code map graph.

        Raises:
            ValueError: If root does not exist or is not a directory.
        """
        # Input validation
        if not root.exists():
            raise ValueError(f"Path does not exist: {root}")
        if not root.is_dir():
            raise ValueError(f"Path is not a directory: {root}")

        # Reinitialize GraphManager for fresh analysis
        self._graph = GraphManager()

        # Step 1: Walk directory and collect FileEntry objects
        entries = self._walker.walk(root)

        # Step 2: Add file nodes to graph
        for entry in entries:
            self._graph.add_file(entry)

        # Step 3-5: Process each file
        for entry in entries:
            file_id = str(entry.path)
            file_path = root / entry.path

            # Skip non-Python files (parser only supports Python)
            if entry.path.suffix != ".py":
                continue

            # Read file content
            try:
                content = self._reader.read_file(file_path)
            except ContentReadError as e:
                logger.warning("Failed to read file %s: %s", entry.path, e)
                continue

            # Parse file to extract code nodes
            try:
                code_nodes = self._parser.parse_file(entry.path, content)
            except ValueError as e:
                logger.warning("Failed to parse file %s: %s", entry.path, e)
                continue

            # Track imports for this file
            imports: list[str] = []

            # Add code nodes and collect imports
            for node in code_nodes:
                if node.type == "import":
                    # Collect import module names for dependency resolution
                    imports.append(node.name)
                else:
                    # Add function/class nodes with CONTAINS edge
                    self._graph.add_node(file_id, node)

            # Step 5: Resolve imports and add IMPORTS edges
            for module_name in imports:
                self._resolve_and_add_import(root, entry.path, module_name)

        return self._graph

    def _resolve_and_add_import(
        self, root: Path, source_file: Path, import_name: str
    ) -> None:
        """Resolve import name to file path and add dependency edge.

        Attempts to resolve an import module name to an actual file path in the
        scanned project by trying multiple resolution strategies:
        1. Simple module name in same directory (e.g., "utils" -> "utils.py")
        2. Dotted module name as path (e.g., "codemap.scout.walker" -> "codemap/scout/walker.py")
        3. Package import with __init__.py (e.g., "pkg" -> "pkg/__init__.py")

        If a matching file is found in the graph nodes, adds an IMPORTS dependency
        edge from source_file to the resolved target file. Silently skips imports
        that cannot be resolved (external modules or non-existent files).

        Args:
            root: Root directory of the project being analyzed
            source_file: Path to the file containing the import statement (relative to root)
            import_name: Module name from the import (e.g., "utils", "codemap.scout.walker")

        Returns:
            None

        Note:
            Silently skips unresolved imports - external stdlib/third-party modules
            are not added as dependencies.
        """
        # Normalize source_file to string for graph node ID (relative path)
        source_file_id = str(source_file)

        # Strategy 1: Simple name in same directory (e.g., "utils" -> "utils.py")
        same_dir_path = source_file.parent / f"{import_name}.py"
        same_dir_id = str(same_dir_path)
        if same_dir_id in self._graph.graph.nodes:
            self._graph.add_dependency(source_file_id, same_dir_id)
            return

        # Strategy 2: Dotted name as path (e.g., "codemap.scout.walker" -> "codemap/scout/walker.py")
        dotted_path = Path(import_name.replace(".", "/")).with_suffix(".py")
        dotted_id = str(dotted_path)
        if dotted_id in self._graph.graph.nodes:
            self._graph.add_dependency(source_file_id, dotted_id)
            return

        # Strategy 3: Package import with __init__.py (e.g., "pkg" -> "pkg/__init__.py")
        # Try same directory first
        package_init_same_dir = source_file.parent / import_name / "__init__.py"
        package_same_dir_id = str(package_init_same_dir)
        if package_same_dir_id in self._graph.graph.nodes:
            self._graph.add_dependency(source_file_id, package_same_dir_id)
            return

        # Try from root for dotted package names
        package_init_root = Path(import_name.replace(".", "/")) / "__init__.py"
        package_root_id = str(package_init_root)
        if package_root_id in self._graph.graph.nodes:
            self._graph.add_dependency(source_file_id, package_root_id)
            return

        # Import could not be resolved - silently skip (external module or unresolved)
