"""CLI update command for ContextCurator."""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from filelock import FileLock, Timeout

from codemap.engine.change_detector import ChangeDetector
from codemap.engine.graph_updater import GraphUpdater
from codemap.graph import GraphManager
from codemap.mapper.engine import ParserEngine
from codemap.mapper.reader import ContentReader

CODEMAP_DIR = ".codemap"


def _load_metadata(codemap_path: Path) -> dict[str, Any]:
    """Load metadata from metadata.json, or return empty dict.

    Args:
        codemap_path: Path to .codemap/ directory.

    Returns:
        Metadata dictionary, or empty dict if file missing/invalid.

    Notes:
        Does not raise on missing file, returns empty dict instead.
        Raises typer.Exit(1) on invalid JSON.
    """
    metadata_path = codemap_path / "metadata.json"
    if metadata_path.exists():
        try:
            return json.loads(metadata_path.read_text())  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            typer.echo("Error: metadata.json is not valid JSON.", err=True)
            raise typer.Exit(1)  # noqa: B904
    return {}


def _save_metadata(codemap_path: Path, project_root: Path, graph_manager: GraphManager) -> None:
    """Save updated build metadata to metadata.json.

    Args:
        codemap_path: Path to .codemap/ directory.
        project_root: Project root directory for git operations.
        graph_manager: GraphManager instance with build_metadata.

    Notes:
        Stores build_time (ISO 8601) and commit_hash (if git available).
    """
    metadata: dict[str, Any] = getattr(graph_manager, "build_metadata", None) or {}
    metadata["build_time"] = datetime.now(UTC).isoformat()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],  # noqa: S603, S607
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True,
        )
        metadata["commit_hash"] = result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        metadata["commit_hash"] = None

    (codemap_path / "metadata.json").write_text(json.dumps(metadata, indent=2))


def update_command(
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress output on success"),
    ] = False,
) -> None:
    """Update the code map with incremental changes.

    Detects file changes since last build and updates the graph incrementally.
    Uses file locking to prevent concurrent updates.

    Args:
        quiet: Suppress output on success. Errors are still shown.

    Raises:
        typer.Exit: If ``.codemap/`` not found, graph.json invalid, or lock timeout.

    Notes:
        - Requires prior ``curator init`` to create ``.codemap/``
        - Uses ``.codemap/.update.lock`` to prevent concurrent execution
        - Updates ``metadata.json`` with new timestamp and commit hash
        - Shows counts of modified/added/deleted files unless ``--quiet``
    """
    codemap_path = Path.cwd() / CODEMAP_DIR

    if not codemap_path.exists():
        typer.echo("Error: .codemap/ not found. Run 'curator init' first.", err=True)
        raise typer.Exit(1)

    lock_file = codemap_path / ".update.lock"
    lock = FileLock(lock_file, timeout=0)

    try:
        with lock:
            graph_json_path = codemap_path / "graph.json"
            if not graph_json_path.exists():
                typer.echo(
                    "Error: graph.json not found in .codemap/. Run 'curator init' first.",
                    err=True,
                )
                raise typer.Exit(1)

            graph_manager = GraphManager()
            try:
                graph_manager.load(graph_json_path)
            except ValueError as e:
                typer.echo(f"Error: Invalid graph.json. {e}", err=True)
                raise typer.Exit(1) from e

            metadata = _load_metadata(codemap_path)
            graph_manager.build_metadata.update(metadata)

            detector = ChangeDetector(graph_manager)
            updater = GraphUpdater(graph_manager, detector, ParserEngine(), ContentReader())

            changes = updater.update(Path.cwd())

            graph_manager.save(codemap_path / "graph.json")

            _save_metadata(codemap_path, Path.cwd(), graph_manager)

            if not quiet:
                if changes.is_empty:
                    typer.echo("No changes detected.")
                else:
                    typer.echo(
                        f"Updated: {len(changes.modified)} modified, "
                        f"{len(changes.added)} added, "
                        f"{len(changes.deleted)} deleted"
                    )
    except Timeout:
        if not quiet:
            typer.echo("Update already in progress, skipping...", err=True)
        raise typer.Exit(0) from None
