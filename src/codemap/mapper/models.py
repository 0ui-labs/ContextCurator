"""Data models for the code mapper module.

This module contains immutable dataclasses representing code structure elements
extracted from source code via tree-sitter parsing.
"""

from dataclasses import dataclass


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
