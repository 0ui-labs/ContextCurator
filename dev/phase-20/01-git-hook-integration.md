# Phase 20: Git-Hook Integration

> **Ziel:** Automatische Map-Aktualisierung nach jedem Commit.
> Der Graph bleibt immer aktuell, ohne dass der User manuell `update` aufrufen muss.

---

## Problem

Aktuell muss der User nach jeder Code-Änderung manuell den Graph aktualisieren:

```bash
# Nach jedem Commit...
python -c "from codemap.engine import MapBuilder; ..."  # Umständlich
```

Die Map wird schnell veraltet, weil niemand daran denkt, sie zu aktualisieren.

## Lösung

Automatisches Update via Git Post-Commit Hook:

```bash
# Nach git commit läuft automatisch:
$ curator update
Updating code map... 3 files changed.
Done in 0.8s

# Hook installieren (einmalig):
$ curator install-hook
Installed post-commit hook to .git/hooks/post-commit
```

---

## Observations

Nach Analyse des bestehenden Codes:

- **Keine CLI existiert:** Kein `cli/` Verzeichnis, keine typer/click Dependency
- **pyproject.toml hat keinen Entry-Point:** Kein `[project.scripts]` Abschnitt
- **Phase 19 liefert GraphUpdater:** `GraphUpdater.update()` führt inkrementelles Update durch
- **Git-Repo vorhanden:** `.git/` existiert, Hooks sind Standard-Shell-Scripts
- **Keine Config-Datei:** Kein `.codemap/` Verzeichnis für Graph-Persistenz

## Approach

### 1. CLI-Infrastruktur mit Typer

```
src/codemap/cli/
├── __init__.py
├── main.py        # Typer app + Entry-Point
├── commands/
│   ├── __init__.py
│   ├── init.py    # curator init
│   ├── update.py  # curator update
│   └── hooks.py   # curator install-hook
```

### 2. CLI Commands

```bash
curator init              # Initialer Full-Scan, erstellt .codemap/
curator update            # Inkrementelles Update (Phase 19)
curator status            # Zeigt Graph-Statistiken
curator install-hook      # Installiert Git Post-Commit Hook
curator uninstall-hook    # Entfernt Hook (optional)
```

### 3. Post-Commit Hook Script

```bash
#!/bin/sh
# .git/hooks/post-commit
# Installed by: curator install-hook

# Run in background to not block commit
curator update --quiet &
```

### 4. Config-Verzeichnis `.codemap/`

```
.codemap/
├── graph.json       # Persistierter Graph
├── config.toml      # (Optional) Konfiguration
└── metadata.json    # Build-Metadata (commit_hash, file_hashes)
```

---

## Implementation Steps

### Phase 1: RED - Failing Tests schreiben

#### 1.1 CLI Tests

Neue Datei: `tests/unit/cli/test_main.py`

```python
"""Tests for CLI main entry point."""

import pytest
from typer.testing import CliRunner

from codemap.cli.main import app


@pytest.fixture
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
        assert "0.1.0" in result.output


class TestInitCommand:
    """Tests for 'curator init' command."""

    def test_init_creates_codemap_directory(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """init creates .codemap/ directory."""
        # Create a minimal Python project
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hello')")

        result = runner.invoke(app, ["init"], catch_exceptions=False)

        assert result.exit_code == 0
        assert (tmp_path / ".codemap").exists()

    def test_init_creates_graph_json(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """init creates .codemap/graph.json."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def foo(): pass")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init", "."])

        assert (tmp_path / ".codemap" / "graph.json").exists()

    def test_init_shows_stats(self, runner: CliRunner, tmp_path: Path) -> None:
        """init displays graph statistics."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def foo(): pass")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init", "."])

        assert "nodes" in result.output.lower() or "files" in result.output.lower()

    def test_init_existing_warns(self, runner: CliRunner, tmp_path: Path) -> None:
        """init on existing .codemap/ warns but continues."""
        (tmp_path / ".codemap").mkdir()
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hello')")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init", "."])

        # Should warn but not fail
        assert result.exit_code == 0


class TestUpdateCommand:
    """Tests for 'curator update' command."""

    def test_update_requires_init(self, runner: CliRunner, tmp_path: Path) -> None:
        """update fails if .codemap/ doesn't exist."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["update"])

        assert result.exit_code != 0
        assert "init" in result.output.lower()

    def test_update_shows_changes(self, runner: CliRunner, tmp_path: Path) -> None:
        """update shows number of changed files."""
        # Setup: init first
        (tmp_path / ".codemap").mkdir()
        (tmp_path / ".codemap" / "graph.json").write_text("{}")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def foo(): pass")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["update"])

        # Should show change count
        assert result.exit_code == 0

    def test_update_quiet_mode(self, runner: CliRunner, tmp_path: Path) -> None:
        """update --quiet produces no output on success."""
        (tmp_path / ".codemap").mkdir()
        (tmp_path / ".codemap" / "graph.json").write_text("{}")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["update", "--quiet"])

        assert result.exit_code == 0
        assert result.output.strip() == ""


class TestStatusCommand:
    """Tests for 'curator status' command."""

    def test_status_shows_node_count(self, runner: CliRunner, tmp_path: Path) -> None:
        """status shows number of nodes and edges."""
        # Setup with existing graph
        (tmp_path / ".codemap").mkdir()
        graph_data = '{"nodes": [], "links": []}'
        (tmp_path / ".codemap" / "graph.json").write_text(graph_data)

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "nodes" in result.output.lower()

    def test_status_shows_last_update(self, runner: CliRunner, tmp_path: Path) -> None:
        """status shows last update timestamp."""
        (tmp_path / ".codemap").mkdir()
        metadata = '{"build_time": "2024-01-15T10:30:00"}'
        (tmp_path / ".codemap" / "metadata.json").write_text(metadata)
        (tmp_path / ".codemap" / "graph.json").write_text('{"nodes":[],"links":[]}')

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["status"])

        assert "2024" in result.output or "update" in result.output.lower()
```

#### 1.2 Hook Commands Tests

Neue Datei: `tests/unit/cli/test_hooks.py`

```python
"""Tests for hook installation commands."""

import os
import stat
import pytest
from pathlib import Path
from typer.testing import CliRunner

from codemap.cli.main import app


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a minimal git repository."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "hooks").mkdir()
    return tmp_path


class TestInstallHookCommand:
    """Tests for 'curator install-hook' command."""

    def test_install_hook_creates_post_commit(
        self, runner: CliRunner, git_repo: Path
    ) -> None:
        """install-hook creates .git/hooks/post-commit."""
        with runner.isolated_filesystem(temp_dir=git_repo):
            result = runner.invoke(app, ["install-hook"])

        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        assert hook_path.exists()
        assert result.exit_code == 0

    def test_install_hook_is_executable(
        self, runner: CliRunner, git_repo: Path
    ) -> None:
        """install-hook makes the hook executable."""
        with runner.isolated_filesystem(temp_dir=git_repo):
            runner.invoke(app, ["install-hook"])

        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        mode = hook_path.stat().st_mode
        assert mode & stat.S_IXUSR  # User execute bit

    def test_install_hook_contains_curator_update(
        self, runner: CliRunner, git_repo: Path
    ) -> None:
        """install-hook script contains 'curator update'."""
        with runner.isolated_filesystem(temp_dir=git_repo):
            runner.invoke(app, ["install-hook"])

        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        content = hook_path.read_text()
        assert "curator" in content
        assert "update" in content

    def test_install_hook_runs_in_background(
        self, runner: CliRunner, git_repo: Path
    ) -> None:
        """install-hook runs update in background (non-blocking)."""
        with runner.isolated_filesystem(temp_dir=git_repo):
            runner.invoke(app, ["install-hook"])

        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        content = hook_path.read_text()
        assert "&" in content  # Background execution

    def test_install_hook_not_git_repo_fails(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """install-hook fails if not in a git repository."""
        # No .git directory
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["install-hook"])

        assert result.exit_code != 0
        assert "git" in result.output.lower()

    def test_install_hook_existing_preserves_content(
        self, runner: CliRunner, git_repo: Path
    ) -> None:
        """install-hook appends to existing hook, doesn't overwrite."""
        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        hook_path.write_text("#!/bin/sh\necho 'existing hook'\n")

        with runner.isolated_filesystem(temp_dir=git_repo):
            result = runner.invoke(app, ["install-hook"])

        content = hook_path.read_text()
        assert "existing hook" in content  # Preserved
        assert "curator update" in content  # Added

    def test_install_hook_idempotent(
        self, runner: CliRunner, git_repo: Path
    ) -> None:
        """install-hook can be run multiple times safely."""
        with runner.isolated_filesystem(temp_dir=git_repo):
            runner.invoke(app, ["install-hook"])
            result = runner.invoke(app, ["install-hook"])

        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        content = hook_path.read_text()

        # Should only contain one curator update call
        assert content.count("curator update") == 1
        assert result.exit_code == 0


class TestUninstallHookCommand:
    """Tests for 'curator uninstall-hook' command."""

    def test_uninstall_hook_removes_curator_lines(
        self, runner: CliRunner, git_repo: Path
    ) -> None:
        """uninstall-hook removes curator-related lines from hook."""
        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        hook_path.write_text(
            "#!/bin/sh\n"
            "echo 'other stuff'\n"
            "# curator-hook-start\n"
            "curator update --quiet &\n"
            "# curator-hook-end\n"
        )

        with runner.isolated_filesystem(temp_dir=git_repo):
            result = runner.invoke(app, ["uninstall-hook"])

        content = hook_path.read_text()
        assert "curator" not in content
        assert "other stuff" in content  # Preserved
        assert result.exit_code == 0

    def test_uninstall_hook_deletes_if_only_curator(
        self, runner: CliRunner, git_repo: Path
    ) -> None:
        """uninstall-hook deletes hook if it only contains curator code."""
        hook_path = git_repo / ".git" / "hooks" / "post-commit"
        hook_path.write_text(
            "#!/bin/sh\n"
            "# curator-hook-start\n"
            "curator update --quiet &\n"
            "# curator-hook-end\n"
        )

        with runner.isolated_filesystem(temp_dir=git_repo):
            runner.invoke(app, ["uninstall-hook"])

        # Hook file should be deleted or empty
        assert not hook_path.exists() or hook_path.read_text().strip() == "#!/bin/sh"

    def test_uninstall_hook_no_hook_succeeds(
        self, runner: CliRunner, git_repo: Path
    ) -> None:
        """uninstall-hook succeeds even if no hook exists."""
        with runner.isolated_filesystem(temp_dir=git_repo):
            result = runner.invoke(app, ["uninstall-hook"])

        assert result.exit_code == 0
```

---

### Phase 2: GREEN - Implementation

#### 2.1 Dependencies hinzufügen

Datei: `pyproject.toml` (erweitern)

```toml
[project]
# ... existing ...
dependencies = [
    "networkx>=3.0",
    "typer[all]>=0.9.0",  # CLI framework with rich support
]

[project.scripts]
curator = "codemap.cli.main:app"
```

#### 2.2 CLI Main Entry Point

Neue Datei: `src/codemap/cli/main.py`

```python
"""ContextCurator CLI - Code mapping and analysis tool.

This module provides the main CLI entry point using Typer.
"""

from pathlib import Path
from typing import Annotated, Optional

import typer

from codemap.cli.commands import hooks, init, status, update

app = typer.Typer(
    name="curator",
    help="ContextCurator - Semantic code mapping tool",
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        typer.echo("curator 0.1.0")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            "-v",
            help="Show version and exit.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """ContextCurator - Semantic code mapping tool."""
    pass


# Register commands
app.command()(init.init_command)
app.command(name="update")(update.update_command)
app.command()(status.status_command)
app.command(name="install-hook")(hooks.install_hook_command)
app.command(name="uninstall-hook")(hooks.uninstall_hook_command)


if __name__ == "__main__":
    app()
```

#### 2.3 Init Command

Neue Datei: `src/codemap/cli/commands/init.py`

```python
"""Init command - create initial code map."""

from pathlib import Path
from typing import Annotated

import typer

from codemap.engine import MapBuilder

CODEMAP_DIR = ".codemap"


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
    """Initialize code map for a project.

    Scans the project directory and creates .codemap/ with the
    initial graph.
    """
    codemap_path = path / CODEMAP_DIR

    if codemap_path.exists():
        typer.echo(f"Warning: {CODEMAP_DIR}/ already exists, rebuilding...", err=True)

    codemap_path.mkdir(exist_ok=True)

    typer.echo(f"Scanning {path}...")

    builder = MapBuilder()
    graph_manager = builder.build(path)

    # Save graph
    graph_path = codemap_path / "graph.json"
    graph_manager.save(graph_path)

    # Save metadata
    _save_metadata(codemap_path, path)

    stats = graph_manager.graph_stats
    typer.echo(f"Created code map: {stats['nodes']} nodes, {stats['edges']} edges")
    typer.echo(f"Saved to {graph_path}")


def _save_metadata(codemap_path: Path, project_root: Path) -> None:
    """Save build metadata."""
    import json
    import subprocess
    from datetime import datetime, timezone

    metadata: dict[str, str | None] = {
        "build_time": datetime.now(timezone.utc).isoformat(),
        "commit_hash": None,
    }

    # Try to get git commit hash
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True,
        )
        metadata["commit_hash"] = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    metadata_path = codemap_path / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))
```

#### 2.4 Update Command

Neue Datei: `src/codemap/cli/commands/update.py`

```python
"""Update command - incremental code map update."""

import sys
from pathlib import Path
from typing import Annotated

import typer

CODEMAP_DIR = ".codemap"


def update_command(
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress output on success"),
    ] = False,
) -> None:
    """Update code map with recent changes.

    Detects changes since last build and updates the graph
    incrementally.
    """
    codemap_path = Path.cwd() / CODEMAP_DIR

    if not codemap_path.exists():
        typer.echo(
            f"Error: {CODEMAP_DIR}/ not found. Run 'curator init' first.",
            err=True,
        )
        raise typer.Exit(1)

    # Import here to avoid circular imports and for lazy loading
    from codemap.engine.change_detector import ChangeDetector
    from codemap.engine.graph_updater import GraphUpdater
    from codemap.graph import GraphManager
    from codemap.mapper.engine import ParserEngine
    from codemap.mapper.reader import ContentReader

    # Load existing graph
    graph_manager = GraphManager()
    graph_path = codemap_path / "graph.json"

    if graph_path.exists():
        graph_manager.load(graph_path)

    # Load metadata
    metadata = _load_metadata(codemap_path)
    graph_manager.build_metadata = metadata

    # Run update
    detector = ChangeDetector(graph_manager)
    updater = GraphUpdater(
        graph_manager,
        detector,
        ParserEngine(),
        ContentReader(),
    )

    changes = updater.update(Path.cwd())

    # Save updated graph
    graph_manager.save(graph_path)
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


def _load_metadata(codemap_path: Path) -> dict:
    """Load build metadata."""
    import json

    metadata_path = codemap_path / "metadata.json"
    if metadata_path.exists():
        return json.loads(metadata_path.read_text())
    return {}


def _save_metadata(codemap_path: Path, project_root: Path, graph_manager) -> None:
    """Save updated build metadata."""
    import json
    import subprocess
    from datetime import datetime, timezone

    metadata = getattr(graph_manager, "build_metadata", {})
    metadata["build_time"] = datetime.now(timezone.utc).isoformat()

    # Update commit hash
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True,
        )
        metadata["commit_hash"] = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    metadata_path = codemap_path / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))
```

#### 2.5 Hook Commands

Neue Datei: `src/codemap/cli/commands/hooks.py`

```python
"""Git hook installation commands."""

import os
import stat
from pathlib import Path
from typing import Annotated

import typer

HOOK_MARKER_START = "# curator-hook-start"
HOOK_MARKER_END = "# curator-hook-end"
HOOK_CONTENT = f"""
{HOOK_MARKER_START}
# ContextCurator: Auto-update code map after commit
# Installed by: curator install-hook
curator update --quiet &
{HOOK_MARKER_END}
"""


def install_hook_command() -> None:
    """Install Git post-commit hook for automatic updates.

    The hook runs 'curator update' in the background after each
    commit to keep the code map up-to-date.
    """
    git_dir = _find_git_dir()
    if not git_dir:
        typer.echo("Error: Not a git repository.", err=True)
        raise typer.Exit(1)

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    hook_path = hooks_dir / "post-commit"

    # Read existing content
    existing_content = ""
    if hook_path.exists():
        existing_content = hook_path.read_text()

        # Check if already installed
        if HOOK_MARKER_START in existing_content:
            typer.echo("Hook already installed.")
            return

    # Build new content
    if not existing_content:
        new_content = "#!/bin/sh\n" + HOOK_CONTENT
    else:
        # Append to existing hook
        new_content = existing_content.rstrip() + "\n" + HOOK_CONTENT

    # Write hook
    hook_path.write_text(new_content)

    # Make executable
    current_mode = hook_path.stat().st_mode
    hook_path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    typer.echo(f"Installed post-commit hook to {hook_path}")


def uninstall_hook_command() -> None:
    """Remove ContextCurator Git hook.

    Removes the curator-specific lines from post-commit hook,
    preserving any other hook content.
    """
    git_dir = _find_git_dir()
    if not git_dir:
        typer.echo("Error: Not a git repository.", err=True)
        raise typer.Exit(1)

    hook_path = git_dir / "hooks" / "post-commit"

    if not hook_path.exists():
        typer.echo("No post-commit hook found.")
        return

    content = hook_path.read_text()

    if HOOK_MARKER_START not in content:
        typer.echo("Curator hook not found in post-commit.")
        return

    # Remove curator section
    lines = content.split("\n")
    new_lines = []
    in_curator_section = False

    for line in lines:
        if HOOK_MARKER_START in line:
            in_curator_section = True
            continue
        if HOOK_MARKER_END in line:
            in_curator_section = False
            continue
        if not in_curator_section:
            new_lines.append(line)

    new_content = "\n".join(new_lines).strip()

    # If only shebang remains, delete the file
    if new_content == "#!/bin/sh" or not new_content:
        hook_path.unlink()
        typer.echo("Removed post-commit hook (was curator-only).")
    else:
        hook_path.write_text(new_content + "\n")
        typer.echo("Removed curator lines from post-commit hook.")


def _find_git_dir() -> Path | None:
    """Find .git directory, searching up from cwd."""
    current = Path.cwd()

    while current != current.parent:
        git_dir = current / ".git"
        if git_dir.is_dir():
            return git_dir
        current = current.parent

    return None
```

#### 2.6 Status Command

Neue Datei: `src/codemap/cli/commands/status.py`

```python
"""Status command - show code map statistics."""

import json
from pathlib import Path

import typer

CODEMAP_DIR = ".codemap"


def status_command() -> None:
    """Show code map status and statistics."""
    codemap_path = Path.cwd() / CODEMAP_DIR

    if not codemap_path.exists():
        typer.echo(f"{CODEMAP_DIR}/ not found. Run 'curator init' first.", err=True)
        raise typer.Exit(1)

    # Load graph stats
    from codemap.graph import GraphManager

    graph_manager = GraphManager()
    graph_path = codemap_path / "graph.json"

    if graph_path.exists():
        graph_manager.load(graph_path)
        stats = graph_manager.graph_stats
    else:
        stats = {"nodes": 0, "edges": 0}

    # Load metadata
    metadata_path = codemap_path / "metadata.json"
    metadata = {}
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text())

    # Display
    typer.echo("Code Map Status")
    typer.echo("=" * 40)
    typer.echo(f"Nodes:       {stats['nodes']}")
    typer.echo(f"Edges:       {stats['edges']}")

    if "build_time" in metadata:
        typer.echo(f"Last update: {metadata['build_time']}")

    if "commit_hash" in metadata and metadata["commit_hash"]:
        typer.echo(f"Commit:      {metadata['commit_hash'][:8]}")
```

#### 2.7 Package Init Files

`src/codemap/cli/__init__.py`:
```python
"""CLI module for ContextCurator."""

from codemap.cli.main import app

__all__ = ["app"]
```

`src/codemap/cli/commands/__init__.py`:
```python
"""CLI commands for ContextCurator."""
```

---

### Phase 3: REFACTOR - Code-Qualität

#### 3.1 Checklist

- [ ] mypy strict auf allen CLI-Dateien
- [ ] ruff Format und Lint
- [ ] Docstrings vollständig
- [ ] Error-Messages konsistent und hilfreich
- [ ] `--help` Text für alle Commands
- [ ] Tests für Edge-Cases (kein Git, keine Permissions)

#### 3.2 Integration

- [ ] Entry-Point in pyproject.toml testen (`pip install -e .`)
- [ ] Hook funktioniert in echtem Git-Repo
- [ ] Background-Execution blockiert Commit nicht

---

## Akzeptanzkriterien

- [ ] `curator init <path>` erstellt `.codemap/` mit `graph.json`
- [ ] `curator update` führt inkrementelles Update durch (Phase 19)
- [ ] `curator update --quiet` produziert keine Ausgabe bei Erfolg
- [ ] `curator status` zeigt Node/Edge-Counts und Last-Update
- [ ] `curator install-hook` installiert Post-Commit Hook
- [ ] `curator uninstall-hook` entfernt Hook sauber
- [ ] Hook ist idempotent (mehrfach installierbar)
- [ ] Hook läuft im Hintergrund (blockiert Commit nicht)
- [ ] 100% Test-Coverage bleibt erhalten
- [ ] mypy strict + ruff clean

---

## Abhängigkeiten

- **Phase 19 (Inkrementelles Update):** `GraphUpdater` und `ChangeDetector`
- **typer:** Neue Dependency für CLI

## Risiken

1. **Git nicht installiert:** Hook-Installation schlägt fehl
   - Mitigation: Klare Fehlermeldung

2. **Kein Python im PATH:** Hook findet `curator` nicht
   - Mitigation: Hook könnte absoluten Pfad speichern (optional)

3. **Große Repos:** Update dauert zu lange für Post-Commit
   - Mitigation: Background-Execution (bereits implementiert)

---

## Schätzung

- **Aufwand:** 🟢 Gering (wie in Roadmap angegeben)
- **Komplexität:** Niedrig - hauptsächlich CLI-Scaffolding
- **Zeitrahmen:** 1 TDD-Zyklus

---

## Nächster Schritt

**RED Phase starten:** Tests für CLI-App in `tests/unit/cli/test_main.py` schreiben.
