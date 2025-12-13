"""Parser engine for extracting code structure using tree-sitter.

This module provides the main parsing functionality that uses tree-sitter
to analyze source code and extract structural information.
"""

from pathlib import Path
from typing import Iterator, Literal

from tree_sitter import Node, Query, QueryCursor
from tree_sitter_language_pack import get_language, get_parser

from codemap.mapper.models import CodeNode
from codemap.mapper.queries import PYTHON_ALL_QUERY

# Extension to language ID mapping
# Currently only Python supported, extensible for future languages
LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
}


class ParserEngine:
    """Parse source code and extract structural elements using tree-sitter.

    This class uses tree-sitter to parse source code and extract information
    about classes, functions, and imports. Currently supports Python only.

    Architecture:
    1. get_language_id() maps file extension to language identifier
    2. get_parser() initializes tree-sitter parser for language
    3. parse() executes queries and extracts CodeNode objects

    Example:
        >>> engine = ParserEngine()
        >>> code = "def foo():\\n    pass\\n"
        >>> nodes = engine.parse(code, language="python")
        >>> print(nodes[0].name)
        foo
    """

    def __init__(self) -> None:
        """Initialize ParserEngine."""
        pass

    def get_language_id(self, path: Path) -> str:
        """Map file path to tree-sitter language identifier.

        Extracts the file extension from the path and maps it to the
        corresponding tree-sitter language identifier.

        Args:
            path: Path to file (extension is extracted via path.suffix).

        Returns:
            Language identifier string (e.g., "python").

        Raises:
            ValueError: If file extension is not supported.
        """
        ext = path.suffix.lower()
        if ext not in LANGUAGE_MAP:
            raise ValueError(f"Unsupported file extension: {ext}")
        return LANGUAGE_MAP[ext]

    def _flatten_captures(self, captures_dict: dict[str, list[Node]]) -> Iterator[tuple[Node, str]]:
        """Flatten captures dict to (node, capture_name) sequence.

        Converts the dict-based captures result from tree-sitter's query API
        into an iterable of (node, capture_name) tuples for uniform iteration.

        Args:
            captures_dict: Dict mapping capture names to lists of nodes.

        Yields:
            Tuples of (node, capture_name) for each captured node.
        """
        for capture_name, nodes in captures_dict.items():
            for node in nodes:
                yield (node, capture_name)

    def parse(self, code: str, language: Literal["python"] = "python") -> list[CodeNode]:
        """Parse code and extract structural elements.

        Uses tree-sitter to parse source code and extract classes, functions,
        and imports as CodeNode objects. Line numbers are 1-indexed.

        Args:
            code: Source code string to parse.
            language: Language identifier (default: "python").

        Returns:
            List of CodeNode objects sorted by start_line.
            Empty list if code is empty or contains no extractable elements.

        Raises:
            ValueError: If language is not supported.
        """
        # Handle empty code
        if not code:
            return []

        # Validate language (type system ensures "python" at compile time,
        # but runtime check for dynamic callers)
        if language != "python":
            raise ValueError(f"Unsupported language: {language}")

        # Initialize parser and language
        parser = get_parser("python")
        lang = get_language("python")

        # Parse code (tree-sitter requires bytes)
        tree = parser.parse(bytes(code, "utf-8"))

        # Create query and cursor using tree-sitter API
        query = Query(lang, PYTHON_ALL_QUERY)
        cursor = QueryCursor(query)

        # Execute query and collect captures as (node, capture_name) sequence
        # cursor.captures() returns dict, we flatten to (node, capture_name) tuples
        captures = self._flatten_captures(cursor.captures(tree.root_node))

        # Map capture names to node types
        capture_to_type = {
            "function.name": "function",
            "class.name": "class",
            "import.name": "import",
            "import.module": "import",
        }

        # Extract CodeNode objects from captures
        nodes: list[CodeNode] = []

        for ts_node, capture_name in captures:
            # Get node type from mapping (all capture names from our query are known)
            node_type = capture_to_type[capture_name]

            # Extract node information
            # text is always bytes for identifier/dotted_name nodes from our queries
            name = ts_node.text.decode("utf-8")  # type: ignore[union-attr]

            # For functions and classes, use parent node for line range
            # (captures the entire definition, not just the identifier)
            if node_type in ("function", "class") and ts_node.parent:
                parent = ts_node.parent
                start_line = parent.start_point[0] + 1
                end_line = parent.end_point[0] + 1
            else:
                # For imports, use the identifier node directly
                start_line = ts_node.start_point[0] + 1
                end_line = ts_node.end_point[0] + 1

            nodes.append(
                CodeNode(
                    type=node_type,
                    name=name,
                    start_line=start_line,
                    end_line=end_line,
                )
            )

        # Sort by start_line for consistent ordering
        nodes.sort(key=lambda n: n.start_line)

        return nodes
