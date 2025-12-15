"""Data models for the code mapper module.

This module contains immutable dataclasses representing code structure elements
extracted from source code via tree-sitter parsing, as well as custom exceptions.
"""

from dataclasses import dataclass


class QueryLoadError(Exception):
    """Raised when a tree-sitter query file cannot be loaded.

    This exception wraps lower-level errors (FileNotFoundError, IOError, etc.)
    that occur when loading .scm query files from the languages/ directory.

    Attributes:
        language_id: The language identifier for which query loading failed.
        message: Human-readable error description.

    Example:
        >>> raise QueryLoadError("python", "Query file not found: languages/python.scm")
    """

    def __init__(self, language_id: str, message: str) -> None:
        """Initialize QueryLoadError.

        Args:
            language_id: The language identifier (e.g., "python", "javascript").
            message: Descriptive error message.
        """
        self.language_id = language_id
        super().__init__(f"Failed to load query for '{language_id}': {message}")


@dataclass(frozen=True)
class CodeNode:
    """Immutable representation of a code structure element.

    This frozen dataclass encapsulates information about a single code element
    (class, function, or import) extracted from source code via tree-sitter.
    Instances cannot be modified after creation.

    Attributes:
        type: Type of code element ("class", "function", "import").
        name: Name of the element (e.g., "MyClass", "calculate_tax", "os").
        start_line: Starting line number (1-indexed).
        end_line: Ending line number (1-indexed, inclusive).

    Example:
        >>> node = CodeNode(
        ...     type="function",
        ...     name="foo",
        ...     start_line=1,
        ...     end_line=3
        ... )
        >>> print(node.name)
        foo
    """

    type: str
    name: str
    start_line: int
    end_line: int
