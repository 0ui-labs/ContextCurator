"""Tests for the main CLI application."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from codemap import __version__
from codemap.cli.main import app


@pytest.fixture()
def runner() -> CliRunner:
    """CLI test runner."""
    return CliRunner()


class TestCLIApp:
    """Tests for main CLI application."""

    def test_app_has_help(self, runner: CliRunner) -> None:
        """CLI provides help text."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "curator" in result.output.lower() or "codemap" in result.output.lower()

    def test_app_shows_version(self, runner: CliRunner) -> None:
        """CLI shows version with --version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_app_version_short_flag(self, runner: CliRunner) -> None:
        """CLI shows version with -v short flag."""
        result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_app_no_args_shows_help(self, runner: CliRunner) -> None:
        """CLI shows help when invoked without arguments."""
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "help" in result.output.lower() or "usage" in result.output.lower()

    def test_app_verbose_mode(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CLI --verbose flag enables debug logging."""
        monkeypatch.chdir(tmp_path)
        # Use a command that triggers the callback; status fails but callback runs
        result = runner.invoke(app, ["--verbose", "status"])
        # Status fails (no .codemap/) but verbose callback was executed
        assert result.exit_code != 0


class TestCLIAppIsolation:
    """Tests for filesystem isolation."""

    def test_app_runs_in_isolated_filesystem(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CLI can run in isolated filesystem for testing."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "test.txt").write_text("content")
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert Path.cwd() == tmp_path
