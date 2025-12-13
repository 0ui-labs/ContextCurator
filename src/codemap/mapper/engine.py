"""Parser engine for extracting code structure using tree-sitter.

This module provides the main parsing functionality that uses tree-sitter
to analyze source code and extract structural information.
"""

from pathlib import Path
from typing import Iterator

from tree_sitter import Node, Query, QueryCursor
from tree_sitter_language_pack import get_language, get_parser

from codemap.mapper.models import CodeNode
from codemap.mapper.queries import PYTHON_ALL_QUERY

# Extension to language ID mapping
# To add a new language: add entry here AND in LANGUAGE_QUERIES below
LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
}

# Language ID to query string mapping
# This is the single source of truth for which languages have query patterns defined.
# To add a new language: add entry here with the appropriate tree-sitter query string.
LANGUAGE_QUERIES: dict[str, str] = {
    "python": PYTHON_ALL_QUERY,
}

def get_supported_languages() -> set[str]:
    """Return the set of language IDs that have query patterns defined.

    Returns:
        Set of language identifier strings (e.g., {"python"}).
    """
    return set(LANGUAGE_QUERIES.keys())


class ParserEngine:
    """Parse source code and extract structural elements using tree-sitter.

    This class uses tree-sitter to parse source code and extract information
    about classes, functions, and imports.

    Extensibility:
        To add support for a new language:
        1. Add extension mapping in LANGUAGE_MAP (e.g., ".js": "javascript")
        2. Add query string in LANGUAGE_QUERIES (e.g., "javascript": JS_QUERY)
        No changes to ParserEngine methods are required.

    Architecture:
        1. LANGUAGE_MAP: maps file extensions to language identifiers
        2. LANGUAGE_QUERIES: maps language IDs to tree-sitter query strings
        3. get_language_id(): resolves path to language using LANGUAGE_MAP
        4. parse(): validates language against LANGUAGE_QUERIES, parses code
        5. parse_file(): combines get_language_id() and parse() for convenience

    Example:
        >>> engine = ParserEngine()
        >>> code = "def foo():\\n    pass\\n"
        >>> nodes = engine.parse(code, language_id="python")
        >>> print(nodes[0].name)
        foo

        # Or use parse_file for automatic language detection:
        >>> nodes = engine.parse_file(Path("example.py"), code)
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

    def parse(self, code: str, language_id: str = "python") -> list[CodeNode]:
        """Parse code and extract structural elements.

        Uses tree-sitter to parse source code and extract classes, functions,
        and imports as CodeNode objects. Line numbers are 1-indexed.

        The language_id parameter accepts any language identifier that has
        query patterns defined in LANGUAGE_QUERIES. Use get_language_id()
        to obtain the correct identifier from a file path, or
        get_supported_languages() to see available languages.

        Args:
            code: Source code string to parse.
            language_id: Language identifier. Must be present in LANGUAGE_QUERIES.
                Use get_supported_languages() to see available options.

        Returns:
            List of CodeNode objects sorted by start_line.
            Empty list if code is empty or contains no extractable elements.

        Raises:
            ValueError: If language_id is not in LANGUAGE_QUERIES.

        Example:
            >>> engine = ParserEngine()
            >>> lang_id = engine.get_language_id(Path("example.py"))
            >>> nodes = engine.parse(code, language_id=lang_id)
        """
        # Handle empty code
        if not code:
            return []

        # Validate language has query patterns defined (uses LANGUAGE_QUERIES as source of truth)
        if language_id not in LANGUAGE_QUERIES:
            supported = ", ".join(sorted(LANGUAGE_QUERIES.keys()))
            raise ValueError(
                f"No query patterns defined for language: {language_id}. "
                f"Supported languages: {supported}."
            )

        # Get the query string for this language from LANGUAGE_QUERIES
        query_string = LANGUAGE_QUERIES[language_id]

        # Initialize parser and language for the requested language_id
        # Type ignore: language_id is validated above; tree-sitter-language-pack
        # expects a Literal type but we use runtime validation for flexibility
        parser = get_parser(language_id)  # type: ignore[arg-type]
        lang = get_language(language_id)  # type: ignore[arg-type]

        # Parse code (tree-sitter requires bytes)
        tree = parser.parse(bytes(code, "utf-8"))

        # Create query and cursor using tree-sitter API
        query = Query(lang, query_string)
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

    def parse_file(self, path: Path, code: str | None = None) -> list[CodeNode]:
        """Parse file and extract structural elements with automatic language detection.

        Convenience method that combines get_language_id() and parse() for
        file-based parsing. Automatically determines the language from the
        file extension.

        Args:
            path: Path to the source file. Used to determine the language
                via get_language_id(). If code is None, the file is read
                from this path.
            code: Optional source code string. If None, the file at path
                is read. If provided, this code is parsed instead of
                reading from the file.

        Returns:
            List of CodeNode objects sorted by start_line.
            Empty list if code is empty or contains no extractable elements.

        Raises:
            ValueError: If file extension is not supported or language has
                no defined query patterns.
            FileNotFoundError: If code is None and the file does not exist.

        Example:
            >>> engine = ParserEngine()
            >>> # Parse file from disk:
            >>> nodes = engine.parse_file(Path("example.py"))
            >>> # Or parse provided code with language detection from path:
            >>> nodes = engine.parse_file(Path("example.py"), "def foo(): pass")
        """
        # Determine language from file extension
        language_id = self.get_language_id(path)

        # Read file if code not provided
        if code is None:
            code = path.read_text(encoding="utf-8")

        return self.parse(code, language_id=language_id)
