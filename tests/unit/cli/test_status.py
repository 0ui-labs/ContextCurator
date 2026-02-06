"""Tests for curator status command."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from codemap.cli.main import app


@pytest.fixture()
def runner() -> CliRunner:
    """CLI test runner."""
    return CliRunner()


@pytest.fixture()
def mock_graph_manager(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock GraphManager class in status module."""
    mock_gm_instance = MagicMock()
    mock_gm_instance.graph_stats = {"nodes": 42, "edges": 17}

    mock_class = MagicMock(return_value=mock_gm_instance)
    monkeypatch.setattr("codemap.cli.commands.status.GraphManager", mock_class)
    return mock_class


@pytest.fixture()
def codemap_with_graph(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create .codemap/ directory with graph.json."""
    monkeypatch.chdir(tmp_path)
    codemap_dir = tmp_path / ".codemap"
    codemap_dir.mkdir()
    (codemap_dir / "graph.json").write_text("{}")
    return tmp_path


@pytest.fixture()
def codemap_with_metadata(codemap_with_graph: Path) -> Path:
    """Add metadata.json to existing .codemap/."""
    metadata = {
        "build_time": "2024-01-15T10:30:00Z",
        "commit_hash": "abc123def456789",
    }
    (codemap_with_graph / ".codemap" / "metadata.json").write_text(json.dumps(metadata))
    return codemap_with_graph


class TestStatusCommand:
    """Tests for basic 'curator status' display."""

    def test_status_shows_node_count(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_graph_manager: MagicMock,
    ) -> None:
        """Status command displays node count from graph_stats.

        Verifies that the number of nodes returned by GraphManager.graph_stats
        is correctly displayed in the status output.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".codemap").mkdir()
        (tmp_path / ".codemap" / "graph.json").write_text("{}")
        mock_graph_manager.return_value.graph_stats = {"nodes": 42, "edges": 17}

        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code == 0
        assert "42" in result.output

    def test_status_shows_edge_count(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_graph_manager: MagicMock,
    ) -> None:
        """Status command displays edge count from graph_stats.

        Verifies that the number of edges returned by GraphManager.graph_stats
        is correctly displayed in the status output.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".codemap").mkdir()
        (tmp_path / ".codemap" / "graph.json").write_text("{}")
        mock_graph_manager.return_value.graph_stats = {"nodes": 42, "edges": 17}

        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code == 0
        assert "17" in result.output

    def test_status_shows_both_stats(
        self,
        runner: CliRunner,
        codemap_with_graph: Path,
        mock_graph_manager: MagicMock,
    ) -> None:
        """Status command displays both node and edge counts together.

        Verifies that both statistics from GraphManager.graph_stats
        appear in the status output simultaneously.
        """
        # Arrange
        mock_graph_manager.return_value.graph_stats = {"nodes": 42, "edges": 17}

        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code == 0
        assert "42" in result.output
        assert "17" in result.output

    def test_status_exit_code_success(
        self,
        runner: CliRunner,
        codemap_with_graph: Path,
        mock_graph_manager: MagicMock,
    ) -> None:
        """Status command returns exit code 0 on success.

        Verifies that when .codemap/ exists with valid graph.json,
        the command completes successfully.
        """
        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code == 0


class TestStatusMetadata:
    """Tests for metadata display in status output."""

    def test_status_shows_last_update_timestamp(
        self,
        runner: CliRunner,
        codemap_with_metadata: Path,
        mock_graph_manager: MagicMock,
    ) -> None:
        """Status command displays build_time from metadata.json.

        Verifies that the last update timestamp is shown in the output.
        """
        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code == 0
        assert "2024-01-15" in result.output or "10:30" in result.output

    def test_status_shows_commit_hash(
        self,
        runner: CliRunner,
        codemap_with_metadata: Path,
        mock_graph_manager: MagicMock,
    ) -> None:
        """Status command displays commit hash from metadata.json.

        Verifies that the git commit hash is present in the output.
        """
        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code == 0
        assert "abc123de" in result.output

    def test_status_shows_short_commit_hash(
        self,
        runner: CliRunner,
        codemap_with_metadata: Path,
        mock_graph_manager: MagicMock,
    ) -> None:
        """Status command shows only first 8 characters of commit hash.

        Verifies that the commit hash is truncated to a short form
        (8 characters) for readability.
        """
        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code == 0
        # Should contain the short hash (first 8 chars)
        assert "abc123de" in result.output
        # Should NOT contain the full hash
        assert "abc123def456789" not in result.output

    def test_status_handles_missing_metadata_json(
        self,
        runner: CliRunner,
        codemap_with_graph: Path,
        mock_graph_manager: MagicMock,
    ) -> None:
        """Status command works when metadata.json is missing.

        Verifies that the status command does not fail when metadata.json
        does not exist - it should still show graph stats.
        """
        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code == 0
        assert "42" in result.output

    def test_status_handles_null_commit_hash(
        self,
        runner: CliRunner,
        codemap_with_graph: Path,
        mock_graph_manager: MagicMock,
    ) -> None:
        """Status command handles null commit_hash in metadata.

        Verifies that the status command works correctly when
        commit_hash is null (e.g., git not available during init).
        """
        # Arrange
        metadata = {
            "build_time": "2024-01-15T10:30:00Z",
            "commit_hash": None,
        }
        (codemap_with_graph / ".codemap" / "metadata.json").write_text(json.dumps(metadata))

        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code == 0


class TestStatusErrors:
    """Tests for error handling in status command."""

    def test_status_fails_without_codemap_directory(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Status command fails when .codemap/ directory does not exist.

        Verifies that the command returns a non-zero exit code when
        no .codemap/ directory is found.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)

        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code != 0

    def test_status_error_message_mentions_init(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Error message suggests running 'curator init' when .codemap/ is missing.

        Verifies that the error output mentions 'init' to guide
        the user towards initializing the code map first.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)

        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code != 0
        assert "init" in result.output.lower()

    def test_status_fails_without_graph_json(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Status command fails when .codemap/ exists but graph.json is missing.

        Verifies that the command requires graph.json to be present
        inside the .codemap/ directory.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".codemap").mkdir()

        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code != 0

    def test_status_handles_corrupted_graph_json(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_graph_manager: MagicMock,
    ) -> None:
        """Status command shows error when graph.json contains invalid JSON.

        Verifies that when GraphManager.load() raises an error due to
        corrupted graph.json, the command handles it gracefully.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".codemap").mkdir()
        (tmp_path / ".codemap" / "graph.json").write_text("not valid json{{{")
        mock_graph_manager.return_value.load.side_effect = ValueError("Invalid JSON")

        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code != 0
        output_lower = result.output.lower()
        assert "error" in output_lower or "invalid" in output_lower

    def test_status_handles_corrupted_metadata_json(
        self,
        runner: CliRunner,
        codemap_with_graph: Path,
        mock_graph_manager: MagicMock,
    ) -> None:
        """Status command works with corrupted metadata.json, showing warning.

        Verifies that the status command does not fail when metadata.json
        contains invalid JSON - it should still show graph stats.
        """
        # Arrange
        (codemap_with_graph / ".codemap" / "metadata.json").write_text("not valid json{{{")

        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code == 0
        assert "42" in result.output


class TestStatusGraphManagerIntegration:
    """Tests for correct GraphManager usage in status command."""

    def test_status_calls_graphmanager_load(
        self,
        runner: CliRunner,
        codemap_with_graph: Path,
        mock_graph_manager: MagicMock,
    ) -> None:
        """Status command calls GraphManager.load() to read graph data.

        Verifies that the status command uses GraphManager.load()
        to load the code graph from disk.
        """
        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code == 0
        mock_graph_manager.assert_called_once()

    def test_status_reads_graph_stats_property(
        self,
        runner: CliRunner,
        codemap_with_graph: Path,
        mock_graph_manager: MagicMock,
    ) -> None:
        """Status command reads graph_stats property from GraphManager.

        Verifies that after loading, the command accesses graph_stats
        to retrieve node and edge counts.
        """
        # Arrange
        mock_graph_manager.return_value.graph_stats = {"nodes": 99, "edges": 55}

        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code == 0
        assert "99" in result.output
        assert "55" in result.output

    def test_status_loads_from_correct_path(
        self,
        runner: CliRunner,
        codemap_with_graph: Path,
        mock_graph_manager: MagicMock,
    ) -> None:
        """Status command loads graph.json from .codemap/ directory.

        Verifies that GraphManager.load() is called with the correct
        path to .codemap/graph.json.
        """
        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code == 0
        mock_graph_manager.assert_called_once()
        mock_gm_instance = mock_graph_manager.return_value
        mock_gm_instance.load.assert_called_once()
        load_path = mock_gm_instance.load.call_args[0][0]
        assert load_path == codemap_with_graph / ".codemap" / "graph.json"


class TestStatusFormatting:
    """Tests for status output formatting."""

    def test_status_output_contains_header(
        self,
        runner: CliRunner,
        codemap_with_graph: Path,
        mock_graph_manager: MagicMock,
    ) -> None:
        """Status output includes a descriptive header.

        Verifies that the output contains a header like 'Code Map Status'
        or similar descriptive title.
        """
        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert "status" in output_lower or "code map" in output_lower

    def test_status_output_is_human_readable(
        self,
        runner: CliRunner,
        codemap_with_graph: Path,
        mock_graph_manager: MagicMock,
    ) -> None:
        """Status output contains human-readable labels for statistics.

        Verifies that the output uses labels like 'Nodes:', 'Edges:'
        to make the output understandable.
        """
        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert "nodes" in output_lower
        assert "edges" in output_lower

    def test_status_output_aligns_values(
        self,
        runner: CliRunner,
        codemap_with_graph: Path,
        mock_graph_manager: MagicMock,
    ) -> None:
        """Status output displays values after their labels.

        Verifies that node and edge values appear in the same
        line or after their respective labels.
        """
        # Arrange
        mock_graph_manager.return_value.graph_stats = {"nodes": 42, "edges": 17}

        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code == 0
        lines = result.output.lower().split("\n")
        node_line = next((line for line in lines if "nodes" in line), None)
        edge_line = next((line for line in lines if "edges" in line), None)
        assert node_line is not None and "42" in node_line
        assert edge_line is not None and "17" in edge_line

    def test_status_output_uses_rich_table(
        self,
        runner: CliRunner,
        codemap_with_graph: Path,
        mock_graph_manager: MagicMock,
    ) -> None:
        """Status output uses Rich table with box-drawing characters.

        Verifies that the output contains Rich table border characters
        (e.g. ┏, ┗, │, ─) indicating proper table rendering.
        """
        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code == 0
        output = result.output
        has_table_chars = any(ch in output for ch in ("┏", "┗", "│", "─", "┃"))
        assert has_table_chars, f"Expected Rich table border characters in output, got:\n{output}"

    def test_status_output_has_column_headers(
        self,
        runner: CliRunner,
        codemap_with_metadata: Path,
        mock_graph_manager: MagicMock,
    ) -> None:
        """Status output contains expected column headers in Rich table.

        Verifies that the Rich table includes column headers for
        Nodes, Edges, Last update, and Commit.
        """
        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert "nodes" in output_lower
        assert "edges" in output_lower
        assert "last update" in output_lower or "last_update" in output_lower
        assert "commit" in output_lower


class TestStatusEdgeCases:
    """Edge case tests for status command."""

    def test_status_with_zero_nodes_and_edges(
        self,
        runner: CliRunner,
        codemap_with_graph: Path,
        mock_graph_manager: MagicMock,
    ) -> None:
        """Status command correctly displays zero counts for empty graph.

        Verifies that when the graph has no nodes or edges,
        the command still runs successfully and shows '0'.
        """
        # Arrange
        mock_graph_manager.return_value.graph_stats = {"nodes": 0, "edges": 0}

        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code == 0
        assert "0" in result.output

    def test_status_with_large_numbers(
        self,
        runner: CliRunner,
        codemap_with_graph: Path,
        mock_graph_manager: MagicMock,
    ) -> None:
        """Status command correctly displays large node/edge counts.

        Verifies that formatting handles large numbers (e.g., 10000+)
        without issues.
        """
        # Arrange
        mock_graph_manager.return_value.graph_stats = {"nodes": 10000, "edges": 25000}

        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code == 0
        assert "10000" in result.output
        assert "25000" in result.output

    def test_status_with_very_old_timestamp(
        self,
        runner: CliRunner,
        codemap_with_graph: Path,
        mock_graph_manager: MagicMock,
    ) -> None:
        """Status command displays old timestamps correctly.

        Verifies that timestamps from years ago are still
        displayed without errors.
        """
        # Arrange
        metadata = {
            "build_time": "2020-03-15T08:00:00Z",
            "commit_hash": "deadbeef12345678",
        }
        (codemap_with_graph / ".codemap" / "metadata.json").write_text(json.dumps(metadata))

        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code == 0
        assert "2020" in result.output

    def test_status_in_subdirectory(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_graph_manager: MagicMock,
    ) -> None:
        """Status command works when invoked from a subdirectory.

        Verifies that the status command searches for .codemap/ in
        parent directories when invoked from a subdirectory.
        """
        # Arrange
        codemap_dir = tmp_path / ".codemap"
        codemap_dir.mkdir()
        (codemap_dir / "graph.json").write_text("{}")
        sub_dir = tmp_path / "src" / "module"
        sub_dir.mkdir(parents=True)
        monkeypatch.chdir(sub_dir)

        # Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code == 0
        assert "42" in result.output
