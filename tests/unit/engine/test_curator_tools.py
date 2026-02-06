"""Unit tests for engine.curator_tools module.

Test suite for CuratorTools - LLM-friendly wrapper around MapRenderer.
Follows AAA (Arrange-Act-Assert) pattern and TDD methodology.

Test Organization:
    - TestCuratorToolsInit: Verify constructor and dependency injection
    - TestGetProjectOverview: Level 0 project overview tool
    - TestZoomToPackage: Level 1 package zoom tool
    - TestZoomToModule: Level 2 module zoom tool
    - TestZoomToSymbol: Level 3 symbol zoom tool
    - TestShowCode: Level 4 code display tool
    - TestDocstrings: LLM-optimized documentation
    - TestIntegration: End-to-end with real graph data
"""

from __future__ import annotations

from pathlib import Path

import pytest

from codemap.engine.curator_tools import CuratorTools
from codemap.engine.map_renderer import MapRenderer
from codemap.graph import GraphManager
from codemap.mapper.models import CodeNode
from codemap.scout.models import FileEntry


@pytest.fixture
def simple_graph_with_hierarchy() -> GraphManager:
    """GraphManager with complete hierarchy and enriched attributes.

    Structure:
        project::TestProject
        └── src (package)
            ├── src/auth (package)
            │   ├── src/auth/login.py (file)
            │   │   ├── authenticate (function)
            │   │   └── LoginValidator (class)
            │   └── src/auth/models.py (file)
            │       └── User (class)
            └── src/utils (package)
                └── src/utils/helpers.py (file)
                    └── format_date (function)

    Imports:
        src/auth/login.py -> src/utils/helpers.py
        src/auth/login.py -> src/auth/models.py
    """
    gm = GraphManager()

    gm.add_file(FileEntry(Path("src/auth/login.py"), size=500, token_est=125))
    gm.add_file(FileEntry(Path("src/auth/models.py"), size=300, token_est=75))
    gm.add_file(FileEntry(Path("src/utils/helpers.py"), size=200, token_est=50))

    gm.add_node("src/auth/login.py", CodeNode("function", "authenticate", 1, 20))
    gm.add_node("src/auth/login.py", CodeNode("class", "LoginValidator", 22, 50))
    gm.add_node("src/auth/models.py", CodeNode("class", "User", 1, 30))
    gm.add_node("src/utils/helpers.py", CodeNode("function", "format_date", 1, 10))

    gm.build_hierarchy("TestProject")

    gm.graph.nodes["project::TestProject"]["summary"] = (
        "A test authentication project"
    )
    gm.graph.nodes["src"]["summary"] = "Source code root"
    gm.graph.nodes["src/auth"]["summary"] = "Authentication package"
    gm.graph.nodes["src/utils"]["summary"] = "Utility functions"
    gm.graph.nodes["src/auth/login.py"]["summary"] = (
        "Login and authentication logic"
    )
    gm.graph.nodes["src/auth/models.py"]["summary"] = "Data models for auth"
    gm.graph.nodes["src/utils/helpers.py"]["summary"] = (
        "Helper utility functions"
    )
    gm.graph.nodes["src/auth/login.py::authenticate"]["summary"] = (
        "Authenticates user credentials"
    )
    gm.graph.nodes["src/auth/login.py::authenticate"]["risks"] = [
        "Security critical",
        "Rate limiting needed",
    ]
    gm.graph.nodes["src/auth/login.py::LoginValidator"]["summary"] = (
        "Validates login form data"
    )
    gm.graph.nodes["src/auth/login.py::LoginValidator"]["risks"] = [
        "Input validation bypass"
    ]
    gm.graph.nodes["src/auth/models.py::User"]["summary"] = "User data model"
    gm.graph.nodes["src/auth/models.py::User"]["risks"] = []
    gm.graph.nodes["src/utils/helpers.py::format_date"]["summary"] = (
        "Formats dates to ISO string"
    )
    gm.graph.nodes["src/utils/helpers.py::format_date"]["risks"] = []

    gm.add_dependency("src/auth/login.py", "src/utils/helpers.py")
    gm.add_dependency("src/auth/login.py", "src/auth/models.py")

    return gm


@pytest.fixture
def empty_graph() -> GraphManager:
    """Empty GraphManager for edge case tests."""
    return GraphManager()


@pytest.fixture
def tools(simple_graph_with_hierarchy: GraphManager) -> CuratorTools:
    """CuratorTools with simple graph hierarchy."""
    renderer = MapRenderer(simple_graph_with_hierarchy)
    return CuratorTools(renderer)


@pytest.fixture
def tools_empty(empty_graph: GraphManager) -> CuratorTools:
    """CuratorTools with empty graph."""
    renderer = MapRenderer(empty_graph)
    return CuratorTools(renderer)


class TestCuratorToolsInit:
    """Tests for initialization and dependency injection."""

    def test_init_stores_map_renderer(self) -> None:
        """CuratorTools stores MapRenderer as _renderer attribute."""
        gm = GraphManager()
        renderer = MapRenderer(gm)
        tools = CuratorTools(renderer)
        assert tools._renderer is renderer

    def test_init_accepts_map_renderer_instance(self) -> None:
        """CuratorTools accepts MapRenderer via dependency injection."""
        gm = GraphManager()
        renderer = MapRenderer(gm)
        tools = CuratorTools(renderer)
        assert isinstance(tools._renderer, MapRenderer)


class TestGetProjectOverview:
    """Tests for get_project_overview tool (Level 0)."""

    def test_returns_project_overview_markdown(
        self, tools: CuratorTools
    ) -> None:
        """Returns Markdown with project name and structure."""
        output = tools.get_project_overview()
        assert "# TestProject" in output
        assert "A test authentication project" in output

    def test_handles_empty_graph(self, tools_empty: CuratorTools) -> None:
        """Returns 'No project node found' for empty graph."""
        output = tools_empty.get_project_overview()
        assert "No project node found" in output


class TestZoomToPackage:
    """Tests for zoom_to_package tool (Level 1)."""

    def test_returns_package_markdown_for_valid_path(
        self, tools: CuratorTools
    ) -> None:
        """Returns Markdown for valid package path."""
        output = tools.zoom_to_package("src/auth")
        assert "# src/auth/" in output
        assert "Authentication package" in output

    def test_raises_value_error_for_nonexistent_package(
        self, tools: CuratorTools
    ) -> None:
        """ValueError raised for package not in graph."""
        with pytest.raises(ValueError, match="nicht gefunden"):
            tools.zoom_to_package("nonexistent/pkg")

    def test_raises_value_error_for_wrong_node_type(
        self, tools: CuratorTools
    ) -> None:
        """ValueError raised when path points to file instead of package."""
        with pytest.raises(ValueError, match="nicht gefunden"):
            tools.zoom_to_package("src/auth/login.py")

    def test_error_message_is_descriptive(
        self, tools: CuratorTools
    ) -> None:
        """Error message contains the requested path."""
        with pytest.raises(ValueError, match="nonexistent/pkg"):
            tools.zoom_to_package("nonexistent/pkg")


class TestZoomToModule:
    """Tests for zoom_to_module tool (Level 2)."""

    def test_returns_module_markdown_for_valid_path(
        self, tools: CuratorTools
    ) -> None:
        """Returns Markdown for valid module path."""
        output = tools.zoom_to_module("src/auth/login.py")
        assert "# src/auth/login.py" in output
        assert "Login and authentication logic" in output

    def test_raises_value_error_for_nonexistent_module(
        self, tools: CuratorTools
    ) -> None:
        """ValueError raised for module not in graph."""
        with pytest.raises(ValueError, match="nicht gefunden"):
            tools.zoom_to_module("nonexistent/file.py")

    def test_raises_value_error_for_wrong_node_type(
        self, tools: CuratorTools
    ) -> None:
        """ValueError raised when path points to package instead of file."""
        with pytest.raises(ValueError, match="nicht gefunden"):
            tools.zoom_to_module("src/auth")

    def test_handles_module_without_code_nodes(self) -> None:
        """Module with no code nodes still renders correctly."""
        gm = GraphManager()
        gm.add_file(FileEntry(Path("src/empty.py"), size=0, token_est=0))
        gm.build_hierarchy("Test")
        gm.graph.nodes["src/empty.py"]["summary"] = "Empty module"
        renderer = MapRenderer(gm)
        tools = CuratorTools(renderer)
        output = tools.zoom_to_module("src/empty.py")
        assert "# src/empty.py" in output
        assert "Empty module" in output


class TestZoomToSymbol:
    """Tests for zoom_to_symbol tool (Level 3)."""

    def test_returns_symbol_markdown_for_valid_inputs(
        self, tools: CuratorTools
    ) -> None:
        """Returns Markdown for valid file_path and symbol_name."""
        output = tools.zoom_to_symbol("src/auth/login.py", "authenticate")
        assert "# src/auth/login.py::authenticate" in output
        assert "Authenticates user credentials" in output

    def test_raises_value_error_for_nonexistent_symbol(
        self, tools: CuratorTools
    ) -> None:
        """ValueError raised for symbol not in graph."""
        with pytest.raises(ValueError, match="nicht gefunden"):
            tools.zoom_to_symbol("src/auth/login.py", "nonexistent_func")

    def test_handles_function_symbols(
        self, tools: CuratorTools
    ) -> None:
        """Function signature is rendered correctly."""
        output = tools.zoom_to_symbol("src/auth/login.py", "authenticate")
        assert "def authenticate(" in output

    def test_handles_class_symbols(
        self, tools: CuratorTools
    ) -> None:
        """Class signature is rendered correctly."""
        output = tools.zoom_to_symbol("src/auth/login.py", "LoginValidator")
        assert "class LoginValidator:" in output


class TestShowCode:
    """Tests for show_code tool (Level 4)."""

    def test_returns_code_markdown_for_valid_inputs(
        self, tmp_path: Path
    ) -> None:
        """Returns Markdown with source code and line numbers."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "example.py").write_text(
            "def hello():\n    return 'world'\n\ndef other():\n    pass\n"
        )

        gm = GraphManager()
        gm.add_file(
            FileEntry(Path("src/example.py"), size=100, token_est=25)
        )
        gm.add_node("src/example.py", CodeNode("function", "hello", 1, 2))
        gm.build_hierarchy("Test")

        renderer = MapRenderer(gm, root_path=tmp_path)
        tools = CuratorTools(renderer)
        output = tools.show_code("src/example.py", "hello")
        assert "def hello():" in output
        assert "return 'world'" in output
        assert "Zeilen 1-2" in output

    def test_raises_value_error_when_root_path_not_set(self) -> None:
        """ValueError raised when MapRenderer has no root_path."""
        gm = GraphManager()
        gm.add_file(
            FileEntry(Path("src/example.py"), size=100, token_est=25)
        )
        gm.add_node("src/example.py", CodeNode("function", "func", 1, 5))
        gm.build_hierarchy("Test")

        renderer = MapRenderer(gm)
        tools = CuratorTools(renderer)
        with pytest.raises(ValueError, match="root_path"):
            tools.show_code("src/example.py", "func")

    def test_raises_value_error_for_nonexistent_file(
        self, tmp_path: Path
    ) -> None:
        """ValueError raised when source file does not exist."""
        gm = GraphManager()
        gm.add_file(
            FileEntry(Path("src/missing.py"), size=100, token_est=25)
        )
        gm.add_node("src/missing.py", CodeNode("function", "func", 1, 5))
        gm.build_hierarchy("Test")

        renderer = MapRenderer(gm, root_path=tmp_path)
        tools = CuratorTools(renderer)
        with pytest.raises(ValueError, match="File not found"):
            tools.show_code("src/missing.py", "func")

    def test_raises_value_error_for_invalid_line_range(
        self, tmp_path: Path
    ) -> None:
        """ValueError raised for inverted line range."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "example.py").write_text("line1\nline2\n")

        gm = GraphManager()
        gm.add_file(
            FileEntry(Path("src/example.py"), size=100, token_est=25)
        )
        gm.add_node("src/example.py", CodeNode("function", "func", 10, 3))
        gm.build_hierarchy("Test")

        renderer = MapRenderer(gm, root_path=tmp_path)
        tools = CuratorTools(renderer)
        with pytest.raises(ValueError, match="Invalid line range"):
            tools.show_code("src/example.py", "func")


class TestDocstrings:
    """Tests for LLM-optimized documentation."""

    def test_all_methods_have_docstrings(self) -> None:
        """All 5 tool methods have docstrings."""
        methods = [
            CuratorTools.get_project_overview,
            CuratorTools.zoom_to_package,
            CuratorTools.zoom_to_module,
            CuratorTools.zoom_to_symbol,
            CuratorTools.show_code,
        ]
        for method in methods:
            assert method.__doc__ is not None, (
                f"{method.__name__} has no docstring"
            )

    def test_docstrings_contain_usage_guidance(self) -> None:
        """Docstrings contain 'Nutze dies' or 'Zeigt' guidance."""
        methods = [
            CuratorTools.get_project_overview,
            CuratorTools.zoom_to_package,
            CuratorTools.zoom_to_module,
            CuratorTools.zoom_to_symbol,
            CuratorTools.show_code,
        ]
        for method in methods:
            doc = method.__doc__ or ""
            assert "Nutze dies" in doc or "Zeigt" in doc, (
                f"{method.__name__} docstring lacks usage guidance"
            )

    def test_docstrings_contain_args_section(self) -> None:
        """Methods with arguments have Args section."""
        methods_with_args = [
            CuratorTools.zoom_to_package,
            CuratorTools.zoom_to_module,
            CuratorTools.zoom_to_symbol,
            CuratorTools.show_code,
        ]
        for method in methods_with_args:
            doc = method.__doc__ or ""
            assert "Args:" in doc, (
                f"{method.__name__} docstring lacks Args section"
            )

    def test_docstrings_contain_examples(self) -> None:
        """Docstrings contain example paths like 'src/auth'."""
        methods_with_args = [
            CuratorTools.zoom_to_package,
            CuratorTools.zoom_to_module,
            CuratorTools.zoom_to_symbol,
            CuratorTools.show_code,
        ]
        for method in methods_with_args:
            doc = method.__doc__ or ""
            assert "src/" in doc, (
                f"{method.__name__} docstring lacks path examples"
            )


class TestIntegration:
    """Integration tests with real graph data."""

    def test_full_pipeline_with_all_tools(
        self,
        simple_graph_with_hierarchy: GraphManager,
        tmp_path: Path,
    ) -> None:
        """All 5 tools work correctly with real graph data."""
        # Create a real source file for Level 4
        auth_dir = tmp_path / "src" / "auth"
        auth_dir.mkdir(parents=True)
        (auth_dir / "login.py").write_text(
            "def authenticate(user, password):\n"
            "    # Verify credentials\n"
            "    return True\n"
        )

        renderer = MapRenderer(
            simple_graph_with_hierarchy, root_path=tmp_path
        )
        tools = CuratorTools(renderer)

        # Level 0: Project overview
        overview = tools.get_project_overview()
        assert "# TestProject" in overview

        # Level 1: Package zoom
        package = tools.zoom_to_package("src/auth")
        assert "# src/auth/" in package
        assert "login.py" in package

        # Level 2: Module zoom
        module = tools.zoom_to_module("src/auth/login.py")
        assert "# src/auth/login.py" in module
        assert "authenticate" in module

        # Level 3: Symbol zoom
        symbol = tools.zoom_to_symbol("src/auth/login.py", "authenticate")
        assert "# src/auth/login.py::authenticate" in symbol

        # Level 4: Code display
        code = tools.show_code("src/auth/login.py", "authenticate")
        assert "def authenticate" in code
        assert "Zeilen" in code
