"""Unit tests for mapper.engine module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from codemap.mapper.engine import (
    LANGUAGE_MAP,
    ParserEngine,
    get_supported_languages,
)
from codemap.mapper.models import QueryLoadError


class TestLanguageConfiguration:
    """Test suite for language configuration constants and helpers."""

    def test_language_map_contains_python(self) -> None:
        """Test LANGUAGE_MAP contains .py -> python mapping."""
        assert ".py" in LANGUAGE_MAP
        assert LANGUAGE_MAP[".py"] == "python"

    def test_supported_languages_contains_python(self) -> None:
        """Test get_supported_languages includes python from .scm file."""
        supported = get_supported_languages()
        assert "python" in supported
        assert isinstance(supported, set)

    def test_get_supported_languages_returns_set(self) -> None:
        """Test get_supported_languages returns a set of language IDs.

        This test verifies only the contract of get_supported_languages():
        - Returns a set type
        - Contains at least one known language (python)

        The implementation source (LANGUAGE_QUERIES dict vs. directory scan)
        is intentionally not tested here to allow implementation flexibility.
        """
        languages = get_supported_languages()
        assert isinstance(languages, set)
        assert "python" in languages

    def test_language_map_values_have_query_support(self) -> None:
        """Test all languages in LANGUAGE_MAP have query support.

        Verifies that every language mapped from file extensions has
        corresponding query patterns available via get_supported_languages().
        This decouples the test from internal implementation details
        (LANGUAGE_QUERIES dict vs. .scm file loading).
        """
        supported = get_supported_languages()
        for lang_id in LANGUAGE_MAP.values():
            assert lang_id in supported, (
                f"Language '{lang_id}' is in LANGUAGE_MAP but not supported. "
                f"Ensure a query file exists at languages/{lang_id}.scm"
            )

    def test_get_supported_languages_scans_directory(self) -> None:
        """Test get_supported_languages scans languages/ directory for .scm files.

        This test verifies that get_supported_languages() dynamically discovers
        available languages by scanning the languages/ directory for .scm files,
        rather than returning hardcoded values.
        """
        from unittest.mock import MagicMock

        # Create mock Traversable objects representing files in languages/ package
        mock_python_scm = MagicMock()
        mock_python_scm.name = "python.scm"

        mock_javascript_scm = MagicMock()
        mock_javascript_scm.name = "javascript.scm"

        mock_readme = MagicMock()
        mock_readme.name = "README.md"

        mock_init = MagicMock()
        mock_init.name = "__init__.py"

        # Mock importlib.resources.files to return our fake directory
        mock_languages_dir = MagicMock()
        mock_languages_dir.iterdir.return_value = [
            mock_python_scm,
            mock_javascript_scm,
            mock_readme,
            mock_init,
        ]

        with patch("codemap.mapper.engine.files", return_value=mock_languages_dir):
            languages = get_supported_languages()

            # Should return language IDs extracted from .scm filenames
            # (excluding non-.scm files like README.md and __init__.py)
            assert languages == {"python", "javascript"}, (
                f"Expected {{'python', 'javascript'}} from directory scan, but got: {languages}"
            )

    def test_get_supported_languages_missing_directory_returns_empty_set(self) -> None:
        """Test get_supported_languages returns empty set when languages/ directory is missing.

        This tests the graceful degradation path when the languages package
        doesn't exist (e.g., during incomplete installation).
        """
        # Mock files() to raise FileNotFoundError (simulating missing package)
        with patch("codemap.mapper.engine.files", side_effect=FileNotFoundError):
            languages = get_supported_languages()

            assert languages == set(), (
                f"Expected empty set when languages/ directory is missing, but got: {languages}"
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

    def test_unsupported_language_raises_query_load_error(self) -> None:
        """Test parser raises QueryLoadError for unsupported language.

        When a language_id is passed that has no corresponding .scm query file,
        ParserEngine.parse() raises QueryLoadError with the language_id attribute.
        """
        code = "def foo(): pass"
        engine = ParserEngine()

        with pytest.raises(QueryLoadError) as exc_info:
            engine.parse(code, language_id="javascript")

        assert exc_info.value.language_id == "javascript"

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

    def test_loads_query_from_disk(self) -> None:
        """Test parser loads query from .scm file via importlib.resources.

        This test verifies that ParserEngine.parse() loads query strings
        from external .scm files using importlib.resources.files().
        """
        from unittest.mock import MagicMock

        code = "def foo():\n    pass\n"
        engine = ParserEngine()

        # Create a mock query file that returns valid Python query
        mock_query_file = MagicMock()
        mock_query_file.read_text.return_value = """
        (function_definition name: (identifier) @function.name)
        """

        # Mock the files() function to return our mock package
        mock_languages_pkg = MagicMock()
        mock_languages_pkg.__truediv__ = MagicMock(return_value=mock_query_file)

        with patch("codemap.mapper.engine.files", return_value=mock_languages_pkg):
            nodes = engine.parse(code, language_id="python")

            # Verify files() was called with the languages package
            # Verify read_text was called on the query file
            mock_query_file.read_text.assert_called_once_with(encoding="utf-8")

        # Verify parsing succeeds with mocked file content
        assert len(nodes) == 1
        assert nodes[0].type == "function"
        assert nodes[0].name == "foo"

    def test_query_file_not_found_raises_query_load_error(self) -> None:
        """Test parser raises QueryLoadError when .scm file is missing.

        This test verifies that when a language's .scm query file is missing,
        ParserEngine.parse() raises QueryLoadError with a helpful message including
        the expected file path and the language_id attribute for programmatic handling.
        """
        from unittest.mock import MagicMock

        code = "def foo():\n    pass\n"
        # Use fresh engine to ensure cache miss
        engine = ParserEngine()

        # Create mock query file that raises FileNotFoundError on read
        mock_query_file = MagicMock()
        mock_query_file.read_text.side_effect = FileNotFoundError("No such file")

        # Mock the files() function to return our mock package
        mock_languages_pkg = MagicMock()
        mock_languages_pkg.__truediv__ = MagicMock(return_value=mock_query_file)

        # Use "python" as language_id (valid tree-sitter language) but mock file load to fail
        with patch("codemap.mapper.engine.files", return_value=mock_languages_pkg):
            with pytest.raises(QueryLoadError) as exc_info:
                engine.parse(code, language_id="python")

            # Verify QueryLoadError has language_id attribute
            assert exc_info.value.language_id == "python", (
                f"Expected QueryLoadError.language_id to be 'python', "
                f"but got: {exc_info.value.language_id}"
            )

            # Verify error message is helpful
            error_message = str(exc_info.value)
            assert "python" in error_message, (
                f"Expected error message to contain language name, but got: {error_message}"
            )
            assert "languages/" in error_message and ".scm" in error_message, (
                f"Expected error message to contain expected file path, but got: {error_message}"
            )

    def test_missing_languages_package_raises_query_load_error(self) -> None:
        """Test parser raises QueryLoadError when languages/ package is missing.

        This test verifies that when the entire languages/ package doesn't exist
        (e.g., incomplete installation), ParserEngine.parse() raises QueryLoadError
        with a helpful message and language_id attribute for programmatic handling.
        """
        code = "def foo():\n    pass\n"
        engine = ParserEngine()

        # Mock files() to raise ModuleNotFoundError (simulating missing package)
        with patch(
            "codemap.mapper.engine.files",
            side_effect=ModuleNotFoundError("No module named 'codemap.mapper.languages'"),
        ):
            with pytest.raises(QueryLoadError) as exc_info:
                engine.parse(code, language_id="python")

            # Verify QueryLoadError has language_id attribute
            assert exc_info.value.language_id == "python", (
                f"Expected QueryLoadError.language_id to be 'python', "
                f"but got: {exc_info.value.language_id}"
            )

            # Verify error message is helpful
            error_message = str(exc_info.value)
            assert "python" in error_message, (
                f"Expected error message to contain language name, but got: {error_message}"
            )
            assert "languages/" in error_message and ".scm" in error_message, (
                f"Expected error message to contain expected file path, but got: {error_message}"
            )


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
