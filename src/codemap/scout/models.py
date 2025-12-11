"""Data models for the scout module.

This module contains dataclasses used for structured data representation
in the scout module, particularly for tree generation reports.
"""

from dataclasses import dataclass


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
