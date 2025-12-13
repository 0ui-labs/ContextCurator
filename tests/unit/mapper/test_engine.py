"""Unit tests for mapper.engine module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from codemap.mapper.engine import (
    LANGUAGE_MAP,
    LANGUAGE_QUERIES,
    ParserEngine,
    get_supported_languages,
)


class TestLanguageConfiguration:
    """Test suite for language configuration constants and helpers."""

    def test_language_map_contains_python(self) -> None:
        """Test LANGUAGE_MAP contains .py -> python mapping."""
        assert ".py" in LANGUAGE_MAP
        assert LANGUAGE_MAP[".py"] == "python"

    def test_language_queries_contains_python(self) -> None:
        """Test LANGUAGE_QUERIES contains python query string."""
        assert "python" in LANGUAGE_QUERIES
        assert isinstance(LANGUAGE_QUERIES["python"], str)
        assert len(LANGUAGE_QUERIES["python"]) > 0

    def test_get_supported_languages_returns_set(self) -> None:
        """Test get_supported_languages returns a set of language IDs."""
        languages = get_supported_languages()
        assert isinstance(languages, set)
        assert "python" in languages

    def test_language_map_values_in_language_queries(self) -> None:
        """Test all languages in LANGUAGE_MAP have queries in LANGUAGE_QUERIES."""
        for lang_id in LANGUAGE_MAP.values():
            assert lang_id in LANGUAGE_QUERIES, (
                f"Language '{lang_id}' is in LANGUAGE_MAP but not in LANGUAGE_QUERIES"
            )


class TestLanguageMapping:
    """Test suite for language identification functionality."""

    def test_get_language_id_python(self) -> None:
        """Test .py extension maps to 'python' language ID."""
        engine = ParserEngine()
        language = engine.get_language_id(Path("example.py"))
        assert language == "python"

    def test_get_language_id_unknown_extension(self) -> None:
        """Test unknown extension raises ValueError."""
        engine = ParserEngine()
        with pytest.raises(ValueError):
            engine.get_language_id(Path("example.xyz"))


class TestParserEngine:
    """Test suite for ParserEngine parsing functionality."""

    def test_extracts_function_definition(self) -> None:
        """Test parser extracts function definition with correct metadata."""
        code = "def foo():\n    pass\n"
        engine = ParserEngine()

        nodes = engine.parse(code, language_id="python")

        assert len(nodes) == 1
        assert nodes[0].type == "function"
        assert nodes[0].name == "foo"
        assert nodes[0].start_line == 1
        assert nodes[0].end_line == 2

    def test_extracts_class_definition(self) -> None:
        """Test parser extracts class definition with correct metadata."""
        code = "class MyClass:\n    pass\n"
        engine = ParserEngine()

        nodes = engine.parse(code, language_id="python")

        assert len(nodes) == 1
        assert nodes[0].type == "class"
        assert nodes[0].name == "MyClass"
        assert nodes[0].start_line == 1
        assert nodes[0].end_line == 2

    def test_extracts_import_statement(self) -> None:
        """Test parser extracts import statement with correct metadata."""
        code = "import os\n"
        engine = ParserEngine()

        nodes = engine.parse(code, language_id="python")

        assert len(nodes) == 1
        assert nodes[0].type == "import"
        assert nodes[0].name == "os"
        assert nodes[0].start_line == 1
        assert nodes[0].end_line == 1

    def test_extracts_import_from_statement(self) -> None:
        """Test parser extracts from-import statement with correct metadata.

        Implementation Note:
            For `from X import Y` statements, the CodeNode represents the module
            being imported FROM, not the imported symbol:
            - type: "import"
            - name: module part (X), e.g., "pathlib" for `from pathlib import Path`

            This design decision means:
            - The module dependency is captured (useful for dependency analysis)
            - Imported symbols (Y) are not stored in this CodeNode

            Future extensions may add imported symbols via additional attributes
            or separate CodeNode instances without breaking this API contract.
        """
        code = "from pathlib import Path\n"
        engine = ParserEngine()

        nodes = engine.parse(code, language_id="python")

        assert len(nodes) == 1
        assert nodes[0].type == "import"
        assert nodes[0].name == "pathlib"  # Module part, not imported symbol
        assert nodes[0].start_line == 1
        assert nodes[0].end_line == 1

    def test_extracts_multiple_definitions(self) -> None:
        """Test parser extracts multiple definitions from complex code."""
        code = """def first_function():
    pass

class MyClass:
    pass

def second_function():
    return 42
"""
        engine = ParserEngine()

        nodes = engine.parse(code, language_id="python")

        assert len(nodes) == 3
        # First function
        assert nodes[0].type == "function"
        assert nodes[0].name == "first_function"
        # Class
        assert nodes[1].type == "class"
        assert nodes[1].name == "MyClass"
        # Second function
        assert nodes[2].type == "function"
        assert nodes[2].name == "second_function"

    def test_empty_code_returns_empty_list(self) -> None:
        """Test parser returns empty list for empty code input."""
        code = ""
        engine = ParserEngine()

        nodes = engine.parse(code, language_id="python")

        assert nodes == []
        assert isinstance(nodes, list)

    def test_unsupported_language_raises_error(self) -> None:
        """Test parser raises ValueError for unsupported language."""
        code = "def foo(): pass"
        engine = ParserEngine()

        with pytest.raises(ValueError):
            engine.parse(code, language_id="javascript")

    def test_query_cache_reuses_compiled_query(self) -> None:
        """Test that ParserEngine reuses cached Query objects for same language.

        Verifies caching via:
        1. Public cached_languages property (stable interface)
        2. Mocking Query constructor to count instantiations
        """
        from tree_sitter import Query

        engine = ParserEngine()
        code = "def foo():\n    pass\n"

        # Wrap Query to count instantiations
        with patch("codemap.mapper.engine.Query", wraps=Query) as mock_query:
            # First parse - populates cache (Query constructor called)
            nodes1 = engine.parse(code, language_id="python")

            # Verify cache was populated via public property
            assert "python" in engine.cached_languages
            assert mock_query.call_count == 1

            # Second parse - should hit cache (Query constructor NOT called again)
            nodes2 = engine.parse(code, language_id="python")

            # Verify Query was only instantiated once (cache hit)
            assert mock_query.call_count == 1

            # Verify results are identical
            assert nodes1 == nodes2


class TestParseFile:
    """Test suite for parse_file() convenience method."""

    def test_parse_file_with_provided_code(self) -> None:
        """Test parse_file uses get_language_id and parses provided code."""
        code = "def foo():\n    pass\n"
        engine = ParserEngine()

        nodes = engine.parse_file(Path("example.py"), code)

        assert len(nodes) == 1
        assert nodes[0].type == "function"
        assert nodes[0].name == "foo"

    def test_parse_file_reads_from_disk(self, tmp_path: Path) -> None:
        """Test parse_file reads file from disk when code is None."""
        code = "class MyClass:\n    pass\n"
        file_path = tmp_path / "test_file.py"
        file_path.write_text(code)
        engine = ParserEngine()

        nodes = engine.parse_file(file_path)

        assert len(nodes) == 1
        assert nodes[0].type == "class"
        assert nodes[0].name == "MyClass"

    def test_parse_file_unsupported_extension(self) -> None:
        """Test parse_file raises ValueError for unsupported file extension."""
        engine = ParserEngine()

        with pytest.raises(ValueError):
            engine.parse_file(Path("example.xyz"), "code")

    def test_parse_file_missing_file(self, tmp_path: Path) -> None:
        """Test parse_file raises FileNotFoundError when file does not exist."""
        engine = ParserEngine()
        non_existent = tmp_path / "non_existent.py"

        with pytest.raises(FileNotFoundError):
            engine.parse_file(non_existent)

    def test_parse_file_uses_get_language_id(self) -> None:
        """Test parse_file correctly delegates to get_language_id."""
        code = "import os\n"
        engine = ParserEngine()

        # This should work because .py maps to "python"
        nodes = engine.parse_file(Path("test.py"), code)

        assert len(nodes) == 1
        assert nodes[0].type == "import"
        assert nodes[0].name == "os"
