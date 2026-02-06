"""CLI commands for git hook management."""

from __future__ import annotations

import shutil
import stat
import sys
from pathlib import Path

import typer

HOOK_MARKER_START = "# curator-hook-start"
HOOK_MARKER_END = "# curator-hook-end"


def _find_git_dir(start: Path) -> Path | None:
    """Find .git directory by searching start and parent directories.

    Args:
        start: Starting directory for search.

    Returns:
        Path to .git directory, or None if not found.

    Notes:
        Searches upwards until filesystem root is reached.
    """
    current = start.resolve()
    while True:
        git_dir = current / ".git"
        if git_dir.is_dir():
            return git_dir
        parent = current.parent
        if parent == current:
            return None
        current = parent


def install_hook_command() -> None:
    """Install a post-commit git hook that runs ``curator update``.

    Creates or modifies ``.git/hooks/post-commit`` to automatically update
    the code map after each commit. The hook runs in background to avoid
    blocking the commit process.

    Raises:
        typer.Exit: If not in a git repository or permission denied.

    Notes:
        - Searches for ``.git/`` in current and parent directories
        - Preserves existing hook content (appends curator section)
        - Idempotent: running multiple times is safe
        - Uses absolute path to curator executable
        - Hook runs ``curator update --quiet > /dev/null 2>&1 &``
        - Markers ``# curator-hook-start`` and ``# curator-hook-end`` for tracking
    """
    git_dir = _find_git_dir(Path.cwd())
    if git_dir is None:
        typer.echo("Error: Not a git repository.", err=True)
        raise typer.Exit(1)

    # Resolve curator executable path
    curator_path = shutil.which("curator")
    if curator_path is None:
        curator_path = str(Path(sys.argv[0]).resolve())

    hook_section = (
        f"{HOOK_MARKER_START}\n"
        f"# ContextCurator: Auto-update code map after commit\n"
        f"{curator_path} update --quiet > /dev/null 2>&1 &\n"
        f"{HOOK_MARKER_END}\n"
    )

    hook_path = git_dir / "hooks" / "post-commit"
    hook_path.parent.mkdir(exist_ok=True)

    existing_content = ""
    if hook_path.exists():
        existing_content = hook_path.read_text()

    # Idempotency: already installed
    if HOOK_MARKER_START in existing_content:
        typer.echo("Hook already installed.")
        return

    if existing_content:
        new_content = existing_content.rstrip() + "\n" + hook_section
    else:
        new_content = "#!/bin/sh\n" + hook_section

    try:
        hook_path.write_text(new_content)
        current_mode = hook_path.stat().st_mode
        hook_path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except PermissionError:
        typer.echo(f"Error: Permission denied writing to {hook_path}", err=True)
        raise typer.Exit(1)  # noqa: B904

    typer.echo(f"Installed post-commit hook to {hook_path}")


def uninstall_hook_command() -> None:
    """Uninstall the curator post-commit git hook.

    Removes curator-specific lines from ``.git/hooks/post-commit``.
    Preserves other hook content. Deletes hook file if it only contained
    curator code.

    Raises:
        typer.Exit: If not in a git repository.

    Notes:
        - Succeeds even if hook doesn't exist or curator not installed
        - Preserves non-curator hook content
        - Deletes hook file if only shebang remains
    """
    git_dir = _find_git_dir(Path.cwd())
    if git_dir is None:
        typer.echo("Error: Not a git repository.", err=True)
        raise typer.Exit(1)

    hook_path = git_dir / "hooks" / "post-commit"

    if not hook_path.exists():
        typer.echo("No post-commit hook found.")
        return

    content = hook_path.read_text()

    if HOOK_MARKER_START not in content:
        typer.echo("Curator hook not installed.")
        return

    # Remove curator section (lines between and including markers)
    new_lines: list[str] = []
    in_curator_section = False
    for line in content.splitlines():
        if HOOK_MARKER_START in line:
            in_curator_section = True
            continue
        if HOOK_MARKER_END in line:
            in_curator_section = False
            continue
        if not in_curator_section:
            new_lines.append(line)

    new_content = "\n".join(new_lines).strip()

    if not new_content or new_content == "#!/bin/sh":
        hook_path.unlink()
        typer.echo("Removed post-commit hook (was curator-only).")
    else:
        hook_path.write_text(new_content + "\n")
        typer.echo("Removed curator hook from post-commit.")
