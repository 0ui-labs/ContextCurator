# Phase 19: Inkrementelles Graph-Update

> **Ziel:** Nur geänderte Dateien re-analysieren, nicht kompletter Rebuild.
> Ein typischer Commit ändert 1-5 Dateien - warum 1000 Dateien neu parsen?

---

## Problem

Aktuell gibt es nur `MapBuilder.build()`, das einen kompletten Graph-Rebuild macht:

```python
# Jeder Aufruf: Alle Dateien neu scannen, parsen, Graph neu bauen
graph_manager = builder.build(Path("src"))
```

Bei einem Projekt mit 500 Dateien dauert ein Build ~30 Sekunden.
Nach einem kleinen Fix in einer Datei: wieder 30 Sekunden.

## Lösung

Inkrementelles Update, das nur betroffene Teile neu verarbeitet:

```python
# Initial: Voller Build + Graph speichern
graph_manager = builder.build(Path("src"))
graph_manager.save(Path(".codemap/graph.json"))

# Nach Änderungen: Nur Delta verarbeiten
updater = GraphUpdater(graph_manager)
changes = updater.detect_changes(Path("src"))
# → ChangedFiles: ["src/auth/login.py"], NewFiles: [], DeletedFiles: []

updater.apply_changes(changes)
# → Nur login.py neu parsen, alte Nodes entfernen, neue einfügen
```

---

## Observations

Nach Analyse des bestehenden Codes:

- **MapBuilder.build() ist stateless:** Jeder Aufruf erstellt neuen GraphManager
- **GraphManager hat keine Update-Methoden:** Nur `add_*`, kein `remove_*` oder `update_*`
- **Node-IDs sind deterministisch:** `src/auth/login.py::authenticate_user` - identisch bei Rebuild
- **FileWalker liefert FileEntry:** Mit `path`, `size`, `token_est` - kein Timestamp/Hash
- **Keine Persistenz-Metadata:** Graph speichert keine Build-Timestamps oder File-Hashes
- **Git ist vorhanden:** Projekt ist Git-Repo, `git diff` liefert Changes

## Approach

### 1. ChangeDetector - Erkennt was sich geändert hat

```python
@dataclass
class ChangeSet:
    """Detected changes since last build."""
    modified: list[Path]   # Inhalt geändert
    added: list[Path]      # Neue Dateien
    deleted: list[Path]    # Gelöschte Dateien
    base_commit: str       # Commit-Hash des letzten Builds
```

Strategien zur Change-Detection:
1. **Git-basiert (primär):** `git diff --name-status <base_commit>`
2. **Hash-basiert (Fallback):** Gespeicherte File-Hashes vergleichen
3. **Timestamp-basiert (schnell):** mtime > last_build_time

### 2. GraphManager erweitern - Remove-Operationen

```python
def remove_file(self, file_id: str) -> None:
    """Entfernt File-Node und alle Kind-Nodes (code elements)."""

def remove_node(self, node_id: str) -> None:
    """Entfernt einzelnen Node mit allen Edges."""
```

### 3. GraphUpdater - Orchestriert inkrementelles Update

```python
class GraphUpdater:
    """Applies incremental changes to existing graph."""

    def __init__(
        self,
        graph_manager: GraphManager,
        change_detector: ChangeDetector,
        parser: ParserEngine,
        reader: ContentReader,
    ) -> None: ...

    def update(self, root: Path) -> ChangeSet:
        """
        1. Detect changes via ChangeDetector
        2. Remove deleted files from graph
        3. Remove modified files from graph
        4. Re-add modified files (fresh parse)
        5. Add new files
        6. Return applied ChangeSet
        """
```

### 4. Build-Metadata persistieren

```python
@dataclass
class BuildMetadata:
    """Stored with graph for incremental updates."""
    build_time: datetime
    commit_hash: str | None
    file_hashes: dict[str, str]  # path → content hash
```

---

## Implementation Steps

### Phase 1: RED - Failing Tests schreiben

#### 1.1 ChangeDetector Tests

Neue Datei: `tests/unit/engine/test_change_detector.py`

```python
"""Tests for ChangeDetector."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from codemap.engine.change_detector import ChangeDetector, ChangeSet


class TestChangeDetectorInit:
    """Tests for ChangeDetector initialization."""

    def test_init_with_graph_manager(self) -> None:
        """ChangeDetector accepts GraphManager with build metadata."""
        manager = MagicMock()
        manager.build_metadata = {"commit_hash": "abc123"}

        detector = ChangeDetector(manager)
        assert detector._graph_manager is manager


class TestGitBasedDetection:
    """Tests for Git-based change detection."""

    def test_detect_changes_uses_git_diff(self, tmp_path: Path) -> None:
        """detect_changes() uses git diff against stored commit hash."""
        manager = MagicMock()
        manager.build_metadata = {"commit_hash": "abc123"}

        detector = ChangeDetector(manager)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="M\tsrc/auth/login.py\nA\tsrc/api/new.py\nD\tsrc/old.py\n"
            )

            changes = detector.detect_changes(tmp_path)

            mock_run.assert_called_once()
            assert "git" in mock_run.call_args[0][0]
            assert "diff" in mock_run.call_args[0][0]

    def test_detect_modified_files(self, tmp_path: Path) -> None:
        """Modified files (M status) are in changes.modified."""
        manager = MagicMock()
        manager.build_metadata = {"commit_hash": "abc123"}
        detector = ChangeDetector(manager)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="M\tsrc/auth/login.py\n"
            )

            changes = detector.detect_changes(tmp_path)

            assert Path("src/auth/login.py") in changes.modified

    def test_detect_added_files(self, tmp_path: Path) -> None:
        """Added files (A status) are in changes.added."""
        manager = MagicMock()
        manager.build_metadata = {"commit_hash": "abc123"}
        detector = ChangeDetector(manager)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="A\tsrc/api/new.py\n"
            )

            changes = detector.detect_changes(tmp_path)

            assert Path("src/api/new.py") in changes.added

    def test_detect_deleted_files(self, tmp_path: Path) -> None:
        """Deleted files (D status) are in changes.deleted."""
        manager = MagicMock()
        manager.build_metadata = {"commit_hash": "abc123"}
        detector = ChangeDetector(manager)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="D\tsrc/old.py\n"
            )

            changes = detector.detect_changes(tmp_path)

            assert Path("src/old.py") in changes.deleted

    def test_detect_renamed_files_as_add_delete(self, tmp_path: Path) -> None:
        """Renamed files (R status) become add + delete."""
        manager = MagicMock()
        manager.build_metadata = {"commit_hash": "abc123"}
        detector = ChangeDetector(manager)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="R100\tsrc/old_name.py\tsrc/new_name.py\n"
            )

            changes = detector.detect_changes(tmp_path)

            assert Path("src/old_name.py") in changes.deleted
            assert Path("src/new_name.py") in changes.added

    def test_no_base_commit_returns_full_scan(self, tmp_path: Path) -> None:
        """Without base commit, all files are returned as 'added'."""
        manager = MagicMock()
        manager.build_metadata = {}  # No commit hash
        manager.graph.nodes.return_value = []

        detector = ChangeDetector(manager)

        # Create test file
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "test.py").write_text("print('hello')")

        changes = detector.detect_changes(tmp_path)

        # Without base commit, should scan filesystem
        assert len(changes.added) > 0 or len(changes.modified) > 0


class TestHashBasedDetection:
    """Tests for hash-based change detection (Git fallback)."""

    def test_fallback_to_hash_when_not_git_repo(self, tmp_path: Path) -> None:
        """Uses hash comparison when directory is not a git repo."""
        manager = MagicMock()
        manager.build_metadata = {
            "file_hashes": {"src/test.py": "old_hash"}
        }

        detector = ChangeDetector(manager)

        # Create file with different content
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "test.py").write_text("new content")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("git not found")

            changes = detector.detect_changes(tmp_path)

            # Should detect modification via hash mismatch
            assert Path("src/test.py") in changes.modified


class TestChangeSetDataclass:
    """Tests for ChangeSet dataclass."""

    def test_changeset_empty_by_default(self) -> None:
        """ChangeSet initializes with empty lists."""
        cs = ChangeSet()

        assert cs.modified == []
        assert cs.added == []
        assert cs.deleted == []
        assert cs.base_commit is None

    def test_changeset_is_empty_property(self) -> None:
        """is_empty returns True when no changes."""
        cs = ChangeSet()
        assert cs.is_empty

        cs.modified.append(Path("test.py"))
        assert not cs.is_empty

    def test_changeset_total_count(self) -> None:
        """total_changes returns sum of all change types."""
        cs = ChangeSet(
            modified=[Path("a.py")],
            added=[Path("b.py"), Path("c.py")],
            deleted=[Path("d.py")],
        )

        assert cs.total_changes == 4
```

#### 1.2 GraphManager Remove-Operations Tests

Datei: `tests/unit/graph/test_manager.py` (erweitern)

```python
class TestRemoveOperations:
    """Tests for node removal operations."""

    def test_remove_node_removes_from_graph(self, manager: GraphManager) -> None:
        """remove_node() removes the node from the graph."""
        manager.add_file(FileEntry(Path("src/test.py"), 100, 25))
        manager.add_node("src/test.py", CodeNode("function", "func", 1, 10))

        manager.remove_node("src/test.py::func")

        assert "src/test.py::func" not in manager.graph.nodes

    def test_remove_node_removes_incoming_edges(self, manager: GraphManager) -> None:
        """remove_node() removes edges pointing TO the node."""
        manager.add_file(FileEntry(Path("src/test.py"), 100, 25))
        manager.add_node("src/test.py", CodeNode("function", "func", 1, 10))

        # Verify edge exists
        assert manager.graph.has_edge("src/test.py", "src/test.py::func")

        manager.remove_node("src/test.py::func")

        # Edge should be gone (along with node)
        assert not manager.graph.has_edge("src/test.py", "src/test.py::func")

    def test_remove_node_removes_outgoing_edges(self, manager: GraphManager) -> None:
        """remove_node() removes edges pointing FROM the node."""
        manager.add_file(FileEntry(Path("src/a.py"), 100, 25))
        manager.add_file(FileEntry(Path("src/b.py"), 100, 25))
        manager.add_dependency("src/a.py", "src/b.py")

        manager.remove_node("src/a.py")

        assert not manager.graph.has_edge("src/a.py", "src/b.py")

    def test_remove_node_nonexistent_raises(self, manager: GraphManager) -> None:
        """remove_node() raises ValueError for non-existent node."""
        with pytest.raises(ValueError, match="not found"):
            manager.remove_node("nonexistent")

    def test_remove_file_removes_file_and_children(self, manager: GraphManager) -> None:
        """remove_file() removes file node and all contained code nodes."""
        manager.add_file(FileEntry(Path("src/test.py"), 100, 25))
        manager.add_node("src/test.py", CodeNode("function", "func1", 1, 10))
        manager.add_node("src/test.py", CodeNode("function", "func2", 11, 20))
        manager.add_node("src/test.py", CodeNode("class", "MyClass", 21, 50))

        manager.remove_file("src/test.py")

        assert "src/test.py" not in manager.graph.nodes
        assert "src/test.py::func1" not in manager.graph.nodes
        assert "src/test.py::func2" not in manager.graph.nodes
        assert "src/test.py::MyClass" not in manager.graph.nodes

    def test_remove_file_preserves_other_files(self, manager: GraphManager) -> None:
        """remove_file() does not affect other file nodes."""
        manager.add_file(FileEntry(Path("src/a.py"), 100, 25))
        manager.add_file(FileEntry(Path("src/b.py"), 100, 25))
        manager.add_node("src/a.py", CodeNode("function", "func_a", 1, 10))
        manager.add_node("src/b.py", CodeNode("function", "func_b", 1, 10))

        manager.remove_file("src/a.py")

        assert "src/b.py" in manager.graph.nodes
        assert "src/b.py::func_b" in manager.graph.nodes

    def test_remove_file_removes_import_edges(self, manager: GraphManager) -> None:
        """remove_file() removes IMPORTS edges to/from the file."""
        manager.add_file(FileEntry(Path("src/a.py"), 100, 25))
        manager.add_file(FileEntry(Path("src/b.py"), 100, 25))
        manager.add_dependency("src/a.py", "src/b.py")  # a imports b

        manager.remove_file("src/a.py")

        # Edge should be gone
        assert not manager.graph.has_edge("src/a.py", "src/b.py")
        # But b.py should still exist
        assert "src/b.py" in manager.graph.nodes

    def test_remove_file_not_a_file_raises(self, manager: GraphManager) -> None:
        """remove_file() raises ValueError if node is not type=file."""
        manager.add_file(FileEntry(Path("src/test.py"), 100, 25))
        manager.add_node("src/test.py", CodeNode("function", "func", 1, 10))

        with pytest.raises(ValueError, match="not a file node"):
            manager.remove_file("src/test.py::func")
```

#### 1.3 GraphUpdater Tests

Neue Datei: `tests/unit/engine/test_graph_updater.py`

```python
"""Tests for GraphUpdater."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from codemap.engine.graph_updater import GraphUpdater
from codemap.engine.change_detector import ChangeSet
from codemap.graph import GraphManager
from codemap.mapper.engine import ParserEngine
from codemap.mapper.reader import ContentReader


@pytest.fixture
def populated_graph() -> GraphManager:
    """Graph with existing file and code nodes."""
    manager = GraphManager()
    manager.add_file(FileEntry(Path("src/auth/login.py"), 100, 25))
    manager.add_node("src/auth/login.py", CodeNode("function", "authenticate", 1, 10))
    manager.add_file(FileEntry(Path("src/utils.py"), 50, 12))
    return manager


class TestGraphUpdaterInit:
    """Tests for GraphUpdater initialization."""

    def test_init_with_dependencies(self, populated_graph: GraphManager) -> None:
        """GraphUpdater accepts all required dependencies."""
        detector = MagicMock()
        parser = MagicMock(spec=ParserEngine)
        reader = MagicMock(spec=ContentReader)

        updater = GraphUpdater(populated_graph, detector, parser, reader)

        assert updater._graph_manager is populated_graph
        assert updater._change_detector is detector


class TestApplyDeletedFiles:
    """Tests for handling deleted files."""

    def test_deleted_file_removed_from_graph(
        self, populated_graph: GraphManager
    ) -> None:
        """Deleted files are removed from graph with their code nodes."""
        detector = MagicMock()
        detector.detect_changes.return_value = ChangeSet(
            deleted=[Path("src/auth/login.py")]
        )

        updater = GraphUpdater(populated_graph, detector, MagicMock(), MagicMock())
        updater.update(Path("/project"))

        assert "src/auth/login.py" not in populated_graph.graph.nodes
        assert "src/auth/login.py::authenticate" not in populated_graph.graph.nodes

    def test_deleted_file_import_edges_removed(
        self, populated_graph: GraphManager
    ) -> None:
        """Deleting a file removes IMPORTS edges pointing to it."""
        # Setup: utils.py imports login.py
        populated_graph.add_dependency("src/utils.py", "src/auth/login.py")

        detector = MagicMock()
        detector.detect_changes.return_value = ChangeSet(
            deleted=[Path("src/auth/login.py")]
        )

        updater = GraphUpdater(populated_graph, detector, MagicMock(), MagicMock())
        updater.update(Path("/project"))

        # Edge should be gone
        assert not populated_graph.graph.has_edge("src/utils.py", "src/auth/login.py")


class TestApplyModifiedFiles:
    """Tests for handling modified files."""

    def test_modified_file_old_nodes_removed(
        self, populated_graph: GraphManager, tmp_path: Path
    ) -> None:
        """Modified files have old code nodes removed first."""
        # Initial state: login.py has 'authenticate' function
        assert "src/auth/login.py::authenticate" in populated_graph.graph.nodes

        detector = MagicMock()
        detector.detect_changes.return_value = ChangeSet(
            modified=[Path("src/auth/login.py")]
        )

        # Parser returns different function after modification
        parser = MagicMock(spec=ParserEngine)
        parser.parse_file.return_value = [
            CodeNode("function", "new_authenticate", 1, 15)  # Different name
        ]

        reader = MagicMock(spec=ContentReader)
        reader.read_file.return_value = "def new_authenticate(): pass"

        # Create file for update
        (tmp_path / "src" / "auth").mkdir(parents=True)
        (tmp_path / "src" / "auth" / "login.py").write_text("def new_authenticate(): pass")

        updater = GraphUpdater(populated_graph, detector, parser, reader)
        updater.update(tmp_path)

        # Old function gone, new function present
        assert "src/auth/login.py::authenticate" not in populated_graph.graph.nodes
        assert "src/auth/login.py::new_authenticate" in populated_graph.graph.nodes

    def test_modified_file_reimported(
        self, populated_graph: GraphManager, tmp_path: Path
    ) -> None:
        """Modified files have their imports re-resolved."""
        detector = MagicMock()
        detector.detect_changes.return_value = ChangeSet(
            modified=[Path("src/auth/login.py")]
        )

        # Parser returns import node
        parser = MagicMock(spec=ParserEngine)
        parser.parse_file.return_value = [
            CodeNode("import", "os", 0, 0),  # New import
            CodeNode("function", "authenticate", 1, 10),
        ]

        reader = MagicMock(spec=ContentReader)
        reader.read_file.return_value = "import os\ndef authenticate(): pass"

        (tmp_path / "src" / "auth").mkdir(parents=True)
        (tmp_path / "src" / "auth" / "login.py").write_text("import os\ndef authenticate(): pass")

        updater = GraphUpdater(populated_graph, detector, parser, reader)
        updater.update(tmp_path)

        # External module node should be created
        assert "external::os" in populated_graph.graph.nodes
        assert populated_graph.graph.has_edge("src/auth/login.py", "external::os")


class TestApplyAddedFiles:
    """Tests for handling newly added files."""

    def test_added_file_creates_file_node(
        self, populated_graph: GraphManager, tmp_path: Path
    ) -> None:
        """Added files create new file nodes."""
        detector = MagicMock()
        detector.detect_changes.return_value = ChangeSet(
            added=[Path("src/api/routes.py")]
        )

        parser = MagicMock(spec=ParserEngine)
        parser.parse_file.return_value = [
            CodeNode("function", "get_routes", 1, 10)
        ]

        reader = MagicMock(spec=ContentReader)
        reader.read_file.return_value = "def get_routes(): pass"

        # Create new file
        (tmp_path / "src" / "api").mkdir(parents=True)
        new_file = tmp_path / "src" / "api" / "routes.py"
        new_file.write_text("def get_routes(): pass")

        updater = GraphUpdater(populated_graph, detector, parser, reader)
        updater.update(tmp_path)

        assert "src/api/routes.py" in populated_graph.graph.nodes
        assert "src/api/routes.py::get_routes" in populated_graph.graph.nodes


class TestUpdateReturnValue:
    """Tests for update() return value."""

    def test_update_returns_applied_changeset(
        self, populated_graph: GraphManager, tmp_path: Path
    ) -> None:
        """update() returns the ChangeSet that was applied."""
        expected_changes = ChangeSet(
            modified=[Path("src/auth/login.py")],
            base_commit="abc123"
        )

        detector = MagicMock()
        detector.detect_changes.return_value = expected_changes

        parser = MagicMock(spec=ParserEngine)
        parser.parse_file.return_value = []

        reader = MagicMock(spec=ContentReader)
        reader.read_file.return_value = ""

        (tmp_path / "src" / "auth").mkdir(parents=True)
        (tmp_path / "src" / "auth" / "login.py").write_text("")

        updater = GraphUpdater(populated_graph, detector, parser, reader)
        result = updater.update(tmp_path)

        assert result is expected_changes

    def test_update_with_no_changes_returns_empty_changeset(
        self, populated_graph: GraphManager
    ) -> None:
        """update() with no changes returns empty ChangeSet."""
        detector = MagicMock()
        detector.detect_changes.return_value = ChangeSet()  # Empty

        updater = GraphUpdater(populated_graph, detector, MagicMock(), MagicMock())
        result = updater.update(Path("/project"))

        assert result.is_empty


class TestBuildMetadataUpdate:
    """Tests for build metadata updates after successful update."""

    def test_update_stores_new_commit_hash(
        self, populated_graph: GraphManager, tmp_path: Path
    ) -> None:
        """Successful update stores current commit hash in metadata."""
        detector = MagicMock()
        detector.detect_changes.return_value = ChangeSet(base_commit="old_hash")
        detector.get_current_commit.return_value = "new_hash"

        updater = GraphUpdater(populated_graph, detector, MagicMock(), MagicMock())
        updater.update(tmp_path)

        assert populated_graph.build_metadata["commit_hash"] == "new_hash"
```

---

### Phase 2: GREEN - Implementation

#### 2.1 ChangeDetector

Neue Datei: `src/codemap/engine/change_detector.py`

```python
"""Change detection for incremental graph updates.

This module provides the ChangeDetector class for detecting file changes
since the last graph build, using Git or hash-based comparison.
"""

import hashlib
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from codemap.graph import GraphManager

logger = logging.getLogger(__name__)


@dataclass
class ChangeSet:
    """Container for detected file changes.

    Attributes:
        modified: Files with changed content.
        added: New files not in previous build.
        deleted: Files that no longer exist.
        base_commit: Git commit hash of the comparison base.
    """

    modified: list[Path] = field(default_factory=list)
    added: list[Path] = field(default_factory=list)
    deleted: list[Path] = field(default_factory=list)
    base_commit: str | None = None

    @property
    def is_empty(self) -> bool:
        """Return True if no changes detected."""
        return not self.modified and not self.added and not self.deleted

    @property
    def total_changes(self) -> int:
        """Return total number of changed files."""
        return len(self.modified) + len(self.added) + len(self.deleted)


class ChangeDetector:
    """Detect file changes since last graph build.

    Uses Git diff as primary strategy, falls back to hash comparison
    when Git is unavailable or for non-Git directories.

    Example:
        detector = ChangeDetector(graph_manager)
        changes = detector.detect_changes(Path("src"))
        print(f"Modified: {changes.modified}")
    """

    def __init__(self, graph_manager: GraphManager) -> None:
        """Initialize with GraphManager containing build metadata."""
        self._graph_manager = graph_manager

    def detect_changes(self, root: Path) -> ChangeSet:
        """Detect file changes since last build.

        Args:
            root: Project root directory.

        Returns:
            ChangeSet with modified, added, and deleted files.
        """
        metadata = getattr(self._graph_manager, "build_metadata", {})
        base_commit = metadata.get("commit_hash")

        if base_commit:
            try:
                return self._detect_via_git(root, base_commit)
            except (FileNotFoundError, subprocess.CalledProcessError) as e:
                logger.warning(f"Git detection failed, falling back to hash: {e}")

        return self._detect_via_hash(root, metadata.get("file_hashes", {}))

    def _detect_via_git(self, root: Path, base_commit: str) -> ChangeSet:
        """Use git diff to detect changes."""
        result = subprocess.run(
            ["git", "diff", "--name-status", base_commit, "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )

        changes = ChangeSet(base_commit=base_commit)

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("\t")
            status = parts[0]

            if status == "M":
                changes.modified.append(Path(parts[1]))
            elif status == "A":
                changes.added.append(Path(parts[1]))
            elif status == "D":
                changes.deleted.append(Path(parts[1]))
            elif status.startswith("R"):
                # Renamed: treat as delete + add
                changes.deleted.append(Path(parts[1]))
                changes.added.append(Path(parts[2]))

        return changes

    def _detect_via_hash(
        self, root: Path, stored_hashes: dict[str, str]
    ) -> ChangeSet:
        """Use file content hashes to detect changes."""
        changes = ChangeSet()
        current_files: set[str] = set()

        # Walk directory and compare hashes
        for file_path in root.rglob("*.py"):
            rel_path = str(file_path.relative_to(root))
            current_files.add(rel_path)

            current_hash = self._hash_file(file_path)
            stored_hash = stored_hashes.get(rel_path)

            if stored_hash is None:
                changes.added.append(Path(rel_path))
            elif current_hash != stored_hash:
                changes.modified.append(Path(rel_path))

        # Find deleted files
        for stored_path in stored_hashes:
            if stored_path not in current_files:
                changes.deleted.append(Path(stored_path))

        return changes

    def _hash_file(self, path: Path) -> str:
        """Compute SHA-256 hash of file content."""
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def get_current_commit(self, root: Path) -> str | None:
        """Get current HEAD commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (FileNotFoundError, subprocess.CalledProcessError):
            return None
```

#### 2.2 GraphManager remove-Methoden

Datei: `src/codemap/graph/manager.py` (erweitern)

```python
def remove_node(self, node_id: str) -> None:
    """Remove a node and all its edges from the graph.

    Args:
        node_id: ID of the node to remove.

    Raises:
        ValueError: If node does not exist in graph.
    """
    if node_id not in self._graph.nodes:
        raise ValueError(f"Node '{node_id}' not found in graph")

    self._graph.remove_node(node_id)

def remove_file(self, file_id: str) -> None:
    """Remove a file node and all contained code nodes.

    Finds all nodes connected via CONTAINS edge and removes them,
    then removes the file node itself.

    Args:
        file_id: ID of the file node to remove.

    Raises:
        ValueError: If node does not exist or is not a file node.
    """
    if file_id not in self._graph.nodes:
        raise ValueError(f"Node '{file_id}' not found in graph")

    if self._graph.nodes[file_id].get("type") != "file":
        raise ValueError(f"Node '{file_id}' is not a file node")

    # Find all child nodes (connected via CONTAINS)
    children_to_remove = []
    for _, target, data in self._graph.out_edges(file_id, data=True):
        if data.get("relationship") == "CONTAINS":
            children_to_remove.append(target)

    # Remove children first
    for child_id in children_to_remove:
        self._graph.remove_node(child_id)

    # Remove file node (also removes remaining edges)
    self._graph.remove_node(file_id)
```

#### 2.3 GraphUpdater

Neue Datei: `src/codemap/engine/graph_updater.py`

```python
"""Incremental graph update orchestration.

This module provides the GraphUpdater class for applying incremental
changes to an existing code graph.
"""

import logging
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

    Example:
        updater = GraphUpdater(graph_manager, detector, parser, reader)
        changes = updater.update(Path("src"))
        print(f"Updated {changes.total_changes} files")
    """

    def __init__(
        self,
        graph_manager: GraphManager,
        change_detector: ChangeDetector,
        parser: ParserEngine,
        reader: ContentReader,
    ) -> None:
        """Initialize with required dependencies."""
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
        changes = self._change_detector.detect_changes(root)

        if changes.is_empty:
            logger.info("No changes detected")
            return changes

        logger.info(
            f"Applying changes: {len(changes.modified)} modified, "
            f"{len(changes.added)} added, {len(changes.deleted)} deleted"
        )

        # Step 2: Remove deleted files
        for file_path in changes.deleted:
            file_id = str(file_path)
            if file_id in self._graph_manager.graph.nodes:
                self._graph_manager.remove_file(file_id)

        # Step 3: Remove modified files (will be re-added)
        for file_path in changes.modified:
            file_id = str(file_path)
            if file_id in self._graph_manager.graph.nodes:
                self._graph_manager.remove_file(file_id)

        # Step 4: Add modified files (re-parse)
        for file_path in changes.modified:
            self._add_file(root, file_path)

        # Step 5: Add new files
        for file_path in changes.added:
            self._add_file(root, file_path)

        # Step 6: Update build metadata
        new_commit = self._change_detector.get_current_commit(root)
        if new_commit:
            if not hasattr(self._graph_manager, "build_metadata"):
                self._graph_manager.build_metadata = {}
            self._graph_manager.build_metadata["commit_hash"] = new_commit

        return changes

    def _add_file(self, root: Path, rel_path: Path) -> None:
        """Add a single file to the graph."""
        file_id = str(rel_path)
        abs_path = root / rel_path

        if not abs_path.exists():
            logger.warning(f"File not found: {abs_path}")
            return

        # Create FileEntry
        stat = abs_path.stat()
        entry = FileEntry(
            path=rel_path,
            size=stat.st_size,
            token_est=stat.st_size // 4,  # Rough estimate
        )
        self._graph_manager.add_file(entry)

        # Skip non-Python files
        if rel_path.suffix != ".py":
            return

        # Read and parse
        try:
            content = self._reader.read_file(abs_path)
        except ContentReadError as e:
            logger.warning(f"Failed to read {rel_path}: {e}")
            return

        try:
            code_nodes = self._parser.parse_file(rel_path, content)
        except ValueError as e:
            logger.warning(f"Failed to parse {rel_path}: {e}")
            return

        # Add code nodes and resolve imports
        imports: list[str] = []
        for node in code_nodes:
            if node.type == "import":
                imports.append(node.name)
            else:
                self._graph_manager.add_node(file_id, node)

        # Resolve imports (simplified - full resolution in MapBuilder)
        for module_name in imports:
            external_id = self._graph_manager.add_external_module(module_name)
            self._graph_manager.add_dependency(file_id, external_id)
```

---

### Phase 3: REFACTOR - Code-Qualität

#### 3.1 Checklist

- [ ] mypy strict auf neuen Dateien
- [ ] ruff Format und Lint
- [ ] Docstrings vollständig
- [ ] `build_metadata` als Property in GraphManager (nicht dynamisch)
- [ ] Import-Resolution in GraphUpdater mit MapBuilder._resolve_and_add_import() wiederverwenden
- [ ] Logging für Performance-Messung (Update-Dauer)

#### 3.2 Integration mit Phase 18

- [ ] Nach Update: `HierarchyEnricher` auf betroffene Package-Nodes beschränken
- [ ] Re-Aggregation nur für Parent-Nodes geänderter Dateien

---

## Akzeptanzkriterien

- [ ] `ChangeDetector.detect_changes()` erkennt modified/added/deleted via Git
- [ ] Fallback zu Hash-Vergleich wenn kein Git
- [ ] `GraphManager.remove_file()` entfernt File + Kind-Nodes + Edges
- [ ] `GraphManager.remove_node()` entfernt einzelne Nodes
- [ ] `GraphUpdater.update()` wendet ChangeSet auf Graph an
- [ ] Build-Metadata wird persistiert (commit_hash, file_hashes)
- [ ] Performance: Update schneller als Full-Rebuild (messbar)
- [ ] 100% Test-Coverage bleibt erhalten
- [ ] mypy strict + ruff clean

---

## Abhängigkeiten

- **Phase 18 (Hierarchische Aggregation):** Für Re-Aggregation nach Update
- **GraphManager:** Basis für alle Operationen

## Risiken

1. **Git nicht verfügbar:** Fallback zu Hash-basiert (langsamer aber funktional)
2. **Große Renames:** Werden als delete + add behandelt (Summaries gehen verloren)
   - Mitigation: Phase 20 könnte `git diff -M` für Rename-Detection nutzen
3. **Concurrent Updates:** Graph ist nicht thread-safe
   - Mitigation: Locking auf Caller-Ebene

---

## Schätzung

- **Aufwand:** 🟡 Mittel (wie in Roadmap angegeben)
- **Komplexität:** Moderate - hauptsächlich CRUD-Operationen
- **Zeitrahmen:** 1-2 TDD-Zyklen

---

## Nächster Schritt

**RED Phase starten:** Tests für `ChangeSet` und `ChangeDetector` in `tests/unit/engine/test_change_detector.py` schreiben.
