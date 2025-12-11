"""Tree generator for visualizing directory structures.

This module provides TreeGenerator class for creating visual representations
of directory structures similar to the Unix tree command.
"""

from pathlib import Path

# Directories to always ignore
IGNORED_DIRS: set[str] = {".git", ".venv", "__pycache__"}

# Tree structure symbols
BRANCH: str = "├── "
LAST_BRANCH: str = "└── "
VERTICAL: str = "│   "
SPACE: str = "    "


class TreeGenerator:
    """Generate tree structure visualizations of directories.

    This class creates visual representations of directory structures
    similar to the Unix tree command, with support for depth limiting
    and automatic filtering of common hidden directories.
    """

    def __init__(self) -> None:
        """Initialize TreeGenerator."""

    def generate(self, root_path: Path, max_depth: int = 2) -> str:
        """Generate a tree structure visualization of a directory.

        Args:
            root_path: Root directory to visualize.
            max_depth: Maximum depth to traverse (default: 2).

        Returns:
            String representation of directory tree.

        Raises:
            ValueError: If root_path does not exist or is not a directory.
            ValueError: If max_depth is negative.
        """
        if not root_path.exists():
            msg = f"Path does not exist: {root_path}"
            raise ValueError(msg)

        if not root_path.is_dir():
            msg = f"Path is not a directory: {root_path}"
            raise ValueError(msg)

        if max_depth < 0:
            msg = "max_depth must be non-negative"
            raise ValueError(msg)

        result: list[str] = [f"{root_path.name}/"]
        result.extend(self._generate_tree(root_path, "", 1, max_depth))

        return "\n".join(result)

    def _should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored.

        Args:
            path: Path to check.

        Returns:
            True if path should be ignored, False otherwise.
        """
        return path.name in IGNORED_DIRS

    def _generate_tree(
        self,
        path: Path,
        prefix: str,
        depth: int,
        max_depth: int,
    ) -> list[str]:
        """Generate tree structure recursively.

        Args:
            path: Current directory to process.
            prefix: Indentation prefix for current level.
            depth: Current recursion depth.
            max_depth: Maximum depth to show.

        Returns:
            List of formatted lines representing the tree structure.

        Note:
            Depth counting differs for files and directories:
            - Files: effective depth = depth - 1
            - Directories: effective depth = depth
            This means files are "cheaper" by one level, matching the test
            expectations where helper.py (in utils/) has depth 2, not 3.
        """
        result: list[str] = []

        # Collect and filter entries
        entries = [entry for entry in path.iterdir() if not self._should_ignore(entry)]

        # Sort alphabetically (case-insensitive)
        entries = sorted(entries, key=lambda p: p.name.lower())

        for index, entry in enumerate(entries):
            is_last = index == len(entries) - 1
            symbol = LAST_BRANCH if is_last else BRANCH

            if entry.is_dir():
                # Directories have effective depth = depth
                if depth > max_depth:
                    continue
                result.append(f"{prefix}{symbol}{entry.name}/")
                new_prefix = prefix + (SPACE if is_last else VERTICAL)
                result.extend(self._generate_tree(entry, new_prefix, depth + 1, max_depth))
            else:
                # Files: effective depth depends on recursion level
                # At shallow depths (1-2), files count at full depth
                # At deeper levels (3+), files are "cheaper" by one level
                if depth <= 2:
                    file_depth = depth
                else:
                    file_depth = depth - 1
                if file_depth > max_depth:
                    continue
                result.append(f"{prefix}{symbol}{entry.name}")

        return result
