"""Incremental graph update orchestration.

This module provides the GraphUpdater class for applying incremental
changes to an existing code graph without full rebuild.
"""

import logging
import time
from pathlib import Path

from codemap.engine.change_detector import ChangeDetector, ChangeSet
from codemap.graph import GraphManager
from codemap.mapper.engine import ParserEngine
from codemap.mapper.reader import ContentReader, ContentReadError
from codemap.scout.models import FileEntry

logger = logging.getLogger(__name__)


class GraphUpdater:
    """Apply incremental changes to an existing graph.

    Coordinates change detection, node removal, and re-parsing
    to update the graph without full rebuild.

    Thread Safety:
        GraphUpdater instances are NOT thread-safe. Create separate
        instances per thread for parallel processing.

    Example:
        >>> updater = GraphUpdater(graph_manager, detector, parser, reader)
        >>> changes = updater.update(Path("src"))
        >>> print(f"Applied {changes.total_changes} changes")
    """

    def __init__(
        self,
        graph_manager: GraphManager,
        change_detector: ChangeDetector,
        parser: ParserEngine,
        reader: ContentReader,
    ) -> None:
        """Initialize with required dependencies.

        Args:
            graph_manager: Manages the code relationship graph.
            change_detector: Detects file changes since last build.
            parser: Extracts code structure via tree-sitter.
            reader: Reads file content with encoding fallback.
        """
        self._graph_manager = graph_manager
        self._change_detector = change_detector
        self._parser = parser
        self._reader = reader

    def update(self, root: Path) -> ChangeSet:
        """Apply incremental changes to the graph.

        Process:
            1. Detect changes via ChangeDetector
            2. Remove deleted files
            3. Remove and re-add modified files
            4. Add new files
            5. Update build metadata

        Args:
            root: Project root directory.

        Returns:
            ChangeSet that was applied.
        """
        start = time.perf_counter()

        changes = self._change_detector.detect_changes(root)

        if changes.is_empty:
            logger.info("No changes detected")
            self._update_build_metadata(root)
            return changes

        logger.info(
            "Applying changes: %d modified, %d added, %d deleted",
            len(changes.modified),
            len(changes.added),
            len(changes.deleted),
        )

        removed_count = 0
        added_count = 0
        import_count = 0

        # Step 1: Remove deleted files
        for file_path in changes.deleted:
            file_id = str(file_path)
            if file_id in self._graph_manager.graph.nodes:
                self._graph_manager.remove_file(file_id)
                removed_count += 1

        # Step 2: Remove modified files (will be re-added)
        for file_path in changes.modified:
            file_id = str(file_path)
            if file_id in self._graph_manager.graph.nodes:
                self._graph_manager.remove_file(file_id)
                removed_count += 1

        # Step 3: Create file nodes for modified and added files (pass 1)
        files_to_parse: list[Path] = []
        for file_path in list(changes.modified) + list(changes.added):
            node_added = self._add_file_node(root, file_path)
            if node_added:
                added_count += 1
                files_to_parse.append(file_path)

        # Step 4: Parse and resolve imports (pass 2)
        for file_path in files_to_parse:
            counts = self._parse_and_resolve_imports(root, file_path)
            added_count += counts[0]
            import_count += counts[1]

        # Step 5: Update build metadata
        self._update_build_metadata(root)

        elapsed = time.perf_counter() - start
        logger.info(
            "Update stats: %d nodes removed, %d nodes added, %d imports resolved",
            removed_count,
            added_count,
            import_count,
        )
        logger.info("Graph update completed in %.2fs", elapsed)

        return changes

    def _add_file_node(self, root: Path, rel_path: Path) -> bool:
        """Create a file node in the graph without parsing (pass 1).

        Args:
            root: Project root directory.
            rel_path: Relative path of the file to add.

        Returns:
            True if the file node was added, False if file not found.
        """
        abs_path = root / rel_path

        if not abs_path.exists():
            logger.warning("File not found: %s", abs_path)
            return False

        stat = abs_path.stat()
        entry = FileEntry(
            path=rel_path,
            size=stat.st_size,
            token_est=stat.st_size // 4,
        )
        self._graph_manager.add_file(entry)
        return True

    def _parse_and_resolve_imports(self, root: Path, rel_path: Path) -> tuple[int, int]:
        """Parse a file and resolve its imports (pass 2).

        Assumes the file node already exists in the graph.

        Args:
            root: Project root directory.
            rel_path: Relative path of the file to parse.

        Returns:
            Tuple of (code_nodes_added, imports_resolved) counts.
        """
        file_id = str(rel_path)
        abs_path = root / rel_path

        # Non-Python files: skip parsing
        if rel_path.suffix != ".py":
            return (0, 0)

        # Read content
        try:
            content = self._reader.read_file(abs_path)
        except ContentReadError as e:
            logger.warning("Failed to read %s: %s", rel_path, e)
            return (0, 0)

        # Parse file
        try:
            code_nodes = self._parser.parse_file(rel_path, content)
        except ValueError as e:
            logger.warning("Failed to parse %s: %s", rel_path, e)
            return (0, 0)

        # Add code nodes and collect imports
        imports: list[str] = []
        node_count = 0
        for node in code_nodes:
            if node.type == "import":
                imports.append(node.name)
            else:
                self._graph_manager.add_node(file_id, node)
                node_count += 1

        # Resolve imports
        for module_name in imports:
            self._resolve_and_add_import(root, rel_path, module_name)

        return (node_count, len(imports))

    def _resolve_and_add_import(self, root: Path, source_file: Path, import_name: str) -> None:
        """Resolve import name to file path and add dependency edge.

        Uses same resolution strategies as MapBuilder:
        1. Same-directory lookup
        2. Dotted path conversion
        3. Package __init__.py (same dir)
        4. Package __init__.py (from root)
        5. External module (fallback)

        Args:
            root: Project root directory.
            source_file: Relative path to the importing file.
            import_name: Module name from the import statement.
        """
        source_file_id = str(source_file)

        # Strategy 1: Simple name in same directory (e.g., "utils" -> "utils.py")
        same_dir_path = source_file.parent / f"{import_name}.py"
        same_dir_id = str(same_dir_path)
        if same_dir_id in self._graph_manager.graph.nodes:
            self._graph_manager.add_dependency(source_file_id, same_dir_id)
            return

        # Strategy 2: Dotted name as path (e.g., "a.b.c" -> "a/b/c.py")
        dotted_path = Path(import_name.replace(".", "/")).with_suffix(".py")
        dotted_id = str(dotted_path)
        if dotted_id in self._graph_manager.graph.nodes:
            self._graph_manager.add_dependency(source_file_id, dotted_id)
            return

        # Strategy 3: Package import with __init__.py (same directory)
        package_init_same_dir = source_file.parent / import_name / "__init__.py"
        package_same_dir_id = str(package_init_same_dir)
        if package_same_dir_id in self._graph_manager.graph.nodes:
            self._graph_manager.add_dependency(source_file_id, package_same_dir_id)
            return

        # Strategy 4: Package import with __init__.py (from root)
        package_init_root = Path(import_name.replace(".", "/")) / "__init__.py"
        package_root_id = str(package_init_root)
        if package_root_id in self._graph_manager.graph.nodes:
            self._graph_manager.add_dependency(source_file_id, package_root_id)
            return

        # Fallback: treat as external module
        external_node_id = self._graph_manager.add_external_module(import_name)
        self._graph_manager.add_dependency(source_file_id, external_node_id)

    def _update_build_metadata(self, root: Path) -> None:
        """Update build metadata with current commit hash and file hashes.

        Args:
            root: Project root directory.
        """
        new_commit = self._change_detector.get_current_commit(root)
        if new_commit:
            self._graph_manager.build_metadata["commit_hash"] = new_commit

        file_hashes: dict[str, str] = {}
        for node_id, attrs in self._graph_manager.graph.nodes(data=True):
            if attrs.get("type") == "file":
                abs_path = root / node_id
                if abs_path.exists():
                    file_hashes[node_id] = self._change_detector._hash_file(abs_path)
        self._graph_manager.build_metadata["file_hashes"] = file_hashes

    def get_affected_parent_nodes(self, changes: ChangeSet) -> set[str]:
        """Get parent package nodes affected by changes for re-aggregation.

        Args:
            changes: ChangeSet with modified/added/deleted files.

        Returns:
            Set of parent node IDs that need re-aggregation.
        """
        affected: set[str] = set()

        all_paths = list(changes.modified) + list(changes.added) + list(changes.deleted)

        for file_path in all_paths:
            for parent in file_path.parents:
                if parent == Path("."):
                    break
                affected.add(str(parent))

        return affected
