"""Tree generator for visualizing directory structures.

This module provides TreeGenerator class for creating visual representations
of directory structures similar to the Unix tree command, returning structured
TreeReport objects with statistics.
"""

from pathlib import Path

import pathspec

from codemap.scout.models import TreeReport

# Directories to always ignore
IGNORED_DIRS: set[str] = {".git", ".venv", "__pycache__"}

# Files to always ignore (meta-files)
IGNORED_FILES: set[str] = {".gitignore"}

# Tree structure symbols
BRANCH: str = "├── "
LAST_BRANCH: str = "└── "
VERTICAL: str = "│   "
SPACE: str = "    "


class TreeGenerator:
    """Generate tree structure visualizations of directories.

    This class creates visual representations of directory structures
    similar to the Unix tree command, with unlimited depth traversal
    and automatic filtering of common hidden directories.

    The generate method returns a TreeReport containing the tree visualization
    string along with statistics about files, folders, and estimated tokens.

    Supports .gitignore patterns for excluding files and directories using
    the pathspec library.
    """

    def __init__(self) -> None:
        """Initialize TreeGenerator."""

    def generate(self, root_path: Path) -> TreeReport:
        """Generate a tree structure visualization of a directory.

        Traverses the entire directory tree without depth limits, filtering
        out hidden directories (.git, .venv, __pycache__), .gitignore patterns,
        and returning a structured report with the tree visualization and statistics.

        Performance optimizations:
        - String building: Uses list accumulation with single final join()
        - PathSpec: Compiles gitignore patterns once, reuses in all recursive calls
        - Path operations: Caches path.name and entry.name to avoid repeated property access
        - Statistics: Mutable dict passed by reference (no copying overhead)
        - Memory: List-based approach is efficient for typical codebases (<10k files)

        Args:
            root_path: Root directory to visualize.

        Returns:
            TreeReport containing tree_string, total_files, total_folders,
            and estimated_tokens.

        Raises:
            ValueError: If root_path does not exist or is not a directory.
        """
        if not root_path.exists():
            msg = f"Path does not exist: {root_path}"
            raise ValueError(msg)

        if not root_path.is_dir():
            msg = f"Path is not a directory: {root_path}"
            raise ValueError(msg)

        # Initialize local state for this traversal
        stats: dict[str, int] = {"files": 0, "folders": 0}
        gitignore_spec = self._load_gitignore(root_path)

        result: list[str] = [f"{root_path.name}/"]
        result.extend(self._generate_tree(root_path, "", root_path, gitignore_spec, stats))

        tree_string = "\n".join(result)
        estimated_tokens = int(len(tree_string) / 3.5)

        return TreeReport(
            tree_string=tree_string,
            total_files=stats["files"],
            total_folders=stats["folders"],
            estimated_tokens=estimated_tokens,
        )

    def _load_gitignore(self, root_path: Path) -> pathspec.PathSpec | None:
        """Load and compile .gitignore patterns from the root directory.

        Args:
            root_path: Root directory to look for .gitignore file.

        Returns:
            Compiled PathSpec if .gitignore exists and is readable, None otherwise.
            Returns None on read errors (permissions, encoding) to allow traversal to continue.
        """
        gitignore_path = root_path / ".gitignore"
        if not gitignore_path.exists():
            return None

        try:
            gitignore_content = gitignore_path.read_text()
        except (OSError, UnicodeError):
            # TODO: Consider logging when .gitignore cannot be read
            return None

        return pathspec.PathSpec.from_lines("gitwildmatch", gitignore_content.splitlines())

    def _should_ignore(
        self,
        path: Path,
        root_path: Path,
        gitignore_spec: pathspec.PathSpec | None,
    ) -> bool:
        """Check if a path should be ignored.

        First checks against hard-coded IGNORED_DIRS and IGNORED_FILES,
        then consults the .gitignore PathSpec if available.

        Performance notes:
        - Cache path.name to avoid repeated property access
        - Early return on hard-coded checks before expensive gitignore matching

        Args:
            path: Path to check.
            root_path: Root directory for relative path calculation.
            gitignore_spec: Compiled gitignore patterns, or None if not available.

        Returns:
            True if path should be ignored, False otherwise.
        """
        # Cache path.name to avoid repeated property access
        path_name = path.name

        # Check hard-coded ignored directories
        if path_name in IGNORED_DIRS:
            return True

        # Check hard-coded ignored files (meta-files like .gitignore)
        if path_name in IGNORED_FILES:
            return True

        # Check .gitignore patterns if available
        if gitignore_spec is not None:
            # Calculate relative path from root for pattern matching
            relative_path = path.relative_to(root_path)
            # Normalize backslashes to forward slashes for cross-platform compatibility
            pattern_path = str(relative_path).replace("\\", "/")
            # For directories, append trailing slash for proper pattern matching
            if path.is_dir():
                pattern_path += "/"
            if gitignore_spec.match_file(pattern_path):
                return True

        return False

    def _generate_tree(
        self,
        path: Path,
        prefix: str,
        root_path: Path,
        gitignore_spec: pathspec.PathSpec | None,
        stats: dict[str, int],
    ) -> list[str]:
        """Generate tree structure recursively with unlimited depth.

        Performance notes:
        - Uses list.append() and list.extend() to avoid string concatenation
        - Caches entry.name to avoid repeated property access in hot path
        - Mutable stats dict passed by reference (no copying overhead)

        Args:
            path: Current directory to process.
            prefix: Indentation prefix for current level.
            root_path: Root directory for relative path calculation.
            gitignore_spec: Compiled gitignore patterns, or None if not available.
            stats: Mutable dictionary with 'files' and 'folders' keys for counting.

        Returns:
            List of formatted lines representing the tree structure.
        """
        result: list[str] = []

        # Collect and filter entries
        # Silently skip directories that cannot be read (e.g., permission denied)
        try:
            entries = [
                entry
                for entry in path.iterdir()
                if not self._should_ignore(entry, root_path, gitignore_spec)
            ]
        except OSError:
            return result

        # Sort alphabetically (case-insensitive)
        entries = sorted(entries, key=lambda p: p.name.lower())

        for index, entry in enumerate(entries):
            is_last = index == len(entries) - 1
            symbol = LAST_BRANCH if is_last else BRANCH
            # Cache entry.name to avoid repeated property access
            entry_name = entry.name

            if entry.is_dir():
                stats["folders"] += 1
                result.append(f"{prefix}{symbol}{entry_name}/")
                new_prefix = prefix + (SPACE if is_last else VERTICAL)
                result.extend(
                    self._generate_tree(entry, new_prefix, root_path, gitignore_spec, stats)
                )
            else:
                stats["files"] += 1
                result.append(f"{prefix}{symbol}{entry_name}")

        return result
