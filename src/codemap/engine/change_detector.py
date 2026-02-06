"""Change detection for incremental graph updates.

This module provides the ChangeDetector class for detecting file changes
since the last graph build, using Git or hash-based comparison.
"""

import hashlib
import logging
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from codemap.graph import GraphManager

logger = logging.getLogger(__name__)


@dataclass
class ChangeSet:
    """Container for detected file changes.

    Attributes:
        modified: Files with changed content.
        added: New files not in previous build.
        deleted: Files that no longer exist.
        base_commit: Git commit hash of the comparison base.
    """

    modified: list[Path] = field(default_factory=list)
    added: list[Path] = field(default_factory=list)
    deleted: list[Path] = field(default_factory=list)
    base_commit: str | None = None

    @property
    def is_empty(self) -> bool:
        """Return True if no changes detected."""
        return not self.modified and not self.added and not self.deleted

    @property
    def total_changes(self) -> int:
        """Return total number of changed files."""
        return len(self.modified) + len(self.added) + len(self.deleted)


class ChangeDetector:
    """Detect file changes since last graph build.

    Uses Git diff as primary strategy, falls back to hash comparison
    when Git is unavailable or for non-Git directories.

    Example:
        detector = ChangeDetector(graph_manager)
        changes = detector.detect_changes(Path("src"))
        print(f"Modified: {changes.modified}")
    """

    def __init__(self, graph_manager: "GraphManager") -> None:
        """Initialize with GraphManager containing build metadata."""
        self._graph_manager = graph_manager

    def detect_changes(self, root: Path) -> ChangeSet:
        """Detect file changes since last build.

        Args:
            root: Project root directory.

        Returns:
            ChangeSet with modified, added, and deleted files.
        """
        start = time.perf_counter()

        metadata = self._graph_manager.build_metadata
        base_commit: str | None = metadata.get("commit_hash")

        if base_commit is not None:
            try:
                changes = self._detect_via_git(root, base_commit)
            except (FileNotFoundError, subprocess.CalledProcessError) as e:
                logger.warning("Git detection failed, falling back to hash: %s", e)
                changes = self._detect_via_hash(root, metadata.get("file_hashes", {}))
        else:
            changes = self._detect_via_hash(root, metadata.get("file_hashes", {}))

        elapsed = time.perf_counter() - start
        logger.info(
            "Change detection completed in %.2fs: %d modified, %d added, %d deleted",
            elapsed,
            len(changes.modified),
            len(changes.added),
            len(changes.deleted),
        )
        return changes

    def _detect_via_git(self, root: Path, base_commit: str) -> ChangeSet:
        """Use git diff to detect changes since base_commit.

        Args:
            root: Project root directory for git command execution.
            base_commit: Git commit hash to compare against HEAD.

        Returns:
            ChangeSet with files changed between base_commit and HEAD.

        Raises:
            FileNotFoundError: If git command is not found.
            subprocess.CalledProcessError: If git diff fails (invalid commit, etc.).
        """
        result = subprocess.run(
            ["git", "diff", "--name-status", base_commit, "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )

        changes = ChangeSet(base_commit=base_commit)

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("\t")
            if len(parts) < 2:
                logger.warning("Skipping malformed git diff line: %s", line)
                continue

            status = parts[0]

            if status == "M":
                changes.modified.append(Path(parts[1]))
            elif status == "A":
                changes.added.append(Path(parts[1]))
            elif status == "D":
                changes.deleted.append(Path(parts[1]))
            elif status.startswith("R"):
                if len(parts) < 3:
                    logger.warning("Skipping malformed rename line: %s", line)
                    continue
                changes.deleted.append(Path(parts[1]))
                changes.added.append(Path(parts[2]))

        return changes

    def _detect_via_hash(
        self,
        root: Path,
        stored_hashes: dict[str, str],
        file_pattern: str = "*.py",
    ) -> ChangeSet:
        """Use SHA-256 file hashes to detect changes.

        Args:
            root: Project root directory to scan for .py files.
            stored_hashes: Dict mapping relative paths to SHA-256 hashes from last build.
            file_pattern: Glob pattern for files to scan (default: "*.py").

        Returns:
            ChangeSet with added/modified/deleted files based on hash comparison.
        """
        changes = ChangeSet()
        current_files: set[str] = set()

        # Walk directory and compare hashes
        for file_path in root.rglob(file_pattern):
            rel_path = str(file_path.relative_to(root))
            current_files.add(rel_path)

            current_hash = self._hash_file(file_path)
            stored_hash = stored_hashes.get(rel_path)

            if stored_hash is None:
                changes.added.append(Path(rel_path))
            elif current_hash != stored_hash:
                changes.modified.append(Path(rel_path))

        # Find deleted files
        for stored_path in stored_hashes:
            if stored_path not in current_files:
                changes.deleted.append(Path(stored_path))

        return changes

    def _hash_file(self, path: Path) -> str:
        """Compute SHA-256 hash of file content.

        Args:
            path: Absolute path to file.

        Returns:
            Hexadecimal SHA-256 hash string.

        Raises:
            OSError: If file cannot be read.
        """
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def get_current_commit(self, root: Path) -> str | None:
        """Get current HEAD commit hash.

        Args:
            root: Project root directory.

        Returns:
            Commit hash string or None if Git unavailable.
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (FileNotFoundError, subprocess.CalledProcessError):
            return None
