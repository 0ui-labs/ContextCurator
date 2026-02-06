"""CLI init command for ContextCurator."""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn

from codemap.engine import MapBuilder

CODEMAP_DIR = ".codemap"


def _save_metadata(codemap_path: Path, project_root: Path) -> None:
    """Save build metadata to metadata.json.

    Args:
        codemap_path: Path to .codemap/ directory.
        project_root: Project root directory for git operations.

    Notes:
        Stores build_time (ISO 8601) and commit_hash (if git available).
    """
    metadata: dict[str, Any] = {
        "build_time": datetime.now(UTC).isoformat(),
    }
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


def init_command(
    path: Annotated[
        Path,
        typer.Argument(
            help="Project root directory to scan",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ] = Path("."),
) -> None:
    """Initialize a code map for the given project directory.

    Creates a ``.codemap/`` directory containing:

    - ``graph.json``: Serialized code dependency graph
    - ``metadata.json``: Build metadata (timestamp, git commit hash)

    Args:
        path: Project root directory to scan. Must be an existing directory.
              Defaults to current working directory.

    Raises:
        typer.Exit: If path does not exist or is not a directory.

    Notes:
        - If ``.codemap/`` already exists, it will be rebuilt (warning shown)
        - Git commit hash is stored if repository is detected
        - Progress indicator shows scan/save status
    """
    codemap_path = path / CODEMAP_DIR

    if codemap_path.exists():
        typer.echo("Warning: .codemap/ already exists, rebuilding...", err=True)

    codemap_path.mkdir(exist_ok=True)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task(f"Scanning {path}...", total=None)

        builder = MapBuilder()
        graph_manager = builder.build(path)

        progress.update(task, description="Saving graph...")
        graph_path = codemap_path / "graph.json"
        graph_manager.save(graph_path)

        progress.update(task, description="Saving metadata...")
        _save_metadata(codemap_path, path)

    stats = graph_manager.graph_stats
    typer.echo(f"Created code map: {stats['nodes']} nodes, {stats['edges']} edges")
    typer.echo(f"Saved to {graph_path}")
