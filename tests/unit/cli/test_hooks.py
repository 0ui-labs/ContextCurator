"""Tests for curator install-hook and uninstall-hook commands."""

import stat
from pathlib import Path

import pytest
from typer.testing import CliRunner

from codemap.cli.main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def runner() -> CliRunner:
    """CLI test runner."""
    return CliRunner()


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Create a minimal git repository with hooks directory."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir()
    return tmp_path


@pytest.fixture()
def existing_hook(git_repo: Path) -> Path:
    """Create a pre-populated post-commit hook file."""
    hook_path = git_repo / ".git" / "hooks" / "post-commit"
    hook_path.write_text("#!/bin/sh\necho 'existing hook'\n")
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR)
    return hook_path


@pytest.fixture()
def mock_curator_path(monkeypatch: pytest.MonkeyPatch) -> str:
    """Mock shutil.which('curator') to return a known absolute path."""
    fake_path = "/usr/local/bin/curator"
    monkeypatch.setattr(
        "codemap.cli.commands.hooks.shutil.which",
        lambda cmd: fake_path if cmd == "curator" else None,
    )
    return fake_path


# ---------------------------------------------------------------------------
# TestInstallHookCommand - Basic functionality
# ---------------------------------------------------------------------------


class TestInstallHookCommand:
    """Tests for basic 'curator install-hook' functionality."""

    def test_install_hook_creates_post_commit(
        self,
        runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_curator_path: str,
    ) -> None:
        """install-hook creates .git/hooks/post-commit file."""
        monkeypatch.chdir(git_repo)

        result = runner.invoke(app, ["install-hook"])

        assert result.exit_code == 0
        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        assert hook_path.exists()

    def test_install_hook_is_executable(
        self,
        runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_curator_path: str,
    ) -> None:
        """install-hook makes the hook file executable."""
        monkeypatch.chdir(git_repo)

        runner.invoke(app, ["install-hook"])

        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        mode = hook_path.stat().st_mode
        assert mode & stat.S_IXUSR, "Hook file should have user execute permission"

    def test_install_hook_contains_curator_update(
        self,
        runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_curator_path: str,
    ) -> None:
        """install-hook content contains 'curator update' command."""
        monkeypatch.chdir(git_repo)

        runner.invoke(app, ["install-hook"])

        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        content = hook_path.read_text()
        assert "curator update" in content

    def test_install_hook_runs_in_background(
        self,
        runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_curator_path: str,
    ) -> None:
        """install-hook runs the update command in background with '&'."""
        monkeypatch.chdir(git_repo)

        runner.invoke(app, ["install-hook"])

        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        content = hook_path.read_text()
        assert "&" in content, "Hook should run curator update in background"
        assert "> /dev/null 2>&1" in content, "Hook should redirect output to /dev/null"

    def test_install_hook_uses_absolute_path(
        self,
        runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_curator_path: str,
    ) -> None:
        """install-hook uses absolute path to the curator executable."""
        monkeypatch.chdir(git_repo)

        runner.invoke(app, ["install-hook"])

        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        content = hook_path.read_text()
        assert mock_curator_path in content, "Hook should contain absolute path to curator"


# ---------------------------------------------------------------------------
# TestInstallHookIdempotency - Repeated installation / preservation
# ---------------------------------------------------------------------------


class TestInstallHookIdempotency:
    """Tests for idempotent hook installation and existing hook preservation."""

    def test_install_hook_idempotent(
        self,
        runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_curator_path: str,
    ) -> None:
        """Running install-hook twice does not duplicate hook content."""
        monkeypatch.chdir(git_repo)

        runner.invoke(app, ["install-hook"])
        first_content = (git_repo / ".git" / "hooks" / "post-commit").read_text()

        result = runner.invoke(app, ["install-hook"])

        assert result.exit_code == 0
        second_content = (git_repo / ".git" / "hooks" / "post-commit").read_text()
        assert first_content == second_content, "Content should not change on re-install"

    def test_install_hook_preserves_existing_content(
        self,
        runner: CliRunner,
        git_repo: Path,
        existing_hook: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_curator_path: str,
    ) -> None:
        """install-hook preserves existing hook content and appends curator section."""
        monkeypatch.chdir(git_repo)

        runner.invoke(app, ["install-hook"])

        content = existing_hook.read_text()
        assert "existing hook" in content, "Original hook content should be preserved"
        assert "curator update" in content, "Curator hook should be appended"

    def test_install_hook_no_duplicate_markers(
        self,
        runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_curator_path: str,
    ) -> None:
        """install-hook uses marker comments and does not duplicate them."""
        monkeypatch.chdir(git_repo)

        runner.invoke(app, ["install-hook"])
        runner.invoke(app, ["install-hook"])

        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        content = hook_path.read_text()
        assert content.count("# curator-hook-start") == 1, "Should have exactly one start marker"
        assert content.count("# curator-hook-end") == 1, "Should have exactly one end marker"

    def test_install_hook_no_duplicate_shebang(
        self,
        runner: CliRunner,
        git_repo: Path,
        existing_hook: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_curator_path: str,
    ) -> None:
        """install-hook does not duplicate the shebang when hook already has one."""
        monkeypatch.chdir(git_repo)

        runner.invoke(app, ["install-hook"])

        content = existing_hook.read_text()
        assert content.count("#!/bin/sh") == 1, "Shebang should appear exactly once"


# ---------------------------------------------------------------------------
# TestInstallHookEdgeCases - Error handling and edge cases
# ---------------------------------------------------------------------------


class TestInstallHookEdgeCases:
    """Tests for install-hook error handling and edge cases."""

    def test_install_hook_not_git_repo_fails(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """install-hook fails when not inside a git repository."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["install-hook"])

        assert result.exit_code != 0
        output_lower = result.output.lower()
        assert "git" in output_lower or "repository" in output_lower

    def test_install_hook_searches_parent_directories(
        self,
        runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_curator_path: str,
    ) -> None:
        """install-hook finds .git/ by searching parent directories."""
        sub_dir = git_repo / "src" / "deep" / "nested"
        sub_dir.mkdir(parents=True)
        monkeypatch.chdir(sub_dir)

        result = runner.invoke(app, ["install-hook"])

        assert result.exit_code == 0
        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        assert hook_path.exists()

    def test_install_hook_handles_permission_error(
        self,
        runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_curator_path: str,
    ) -> None:
        """install-hook shows error when write permissions are missing."""
        monkeypatch.chdir(git_repo)

        original_write_text = Path.write_text

        def mock_write_text(self: Path, *args: object, **kwargs: object) -> None:
            if "post-commit" in str(self):
                raise PermissionError("Permission denied")
            original_write_text(self, *args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, "write_text", mock_write_text)

        result = runner.invoke(app, ["install-hook"])

        assert result.exit_code != 0
        output_lower = result.output.lower()
        assert "permission" in output_lower or "error" in output_lower

    def test_install_hook_fallback_to_sys_argv(
        self,
        runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """install-hook falls back to sys.argv[0] when shutil.which returns None."""
        monkeypatch.chdir(git_repo)
        monkeypatch.setattr(
            "codemap.cli.commands.hooks.shutil.which",
            lambda cmd: None,
        )
        monkeypatch.setattr(
            "codemap.cli.commands.hooks.sys.argv",
            ["/path/to/curator"],
        )

        result = runner.invoke(app, ["install-hook"])

        assert result.exit_code == 0
        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        content = hook_path.read_text()
        assert "/path/to/curator" in content


# ---------------------------------------------------------------------------
# TestUninstallHookCommand - Basic uninstallation
# ---------------------------------------------------------------------------


class TestUninstallHookCommand:
    """Tests for basic 'curator uninstall-hook' functionality."""

    def test_uninstall_hook_removes_curator_lines(
        self,
        runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_curator_path: str,
    ) -> None:
        """uninstall-hook removes lines between curator markers."""
        monkeypatch.chdir(git_repo)

        # Install first, then uninstall
        runner.invoke(app, ["install-hook"])
        result = runner.invoke(app, ["uninstall-hook"])

        assert result.exit_code == 0
        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        if hook_path.exists():
            content = hook_path.read_text()
            assert "# curator-hook-start" not in content
            assert "curator update" not in content
            assert "# curator-hook-end" not in content

    def test_uninstall_hook_preserves_other_content(
        self,
        runner: CliRunner,
        git_repo: Path,
        existing_hook: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_curator_path: str,
    ) -> None:
        """uninstall-hook preserves non-curator hook content."""
        monkeypatch.chdir(git_repo)

        # Install curator hook on existing hook, then uninstall
        runner.invoke(app, ["install-hook"])
        result = runner.invoke(app, ["uninstall-hook"])

        assert result.exit_code == 0
        content = existing_hook.read_text()
        assert "existing hook" in content, "Original content should be preserved"
        assert "# curator-hook-start" not in content, "Curator markers should be removed"

    def test_uninstall_hook_deletes_if_only_curator(
        self,
        runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_curator_path: str,
    ) -> None:
        """uninstall-hook deletes hook file when it only contains curator code."""
        monkeypatch.chdir(git_repo)

        # Install curator-only hook, then uninstall
        runner.invoke(app, ["install-hook"])
        result = runner.invoke(app, ["uninstall-hook"])

        assert result.exit_code == 0
        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        if hook_path.exists():
            content = hook_path.read_text().strip()
            assert content == "" or content == "#!/bin/sh", (
                "File should be deleted or contain only shebang"
            )


# ---------------------------------------------------------------------------
# TestUninstallHookEdgeCases - Uninstallation edge cases
# ---------------------------------------------------------------------------


class TestUninstallHookEdgeCases:
    """Tests for uninstall-hook edge cases."""

    def test_uninstall_hook_no_hook_succeeds(
        self,
        runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """uninstall-hook succeeds when no post-commit hook exists."""
        monkeypatch.chdir(git_repo)

        result = runner.invoke(app, ["uninstall-hook"])

        assert result.exit_code == 0

    def test_uninstall_hook_not_installed_succeeds(
        self,
        runner: CliRunner,
        git_repo: Path,
        existing_hook: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """uninstall-hook succeeds when hook exists but curator is not installed."""
        monkeypatch.chdir(git_repo)

        original_content = existing_hook.read_text()
        result = runner.invoke(app, ["uninstall-hook"])

        assert result.exit_code == 0
        assert existing_hook.read_text() == original_content, "Existing hook should not be modified"

    def test_uninstall_hook_not_git_repo_fails(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """uninstall-hook fails when not inside a git repository."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["uninstall-hook"])

        assert result.exit_code != 0
        output_lower = result.output.lower()
        assert "git" in output_lower or "repository" in output_lower


# ---------------------------------------------------------------------------
# TestHookHelpers - Tests for helper functions
# ---------------------------------------------------------------------------


class TestHookHelpers:
    """Tests for hook helper functions like _find_git_dir()."""

    def test_find_git_dir_in_root(
        self,
        git_repo: Path,
    ) -> None:
        """_find_git_dir returns .git path when called from repository root."""
        from codemap.cli.commands.hooks import _find_git_dir

        result = _find_git_dir(git_repo)

        assert result is not None
        assert result == git_repo / ".git"

    def test_find_git_dir_in_subdirectory(
        self,
        git_repo: Path,
    ) -> None:
        """_find_git_dir searches parent directories from a subdirectory."""
        from codemap.cli.commands.hooks import _find_git_dir

        sub_dir = git_repo / "src" / "deep" / "nested"
        sub_dir.mkdir(parents=True)

        result = _find_git_dir(sub_dir)

        assert result is not None
        assert result == git_repo / ".git"

    def test_find_git_dir_not_found(
        self,
        tmp_path: Path,
    ) -> None:
        """_find_git_dir returns None when no .git directory exists."""
        from codemap.cli.commands.hooks import _find_git_dir

        result = _find_git_dir(tmp_path)

        assert result is None


# ---------------------------------------------------------------------------
# TestHookContentValidation - Exact content structure
# ---------------------------------------------------------------------------


class TestHookContentValidation:
    """Tests validating the exact hook content structure."""

    def test_hook_starts_with_shebang(
        self,
        runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_curator_path: str,
    ) -> None:
        """Newly created hook starts with #!/bin/sh shebang."""
        monkeypatch.chdir(git_repo)

        runner.invoke(app, ["install-hook"])

        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        content = hook_path.read_text()
        assert content.startswith("#!/bin/sh")

    def test_hook_contains_marker_comments(
        self,
        runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_curator_path: str,
    ) -> None:
        """Hook contains start and end marker comments for idempotency."""
        monkeypatch.chdir(git_repo)

        runner.invoke(app, ["install-hook"])

        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        content = hook_path.read_text()
        assert "# curator-hook-start" in content
        assert "# curator-hook-end" in content

    def test_hook_contains_quiet_flag(
        self,
        runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_curator_path: str,
    ) -> None:
        """Hook command uses --quiet flag to suppress output."""
        monkeypatch.chdir(git_repo)

        runner.invoke(app, ["install-hook"])

        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        content = hook_path.read_text()
        assert "--quiet" in content

    def test_hook_markers_wrap_curator_content(
        self,
        runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_curator_path: str,
    ) -> None:
        """Curator content is between start and end markers."""
        monkeypatch.chdir(git_repo)

        runner.invoke(app, ["install-hook"])

        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        content = hook_path.read_text()
        start_idx = content.index("# curator-hook-start")
        end_idx = content.index("# curator-hook-end")
        curator_section = content[start_idx:end_idx]
        assert "curator update" in curator_section


# ---------------------------------------------------------------------------
# TestConcurrentExecution - Background execution safety
# ---------------------------------------------------------------------------


class TestConcurrentExecution:
    """Tests for concurrent hook execution handling."""

    def test_hook_uses_background_execution(
        self,
        runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_curator_path: str,
    ) -> None:
        """Hook script uses background execution with '&'."""
        monkeypatch.chdir(git_repo)

        runner.invoke(app, ["install-hook"])

        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        content = hook_path.read_text()
        # The curator command line should end with & for background execution
        curator_lines = [
            line for line in content.splitlines() if "curator" in line and "update" in line
        ]
        assert len(curator_lines) >= 1
        assert any("&" in line for line in curator_lines), "Curator update should run in background"

    def test_hook_redirects_output(
        self,
        runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_curator_path: str,
    ) -> None:
        """Hook redirects stdout and stderr to /dev/null."""
        monkeypatch.chdir(git_repo)

        runner.invoke(app, ["install-hook"])

        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        content = hook_path.read_text()
        assert "> /dev/null 2>&1" in content, "Hook should redirect all output to /dev/null"
