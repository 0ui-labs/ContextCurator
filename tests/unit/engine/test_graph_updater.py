"""Tests for GraphUpdater.

This module contains comprehensive unit tests for the GraphUpdater class
which orchestrates incremental graph updates by coordinating ChangeDetector,
GraphManager, ParserEngine, and ContentReader.
"""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from codemap.engine.change_detector import ChangeDetector, ChangeSet
from codemap.engine.graph_updater import GraphUpdater
from codemap.graph import GraphManager
from codemap.mapper.engine import ParserEngine
from codemap.mapper.models import CodeNode
from codemap.mapper.reader import ContentReader, ContentReadError
from codemap.scout.models import FileEntry


@pytest.fixture
def graph_manager() -> GraphManager:
    """Fresh GraphManager instance."""
    return GraphManager()


@pytest.fixture
def change_detector(graph_manager: GraphManager) -> MagicMock:
    """Mocked ChangeDetector."""
    mock = MagicMock(spec=ChangeDetector)
    return mock


@pytest.fixture
def parser() -> MagicMock:
    """Mocked ParserEngine."""
    return MagicMock(spec=ParserEngine)


@pytest.fixture
def reader() -> MagicMock:
    """Mocked ContentReader."""
    return MagicMock(spec=ContentReader)


@pytest.fixture
def updater(
    graph_manager: GraphManager,
    change_detector: MagicMock,
    parser: MagicMock,
    reader: MagicMock,
) -> GraphUpdater:
    """GraphUpdater with mocked dependencies."""
    return GraphUpdater(
        graph_manager=graph_manager,
        change_detector=change_detector,
        parser=parser,
        reader=reader,
    )


@pytest.fixture
def populated_graph() -> GraphManager:
    """Graph with existing file and code nodes for update tests."""
    manager = GraphManager()
    manager.add_file(FileEntry(Path("src/auth/login.py"), 100, 25))
    manager.add_node("src/auth/login.py", CodeNode("function", "authenticate", 1, 10))
    manager.add_file(FileEntry(Path("src/utils.py"), 50, 12))
    manager.add_node("src/utils.py", CodeNode("function", "helper", 1, 5))
    manager.add_dependency("src/auth/login.py", "src/utils.py")
    return manager


class TestGraphUpdaterInit:
    """Tests for GraphUpdater constructor."""

    def test_init_accepts_all_dependencies(
        self,
        graph_manager: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """GraphUpdater accepts GraphManager, ChangeDetector, ParserEngine, ContentReader."""
        updater = GraphUpdater(
            graph_manager=graph_manager,
            change_detector=change_detector,
            parser=parser,
            reader=reader,
        )
        assert updater is not None

    def test_init_stores_dependency_references(
        self,
        graph_manager: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """Dependencies are stored as private attributes."""
        updater = GraphUpdater(
            graph_manager=graph_manager,
            change_detector=change_detector,
            parser=parser,
            reader=reader,
        )
        assert updater._graph_manager is graph_manager
        assert updater._change_detector is change_detector
        assert updater._parser is parser
        assert updater._reader is reader


class TestApplyDeletedFiles:
    """Tests for deleted file processing in update()."""

    def test_deleted_file_removed_from_graph(
        self,
        populated_graph: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """Deleted files are removed via GraphManager.remove_file()."""
        changes = ChangeSet(deleted=[Path("src/utils.py")])
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        updater = GraphUpdater(populated_graph, change_detector, parser, reader)
        updater.update(Path("/project"))

        assert "src/utils.py" not in populated_graph.graph.nodes

    def test_deleted_file_children_removed(
        self,
        populated_graph: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """Code nodes (CONTAINS) are removed with the file."""
        changes = ChangeSet(deleted=[Path("src/auth/login.py")])
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        updater = GraphUpdater(populated_graph, change_detector, parser, reader)
        updater.update(Path("/project"))

        assert "src/auth/login.py" not in populated_graph.graph.nodes
        assert "src/auth/login.py::authenticate" not in populated_graph.graph.nodes

    def test_deleted_file_import_edges_removed(
        self,
        populated_graph: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """IMPORTS edges to/from deleted file are removed."""
        changes = ChangeSet(deleted=[Path("src/utils.py")])
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        updater = GraphUpdater(populated_graph, change_detector, parser, reader)
        updater.update(Path("/project"))

        assert not populated_graph.graph.has_edge("src/auth/login.py", "src/utils.py")

    def test_deleted_nonexistent_file_skipped(
        self,
        populated_graph: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """Non-existent files in deleted list are skipped without error."""
        changes = ChangeSet(deleted=[Path("src/nonexistent.py")])
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        updater = GraphUpdater(populated_graph, change_detector, parser, reader)
        # Should not raise
        result = updater.update(Path("/project"))
        assert result is changes


class TestApplyModifiedFiles:
    """Tests for modified file processing in update()."""

    def test_modified_file_old_nodes_removed(
        self,
        populated_graph: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """Old code nodes are removed via remove_file() for modified files."""
        changes = ChangeSet(modified=[Path("src/utils.py")])
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        # Parser returns empty list (no new nodes)
        parser.parse_file.return_value = []

        updater = GraphUpdater(populated_graph, change_detector, parser, reader)

        # The old node should exist before
        assert "src/utils.py::helper" in populated_graph.graph.nodes

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat", return_value=MagicMock(st_size=50)),
        ):
            reader.read_file.return_value = "# empty"
            updater.update(Path("/project"))

        # Old code node should be gone
        assert "src/utils.py::helper" not in populated_graph.graph.nodes

    def test_modified_file_reparsed(
        self,
        populated_graph: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """ParserEngine.parse_file() is called for modified files."""
        changes = ChangeSet(modified=[Path("src/utils.py")])
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        parser.parse_file.return_value = []
        reader.read_file.return_value = "def new_helper(): pass"

        updater = GraphUpdater(populated_graph, change_detector, parser, reader)

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat", return_value=MagicMock(st_size=50)),
        ):
            updater.update(Path("/project"))

        parser.parse_file.assert_called_once_with(Path("src/utils.py"), "def new_helper(): pass")

    def test_modified_file_new_nodes_added(
        self,
        populated_graph: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """New code nodes are added via add_node() after re-parsing."""
        changes = ChangeSet(modified=[Path("src/utils.py")])
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        new_node = CodeNode("function", "new_helper", 1, 8)
        parser.parse_file.return_value = [new_node]
        reader.read_file.return_value = "def new_helper(): pass"

        updater = GraphUpdater(populated_graph, change_detector, parser, reader)

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat", return_value=MagicMock(st_size=50)),
        ):
            updater.update(Path("/project"))

        assert "src/utils.py::new_helper" in populated_graph.graph.nodes

    def test_modified_file_imports_reresolved(
        self,
        populated_graph: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """Import edges are re-created for modified files."""
        changes = ChangeSet(modified=[Path("src/utils.py")])
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        import_node = CodeNode("import", "os", 1, 1)
        parser.parse_file.return_value = [import_node]
        reader.read_file.return_value = "import os"

        updater = GraphUpdater(populated_graph, change_detector, parser, reader)

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat", return_value=MagicMock(st_size=50)),
        ):
            updater.update(Path("/project"))

        # External module node should be created for 'os'
        assert "external::os" in populated_graph.graph.nodes
        assert populated_graph.graph.has_edge("src/utils.py", "external::os")

    def test_modified_file_read_error_logged(
        self,
        populated_graph: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """ContentReadError is logged and update continues."""
        changes = ChangeSet(modified=[Path("src/utils.py")])
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        reader.read_file.side_effect = ContentReadError("Binary file")

        updater = GraphUpdater(populated_graph, change_detector, parser, reader)

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat", return_value=MagicMock(st_size=50)),
            caplog.at_level(logging.WARNING),
        ):
            result = updater.update(Path("/project"))

        assert result is changes
        assert "Failed to read" in caplog.text

    def test_modified_file_parse_error_logged(
        self,
        populated_graph: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """ValueError from parser is logged and update continues."""
        changes = ChangeSet(modified=[Path("src/utils.py")])
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        reader.read_file.return_value = "invalid content"
        parser.parse_file.side_effect = ValueError("Parse error")

        updater = GraphUpdater(populated_graph, change_detector, parser, reader)

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat", return_value=MagicMock(st_size=50)),
            caplog.at_level(logging.WARNING),
        ):
            result = updater.update(Path("/project"))

        assert result is changes
        assert "Failed to parse" in caplog.text


class TestApplyAddedFiles:
    """Tests for added file processing in update()."""

    def test_added_file_creates_file_node(
        self,
        graph_manager: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """New file node is created via add_file() for added files."""
        changes = ChangeSet(added=[Path("src/new_module.py")])
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        parser.parse_file.return_value = []
        reader.read_file.return_value = "# new module"

        updater = GraphUpdater(graph_manager, change_detector, parser, reader)

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat", return_value=MagicMock(st_size=200)),
        ):
            updater.update(Path("/project"))

        assert "src/new_module.py" in graph_manager.graph.nodes
        assert graph_manager.graph.nodes["src/new_module.py"]["type"] == "file"

    def test_added_file_code_nodes_added(
        self,
        graph_manager: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """Code nodes from parsing are added for new files."""
        changes = ChangeSet(added=[Path("src/new_module.py")])
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        func_node = CodeNode("function", "new_func", 1, 5)
        parser.parse_file.return_value = [func_node]
        reader.read_file.return_value = "def new_func(): pass"

        updater = GraphUpdater(graph_manager, change_detector, parser, reader)

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat", return_value=MagicMock(st_size=200)),
        ):
            updater.update(Path("/project"))

        assert "src/new_module.py::new_func" in graph_manager.graph.nodes

    def test_added_file_imports_resolved(
        self,
        graph_manager: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """Imports are resolved via _resolve_and_add_import() for added files."""
        changes = ChangeSet(added=[Path("src/new_module.py")])
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        import_node = CodeNode("import", "json", 1, 1)
        parser.parse_file.return_value = [import_node]
        reader.read_file.return_value = "import json"

        updater = GraphUpdater(graph_manager, change_detector, parser, reader)

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat", return_value=MagicMock(st_size=200)),
        ):
            updater.update(Path("/project"))

        assert "external::json" in graph_manager.graph.nodes
        assert graph_manager.graph.has_edge("src/new_module.py", "external::json")

    def test_added_non_python_file_skips_parsing(
        self,
        graph_manager: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """Non-Python files are added as file nodes but not parsed."""
        changes = ChangeSet(added=[Path("docs/readme.md")])
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        updater = GraphUpdater(graph_manager, change_detector, parser, reader)

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat", return_value=MagicMock(st_size=500)),
        ):
            updater.update(Path("/project"))

        assert "docs/readme.md" in graph_manager.graph.nodes
        assert graph_manager.graph.nodes["docs/readme.md"]["type"] == "file"
        parser.parse_file.assert_not_called()
        reader.read_file.assert_not_called()

    def test_added_nonexistent_file_skipped(
        self,
        graph_manager: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """Non-existent files in added list are skipped without error."""
        changes = ChangeSet(added=[Path("src/ghost.py")])
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        updater = GraphUpdater(graph_manager, change_detector, parser, reader)

        with patch.object(Path, "exists", return_value=False):
            result = updater.update(Path("/project"))

        assert result is changes
        assert "src/ghost.py" not in graph_manager.graph.nodes


class TestUpdateReturnValue:
    """Tests for update() return value."""

    def test_update_returns_applied_changeset(
        self, updater: GraphUpdater, change_detector: MagicMock
    ) -> None:
        """update() returns the applied ChangeSet."""
        changes = ChangeSet(
            modified=[Path("a.py")],
            added=[Path("b.py")],
            deleted=[Path("c.py")],
        )
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        with patch.object(Path, "exists", return_value=False):
            result = updater.update(Path("/project"))

        assert result is changes

    def test_update_with_no_changes_returns_empty_changeset(
        self, updater: GraphUpdater, change_detector: MagicMock
    ) -> None:
        """Empty ChangeSet is returned when no changes detected."""
        empty_changes = ChangeSet()
        change_detector.detect_changes.return_value = empty_changes

        result = updater.update(Path("/project"))

        assert result is empty_changes
        assert result.is_empty


class TestBuildMetadataUpdate:
    """Tests for build metadata updates after update()."""

    def test_update_stores_new_commit_hash(
        self,
        graph_manager: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """After update, commit_hash is updated in build_metadata."""
        changes = ChangeSet(added=[Path("src/new.py")])
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = "abc123def456"

        updater = GraphUpdater(graph_manager, change_detector, parser, reader)

        with patch.object(Path, "exists", return_value=False):
            updater.update(Path("/project"))

        assert graph_manager.build_metadata["commit_hash"] == "abc123def456"

    def test_update_stores_file_hashes(
        self,
        graph_manager: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """File hashes are stored in build_metadata['file_hashes']."""
        # Add a file to graph first
        graph_manager.add_file(FileEntry(Path("src/main.py"), 100, 25))

        changes = ChangeSet()
        changes.modified = []
        changes.added = [Path("src/main.py")]
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None
        change_detector._hash_file.return_value = "fakehash123"

        updater = GraphUpdater(graph_manager, change_detector, parser, reader)

        # File exists on disk for _add_file but we already added it above
        # For _update_build_metadata, the file node is already in graph
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat", return_value=MagicMock(st_size=100)),
        ):
            reader.read_file.return_value = "# content"
            parser.parse_file.return_value = []
            updater.update(Path("/project"))

        assert "file_hashes" in graph_manager.build_metadata
        assert "src/main.py" in graph_manager.build_metadata["file_hashes"]

    def test_update_without_git_skips_commit_hash(
        self,
        graph_manager: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """When get_current_commit() returns None, commit_hash is not set."""
        changes = ChangeSet()
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        updater = GraphUpdater(graph_manager, change_detector, parser, reader)
        updater.update(Path("/project"))

        assert "commit_hash" not in graph_manager.build_metadata


class TestUpdateOrchestration:
    """Tests for update() orchestration behavior."""

    def test_update_processes_in_correct_order(
        self,
        populated_graph: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """Deleted -> Modified -> Added order is enforced."""
        call_order: list[str] = []

        original_remove_file = populated_graph.remove_file

        def track_remove_file(file_id: str) -> None:
            call_order.append(f"remove:{file_id}")
            original_remove_file(file_id)

        original_add_file = populated_graph.add_file

        def track_add_file(entry: FileEntry) -> None:
            call_order.append(f"add:{entry.path}")
            original_add_file(entry)

        populated_graph.remove_file = track_remove_file  # type: ignore[assignment]
        populated_graph.add_file = track_add_file  # type: ignore[assignment]

        changes = ChangeSet(
            deleted=[Path("src/utils.py")],
            modified=[Path("src/auth/login.py")],
            added=[Path("src/new.py")],
        )
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        parser.parse_file.return_value = []
        reader.read_file.return_value = "# content"

        updater = GraphUpdater(populated_graph, change_detector, parser, reader)

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat", return_value=MagicMock(st_size=50)),
        ):
            updater.update(Path("/project"))

        # Verify order: delete first, then modified remove, then adds
        assert call_order[0] == "remove:src/utils.py"
        assert call_order[1] == "remove:src/auth/login.py"
        # add_file calls follow (for modified re-add and new file)
        add_calls = [c for c in call_order if c.startswith("add:")]
        assert len(add_calls) >= 2

    def test_update_calls_change_detector(
        self, updater: GraphUpdater, change_detector: MagicMock
    ) -> None:
        """ChangeDetector.detect_changes() is called with root."""
        empty_changes = ChangeSet()
        change_detector.detect_changes.return_value = empty_changes

        root = Path("/my/project")
        updater.update(root)

        change_detector.detect_changes.assert_called_once_with(root)

    def test_update_logs_performance_metrics(
        self,
        updater: GraphUpdater,
        change_detector: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Update duration is logged."""
        changes = ChangeSet(added=[Path("src/a.py")])
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        with patch.object(Path, "exists", return_value=False), caplog.at_level(logging.INFO):
            updater.update(Path("/project"))

        assert "completed in" in caplog.text


class TestImportResolution:
    """Tests for import resolution in _resolve_and_add_import()."""

    def test_import_resolution_reuses_mapbuilder_logic(
        self,
        graph_manager: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """_resolve_and_add_import() is called for imports."""
        # Set up graph with existing file that can be imported
        graph_manager.add_file(FileEntry(Path("src/utils.py"), 50, 12))

        changes = ChangeSet(added=[Path("src/main.py")])
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        import_node = CodeNode("import", "utils", 1, 1)
        parser.parse_file.return_value = [import_node]
        reader.read_file.return_value = "import utils"

        updater = GraphUpdater(graph_manager, change_detector, parser, reader)

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat", return_value=MagicMock(st_size=100)),
        ):
            updater.update(Path("/project"))

        # utils.py is in same dir as main.py -> resolved to src/utils.py
        assert graph_manager.graph.has_edge("src/main.py", "src/utils.py")

    def test_external_imports_create_external_nodes(
        self,
        graph_manager: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """External imports create external:: nodes."""
        changes = ChangeSet(added=[Path("src/main.py")])
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        import_node = CodeNode("import", "requests", 1, 1)
        parser.parse_file.return_value = [import_node]
        reader.read_file.return_value = "import requests"

        updater = GraphUpdater(graph_manager, change_detector, parser, reader)

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat", return_value=MagicMock(st_size=100)),
        ):
            updater.update(Path("/project"))

        assert "external::requests" in graph_manager.graph.nodes
        assert graph_manager.graph.nodes["external::requests"]["type"] == "external_module"

    def test_package_init_same_dir_import_resolved(
        self,
        graph_manager: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """Package __init__.py in same directory resolves import."""
        # Pre-populate graph with package __init__.py in same dir
        graph_manager.add_file(FileEntry(Path("src/pkg/__init__.py"), 50, 12))

        changes = ChangeSet(added=[Path("src/main.py")])
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        import_node = CodeNode("import", "pkg", 1, 1)
        parser.parse_file.return_value = [import_node]
        reader.read_file.return_value = "import pkg"

        updater = GraphUpdater(graph_manager, change_detector, parser, reader)

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat", return_value=MagicMock(st_size=100)),
        ):
            updater.update(Path("/project"))

        assert graph_manager.graph.has_edge("src/main.py", "src/pkg/__init__.py")

    def test_package_init_from_root_import_resolved(
        self,
        graph_manager: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """Package __init__.py from root resolves dotted import."""
        # Pre-populate graph with package __init__.py from root
        graph_manager.add_file(FileEntry(Path("codemap/scout/__init__.py"), 50, 12))

        changes = ChangeSet(added=[Path("src/main.py")])
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        import_node = CodeNode("import", "codemap.scout", 1, 1)
        parser.parse_file.return_value = [import_node]
        reader.read_file.return_value = "import codemap.scout"

        updater = GraphUpdater(graph_manager, change_detector, parser, reader)

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat", return_value=MagicMock(st_size=100)),
        ):
            updater.update(Path("/project"))

        assert graph_manager.graph.has_edge("src/main.py", "codemap/scout/__init__.py")

    def test_internal_imports_create_edges(
        self,
        graph_manager: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """Internal imports create IMPORTS edges to file nodes."""
        # Pre-populate graph with target file
        graph_manager.add_file(FileEntry(Path("codemap/scout/walker.py"), 200, 50))

        changes = ChangeSet(added=[Path("src/main.py")])
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        import_node = CodeNode("import", "codemap.scout.walker", 1, 1)
        parser.parse_file.return_value = [import_node]
        reader.read_file.return_value = "from codemap.scout import walker"

        updater = GraphUpdater(graph_manager, change_detector, parser, reader)

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat", return_value=MagicMock(st_size=100)),
        ):
            updater.update(Path("/project"))

        # Dotted path resolution: codemap.scout.walker -> codemap/scout/walker.py
        assert graph_manager.graph.has_edge("src/main.py", "codemap/scout/walker.py")


class TestGetAffectedParentNodes:
    """Tests for get_affected_parent_nodes()."""

    def test_returns_parent_packages_for_changed_files(
        self,
        graph_manager: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """Parent package nodes of changed files are returned."""
        # Build hierarchy with package nodes
        graph_manager.add_file(FileEntry(Path("src/auth/login.py"), 100, 25))
        graph_manager.build_hierarchy("TestProject")

        updater = GraphUpdater(graph_manager, change_detector, parser, reader)

        changes = ChangeSet(modified=[Path("src/auth/login.py")])
        affected = updater.get_affected_parent_nodes(changes)

        assert "src/auth" in affected

    def test_returns_empty_set_for_empty_changeset(
        self,
        graph_manager: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """Empty set returned for empty ChangeSet."""
        updater = GraphUpdater(graph_manager, change_detector, parser, reader)

        changes = ChangeSet()
        affected = updater.get_affected_parent_nodes(changes)

        assert affected == set()

    def test_root_level_files_excluded_from_parents(
        self,
        graph_manager: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """Files at root level (parent='.') are not included as parent nodes."""
        updater = GraphUpdater(graph_manager, change_detector, parser, reader)

        changes = ChangeSet(modified=[Path("setup.py")])
        affected = updater.get_affected_parent_nodes(changes)

        assert affected == set()

    def test_collects_parents_from_all_change_types(
        self,
        graph_manager: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """Parents from modified, added, and deleted files are all collected."""
        graph_manager.add_file(FileEntry(Path("src/auth/login.py"), 100, 25))
        graph_manager.add_file(FileEntry(Path("src/utils/helpers.py"), 50, 12))
        graph_manager.build_hierarchy("TestProject")

        updater = GraphUpdater(graph_manager, change_detector, parser, reader)

        changes = ChangeSet(
            modified=[Path("src/auth/login.py")],
            added=[Path("src/utils/helpers.py")],
            deleted=[Path("src/config/settings.py")],
        )
        affected = updater.get_affected_parent_nodes(changes)

        assert "src/auth" in affected
        assert "src/utils" in affected
        # deleted file's parent is also included (even if not in graph)
        assert "src/config" in affected
        # Common ancestor 'src' is also included via full parent chain
        assert "src" in affected

    def test_multi_level_paths_include_all_ancestors(
        self,
        graph_manager: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """Deep paths like src/a/b/c.py include all ancestors up to root."""
        updater = GraphUpdater(graph_manager, change_detector, parser, reader)

        changes = ChangeSet(modified=[Path("src/a/b/c.py")])
        affected = updater.get_affected_parent_nodes(changes)

        assert "src/a/b" in affected
        assert "src/a" in affected
        assert "src" in affected
        assert "." not in affected


class TestBuildMetadataOnEmptyChangeSet:
    """Tests for build metadata update on empty ChangeSet (Comment 1)."""

    def test_empty_changeset_updates_commit_hash(
        self,
        graph_manager: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """commit_hash is updated even when no files changed."""
        empty_changes = ChangeSet()
        change_detector.detect_changes.return_value = empty_changes
        change_detector.get_current_commit.return_value = "newcommit789"

        updater = GraphUpdater(graph_manager, change_detector, parser, reader)
        updater.update(Path("/project"))

        assert graph_manager.build_metadata["commit_hash"] == "newcommit789"

    def test_empty_changeset_updates_file_hashes(
        self,
        graph_manager: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """file_hashes is updated even when no files changed."""
        graph_manager.add_file(FileEntry(Path("src/existing.py"), 100, 25))

        empty_changes = ChangeSet()
        change_detector.detect_changes.return_value = empty_changes
        change_detector.get_current_commit.return_value = None
        change_detector._hash_file.return_value = "hash_abc"

        updater = GraphUpdater(graph_manager, change_detector, parser, reader)

        with patch.object(Path, "exists", return_value=True):
            updater.update(Path("/project"))

        assert "file_hashes" in graph_manager.build_metadata
        assert "src/existing.py" in graph_manager.build_metadata["file_hashes"]


class TestTwoPassImportResolution:
    """Tests for two-pass file processing (Comment 3)."""

    def test_imports_between_new_files_resolved_internally(
        self,
        graph_manager: GraphManager,
        change_detector: MagicMock,
        parser: MagicMock,
        reader: MagicMock,
    ) -> None:
        """Imports between simultaneously added files resolve as internal, not external."""
        changes = ChangeSet(
            added=[Path("src/api.py"), Path("src/helpers.py")],
        )
        change_detector.detect_changes.return_value = changes
        change_detector.get_current_commit.return_value = None

        def mock_parse(path: Path, content: str) -> list[CodeNode]:
            if path == Path("src/api.py"):
                return [CodeNode("import", "helpers", 1, 1)]
            return [CodeNode("function", "do_stuff", 1, 5)]

        parser.parse_file.side_effect = mock_parse
        reader.read_file.return_value = "# content"

        updater = GraphUpdater(graph_manager, change_detector, parser, reader)

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat", return_value=MagicMock(st_size=100)),
        ):
            updater.update(Path("/project"))

        # helpers.py should resolve as internal (same dir), not external
        assert graph_manager.graph.has_edge("src/api.py", "src/helpers.py")
        assert "external::helpers" not in graph_manager.graph.nodes
