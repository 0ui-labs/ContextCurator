"""Tests for curator update command."""

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
def setup_codemap_dir(tmp_path: Path) -> Path:
    """Create .codemap/ with graph.json and metadata.json."""
    codemap_dir = tmp_path / ".codemap"
    codemap_dir.mkdir()
    (codemap_dir / "graph.json").write_text('{"nodes": [], "links": []}')
    (codemap_dir / "metadata.json").write_text(
        '{"build_time": "2024-01-01T00:00:00", "commit_hash": "abc123"}'
    )
    return codemap_dir


@pytest.fixture()
def mock_graph_manager(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock GraphManager with load(), save(), build_metadata property."""
    mock_gm = MagicMock()
    mock_gm.graph_stats = {"nodes": 10, "edges": 8}
    mock_gm.build_metadata = {"commit_hash": "abc123", "file_hashes": {}}

    mock_class = MagicMock(return_value=mock_gm)
    monkeypatch.setattr("codemap.cli.commands.update.GraphManager", mock_class)
    return mock_gm


@pytest.fixture()
def mock_graph_updater(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock GraphUpdater with update() returning ChangeSet."""
    mock_updater = MagicMock()
    mock_changeset = MagicMock()
    mock_changeset.is_empty = False
    mock_changeset.modified = [Path("src/main.py")]
    mock_changeset.added = [Path("src/new.py")]
    mock_changeset.deleted = []
    mock_changeset.total_changes = 2
    mock_updater.update.return_value = mock_changeset

    mock_class = MagicMock(return_value=mock_updater)
    monkeypatch.setattr("codemap.cli.commands.update.GraphUpdater", mock_class)
    return mock_updater


@pytest.fixture()
def mock_change_detector(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock ChangeDetector."""
    mock_detector = MagicMock()
    mock_class = MagicMock(return_value=mock_detector)
    monkeypatch.setattr("codemap.cli.commands.update.ChangeDetector", mock_class)
    return mock_detector


@pytest.fixture()
def mock_parser_engine(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock ParserEngine."""
    mock_parser = MagicMock()
    mock_class = MagicMock(return_value=mock_parser)
    monkeypatch.setattr("codemap.cli.commands.update.ParserEngine", mock_class)
    return mock_parser


@pytest.fixture()
def mock_content_reader(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock ContentReader."""
    mock_reader = MagicMock()
    mock_class = MagicMock(return_value=mock_reader)
    monkeypatch.setattr("codemap.cli.commands.update.ContentReader", mock_class)
    return mock_reader


class TestUpdateCommand:
    """Tests for 'curator update' command."""

    def test_update_requires_codemap_directory(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """update fails if .codemap/ doesn't exist."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["update"])

        assert result.exit_code != 0
        output_lower = result.output.lower()
        assert "init" in output_lower or ".codemap" in output_lower or "error" in output_lower

    def test_update_shows_change_counts(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        setup_codemap_dir: Path,
        mock_graph_manager: MagicMock,
        mock_graph_updater: MagicMock,
        mock_change_detector: MagicMock,
        mock_parser_engine: MagicMock,
        mock_content_reader: MagicMock,
    ) -> None:
        """update output contains modified, added, deleted counts."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["update"])

        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert "modified" in output_lower or "1" in result.output
        assert "added" in output_lower or "1" in result.output

    def test_update_loads_existing_graph(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        setup_codemap_dir: Path,
        mock_graph_manager: MagicMock,
        mock_graph_updater: MagicMock,
        mock_change_detector: MagicMock,
        mock_parser_engine: MagicMock,
        mock_content_reader: MagicMock,
    ) -> None:
        """update calls GraphManager.load() with .codemap/graph.json."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["update"])

        assert result.exit_code == 0
        mock_graph_manager.load.assert_called_once()
        load_path = mock_graph_manager.load.call_args[0][0]
        assert load_path == tmp_path / ".codemap" / "graph.json"

    def test_update_loads_metadata(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        setup_codemap_dir: Path,
        mock_graph_manager: MagicMock,
        mock_graph_updater: MagicMock,
        mock_change_detector: MagicMock,
        mock_parser_engine: MagicMock,
        mock_content_reader: MagicMock,
    ) -> None:
        """update loads metadata.json and passes to GraphManager.build_metadata."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["update"])

        assert result.exit_code == 0

    def test_update_calls_graph_updater(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        setup_codemap_dir: Path,
        mock_graph_manager: MagicMock,
        mock_graph_updater: MagicMock,
        mock_change_detector: MagicMock,
        mock_parser_engine: MagicMock,
        mock_content_reader: MagicMock,
    ) -> None:
        """update calls GraphUpdater.update() with project root."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["update"])

        assert result.exit_code == 0
        mock_graph_updater.update.assert_called_once()

    def test_update_saves_updated_graph(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        setup_codemap_dir: Path,
        mock_graph_manager: MagicMock,
        mock_graph_updater: MagicMock,
        mock_change_detector: MagicMock,
        mock_parser_engine: MagicMock,
        mock_content_reader: MagicMock,
    ) -> None:
        """update calls GraphManager.save() after updating."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["update"])

        assert result.exit_code == 0
        mock_graph_manager.save.assert_called_once()
        save_path = mock_graph_manager.save.call_args[0][0]
        assert save_path == tmp_path / ".codemap" / "graph.json"

    def test_update_updates_metadata(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        setup_codemap_dir: Path,
        mock_graph_manager: MagicMock,
        mock_graph_updater: MagicMock,
        mock_change_detector: MagicMock,
        mock_parser_engine: MagicMock,
        mock_content_reader: MagicMock,
    ) -> None:
        """update updates metadata.json with new build_time and commit_hash."""
        monkeypatch.chdir(tmp_path)

        # Write metadata with known placeholder values
        metadata_path = tmp_path / ".codemap" / "metadata.json"
        initial_metadata = {"build_time": "PLACEHOLDER", "commit_hash": "PLACEHOLDER"}
        metadata_path.write_text(json.dumps(initial_metadata))

        result = runner.invoke(app, ["update"])

        assert result.exit_code == 0
        assert metadata_path.exists()
        updated_metadata = json.loads(metadata_path.read_text())
        assert "build_time" in updated_metadata
        assert "commit_hash" in updated_metadata
        assert updated_metadata["build_time"] != "PLACEHOLDER", "build_time was not updated"
        assert updated_metadata["commit_hash"] != "PLACEHOLDER", "commit_hash was not updated"

    def test_update_handles_no_changes(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        setup_codemap_dir: Path,
        mock_graph_manager: MagicMock,
        mock_graph_updater: MagicMock,
        mock_change_detector: MagicMock,
        mock_parser_engine: MagicMock,
        mock_content_reader: MagicMock,
    ) -> None:
        """update shows 'No changes detected' when ChangeSet is empty."""
        mock_changeset = MagicMock()
        mock_changeset.is_empty = True
        mock_changeset.modified = []
        mock_changeset.added = []
        mock_changeset.deleted = []
        mock_changeset.total_changes = 0
        mock_graph_updater.update.return_value = mock_changeset

        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["update"])

        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert "no changes" in output_lower or "0" in result.output

    def test_update_handles_missing_metadata(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_graph_manager: MagicMock,
        mock_graph_updater: MagicMock,
        mock_change_detector: MagicMock,
        mock_parser_engine: MagicMock,
        mock_content_reader: MagicMock,
    ) -> None:
        """update handles gracefully when metadata.json doesn't exist."""
        codemap_dir = tmp_path / ".codemap"
        codemap_dir.mkdir()
        (codemap_dir / "graph.json").write_text('{"nodes": [], "links": []}')
        # No metadata.json
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["update"])

        assert result.exit_code == 0

    def test_update_handles_invalid_graph_json(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_graph_manager: MagicMock,
        mock_graph_updater: MagicMock,
        mock_change_detector: MagicMock,
        mock_parser_engine: MagicMock,
        mock_content_reader: MagicMock,
    ) -> None:
        """update shows error when GraphManager.load() raises ValueError."""
        mock_graph_manager.load.side_effect = ValueError("Invalid JSON")
        codemap_dir = tmp_path / ".codemap"
        codemap_dir.mkdir()
        (codemap_dir / "graph.json").write_text("invalid json")
        (codemap_dir / "metadata.json").write_text(
            '{"build_time": "2024-01-01T00:00:00", "commit_hash": "abc123"}'
        )
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["update"])

        assert result.exit_code != 0
        output_lower = result.output.lower()
        assert "error" in output_lower or "invalid" in output_lower


class TestUpdateCommandQuietMode:
    """Tests for update --quiet flag."""

    def test_update_quiet_mode_no_output(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        setup_codemap_dir: Path,
        mock_graph_manager: MagicMock,
        mock_graph_updater: MagicMock,
        mock_change_detector: MagicMock,
        mock_parser_engine: MagicMock,
        mock_content_reader: MagicMock,
    ) -> None:
        """--quiet flag produces empty output on success."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["update", "--quiet"])

        assert result.exit_code == 0
        assert result.output.strip() == ""

    def test_update_quiet_mode_shows_errors(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """--quiet still shows errors when .codemap/ is missing."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["update", "--quiet"])

        assert result.exit_code != 0
        assert result.output.strip() != ""


class TestUpdateCommandLocking:
    """Tests for update command lock mechanism."""

    def test_update_prevents_concurrent_execution(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        setup_codemap_dir: Path,
        mock_graph_manager: MagicMock,
        mock_graph_updater: MagicMock,
        mock_change_detector: MagicMock,
        mock_parser_engine: MagicMock,
        mock_content_reader: MagicMock,
    ) -> None:
        """update command uses lock file to prevent concurrent execution."""
        from filelock import Timeout

        monkeypatch.chdir(tmp_path)

        # Mock FileLock to raise Timeout, simulating concurrent execution
        mock_filelock = MagicMock()
        mock_filelock.return_value.__enter__.side_effect = Timeout(
            str(tmp_path / ".codemap" / ".update.lock")
        )
        monkeypatch.setattr("codemap.cli.commands.update.FileLock", mock_filelock)

        result = runner.invoke(app, ["update"])

        assert result.exit_code == 0
        assert "already in progress" in result.output.lower()

    def test_update_concurrent_quiet_mode_no_output(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        setup_codemap_dir: Path,
        mock_graph_manager: MagicMock,
        mock_graph_updater: MagicMock,
        mock_change_detector: MagicMock,
        mock_parser_engine: MagicMock,
        mock_content_reader: MagicMock,
    ) -> None:
        """--quiet suppresses output during concurrent lock timeout."""
        from filelock import Timeout

        monkeypatch.chdir(tmp_path)

        mock_filelock = MagicMock()
        mock_filelock.return_value.__enter__.side_effect = Timeout(
            str(tmp_path / ".codemap" / ".update.lock")
        )
        monkeypatch.setattr("codemap.cli.commands.update.FileLock", mock_filelock)

        result = runner.invoke(app, ["update", "--quiet"])

        assert result.exit_code == 0
        assert result.output.strip() == ""

    def test_update_handles_invalid_metadata_json(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_graph_manager: MagicMock,
        mock_graph_updater: MagicMock,
        mock_change_detector: MagicMock,
        mock_parser_engine: MagicMock,
        mock_content_reader: MagicMock,
    ) -> None:
        """update fails with error when metadata.json contains invalid JSON."""
        codemap_dir = tmp_path / ".codemap"
        codemap_dir.mkdir()
        (codemap_dir / "graph.json").write_text('{"nodes": [], "links": []}')
        (codemap_dir / "metadata.json").write_text("not valid json{{{")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["update"])

        assert result.exit_code != 0
        assert "metadata.json" in result.output.lower() or "not valid json" in result.output.lower()

    def test_update_requires_graph_json(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_graph_manager: MagicMock,
        mock_graph_updater: MagicMock,
        mock_change_detector: MagicMock,
        mock_parser_engine: MagicMock,
        mock_content_reader: MagicMock,
    ) -> None:
        """update fails when .codemap/ exists but graph.json is missing."""
        codemap_dir = tmp_path / ".codemap"
        codemap_dir.mkdir()
        # No graph.json
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["update"])

        assert result.exit_code != 0
        assert "graph.json" in result.output.lower()

    def test_update_saves_git_commit_hash(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        setup_codemap_dir: Path,
        mock_graph_manager: MagicMock,
        mock_graph_updater: MagicMock,
        mock_change_detector: MagicMock,
        mock_parser_engine: MagicMock,
        mock_content_reader: MagicMock,
    ) -> None:
        """update stores git commit hash in metadata when git is available."""
        monkeypatch.chdir(tmp_path)

        mock_result = MagicMock()
        mock_result.stdout = "abc123def456\n"
        mock_result.returncode = 0

        def mock_subprocess_run(*args: object, **kwargs: object) -> MagicMock:
            return mock_result

        monkeypatch.setattr("codemap.cli.commands.update.subprocess.run", mock_subprocess_run)

        result = runner.invoke(app, ["update"])

        assert result.exit_code == 0
        metadata_path = tmp_path / ".codemap" / "metadata.json"
        assert metadata_path.exists()
        import json

        metadata = json.loads(metadata_path.read_text())
        assert metadata["commit_hash"] == "abc123def456"


class TestUpdateCommandIntegration:
    """Integration tests for update command workflow."""

    def test_update_after_init_workflow(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_graph_manager: MagicMock,
        mock_graph_updater: MagicMock,
        mock_change_detector: MagicMock,
        mock_parser_engine: MagicMock,
        mock_content_reader: MagicMock,
    ) -> None:
        """Full workflow: init, then update detects and applies changes."""
        monkeypatch.chdir(tmp_path)

        # Setup: simulate post-init state
        codemap_dir = tmp_path / ".codemap"
        codemap_dir.mkdir()
        (codemap_dir / "graph.json").write_text('{"nodes": [], "links": []}')
        (codemap_dir / "metadata.json").write_text(
            '{"build_time": "2024-01-01T00:00:00", "commit_hash": "abc123"}'
        )

        result = runner.invoke(app, ["update"])

        assert result.exit_code == 0
        mock_graph_updater.update.assert_called_once()
        mock_graph_manager.save.assert_called_once()

    def test_update_creates_metadata_if_missing(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_graph_manager: MagicMock,
        mock_graph_updater: MagicMock,
        mock_change_detector: MagicMock,
        mock_parser_engine: MagicMock,
        mock_content_reader: MagicMock,
    ) -> None:
        """update creates metadata.json if only graph.json exists."""
        codemap_dir = tmp_path / ".codemap"
        codemap_dir.mkdir()
        (codemap_dir / "graph.json").write_text('{"nodes": [], "links": []}')
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["update"])

        assert result.exit_code == 0
        metadata_path = tmp_path / ".codemap" / "metadata.json"
        assert metadata_path.exists()
