"""Data models for the scout module.

This module contains dataclasses used for structured data representation
in the scout module, particularly for tree generation reports.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TreeReport:
    """Immutable report containing tree visualization and statistics.

    This frozen dataclass encapsulates the results of a directory tree generation,
    including the visual representation and metadata about the scanned structure.
    Instances cannot be modified after creation.

    Attributes:
        tree_string: The visual tree structure in Unix tree style format.
        total_files: Count of scanned files in the directory tree.
        total_folders: Count of scanned folders (directories) in the tree.
        estimated_tokens: Token estimation for LLM context usage,
            calculated as len(tree_string) / 3.5 rounded to int.

    Example:
        >>> report = TreeReport(
        ...     tree_string="project/\\n├── src/\\n└── README.md",
        ...     total_files=1,
        ...     total_folders=1,
        ...     estimated_tokens=10
        ... )
        >>> print(report.tree_string)
        project/
        ├── src/
        └── README.md
    """

    tree_string: str
    total_files: int
    total_folders: int
    estimated_tokens: int


@dataclass(frozen=True)
class FileEntry:
    """Immutable representation of a file with metadata for LLM context.

    This frozen dataclass encapsulates information about a single file,
    including its path, size, and estimated token count for LLM processing.
    Instances cannot be modified after creation.

    Attributes:
        path: Relative file path from the project root as a Path object.
        size: File size in bytes.
        token_est: Estimated token count for LLM context usage,
            calculated as size / 4 rounded to int.

    Example:
        >>> entry = FileEntry(
        ...     path=Path("src/main.py"),
        ...     size=1024,
        ...     token_est=256
        ... )
        >>> print(entry.path)
        src/main.py
        >>> print(entry.size)
        1024
    """

    path: Path
    size: int
    token_est: int
