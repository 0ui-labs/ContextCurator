"""File walker for discovering files in a directory with pattern matching.

This module provides FileWalker class for discovering files in a directory
and returning FileEntry objects with metadata (path, size, token estimation).
Supports pattern-based exclusion using gitignore-style wildcards.
"""

from pathlib import Path

import pathspec

from codemap.scout.models import FileEntry

# Directories to always ignore
DEFAULT_IGNORES: set[str] = {".git", ".venv", "__pycache__"}


class FileWalker:
    """Discover files in a directory and return FileEntry objects with metadata.

    This class walks a directory tree and collects file information, excluding
    files and directories based on both default ignore patterns and custom
    gitignore-style patterns provided by the user.

    Default ignores:
    - .git (version control)
    - .venv (virtual environment)
    - __pycache__ (Python cache)

    Pattern matching uses pathspec library for gitignore-style wildcards:
    - *.tmp - matches all .tmp files
    - *.log - matches all .log files
    - node_modules/ - matches entire directory
    - test_*.py - matches files with wildcards

    Returns:
    - List of FileEntry objects sorted alphabetically by path
    - Each FileEntry contains: path (relative Path), size (bytes), token_est (size // 4)
    """

    def __init__(self) -> None:
        """Initialize FileWalker."""

    def walk(self, root: Path, ignore_patterns: list[str] | None = None) -> list[FileEntry]:
        """Walk directory tree and collect file information.

        Traverses the directory tree starting from root, collecting FileEntry
        objects for each file found. Excludes directories and files matching
        default ignores or provided patterns. Results are sorted alphabetically.

        Args:
            root: Root directory to walk (must exist and be a directory).
            ignore_patterns: Optional list of gitignore-style patterns to exclude
                files/dirs. Defaults to None (only DEFAULT_IGNORES applied).
                Examples: ["*.tmp", "*.log", "node_modules/", "test_*.py"]

        Returns:
            List of FileEntry objects sorted alphabetically by path.
            Each entry contains relative path, size in bytes, and estimated tokens.

        Raises:
            ValueError: If root does not exist or is not a directory.
        """
        # Normalize ignore_patterns to empty list if None
        if ignore_patterns is None:
            ignore_patterns = []

        # Input validation
        if not root.exists():
            msg = f"Path does not exist: {root}"
            raise ValueError(msg)

        if not root.is_dir():
            msg = f"Path is not a directory: {root}"
            raise ValueError(msg)

        # Task 4: Compile patterns
        all_patterns = list(DEFAULT_IGNORES) + ignore_patterns
        spec = pathspec.PathSpec.from_lines("gitwildmatch", all_patterns)

        entries: list[FileEntry] = []

        # Directory traversal
        for path in root.rglob("*"):
            # Skip directories - only collect files
            # Handle OSError in case is_dir() fails (e.g., permission denied)
            try:
                is_directory = path.is_dir()
            except OSError:
                continue
            if is_directory:
                continue

            # Calculate relative path
            relative_path = path.relative_to(root)

            # Early pruning: skip files within default-ignored directories
            # This short-circuits before pathspec matching for better efficiency
            if any(part in DEFAULT_IGNORES for part in relative_path.parts):
                continue

            # Normalize for cross-platform pattern matching
            pattern_path = str(relative_path).replace("\\", "/")

            # Check against pathspec (user-specified patterns)
            if spec.match_file(pattern_path):
                continue

            # Collect metadata with error handling for inaccessible files
            try:
                size = path.stat().st_size
                token_est = size // 4
                entries.append(FileEntry(path=relative_path, size=size, token_est=token_est))
            except OSError:
                # Skip files that become inaccessible (permission errors, etc.)
                continue

        # Sort alphabetically by path (case-sensitive string comparison)
        entries.sort(key=lambda e: str(e.path))

        return entries
