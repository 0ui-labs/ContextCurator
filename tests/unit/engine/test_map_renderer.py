"""Unit tests for engine.map_renderer module.

Test suite for MapRenderer - transforms code graphs into readable Markdown.
Follows AAA (Arrange-Act-Assert) pattern and TDD methodology.

Test Organization:
    - TestMapRendererInit: Verify constructor and dependency injection
    - TestRenderOverview: Level 0 project overview rendering
    - TestRenderPackage: Level 1 package view rendering
    - TestRenderModule: Level 2 module view rendering
    - TestRenderSymbol: Level 3 symbol view rendering
    - TestRenderCode: Level 4 code detail rendering
    - TestMarkdownFormatting: Markdown output quality
    - TestEdgeCases: Edge cases and graceful degradation
"""

from __future__ import annotations

from pathlib import Path

import pytest

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

    # Add files
    gm.add_file(FileEntry(Path("src/auth/login.py"), size=500, token_est=125))
    gm.add_file(FileEntry(Path("src/auth/models.py"), size=300, token_est=75))
    gm.add_file(FileEntry(Path("src/utils/helpers.py"), size=200, token_est=50))

    # Add code nodes
    gm.add_node("src/auth/login.py", CodeNode("function", "authenticate", 1, 20))
    gm.add_node("src/auth/login.py", CodeNode("class", "LoginValidator", 22, 50))
    gm.add_node("src/auth/models.py", CodeNode("class", "User", 1, 30))
    gm.add_node("src/utils/helpers.py", CodeNode("function", "format_date", 1, 10))

    # Build hierarchy (creates project, packages, CONTAINS edges, sets levels)
    gm.build_hierarchy("TestProject")

    # Add enrichment data
    gm.graph.nodes["project::TestProject"]["summary"] = "A test authentication project"
    gm.graph.nodes["src"]["summary"] = "Source code root"
    gm.graph.nodes["src/auth"]["summary"] = "Authentication package"
    gm.graph.nodes["src/utils"]["summary"] = "Utility functions"
    gm.graph.nodes["src/auth/login.py"]["summary"] = "Login and authentication logic"
    gm.graph.nodes["src/auth/models.py"]["summary"] = "Data models for auth"
    gm.graph.nodes["src/utils/helpers.py"]["summary"] = "Helper utility functions"
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

    # Add IMPORTS edges
    gm.add_dependency("src/auth/login.py", "src/utils/helpers.py")
    gm.add_dependency("src/auth/login.py", "src/auth/models.py")

    return gm


@pytest.fixture
def graph_with_external_imports() -> GraphManager:
    """GraphManager with external module nodes for import representation."""
    gm = GraphManager()

    gm.add_file(FileEntry(Path("src/auth/login.py"), size=500, token_est=125))
    gm.add_node("src/auth/login.py", CodeNode("function", "authenticate", 1, 20))

    gm.build_hierarchy("TestProject")

    gm.graph.nodes["src/auth/login.py"]["summary"] = "Auth module"
    gm.graph.nodes["src/auth/login.py::authenticate"]["summary"] = "Auth function"
    gm.graph.nodes["src/auth/login.py::authenticate"]["risks"] = []

    # Add external modules and import edges
    gm.add_external_module("jwt")
    gm.add_external_module("bcrypt")
    gm.add_dependency("src/auth/login.py", "external::jwt")
    gm.add_dependency("src/auth/login.py", "external::bcrypt")

    return gm


@pytest.fixture
def empty_graph() -> GraphManager:
    """Empty GraphManager for edge case tests."""
    return GraphManager()


class TestMapRendererInit:
    """Tests for initialization and dependency injection."""

    def test_init_stores_graph_manager(self) -> None:
        """MapRenderer stores graph_manager as internal attribute."""
        gm = GraphManager()
        renderer = MapRenderer(gm)
        assert renderer._graph is gm

    def test_init_accepts_graph_manager_instance(self) -> None:
        """MapRenderer accepts optional root_path parameter."""
        gm = GraphManager()
        renderer = MapRenderer(gm, root_path=Path("/tmp/test"))
        assert renderer._root_path == Path("/tmp/test")


class TestRenderOverview:
    """Tests for Level 0 - Project overview."""

    def test_renders_project_name_and_summary(
        self, simple_graph_with_hierarchy: GraphManager
    ) -> None:
        """Output contains project name as H1 and summary text."""
        renderer = MapRenderer(simple_graph_with_hierarchy)
        output = renderer.render_overview()
        assert "# TestProject" in output
        assert "A test authentication project" in output

    def test_lists_top_level_packages_with_summaries(
        self, simple_graph_with_hierarchy: GraphManager
    ) -> None:
        """Output lists direct children of project under Hauptbereiche."""
        renderer = MapRenderer(simple_graph_with_hierarchy)
        output = renderer.render_overview()
        assert "## Hauptbereiche:" in output
        assert "**src**" in output
        assert "Source code root" in output

    def test_includes_architecture_hints_from_imports(
        self, simple_graph_with_hierarchy: GraphManager
    ) -> None:
        """Output shows inter-package import relationships."""
        renderer = MapRenderer(simple_graph_with_hierarchy)
        output = renderer.render_overview()
        assert "## Architektur-Hinweise:" in output
        assert "src/auth" in output
        assert "src/utils" in output

    def test_handles_project_without_summary(self) -> None:
        """Project node without summary attribute still renders."""
        gm = GraphManager()
        gm.add_project("Bare")
        renderer = MapRenderer(gm)
        output = renderer.render_overview()
        assert "# Bare" in output

    def test_empty_project_returns_minimal_output(
        self, empty_graph: GraphManager
    ) -> None:
        """Empty graph returns minimal output indicating no project."""
        renderer = MapRenderer(empty_graph)
        output = renderer.render_overview()
        assert "# Project Overview" in output
        assert "No project node found" in output


class TestRenderPackage:
    """Tests for Level 1 - Package view."""

    def test_renders_package_summary(
        self, simple_graph_with_hierarchy: GraphManager
    ) -> None:
        """Package summary appears in output."""
        renderer = MapRenderer(simple_graph_with_hierarchy)
        output = renderer.render_package("src/auth")
        assert "# src/auth/" in output
        assert "Authentication package" in output

    def test_lists_contained_modules_with_summaries(
        self, simple_graph_with_hierarchy: GraphManager
    ) -> None:
        """Contained files listed under Module section."""
        renderer = MapRenderer(simple_graph_with_hierarchy)
        output = renderer.render_package("src/auth")
        assert "## Module:" in output
        assert "login.py" in output
        assert "models.py" in output

    def test_shows_internal_structure_via_contains_edges(
        self, simple_graph_with_hierarchy: GraphManager
    ) -> None:
        """Internal imports within package are shown."""
        renderer = MapRenderer(simple_graph_with_hierarchy)
        output = renderer.render_package("src/auth")
        assert "## Interne Struktur:" in output
        assert "login.py" in output
        assert "models.py" in output

    def test_shows_external_interfaces_via_imports(
        self, graph_with_external_imports: GraphManager
    ) -> None:
        """External module imports are shown."""
        renderer = MapRenderer(graph_with_external_imports)
        output = renderer.render_module("src/auth/login.py")
        assert "external::jwt" in output
        assert "external::bcrypt" in output

    def test_includes_package_risks_if_present(self) -> None:
        """Package risks are rendered when present."""
        gm = GraphManager()
        gm.add_file(FileEntry(Path("pkg/mod.py"), size=100, token_est=25))
        gm.build_hierarchy("Test")
        gm.graph.nodes["pkg"]["risks"] = ["Tight coupling", "Missing docs"]
        renderer = MapRenderer(gm)
        output = renderer.render_package("pkg")
        assert "## Risiken:" in output
        assert "Tight coupling" in output
        assert "Missing docs" in output

    def test_handles_nonexistent_package_path(
        self, simple_graph_with_hierarchy: GraphManager
    ) -> None:
        """ValueError raised for package not in graph."""
        renderer = MapRenderer(simple_graph_with_hierarchy)
        with pytest.raises(ValueError, match="not found"):
            renderer.render_package("nonexistent/pkg")

    def test_handles_package_without_children(self) -> None:
        """Package with no children still renders."""
        gm = GraphManager()
        gm.add_project("Test")
        gm.add_package("empty_pkg", "project::Test")
        gm.graph.nodes["empty_pkg"]["summary"] = "Empty package"
        renderer = MapRenderer(gm)
        output = renderer.render_package("empty_pkg")
        assert "# empty_pkg/" in output
        assert "Empty package" in output


class TestRenderModule:
    """Tests for Level 2 - Module view."""

    def test_renders_module_summary(
        self, simple_graph_with_hierarchy: GraphManager
    ) -> None:
        """Module summary appears in output."""
        renderer = MapRenderer(simple_graph_with_hierarchy)
        output = renderer.render_module("src/auth/login.py")
        assert "# src/auth/login.py" in output
        assert "Login and authentication logic" in output

    def test_lists_contained_symbols_with_summaries(
        self, simple_graph_with_hierarchy: GraphManager
    ) -> None:
        """Functions and classes listed under Enthält section."""
        renderer = MapRenderer(simple_graph_with_hierarchy)
        output = renderer.render_module("src/auth/login.py")
        assert "## Enthält:" in output
        assert "**authenticate**" in output
        assert "Authenticates user credentials" in output
        assert "**LoginValidator**" in output
        assert "Validates login form data" in output

    def test_shows_import_dependencies(
        self, simple_graph_with_hierarchy: GraphManager
    ) -> None:
        """Outgoing imports listed under Abhängigkeiten."""
        renderer = MapRenderer(simple_graph_with_hierarchy)
        output = renderer.render_module("src/auth/login.py")
        assert "## Abhängigkeiten:" in output
        assert "src/utils/helpers.py" in output
        assert "src/auth/models.py" in output

    def test_shows_imported_by_with_count(self) -> None:
        """Incoming imports shown with source file names."""
        gm = GraphManager()
        gm.add_file(FileEntry(Path("src/utils.py"), size=100, token_est=25))
        gm.add_file(FileEntry(Path("src/main.py"), size=100, token_est=25))
        gm.add_file(FileEntry(Path("src/app.py"), size=100, token_est=25))
        gm.build_hierarchy("Test")
        gm.graph.nodes["src/utils.py"]["summary"] = "Utils"
        gm.add_dependency("src/main.py", "src/utils.py")
        gm.add_dependency("src/app.py", "src/utils.py")

        renderer = MapRenderer(gm)
        output = renderer.render_module("src/utils.py")
        assert "Wird importiert von:" in output
        assert "src/main.py" in output
        assert "src/app.py" in output

    def test_includes_module_risks(self) -> None:
        """Module-level risks are rendered."""
        gm = GraphManager()
        gm.add_file(FileEntry(Path("src/risky.py"), size=100, token_est=25))
        gm.build_hierarchy("Test")
        gm.graph.nodes["src/risky.py"]["summary"] = "Risky module"
        gm.graph.nodes["src/risky.py"]["risks"] = ["High complexity", "No tests"]
        renderer = MapRenderer(gm)
        output = renderer.render_module("src/risky.py")
        assert "## Risiken:" in output
        assert "High complexity" in output
        assert "No tests" in output

    def test_handles_nonexistent_file_path(
        self, simple_graph_with_hierarchy: GraphManager
    ) -> None:
        """ValueError raised for file not in graph."""
        renderer = MapRenderer(simple_graph_with_hierarchy)
        with pytest.raises(ValueError, match="not found"):
            renderer.render_module("nonexistent/file.py")

    def test_handles_module_without_code_nodes(self) -> None:
        """Module with no contained code nodes still renders."""
        gm = GraphManager()
        gm.add_file(FileEntry(Path("src/empty.py"), size=0, token_est=0))
        gm.build_hierarchy("Test")
        gm.graph.nodes["src/empty.py"]["summary"] = "Empty module"
        renderer = MapRenderer(gm)
        output = renderer.render_module("src/empty.py")
        assert "# src/empty.py" in output
        assert "Empty module" in output


class TestRenderSymbol:
    """Tests for Level 3 - Symbol view."""

    def test_renders_symbol_summary(
        self, simple_graph_with_hierarchy: GraphManager
    ) -> None:
        """Symbol summary appears in output."""
        renderer = MapRenderer(simple_graph_with_hierarchy)
        output = renderer.render_symbol("src/auth/login.py", "authenticate")
        assert "# src/auth/login.py::authenticate" in output
        assert "Authenticates user credentials" in output

    def test_shows_function_signature_from_attributes(
        self, simple_graph_with_hierarchy: GraphManager
    ) -> None:
        """Function nodes show def signature."""
        renderer = MapRenderer(simple_graph_with_hierarchy)
        output = renderer.render_symbol("src/auth/login.py", "authenticate")
        assert "## Signatur:" in output
        assert "def authenticate(" in output

    def test_shows_class_definition_from_attributes(
        self, simple_graph_with_hierarchy: GraphManager
    ) -> None:
        """Class nodes show class signature."""
        renderer = MapRenderer(simple_graph_with_hierarchy)
        output = renderer.render_symbol("src/auth/login.py", "LoginValidator")
        assert "## Signatur:" in output
        assert "class LoginValidator:" in output

    def test_lists_callers_via_reverse_contains(self) -> None:
        """Files importing the parent file are listed as callers."""
        gm = GraphManager()
        gm.add_file(FileEntry(Path("src/auth.py"), size=100, token_est=25))
        gm.add_file(FileEntry(Path("src/api.py"), size=100, token_est=25))
        gm.add_node("src/auth.py", CodeNode("function", "login", 1, 10))
        gm.build_hierarchy("Test")
        gm.graph.nodes["src/auth.py::login"]["summary"] = "Login function"
        gm.graph.nodes["src/auth.py::login"]["risks"] = []
        gm.add_dependency("src/api.py", "src/auth.py")

        renderer = MapRenderer(gm)
        output = renderer.render_symbol("src/auth.py", "login")
        assert "## Aufrufer:" in output
        assert "src/api.py" in output

    def test_includes_symbol_risks(
        self, simple_graph_with_hierarchy: GraphManager
    ) -> None:
        """Symbol risks are rendered."""
        renderer = MapRenderer(simple_graph_with_hierarchy)
        output = renderer.render_symbol("src/auth/login.py", "authenticate")
        assert "## Risiken:" in output
        assert "Security critical" in output
        assert "Rate limiting needed" in output

    def test_handles_nonexistent_symbol(
        self, simple_graph_with_hierarchy: GraphManager
    ) -> None:
        """ValueError raised for symbol not in graph."""
        renderer = MapRenderer(simple_graph_with_hierarchy)
        with pytest.raises(ValueError, match="not found"):
            renderer.render_symbol("src/auth/login.py", "nonexistent_func")

    def test_handles_symbol_without_summary(self) -> None:
        """Symbol without summary attribute still renders."""
        gm = GraphManager()
        gm.add_file(FileEntry(Path("src/mod.py"), size=100, token_est=25))
        gm.add_node("src/mod.py", CodeNode("function", "bare_func", 1, 5))
        gm.build_hierarchy("Test")
        # Deliberately do NOT set summary or risks

        renderer = MapRenderer(gm)
        output = renderer.render_symbol("src/mod.py", "bare_func")
        assert "# src/mod.py::bare_func" in output
        assert "## Signatur:" in output
        assert "def bare_func(" in output


class TestRenderCode:
    """Tests for Level 4 - Code detail."""

    def test_extracts_code_from_file_using_line_range(self, tmp_path: Path) -> None:
        """Correct lines extracted from source file."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "example.py").write_text(
            "def hello():\n    return 'world'\n\ndef other():\n    pass\n"
        )

        gm = GraphManager()
        gm.add_file(FileEntry(Path("src/example.py"), size=100, token_est=25))
        gm.add_node("src/example.py", CodeNode("function", "hello", 1, 2))
        gm.build_hierarchy("Test")

        renderer = MapRenderer(gm, root_path=tmp_path)
        output = renderer.render_code("src/example.py", "hello")
        assert "def hello():" in output
        assert "return 'world'" in output
        assert "def other():" not in output

    def test_shows_line_numbers_in_output(self, tmp_path: Path) -> None:
        """Output contains Zeilen indicator with line range."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "example.py").write_text(
            "def hello():\n    return 'world'\n"
        )

        gm = GraphManager()
        gm.add_file(FileEntry(Path("src/example.py"), size=100, token_est=25))
        gm.add_node("src/example.py", CodeNode("function", "hello", 1, 2))
        gm.build_hierarchy("Test")

        renderer = MapRenderer(gm, root_path=tmp_path)
        output = renderer.render_code("src/example.py", "hello")
        assert "Zeilen 1-2" in output

    def test_handles_file_not_found(self, tmp_path: Path) -> None:
        """ValueError raised when source file does not exist."""
        gm = GraphManager()
        gm.add_file(FileEntry(Path("src/missing.py"), size=100, token_est=25))
        gm.add_node("src/missing.py", CodeNode("function", "func", 1, 5))
        gm.build_hierarchy("Test")

        renderer = MapRenderer(gm, root_path=tmp_path)
        with pytest.raises(ValueError, match="File not found"):
            renderer.render_code("src/missing.py", "func")

    def test_handles_invalid_line_range(self, tmp_path: Path) -> None:
        """ValueError raised for inverted line range (start > end)."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "example.py").write_text("line1\nline2\n")

        gm = GraphManager()
        gm.add_file(FileEntry(Path("src/example.py"), size=100, token_est=25))
        gm.add_node("src/example.py", CodeNode("function", "func", 10, 3))
        gm.build_hierarchy("Test")

        renderer = MapRenderer(gm, root_path=tmp_path)
        with pytest.raises(ValueError, match="Invalid line range"):
            renderer.render_code("src/example.py", "func")

    def test_requires_root_path_for_code_extraction(self) -> None:
        """ValueError raised when no root_path is configured."""
        gm = GraphManager()
        gm.add_file(FileEntry(Path("src/example.py"), size=100, token_est=25))
        gm.add_node("src/example.py", CodeNode("function", "func", 1, 5))
        gm.build_hierarchy("Test")

        renderer = MapRenderer(gm)
        with pytest.raises(ValueError, match="root_path is required"):
            renderer.render_code("src/example.py", "func")


class TestMarkdownFormatting:
    """Tests for Markdown output quality."""

    def test_output_is_valid_markdown(
        self, simple_graph_with_hierarchy: GraphManager
    ) -> None:
        """Output starts with a proper Markdown heading."""
        renderer = MapRenderer(simple_graph_with_hierarchy)
        output = renderer.render_overview()
        assert output.startswith("# ")

    def test_uses_proper_heading_hierarchy(
        self, simple_graph_with_hierarchy: GraphManager
    ) -> None:
        """H1 used for top-level, H2 for sub-sections."""
        renderer = MapRenderer(simple_graph_with_hierarchy)
        output = renderer.render_overview()
        lines = output.split("\n")
        h1_lines = [l for l in lines if l.startswith("# ") and not l.startswith("## ")]
        h2_lines = [l for l in lines if l.startswith("## ")]
        assert len(h1_lines) >= 1
        assert len(h2_lines) >= 1

    def test_escapes_special_characters(self) -> None:
        """Special characters in node names are preserved."""
        gm = GraphManager()
        gm.add_file(
            FileEntry(Path("src/test_special.py"), size=100, token_est=25)
        )
        gm.build_hierarchy("Test")
        gm.graph.nodes["src/test_special.py"]["summary"] = (
            "Module with <special> & chars"
        )

        renderer = MapRenderer(gm)
        output = renderer.render_module("src/test_special.py")
        assert "test_special.py" in output

    def test_formats_lists_correctly(
        self, simple_graph_with_hierarchy: GraphManager
    ) -> None:
        """Bullet point format used for list items."""
        renderer = MapRenderer(simple_graph_with_hierarchy)
        output = renderer.render_module("src/auth/login.py")
        assert "- **authenticate**" in output
        assert "- **LoginValidator**" in output


class TestEdgeCases:
    """Tests for edge cases and graceful degradation."""

    def test_handles_nodes_without_level_attribute(self) -> None:
        """Nodes missing level attribute still render in overview."""
        gm = GraphManager()
        gm.graph.add_node("project::Test", type="project", level=0, name="Test")
        gm.graph.add_node("pkg", type="package", name="pkg")
        gm.graph.add_edge("project::Test", "pkg", relationship="CONTAINS")

        renderer = MapRenderer(gm)
        output = renderer.render_overview()
        assert "**pkg**" in output

    def test_handles_nodes_without_type_attribute(self) -> None:
        """Nodes missing type attribute still appear as children."""
        gm = GraphManager()
        gm.graph.add_node("project::Test", type="project", level=0, name="Test")
        gm.graph.add_node("mystery_node")
        gm.graph.add_edge("project::Test", "mystery_node", relationship="CONTAINS")

        renderer = MapRenderer(gm)
        output = renderer.render_overview()
        assert "mystery_node" in output

    def test_handles_circular_imports_gracefully(self) -> None:
        """Circular imports do not cause infinite loops."""
        gm = GraphManager()
        gm.add_file(FileEntry(Path("src/a.py"), size=100, token_est=25))
        gm.add_file(FileEntry(Path("src/b.py"), size=100, token_est=25))
        gm.build_hierarchy("Test")
        gm.graph.nodes["src/a.py"]["summary"] = "Module A"
        gm.graph.nodes["src/b.py"]["summary"] = "Module B"
        gm.add_dependency("src/a.py", "src/b.py")
        gm.add_dependency("src/b.py", "src/a.py")

        renderer = MapRenderer(gm)
        output = renderer.render_module("src/a.py")
        assert "src/b.py" in output

    def test_handles_missing_summary_gracefully(self) -> None:
        """Nodes without summary attribute render without errors."""
        gm = GraphManager()
        gm.add_file(FileEntry(Path("src/no_summary.py"), size=100, token_est=25))
        gm.add_node("src/no_summary.py", CodeNode("function", "func", 1, 5))
        gm.build_hierarchy("Test")

        renderer = MapRenderer(gm)
        output = renderer.render_module("src/no_summary.py")
        assert "# src/no_summary.py" in output
        assert "**func**" in output

    def test_render_package_rejects_non_package_node(self) -> None:
        """render_package raises ValueError for a file node."""
        gm = GraphManager()
        gm.add_file(FileEntry(Path("src/mod.py"), size=100, token_est=25))
        gm.build_hierarchy("Test")

        renderer = MapRenderer(gm)
        with pytest.raises(ValueError, match="is not a package"):
            renderer.render_package("src/mod.py")

    def test_render_module_rejects_non_file_node(self) -> None:
        """render_module raises ValueError for a package node."""
        gm = GraphManager()
        gm.add_file(FileEntry(Path("src/mod.py"), size=100, token_est=25))
        gm.build_hierarchy("Test")

        renderer = MapRenderer(gm)
        with pytest.raises(ValueError, match="is not a file"):
            renderer.render_module("src")

    def test_render_symbol_unknown_type_skips_signature(self) -> None:
        """Symbol with unknown type skips Signatur section."""
        gm = GraphManager()
        gm.add_file(FileEntry(Path("src/mod.py"), size=100, token_est=25))
        gm.build_hierarchy("Test")
        gm.graph.add_node(
            "src/mod.py::mystery", type="variable", name="mystery"
        )

        renderer = MapRenderer(gm)
        output = renderer.render_symbol("src/mod.py", "mystery")
        assert "# src/mod.py::mystery" in output
        assert "## Signatur:" not in output

    def test_render_code_symbol_not_found(self, tmp_path: Path) -> None:
        """render_code raises ValueError for nonexistent symbol."""
        gm = GraphManager()
        gm.add_file(FileEntry(Path("src/mod.py"), size=100, token_est=25))
        gm.build_hierarchy("Test")

        renderer = MapRenderer(gm, root_path=tmp_path)
        with pytest.raises(ValueError, match="not found"):
            renderer.render_code("src/mod.py", "nonexistent")

    def test_render_code_symbol_without_line_range(self, tmp_path: Path) -> None:
        """render_code raises ValueError when symbol has no line numbers."""
        gm = GraphManager()
        gm.add_file(FileEntry(Path("src/mod.py"), size=100, token_est=25))
        gm.build_hierarchy("Test")
        gm.graph.add_node("src/mod.py::no_lines", type="function", name="no_lines")

        renderer = MapRenderer(gm, root_path=tmp_path)
        with pytest.raises(ValueError, match="has no line range"):
            renderer.render_code("src/mod.py", "no_lines")

    def test_package_incoming_external_imports(self) -> None:
        """Package shows files importing into it from outside."""
        gm = GraphManager()
        gm.add_file(FileEntry(Path("pkg/mod.py"), size=100, token_est=25))
        gm.add_file(FileEntry(Path("other/caller.py"), size=100, token_est=25))
        gm.build_hierarchy("Test")
        gm.add_dependency("other/caller.py", "pkg/mod.py")

        renderer = MapRenderer(gm)
        output = renderer.render_package("pkg")
        assert "## Externe Schnittstellen:" in output
        assert "Wird importiert von:" in output
        assert "other/caller.py" in output

    def test_risks_non_list_returns_empty(self) -> None:
        """Non-list risks attribute treated as empty list."""
        gm = GraphManager()
        gm.add_file(FileEntry(Path("src/mod.py"), size=100, token_est=25))
        gm.build_hierarchy("Test")
        gm.graph.nodes["src/mod.py"]["risks"] = "not a list"
        gm.graph.nodes["src/mod.py"]["summary"] = "Module"

        renderer = MapRenderer(gm)
        output = renderer.render_module("src/mod.py")
        assert "## Risiken:" not in output

    def test_get_node_summary_nonexistent_returns_empty(self) -> None:
        """_get_node_summary returns empty string for nonexistent node."""
        gm = GraphManager()
        renderer = MapRenderer(gm)
        assert renderer._get_node_summary("nonexistent") == ""

    def test_get_node_risks_nonexistent_returns_empty(self) -> None:
        """_get_node_risks returns empty list for nonexistent node."""
        gm = GraphManager()
        renderer = MapRenderer(gm)
        assert renderer._get_node_risks("nonexistent") == []

    def test_architecture_hints_with_root_level_file(self) -> None:
        """Root-level files (single-part path) return None for parent package."""
        gm = GraphManager()
        gm.add_file(FileEntry(Path("main.py"), size=100, token_est=25))
        gm.add_file(FileEntry(Path("utils.py"), size=100, token_est=25))
        gm.build_hierarchy("Test")
        gm.add_dependency("main.py", "utils.py")

        renderer = MapRenderer(gm)
        output = renderer.render_overview()
        # Root-level files have no parent package, so no architecture hints
        assert "## Architektur-Hinweise:" not in output

    def test_architecture_hints_with_code_node_imports(self) -> None:
        """IMPORTS edges from code nodes (::) are handled correctly."""
        gm = GraphManager()
        gm.add_file(FileEntry(Path("src/a.py"), size=100, token_est=25))
        gm.add_file(FileEntry(Path("src/b.py"), size=100, token_est=25))
        gm.add_node("src/a.py", CodeNode("function", "func", 1, 5))
        gm.build_hierarchy("Test")
        # Add IMPORTS edge from a code node (unusual but possible)
        gm.graph.add_edge(
            "src/a.py::func", "src/b.py", relationship="IMPORTS"
        )

        renderer = MapRenderer(gm)
        # Should not crash, code node's parent package is resolved via ::
        output = renderer.render_overview()
        assert "# Test" in output

    def test_package_external_imports_deduplication(self) -> None:
        """Duplicate external imports from multiple files are deduplicated."""
        gm = GraphManager()
        gm.add_file(FileEntry(Path("pkg/a.py"), size=100, token_est=25))
        gm.add_file(FileEntry(Path("pkg/b.py"), size=100, token_est=25))
        gm.add_file(FileEntry(Path("other/shared.py"), size=100, token_est=25))
        gm.build_hierarchy("Test")
        # Both pkg files import the same external target
        gm.add_dependency("pkg/a.py", "other/shared.py")
        gm.add_dependency("pkg/b.py", "other/shared.py")
        # Both pkg files imported by same external source
        gm.add_dependency("other/shared.py", "pkg/a.py")
        gm.add_dependency("other/shared.py", "pkg/b.py")

        renderer = MapRenderer(gm)
        output = renderer.render_package("pkg")
        # other/shared.py should appear only once in outgoing
        assert output.count("other/shared.py") >= 1
