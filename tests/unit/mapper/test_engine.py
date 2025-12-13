"""Unit tests for mapper.engine module."""

import pytest
from pathlib import Path

from codemap.mapper.engine import ParserEngine
from codemap.mapper.models import CodeNode


class TestLanguageMapping:
    """Test suite for language identification functionality."""

    def test_get_language_id_python(self):
        """Test .py extension maps to 'python' language ID."""
        engine = ParserEngine()
        language = engine.get_language_id(".py")
        assert language == "python"

    def test_get_language_id_unknown_extension(self):
        """Test unknown extension raises ValueError."""
        engine = ParserEngine()
        with pytest.raises(ValueError):
            engine.get_language_id(".xyz")


class TestParserEngine:
    """Test suite for ParserEngine parsing functionality."""

    def test_extracts_function_definition(self):
        """Test parser extracts function definition with correct metadata."""
        code = "def foo():\n    pass\n"
        engine = ParserEngine()

        nodes = engine.parse(code, language="python")

        assert len(nodes) == 1
        assert nodes[0].type == "function"
        assert nodes[0].name == "foo"
        assert nodes[0].start_line == 1
        assert nodes[0].end_line == 2

    def test_extracts_class_definition(self):
        """Test parser extracts class definition with correct metadata."""
        code = "class MyClass:\n    pass\n"
        engine = ParserEngine()

        nodes = engine.parse(code, language="python")

        assert len(nodes) == 1
        assert nodes[0].type == "class"
        assert nodes[0].name == "MyClass"
        assert nodes[0].start_line == 1
        assert nodes[0].end_line == 2

    def test_extracts_import_statement(self):
        """Test parser extracts import statement with correct metadata."""
        code = "import os\n"
        engine = ParserEngine()

        nodes = engine.parse(code, language="python")

        assert len(nodes) == 1
        assert nodes[0].type == "import"
        assert nodes[0].name == "os"
        assert nodes[0].start_line == 1
        assert nodes[0].end_line == 1

    def test_extracts_import_from_statement(self):
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

        nodes = engine.parse(code, language="python")

        assert len(nodes) == 1
        assert nodes[0].type == "import"
        assert nodes[0].name == "pathlib"  # Module part, not imported symbol
        assert nodes[0].start_line == 1
        assert nodes[0].end_line == 1

    def test_extracts_multiple_definitions(self):
        """Test parser extracts multiple definitions from complex code."""
        code = """def first_function():
    pass

class MyClass:
    pass

def second_function():
    return 42
"""
        engine = ParserEngine()

        nodes = engine.parse(code, language="python")

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

    def test_empty_code_returns_empty_list(self):
        """Test parser returns empty list for empty code input."""
        code = ""
        engine = ParserEngine()

        nodes = engine.parse(code, language="python")

        assert nodes == []
        assert isinstance(nodes, list)
