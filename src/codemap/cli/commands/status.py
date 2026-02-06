"""CLI status command for ContextCurator."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from codemap.graph import GraphManager

logger = logging.getLogger(__name__)

CODEMAP_DIR = ".codemap"


def _find_codemap_dir(start: Path) -> Path | None:
    """Find .codemap directory by searching start and parent directories.

    Args:
        start: Starting directory for search.

    Returns:
        Path to .codemap directory, or None if not found.

    Notes:
        Searches upwards until filesystem root is reached.
    """
    current = start.resolve()
    while True:
        codemap_dir = current / CODEMAP_DIR
        if codemap_dir.is_dir():
            return codemap_dir
        parent = current.parent
        if parent == current:
            return None
        current = parent


def _load_metadata(codemap_path: Path) -> dict[str, Any]:
    """Load metadata from metadata.json, or return empty dict.

    Unlike the update command, corrupted metadata does not cause a fatal error --
    the status command simply skips the metadata section.

    Args:
        codemap_path: Path to .codemap/ directory.

    Returns:
        Metadata dictionary, or empty dict if file missing/invalid.

    Notes:
        Does not raise on invalid JSON, returns empty dict instead.
    """
    metadata_path = codemap_path / "metadata.json"
    if metadata_path.exists():
        try:
            return json.loads(metadata_path.read_text())  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            logger.warning("metadata.json is not valid JSON, skipping metadata.")
    return {}


def status_command() -> None:
    """Display the current code map status.

    Shows graph statistics (nodes, edges) and metadata (last update, commit hash)
    in a formatted Rich table. Searches for ``.codemap/`` in current and parent
    directories.

    Raises:
        typer.Exit: If ``.codemap/`` not found or graph.json invalid.

    Notes:
        - Searches parent directories for ``.codemap/``
        - Handles missing or corrupted ``metadata.json`` gracefully
        - Commit hash truncated to 8 characters for readability
        - Uses Rich table for formatted output
    """
    codemap_path = _find_codemap_dir(Path.cwd())
    if codemap_path is None:
        typer.echo("Error: .codemap/ not found. Run 'curator init' first.", err=True)
        raise typer.Exit(1)

    graph_json_path = codemap_path / "graph.json"
    if not graph_json_path.exists():
        typer.echo(
            "Error: graph.json not found in .codemap/. Run 'curator init' first.",
            err=True,
        )
        raise typer.Exit(1)

    try:
        gm = GraphManager()
        gm.load(graph_json_path)
    except ValueError as e:
        typer.echo(f"Error: Invalid graph.json. {e}", err=True)
        raise typer.Exit(1) from e

    stats = gm.graph_stats
    metadata = _load_metadata(codemap_path)

    table = Table(title="Code Map Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Nodes", str(stats["nodes"]))
    table.add_row("Edges", str(stats["edges"]))
    if "build_time" in metadata:
        table.add_row("Last update", metadata["build_time"])
    if metadata.get("commit_hash"):
        table.add_row("Commit", metadata["commit_hash"][:8])

    Console().print(table)
