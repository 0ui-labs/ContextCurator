"""Fixtures for CLI integration tests."""

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner


@pytest.fixture()
def cli_runner() -> CliRunner:
    """CLI test runner."""
    return CliRunner()


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Create a real git repository with user config."""
    subprocess.run(
        ["git", "init", str(tmp_path)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    return tmp_path


@pytest.fixture()
def sample_project(tmp_path: Path) -> Path:
    """Create a minimal Python project with sample .py files."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("def hello():\n    return 'hello'\n")
    (src_dir / "utils.py").write_text("def add(a, b):\n    return a + b\n")
    return tmp_path
