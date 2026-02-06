"""Tests for git hook execution in real git repositories."""

import shutil
import stat
import subprocess
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from codemap.cli.main import app


@pytest.fixture()
def mock_curator_path(monkeypatch: pytest.MonkeyPatch) -> str:
    """Mock shutil.which to return a known curator path."""
    fake_path = "/usr/local/bin/curator"
    monkeypatch.setattr(
        "codemap.cli.commands.hooks.shutil.which",
        lambda cmd: fake_path if cmd == "curator" else None,
    )
    return fake_path


class TestHookExecution:
    """Tests for git hook execution after commits."""

    @pytest.mark.skipif(
        shutil.which("curator") is None,
        reason="curator not installed in PATH",
    )
    def test_hook_executes_after_commit(
        self,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Post-commit hook triggers curator update after git commit."""
        src_dir = git_repo / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("def hello(): pass\n")
        (git_repo / ".gitignore").write_text(".codemap/\n")

        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        monkeypatch.chdir(git_repo)
        runner = CliRunner()
        runner.invoke(app, ["init", str(git_repo)])
        runner.invoke(app, ["install-hook"])

        graph_path = git_repo / ".codemap" / "graph.json"
        initial_mtime = graph_path.stat().st_mtime

        # Modify and commit (hook fires in background)
        (src_dir / "main.py").write_text("def hello(): return 'modified'\n")
        subprocess.run(["git", "add", "src/"], cwd=git_repo, check=True, capture_output=True)
        time.sleep(0.1)  # Ensure mtime difference is detectable
        subprocess.run(
            ["git", "commit", "-m", "Modify hello"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Poll for background hook to complete
        max_wait = 5.0
        poll_interval = 0.3
        elapsed = 0.0
        while elapsed < max_wait:
            if graph_path.stat().st_mtime > initial_mtime:
                break
            time.sleep(poll_interval)
            elapsed += poll_interval

        assert graph_path.stat().st_mtime > initial_mtime, (
            "graph.json should have been updated by the post-commit hook"
        )

    def test_hook_is_non_blocking(
        self,
        cli_runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_curator_path: str,
    ) -> None:
        """Hook runs curator update in background with output redirected."""
        monkeypatch.chdir(git_repo)
        cli_runner.invoke(app, ["install-hook"])

        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        content = hook_path.read_text()
        assert "> /dev/null 2>&1" in content
        curator_lines = [
            line for line in content.splitlines() if "curator" in line and "update" in line
        ]
        assert len(curator_lines) >= 1
        assert any(line.rstrip().endswith("&") for line in curator_lines)


class TestHookContentPreservation:
    """Tests for hook content preservation during install/uninstall."""

    def test_hook_preserves_existing_content(
        self,
        cli_runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_curator_path: str,
    ) -> None:
        """install-hook preserves existing hook content and appends curator section."""
        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        hook_path.parent.mkdir(exist_ok=True)
        hook_path.write_text("#!/bin/sh\necho 'custom hook'\n")
        hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR)

        monkeypatch.chdir(git_repo)
        result = cli_runner.invoke(app, ["install-hook"])

        assert result.exit_code == 0
        content = hook_path.read_text()
        assert "custom hook" in content
        assert "curator update" in content

    def test_hook_uninstall_preserves_other_content(
        self,
        cli_runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_curator_path: str,
    ) -> None:
        """uninstall-hook removes curator section but keeps custom content."""
        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        hook_path.parent.mkdir(exist_ok=True)
        hook_path.write_text("#!/bin/sh\necho 'custom hook'\n")
        hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR)

        monkeypatch.chdir(git_repo)
        cli_runner.invoke(app, ["install-hook"])
        result = cli_runner.invoke(app, ["uninstall-hook"])

        assert result.exit_code == 0
        content = hook_path.read_text()
        assert "custom hook" in content
        assert "# curator-hook-start" not in content

    def test_hook_idempotency(
        self,
        cli_runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_curator_path: str,
    ) -> None:
        """Running install-hook three times produces exactly one curator section."""
        monkeypatch.chdir(git_repo)

        cli_runner.invoke(app, ["install-hook"])
        cli_runner.invoke(app, ["install-hook"])
        cli_runner.invoke(app, ["install-hook"])

        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        content = hook_path.read_text()
        assert content.count("# curator-hook-start") == 1
        mode = hook_path.stat().st_mode
        assert mode & stat.S_IXUSR, "Hook should be executable"
