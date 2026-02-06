"""Tests for curator init command."""

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
def mock_mapbuilder(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock MapBuilder with build() returning GraphManager."""
    mock_builder = MagicMock()
    mock_graph_manager = MagicMock()
    mock_graph_manager.graph_stats = {"nodes": 5, "edges": 3}
    mock_builder.build.return_value = mock_graph_manager

    mock_class = MagicMock(return_value=mock_builder)
    monkeypatch.setattr("codemap.cli.commands.init.MapBuilder", mock_class)
    return mock_builder


class TestInitCommand:
    """Tests for 'curator init' command."""

    def test_init_creates_codemap_directory(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_mapbuilder: MagicMock,
    ) -> None:
        """init creates .codemap/ directory in project root."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def foo(): pass")

        result = runner.invoke(app, ["init", str(tmp_path)])

        assert result.exit_code == 0
        assert (tmp_path / ".codemap").is_dir()

    def test_init_creates_graph_json(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_mapbuilder: MagicMock,
    ) -> None:
        """init creates graph.json with valid JSON structure."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def foo(): pass")

        result = runner.invoke(app, ["init", str(tmp_path)])

        assert result.exit_code == 0
        mock_gm = mock_mapbuilder.build.return_value
        mock_gm.save.assert_called_once()
        save_path = mock_gm.save.call_args[0][0]
        assert save_path == tmp_path / ".codemap" / "graph.json"

    def test_init_creates_metadata_json(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_mapbuilder: MagicMock,
    ) -> None:
        """init creates metadata.json with build_time and commit_hash fields."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def foo(): pass")

        result = runner.invoke(app, ["init", str(tmp_path)])

        assert result.exit_code == 0
        metadata_path = tmp_path / ".codemap" / "metadata.json"
        assert metadata_path.exists()
        metadata = json.loads(metadata_path.read_text())
        assert "build_time" in metadata
        assert "commit_hash" in metadata

    def test_init_shows_statistics(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_mapbuilder: MagicMock,
    ) -> None:
        """init output contains node/edge counts from graph_stats."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def foo(): pass")

        result = runner.invoke(app, ["init", str(tmp_path)])

        assert result.exit_code == 0
        assert "5" in result.output
        assert "3" in result.output

    def test_init_warns_on_existing_codemap(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_mapbuilder: MagicMock,
    ) -> None:
        """init warns when .codemap/ already exists but continues."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".codemap").mkdir()
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def foo(): pass")

        result = runner.invoke(app, ["init", str(tmp_path)])

        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert "exist" in output_lower or "already" in output_lower or "warning" in output_lower

    def test_init_fails_on_nonexistent_path(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """init fails with clear error for non-existent path."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["init", "nonexistent"])

        assert result.exit_code != 0
        output_lower = result.output.lower()
        assert (
            "not found" in output_lower
            or "does not exist" in output_lower
            or "error" in output_lower
        )

    def test_init_fails_on_file_path(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """init fails when path argument is a file, not directory."""
        monkeypatch.chdir(tmp_path)
        file_path = tmp_path / "not_a_dir.txt"
        file_path.write_text("content")

        result = runner.invoke(app, ["init", str(file_path)])

        assert result.exit_code != 0
        output_lower = result.output.lower()
        assert (
            "directory" in output_lower
            or "not a directory" in output_lower
            or "error" in output_lower
        )

    def test_init_default_path_is_current_directory(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_mapbuilder: MagicMock,
    ) -> None:
        """init without path argument uses current working directory."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def foo(): pass")

        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert (tmp_path / ".codemap").is_dir()


class TestInitCommandMocking:
    """Tests for init command with mocked dependencies."""

    def test_init_calls_mapbuilder_build(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_mapbuilder: MagicMock,
    ) -> None:
        """init calls MapBuilder.build() with correct path."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def foo(): pass")

        result = runner.invoke(app, ["init", str(tmp_path)])

        assert result.exit_code == 0
        mock_mapbuilder.build.assert_called_once()
        call_args = mock_mapbuilder.build.call_args
        assert call_args[0][0] == tmp_path or call_args[0][0] == Path(str(tmp_path))

    def test_init_saves_graph_via_graphmanager(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_mapbuilder: MagicMock,
    ) -> None:
        """init calls GraphManager.save() with .codemap/graph.json."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def foo(): pass")

        result = runner.invoke(app, ["init", str(tmp_path)])

        assert result.exit_code == 0
        mock_gm = mock_mapbuilder.build.return_value
        mock_gm.save.assert_called_once()
        save_path = mock_gm.save.call_args[0][0]
        assert save_path == tmp_path / ".codemap" / "graph.json"

    def test_init_handles_git_unavailable(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_mapbuilder: MagicMock,
    ) -> None:
        """init handles git being unavailable by setting commit_hash to None."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def foo(): pass")

        def mock_subprocess_run(*args: object, **kwargs: object) -> None:
            raise FileNotFoundError("git not found")

        monkeypatch.setattr("codemap.cli.commands.init.subprocess.run", mock_subprocess_run)

        result = runner.invoke(app, ["init", str(tmp_path)])

        assert result.exit_code == 0
        metadata_path = tmp_path / ".codemap" / "metadata.json"
        assert metadata_path.exists()
        metadata = json.loads(metadata_path.read_text())
        assert metadata["commit_hash"] is None

    def test_init_stores_git_commit_hash(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_mapbuilder: MagicMock,
    ) -> None:
        """init stores git commit hash in metadata.json."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def foo(): pass")

        mock_result = MagicMock()
        mock_result.stdout = "abc123def456\n"
        mock_result.returncode = 0

        def mock_subprocess_run(*args: object, **kwargs: object) -> MagicMock:
            return mock_result

        monkeypatch.setattr("codemap.cli.commands.init.subprocess.run", mock_subprocess_run)

        result = runner.invoke(app, ["init", str(tmp_path)])

        assert result.exit_code == 0
        metadata_path = tmp_path / ".codemap" / "metadata.json"
        assert metadata_path.exists()
        metadata = json.loads(metadata_path.read_text())
        assert metadata["commit_hash"] == "abc123def456"
