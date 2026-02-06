"""End-to-end workflow tests for the curator CLI."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from codemap.cli.main import app


class TestCompleteWorkflow:
    """Tests for the complete init -> update -> status -> install-hook workflow."""

    def test_init_update_status_install_hook(
        self,
        cli_runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Complete workflow: init, update after change, status, install-hook."""
        src_dir = git_repo / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("def hello():\n    return 'hello'\n")
        (src_dir / "utils.py").write_text("def add(a, b):\n    return a + b\n")
        (git_repo / ".gitignore").write_text(".codemap/\n")

        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        monkeypatch.chdir(git_repo)

        # Step 1: Init
        result = cli_runner.invoke(app, ["init", str(git_repo)])
        assert result.exit_code == 0
        assert (git_repo / ".codemap").is_dir()
        assert (git_repo / ".codemap" / "graph.json").exists()
        assert (git_repo / ".codemap" / "metadata.json").exists()

        # Step 2: Modify file and commit
        (src_dir / "main.py").write_text(
            "def hello():\n    return 'hello world'\n\n"
            "def greet(name):\n    return f'Hello, {name}'\n"
        )
        subprocess.run(["git", "add", "src/"], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add greet function"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Step 3: Update
        result = cli_runner.invoke(app, ["update"])
        assert result.exit_code == 0

        # Step 4: Status
        result = cli_runner.invoke(app, ["status"])
        assert result.exit_code == 0

        # Step 5: Install hook
        result = cli_runner.invoke(app, ["install-hook"])
        assert result.exit_code == 0
        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        assert hook_path.exists()
        assert "curator update" in hook_path.read_text()


class TestInitWorkflow:
    """Tests for curator init in different scenarios."""

    def test_init_empty_project(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """init on empty directory succeeds with 0 nodes, 0 edges."""
        monkeypatch.chdir(tmp_path)

        result = cli_runner.invoke(app, ["init", str(tmp_path)])

        assert result.exit_code == 0
        assert (tmp_path / ".codemap" / "graph.json").exists()
        graph_data = json.loads((tmp_path / ".codemap" / "graph.json").read_bytes())
        assert isinstance(graph_data, dict)

    def test_init_with_dependencies(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """init captures import relationships between files."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "a.py").write_text("import utils\n\ndef func_a():\n    return utils.add(1, 2)\n")
        (src_dir / "utils.py").write_text("def add(a, b):\n    return a + b\n")

        monkeypatch.chdir(tmp_path)
        result = cli_runner.invoke(app, ["init", str(tmp_path)])

        assert result.exit_code == 0
        assert "nodes" in result.output
        assert "edges" in result.output

    def test_init_with_git_stores_commit_hash(
        self,
        cli_runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """init in git repo stores commit_hash in metadata.json."""
        src_dir = git_repo / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("def hello(): pass\n")

        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        monkeypatch.chdir(git_repo)
        result = cli_runner.invoke(app, ["init", str(git_repo)])

        assert result.exit_code == 0
        metadata = json.loads((git_repo / ".codemap" / "metadata.json").read_text())
        assert "build_time" in metadata
        assert metadata["commit_hash"] is not None


class TestUpdateWorkflow:
    """Tests for curator update in different scenarios."""

    def test_update_no_changes(
        self,
        cli_runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """update immediately after init shows 'No changes detected.'."""
        src_dir = git_repo / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("def hello(): pass\n")

        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        monkeypatch.chdir(git_repo)
        cli_runner.invoke(app, ["init", str(git_repo)])

        result = cli_runner.invoke(app, ["update"])

        assert result.exit_code == 0
        assert "no changes" in result.output.lower()

    def test_update_with_multiple_change_types(
        self,
        cli_runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """update detects modified, added, and deleted files."""
        src_dir = git_repo / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("def hello(): pass\n")
        (src_dir / "utils.py").write_text("def add(a, b): return a + b\n")
        (src_dir / "old.py").write_text("def old(): pass\n")
        (git_repo / ".gitignore").write_text(".codemap/\n")

        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        monkeypatch.chdir(git_repo)
        cli_runner.invoke(app, ["init", str(git_repo)])

        # Modify, add, delete
        (src_dir / "main.py").write_text("def hello(): return 'modified'\n")
        (src_dir / "new.py").write_text("def new_func(): pass\n")
        (src_dir / "old.py").unlink()

        subprocess.run(["git", "add", "-A"], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Changes"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        result = cli_runner.invoke(app, ["update"])

        assert result.exit_code == 0
        assert "1 modified" in result.output
        assert "1 added" in result.output
        assert "1 deleted" in result.output


class TestStatusWorkflow:
    """Tests for curator status in different scenarios."""

    def test_status_from_subdirectory(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """status finds .codemap/ in parent directory."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("def hello(): pass\n")

        monkeypatch.chdir(tmp_path)
        init_result = cli_runner.invoke(app, ["init", str(tmp_path)])
        assert init_result.exit_code == 0

        sub_dir = tmp_path / "src" / "deep" / "nested"
        sub_dir.mkdir(parents=True)
        monkeypatch.chdir(sub_dir)

        result = cli_runner.invoke(app, ["status"])

        assert result.exit_code == 0


class TestNonGitRepository:
    """Tests for CLI commands in non-git directories."""

    def test_init_succeeds_without_git(
        self,
        cli_runner: CliRunner,
        sample_project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """init succeeds without git, commit_hash is null."""
        monkeypatch.chdir(sample_project)

        result = cli_runner.invoke(app, ["init", str(sample_project)])

        assert result.exit_code == 0
        metadata = json.loads((sample_project / ".codemap" / "metadata.json").read_text())
        assert metadata["commit_hash"] is None

    def test_install_hook_fails_without_git(
        self,
        cli_runner: CliRunner,
        sample_project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """install-hook fails with error when not in a git repository."""
        monkeypatch.chdir(sample_project)

        result = cli_runner.invoke(app, ["install-hook"])

        assert result.exit_code != 0
        output_lower = result.output.lower()
        assert "git" in output_lower or "repository" in output_lower


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_init_invalid_path(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """init fails for non-existent path with exit code 2."""
        monkeypatch.chdir(tmp_path)

        result = cli_runner.invoke(app, ["init", "/nonexistent/path"])

        assert result.exit_code == 2

    def test_update_without_init(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """update fails with exit code 1 when .codemap/ doesn't exist."""
        monkeypatch.chdir(tmp_path)

        result = cli_runner.invoke(app, ["update"])

        assert result.exit_code == 1
        assert "init" in result.output.lower()

    def test_status_corrupted_graph_json(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """status fails with exit code 1 for corrupted graph.json."""
        monkeypatch.chdir(tmp_path)
        codemap_dir = tmp_path / ".codemap"
        codemap_dir.mkdir()
        (codemap_dir / "graph.json").write_text("not valid json{{{")

        result = cli_runner.invoke(app, ["status"])

        assert result.exit_code == 1

    def test_concurrent_update_prevention(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """update skips with 'already in progress' when lock is held."""
        from filelock import Timeout

        monkeypatch.chdir(tmp_path)
        codemap_dir = tmp_path / ".codemap"
        codemap_dir.mkdir()
        (codemap_dir / "graph.json").write_text('{"nodes": [], "links": []}')
        (codemap_dir / "metadata.json").write_text(
            '{"build_time": "2024-01-01", "commit_hash": null}'
        )

        mock_lock = MagicMock()
        mock_lock.return_value.__enter__.side_effect = Timeout(str(codemap_dir / ".update.lock"))
        monkeypatch.setattr("codemap.cli.commands.update.FileLock", mock_lock)

        result = cli_runner.invoke(app, ["update"])

        assert result.exit_code == 0
        assert "already in progress" in result.output.lower()
