"""Tests for ChangeDetector and ChangeSet.

This module contains comprehensive unit tests for the change detection
system used in incremental graph updates, following strict TDD principles.
"""

import logging
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from codemap.engine.change_detector import ChangeDetector, ChangeSet
from codemap.graph import GraphManager


class TestChangeSetDataclass:
    """Tests for ChangeSet dataclass."""

    def test_changeset_empty_by_default(self) -> None:
        """ChangeSet initializes with empty lists and None base_commit."""
        cs = ChangeSet()
        assert cs.modified == []
        assert cs.added == []
        assert cs.deleted == []
        assert cs.base_commit is None

    def test_changeset_accepts_modified_files(self) -> None:
        """ChangeSet accepts list of modified Path objects."""
        cs = ChangeSet(modified=[Path("src/a.py"), Path("src/b.py")])
        assert cs.modified == [Path("src/a.py"), Path("src/b.py")]

    def test_changeset_accepts_added_files(self) -> None:
        """ChangeSet accepts list of added Path objects."""
        cs = ChangeSet(added=[Path("src/new.py")])
        assert cs.added == [Path("src/new.py")]

    def test_changeset_accepts_deleted_files(self) -> None:
        """ChangeSet accepts list of deleted Path objects."""
        cs = ChangeSet(deleted=[Path("src/old.py")])
        assert cs.deleted == [Path("src/old.py")]

    def test_changeset_accepts_base_commit(self) -> None:
        """ChangeSet accepts base_commit string."""
        cs = ChangeSet(base_commit="abc123def456")
        assert cs.base_commit == "abc123def456"

    def test_changeset_is_empty_property_true_when_no_changes(self) -> None:
        """is_empty returns True when all lists are empty."""
        cs = ChangeSet()
        assert cs.is_empty is True

    def test_changeset_is_empty_property_false_when_modified(self) -> None:
        """is_empty returns False when modified list has items."""
        cs = ChangeSet(modified=[Path("src/a.py")])
        assert cs.is_empty is False

    def test_changeset_is_empty_property_false_when_added(self) -> None:
        """is_empty returns False when added list has items."""
        cs = ChangeSet(added=[Path("src/new.py")])
        assert cs.is_empty is False

    def test_changeset_is_empty_property_false_when_deleted(self) -> None:
        """is_empty returns False when deleted list has items."""
        cs = ChangeSet(deleted=[Path("src/old.py")])
        assert cs.is_empty is False

    def test_changeset_total_changes_sums_all_lists(self) -> None:
        """total_changes returns sum of modified + added + deleted."""
        cs = ChangeSet(
            modified=[Path("a.py"), Path("b.py")],
            added=[Path("c.py")],
            deleted=[Path("d.py"), Path("e.py"), Path("f.py")],
        )
        assert cs.total_changes == 6

    def test_changeset_total_changes_zero_when_empty(self) -> None:
        """total_changes returns 0 for empty ChangeSet."""
        cs = ChangeSet()
        assert cs.total_changes == 0


class TestChangeDetectorInit:
    """Tests for ChangeDetector initialization."""

    def test_init_accepts_graph_manager(self) -> None:
        """ChangeDetector accepts GraphManager instance."""
        manager = GraphManager()
        detector = ChangeDetector(manager)
        assert detector is not None

    def test_init_stores_graph_manager_reference(self) -> None:
        """ChangeDetector stores GraphManager for metadata access."""
        manager = GraphManager()
        detector = ChangeDetector(manager)
        assert detector._graph_manager is manager


class TestGitBasedDetection:
    """Tests for Git-based change detection."""

    @patch("codemap.engine.change_detector.subprocess.run")
    def test_detect_changes_calls_git_diff(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """detect_changes() calls git diff with stored commit hash."""
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        manager = GraphManager()
        manager.build_metadata["commit_hash"] = "abc123"
        detector = ChangeDetector(manager)

        detector.detect_changes(tmp_path)

        mock_run.assert_called_once_with(
            ["git", "diff", "--name-status", "abc123", "HEAD"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("codemap.engine.change_detector.subprocess.run")
    def test_detect_modified_files_parsed_correctly(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Modified files (M status) are in changes.modified."""
        mock_run.return_value = MagicMock(stdout="M\tsrc/auth.py\nM\tsrc/utils.py", returncode=0)
        manager = GraphManager()
        manager.build_metadata["commit_hash"] = "abc123"
        detector = ChangeDetector(manager)

        changes = detector.detect_changes(tmp_path)

        assert Path("src/auth.py") in changes.modified
        assert Path("src/utils.py") in changes.modified

    @patch("codemap.engine.change_detector.subprocess.run")
    def test_detect_added_files_parsed_correctly(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Added files (A status) are in changes.added."""
        mock_run.return_value = MagicMock(stdout="A\tsrc/new_module.py", returncode=0)
        manager = GraphManager()
        manager.build_metadata["commit_hash"] = "abc123"
        detector = ChangeDetector(manager)

        changes = detector.detect_changes(tmp_path)

        assert Path("src/new_module.py") in changes.added

    @patch("codemap.engine.change_detector.subprocess.run")
    def test_detect_deleted_files_parsed_correctly(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Deleted files (D status) are in changes.deleted."""
        mock_run.return_value = MagicMock(stdout="D\tsrc/old_module.py", returncode=0)
        manager = GraphManager()
        manager.build_metadata["commit_hash"] = "abc123"
        detector = ChangeDetector(manager)

        changes = detector.detect_changes(tmp_path)

        assert Path("src/old_module.py") in changes.deleted

    @patch("codemap.engine.change_detector.subprocess.run")
    def test_detect_renamed_files_as_add_delete(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Renamed files (R status) become add + delete."""
        mock_run.return_value = MagicMock(stdout="R100\tsrc/old.py\tsrc/new.py", returncode=0)
        manager = GraphManager()
        manager.build_metadata["commit_hash"] = "abc123"
        detector = ChangeDetector(manager)

        changes = detector.detect_changes(tmp_path)

        assert Path("src/old.py") in changes.deleted
        assert Path("src/new.py") in changes.added

    @patch("codemap.engine.change_detector.subprocess.run")
    def test_git_diff_includes_base_commit_in_command(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """git diff command includes base_commit from metadata."""
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        manager = GraphManager()
        manager.build_metadata["commit_hash"] = "deadbeef1234"
        detector = ChangeDetector(manager)

        detector.detect_changes(tmp_path)

        args = mock_run.call_args[0][0]
        assert "deadbeef1234" in args

    @patch("codemap.engine.change_detector.subprocess.run")
    def test_git_diff_runs_in_correct_directory(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """git diff subprocess runs with cwd=root."""
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        manager = GraphManager()
        manager.build_metadata["commit_hash"] = "abc123"
        detector = ChangeDetector(manager)

        detector.detect_changes(tmp_path)

        assert mock_run.call_args[1]["cwd"] == tmp_path

    @patch("codemap.engine.change_detector.subprocess.run")
    def test_git_diff_failure_falls_back_to_hash(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """git diff failure falls back to hash-based detection."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")
        manager = GraphManager()
        manager.build_metadata["commit_hash"] = "abc123"
        detector = ChangeDetector(manager)

        # Should not raise, falls back to hash detection
        changes = detector.detect_changes(tmp_path)
        assert isinstance(changes, ChangeSet)

    @patch("codemap.engine.change_detector.subprocess.run")
    def test_unknown_git_status_ignored(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Unknown git status codes (e.g. C for copy) are silently ignored."""
        mock_run.return_value = MagicMock(stdout="C100\tsrc/a.py\tsrc/b.py", returncode=0)
        manager = GraphManager()
        manager.build_metadata["commit_hash"] = "abc123"
        detector = ChangeDetector(manager)

        changes = detector.detect_changes(tmp_path)

        assert changes.is_empty


class TestHashBasedDetection:
    """Tests for hash-based change detection (Git fallback)."""

    @patch("codemap.engine.change_detector.subprocess.run")
    def test_fallback_to_hash_when_git_fails(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Uses hash comparison when git command fails."""
        mock_run.side_effect = FileNotFoundError("git not found")
        # Create a file on disk
        py_file = tmp_path / "hello.py"
        py_file.write_text("print('hello')")

        manager = GraphManager()
        manager.build_metadata["commit_hash"] = "abc123"
        detector = ChangeDetector(manager)

        changes = detector.detect_changes(tmp_path)

        # File should appear as added (no stored hashes)
        assert Path("hello.py") in changes.added

    def test_hash_detection_finds_modified_files(self, tmp_path: Path) -> None:
        """Hash mismatch detected for modified files."""
        py_file = tmp_path / "app.py"
        py_file.write_text("original content")

        manager = GraphManager()
        # Store old hash (different from current content)
        manager.build_metadata["file_hashes"] = {"app.py": "old_hash_value"}
        detector = ChangeDetector(manager)

        changes = detector.detect_changes(tmp_path)

        assert Path("app.py") in changes.modified

    def test_hash_detection_finds_added_files(self, tmp_path: Path) -> None:
        """New files not in stored_hashes are detected as added."""
        py_file = tmp_path / "new_module.py"
        py_file.write_text("new content")

        manager = GraphManager()
        manager.build_metadata["file_hashes"] = {}
        detector = ChangeDetector(manager)

        changes = detector.detect_changes(tmp_path)

        assert Path("new_module.py") in changes.added

    def test_hash_detection_finds_deleted_files(self, tmp_path: Path) -> None:
        """Files in stored_hashes but not on disk are deleted."""
        manager = GraphManager()
        manager.build_metadata["file_hashes"] = {"gone.py": "some_hash"}
        detector = ChangeDetector(manager)

        changes = detector.detect_changes(tmp_path)

        assert Path("gone.py") in changes.deleted

    def test_hash_detection_with_no_stored_hashes(self, tmp_path: Path) -> None:
        """All files are added when no stored_hashes exist."""
        (tmp_path / "a.py").write_text("a")
        (tmp_path / "b.py").write_text("b")

        manager = GraphManager()
        # No file_hashes in metadata
        detector = ChangeDetector(manager)

        changes = detector.detect_changes(tmp_path)

        assert Path("a.py") in changes.added
        assert Path("b.py") in changes.added

    def test_hash_detection_unchanged_files_not_in_changeset(self, tmp_path: Path) -> None:
        """Files with matching hashes are not in ChangeSet."""
        import hashlib

        py_file = tmp_path / "stable.py"
        py_file.write_text("stable content")
        file_hash = hashlib.sha256(py_file.read_bytes()).hexdigest()

        manager = GraphManager()
        manager.build_metadata["file_hashes"] = {"stable.py": file_hash}
        detector = ChangeDetector(manager)

        changes = detector.detect_changes(tmp_path)

        assert Path("stable.py") not in changes.modified
        assert Path("stable.py") not in changes.added
        assert Path("stable.py") not in changes.deleted


class TestGetCurrentCommit:
    """Tests for get_current_commit() method."""

    @patch("codemap.engine.change_detector.subprocess.run")
    def test_get_current_commit_calls_git_rev_parse(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """get_current_commit() calls git rev-parse HEAD."""
        mock_run.return_value = MagicMock(stdout="abc123def456\n", returncode=0)
        manager = GraphManager()
        detector = ChangeDetector(manager)

        detector.get_current_commit(tmp_path)

        mock_run.assert_called_once_with(
            ["git", "rev-parse", "HEAD"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("codemap.engine.change_detector.subprocess.run")
    def test_get_current_commit_returns_commit_hash(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """get_current_commit() returns commit hash string."""
        mock_run.return_value = MagicMock(stdout="abc123def456\n", returncode=0)
        manager = GraphManager()
        detector = ChangeDetector(manager)

        result = detector.get_current_commit(tmp_path)

        assert result == "abc123def456"

    @patch("codemap.engine.change_detector.subprocess.run")
    def test_get_current_commit_returns_none_on_failure(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """get_current_commit() returns None when git fails."""
        mock_run.side_effect = FileNotFoundError("git not found")
        manager = GraphManager()
        detector = ChangeDetector(manager)

        result = detector.get_current_commit(tmp_path)

        assert result is None


class TestGitParsingEdgeCases:
    """Tests for malformed git diff output handling."""

    @patch("codemap.engine.change_detector.subprocess.run")
    def test_malformed_line_single_part_skipped(
        self, mock_run: MagicMock, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Malformed git diff line with only one part is skipped with warning."""
        mock_run.return_value = MagicMock(stdout="MALFORMED_NO_TAB", returncode=0)
        manager = GraphManager()
        manager.build_metadata["commit_hash"] = "abc123"
        detector = ChangeDetector(manager)

        with caplog.at_level(logging.WARNING):
            changes = detector.detect_changes(tmp_path)

        assert changes.is_empty
        assert "Skipping malformed git diff line" in caplog.text

    @patch("codemap.engine.change_detector.subprocess.run")
    def test_rename_without_target_path_skipped(
        self, mock_run: MagicMock, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Rename line without target path is skipped with warning."""
        mock_run.return_value = MagicMock(stdout="R100\tsrc/old.py", returncode=0)
        manager = GraphManager()
        manager.build_metadata["commit_hash"] = "abc123"
        detector = ChangeDetector(manager)

        with caplog.at_level(logging.WARNING):
            changes = detector.detect_changes(tmp_path)

        assert changes.is_empty
        assert "Skipping malformed rename line" in caplog.text

    @patch("codemap.engine.change_detector.subprocess.run")
    def test_malformed_lines_do_not_affect_valid_lines(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Valid lines are still parsed when malformed lines are present."""
        mock_run.return_value = MagicMock(
            stdout="MALFORMED\nM\tsrc/valid.py", returncode=0
        )
        manager = GraphManager()
        manager.build_metadata["commit_hash"] = "abc123"
        detector = ChangeDetector(manager)

        changes = detector.detect_changes(tmp_path)

        assert Path("src/valid.py") in changes.modified


class TestHashDetectionCustomPattern:
    """Tests for custom file pattern in hash-based detection."""

    def test_hash_detection_custom_pattern(self, tmp_path: Path) -> None:
        """_detect_via_hash supports custom file patterns."""
        (tmp_path / "test.txt").write_text("text")
        manager = GraphManager()
        detector = ChangeDetector(manager)

        changes = detector._detect_via_hash(tmp_path, {}, file_pattern="*.txt")

        assert Path("test.txt") in changes.added
