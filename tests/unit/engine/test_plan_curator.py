"""Unit tests for engine.plan_curator module.

Test suite for PlanCurator - orchestrates plan analysis with code graph context.
Follows AAA (Arrange-Act-Assert) pattern and TDD methodology.

Test Organization:
    - TestPlanCuratorInit: Verify constructor with dependency injection
    - TestCurateSimplePlan: Simple plan - direct final answer
    - TestCurateWithRisks: Plan with risks - LLM uses tools then final answer
    - TestCurateEndToEnd: Realistic plans with tool navigation
    - TestCurateErrorHandling: Error propagation from CuratorAgent
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import openai
import pytest

from codemap.engine.builder import MapBuilder
from codemap.engine.curator_agent import CuratorAgent
from codemap.engine.curator_tools import CuratorTools
from codemap.engine.map_renderer import MapRenderer
from codemap.engine.plan_curator import PlanCurator
from codemap.graph import GraphManager
from codemap.mapper.models import CodeNode
from codemap.scout.models import FileEntry


def _tool_call(
    tool: str, args: dict[str, Any] | None = None
) -> str:
    """Build a tool_call JSON response string."""
    return json.dumps(
        {"action": "tool_call", "tool": tool, "args": args or {}}
    )


def _final_answer(plan: str) -> str:
    """Build a final_answer JSON response string."""
    return json.dumps({"action": "final_answer", "plan": plan})


@pytest.fixture
def enriched_graph() -> GraphManager:
    """Graph with src/auth/legacy.py, src/auth/login.py, src/api/auth.py.

    legacy.py is imported by login.py and api/auth.py.
    All nodes have summary and risks attributes.

    Structure:
        project::TestProject
        └── src (package)
            ├── src/auth (package)
            │   ├── src/auth/legacy.py (file)
            │   │   └── old_authenticate (function)
            │   └── src/auth/login.py (file)
            │       └── authenticate (function)
            └── src/api (package)
                └── src/api/auth.py (file)
                    └── verify_token (function)

    Imports:
        src/auth/login.py -> src/auth/legacy.py
        src/api/auth.py -> src/auth/legacy.py
    """
    gm = GraphManager()

    gm.add_file(
        FileEntry(Path("src/auth/legacy.py"), size=400, token_est=100)
    )
    gm.add_file(
        FileEntry(Path("src/auth/login.py"), size=500, token_est=125)
    )
    gm.add_file(
        FileEntry(Path("src/api/auth.py"), size=300, token_est=75)
    )

    gm.add_node(
        "src/auth/legacy.py",
        CodeNode("function", "old_authenticate", 1, 25),
    )
    gm.add_node(
        "src/auth/login.py",
        CodeNode("function", "authenticate", 1, 20),
    )
    gm.add_node(
        "src/api/auth.py",
        CodeNode("function", "verify_token", 1, 15),
    )

    gm.build_hierarchy("TestProject")

    # Project-level enrichment
    gm.graph.nodes["project::TestProject"]["summary"] = (
        "Authentication service project"
    )

    # Package-level enrichment
    gm.graph.nodes["src"]["summary"] = "Source code root"
    gm.graph.nodes["src/auth"]["summary"] = "Authentication package"
    gm.graph.nodes["src/api"]["summary"] = "API endpoints package"

    # File-level enrichment
    gm.graph.nodes["src/auth/legacy.py"]["summary"] = (
        "Legacy authentication logic - deprecated"
    )
    gm.graph.nodes["src/auth/legacy.py"]["risks"] = [
        "Deprecated code",
        "Security vulnerabilities",
    ]
    gm.graph.nodes["src/auth/login.py"]["summary"] = (
        "Modern login and authentication"
    )
    gm.graph.nodes["src/auth/login.py"]["risks"] = []
    gm.graph.nodes["src/api/auth.py"]["summary"] = (
        "API authentication endpoints"
    )
    gm.graph.nodes["src/api/auth.py"]["risks"] = []

    # Symbol-level enrichment
    gm.graph.nodes["src/auth/legacy.py::old_authenticate"]["summary"] = (
        "Legacy authentication function"
    )
    gm.graph.nodes["src/auth/legacy.py::old_authenticate"]["risks"] = [
        "No password hashing",
    ]
    gm.graph.nodes["src/auth/login.py::authenticate"]["summary"] = (
        "Modern authentication with hashing"
    )
    gm.graph.nodes["src/auth/login.py::authenticate"]["risks"] = []
    gm.graph.nodes["src/api/auth.py::verify_token"]["summary"] = (
        "Verifies JWT tokens"
    )
    gm.graph.nodes["src/api/auth.py::verify_token"]["risks"] = []

    # Import dependencies: login.py and api/auth.py both import legacy.py
    gm.add_dependency("src/auth/login.py", "src/auth/legacy.py")
    gm.add_dependency("src/api/auth.py", "src/auth/legacy.py")

    return gm


@pytest.fixture
def real_enriched_graph(tmp_path: Path) -> GraphManager:
    """Graph built via MapBuilder from real Python source files.

    Creates a temporary project with the same structure as enriched_graph
    but using MapBuilder.build() for realistic node/edge construction.
    Tool calls (zoom_to_module, zoom_to_symbol, etc.) operate on real
    nodes and import edges discovered by MapBuilder.
    """
    # Create project directory structure
    auth_dir = tmp_path / "src" / "auth"
    api_dir = tmp_path / "src" / "api"
    auth_dir.mkdir(parents=True)
    api_dir.mkdir(parents=True)

    (auth_dir / "__init__.py").write_text("")
    (auth_dir / "legacy.py").write_text(
        "def old_authenticate(username, password):\n"
        '    """Legacy auth - deprecated."""\n'
        '    return username == "admin" and password == "admin"\n'
    )
    (auth_dir / "login.py").write_text(
        "import legacy\n\n\n"
        "def authenticate(username, password):\n"
        '    """Modern authentication."""\n'
        "    return legacy.old_authenticate(username, password)\n"
    )
    (api_dir / "__init__.py").write_text("")
    (api_dir / "auth.py").write_text(
        "import src.auth.legacy\n\n\n"
        "def verify_token(token):\n"
        '    """Verify JWT token."""\n'
        "    return token is not None\n"
    )

    # Build graph from real source files
    builder = MapBuilder()
    gm = builder.build(tmp_path)
    gm.build_hierarchy("TestProject")

    # Add enrichment (summaries and risks) - simulates GraphEnricher output
    gm.graph.nodes["project::TestProject"]["summary"] = (
        "Authentication service project"
    )
    gm.graph.nodes["src"]["summary"] = "Source code root"
    gm.graph.nodes["src/auth"]["summary"] = "Authentication package"
    gm.graph.nodes["src/api"]["summary"] = "API endpoints package"

    gm.graph.nodes["src/auth/legacy.py"]["summary"] = (
        "Legacy authentication logic - deprecated"
    )
    gm.graph.nodes["src/auth/legacy.py"]["risks"] = [
        "Deprecated code",
        "Security vulnerabilities",
    ]
    gm.graph.nodes["src/auth/login.py"]["summary"] = (
        "Modern login and authentication"
    )
    gm.graph.nodes["src/auth/login.py"]["risks"] = []
    gm.graph.nodes["src/api/auth.py"]["summary"] = (
        "API authentication endpoints"
    )
    gm.graph.nodes["src/api/auth.py"]["risks"] = []

    gm.graph.nodes["src/auth/legacy.py::old_authenticate"]["summary"] = (
        "Legacy authentication function"
    )
    gm.graph.nodes["src/auth/legacy.py::old_authenticate"]["risks"] = [
        "No password hashing",
    ]
    gm.graph.nodes["src/auth/login.py::authenticate"]["summary"] = (
        "Modern authentication with hashing"
    )
    gm.graph.nodes["src/auth/login.py::authenticate"]["risks"] = []
    gm.graph.nodes["src/api/auth.py::verify_token"]["summary"] = (
        "Verifies JWT tokens"
    )
    gm.graph.nodes["src/api/auth.py::verify_token"]["risks"] = []

    return gm


@pytest.fixture
def mock_llm_simple() -> AsyncMock:
    """LLM that returns a direct final answer."""
    mock = AsyncMock()
    mock.send.return_value = _final_answer(
        "# Plan\n1. Implement feature"
    )
    return mock


@pytest.fixture
def mock_llm_with_analysis() -> AsyncMock:
    """LLM that uses tools, then returns revised plan."""
    mock = AsyncMock()
    mock.send.side_effect = [
        _tool_call(
            "zoom_to_module",
            {"file_path": "src/auth/legacy.py"},
        ),
        _final_answer(
            "# Revised Plan\n"
            "1. Update imports in login.py and api/auth.py\n"
            "2. Then refactor legacy.py"
        ),
    ]
    return mock


class TestPlanCuratorInit:
    """Tests for initialization and dependency injection."""

    def test_init_stores_graph_manager(
        self, enriched_graph: GraphManager, mock_llm_simple: AsyncMock
    ) -> None:
        """PlanCurator stores GraphManager as _graph attribute."""
        curator = PlanCurator(enriched_graph, mock_llm_simple)
        assert curator._graph is enriched_graph

    def test_init_stores_llm_provider(
        self, enriched_graph: GraphManager, mock_llm_simple: AsyncMock
    ) -> None:
        """PlanCurator stores LLMProvider as _llm attribute."""
        curator = PlanCurator(enriched_graph, mock_llm_simple)
        assert curator._llm is mock_llm_simple

    def test_init_creates_map_renderer(
        self, enriched_graph: GraphManager, mock_llm_simple: AsyncMock
    ) -> None:
        """PlanCurator creates MapRenderer with GraphManager."""
        curator = PlanCurator(enriched_graph, mock_llm_simple)
        assert isinstance(curator._renderer, MapRenderer)
        assert curator._renderer._graph is enriched_graph

    def test_init_creates_curator_tools(
        self, enriched_graph: GraphManager, mock_llm_simple: AsyncMock
    ) -> None:
        """PlanCurator creates CuratorTools with MapRenderer."""
        curator = PlanCurator(enriched_graph, mock_llm_simple)
        assert isinstance(curator._tools, CuratorTools)
        assert curator._tools._renderer is curator._renderer

    def test_init_creates_curator_agent(
        self, enriched_graph: GraphManager, mock_llm_simple: AsyncMock
    ) -> None:
        """PlanCurator creates CuratorAgent with LLM and Tools."""
        curator = PlanCurator(enriched_graph, mock_llm_simple)
        assert isinstance(curator._agent, CuratorAgent)
        assert curator._agent._llm is mock_llm_simple
        assert curator._agent._tools is curator._tools

    def test_init_accepts_optional_root_path(
        self, enriched_graph: GraphManager, mock_llm_simple: AsyncMock
    ) -> None:
        """root_path is passed to MapRenderer."""
        root = Path("/tmp/project")
        curator = PlanCurator(
            enriched_graph, mock_llm_simple, root_path=root
        )
        assert curator._renderer._root_path == root


class TestCurateSimplePlan:
    """Tests for simple plan - direct final answer from LLM."""

    @pytest.mark.asyncio
    async def test_returns_curated_plan_string(
        self,
        enriched_graph: GraphManager,
        mock_llm_simple: AsyncMock,
    ) -> None:
        """curate() returns a string."""
        curator = PlanCurator(enriched_graph, mock_llm_simple)
        result = await curator.curate("# Simple Plan\n1. Do something")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_delegates_to_curator_agent(
        self,
        enriched_graph: GraphManager,
        mock_llm_simple: AsyncMock,
    ) -> None:
        """curate() calls CuratorAgent.analyze_plan()."""
        curator = PlanCurator(enriched_graph, mock_llm_simple)
        await curator.curate("# Test Plan")
        mock_llm_simple.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_plan_to_agent(
        self,
        enriched_graph: GraphManager,
        mock_llm_simple: AsyncMock,
    ) -> None:
        """The plan is passed through to the LLM."""
        curator = PlanCurator(enriched_graph, mock_llm_simple)
        await curator.curate("# My Specific Plan\n1. Step one")
        call_args = mock_llm_simple.send.call_args
        user_prompt = call_args[0][1]
        assert "# My Specific Plan" in user_prompt

    @pytest.mark.asyncio
    async def test_simple_plan_without_risks(
        self,
        enriched_graph: GraphManager,
        mock_llm_simple: AsyncMock,
    ) -> None:
        """LLM gives direct final_answer for simple plan."""
        curator = PlanCurator(enriched_graph, mock_llm_simple)
        result = await curator.curate("# Simple Plan\n1. Add logging")
        assert result == "# Plan\n1. Implement feature"
        assert mock_llm_simple.send.call_count == 1


class TestCurateWithRisks:
    """Tests for plans with risks - LLM navigates graph via tools."""

    @pytest.mark.asyncio
    async def test_plan_with_file_modification(
        self,
        enriched_graph: GraphManager,
        mock_llm_with_analysis: AsyncMock,
    ) -> None:
        """Plan modifies file, LLM checks dependencies via tools."""
        curator = PlanCurator(enriched_graph, mock_llm_with_analysis)
        result = await curator.curate(
            "# Plan\n1. Refactor src/auth/legacy.py"
        )
        assert "Revised Plan" in result
        assert mock_llm_with_analysis.send.call_count == 2

    @pytest.mark.asyncio
    async def test_plan_with_file_deletion(
        self, enriched_graph: GraphManager
    ) -> None:
        """Plan deletes file, LLM detects importers."""
        mock = AsyncMock()
        mock.send.side_effect = [
            _tool_call(
                "zoom_to_module",
                {"file_path": "src/auth/legacy.py"},
            ),
            _final_answer(
                "# Adjusted Plan\n"
                "1. Update login.py and api/auth.py imports\n"
                "2. Then delete legacy.py"
            ),
        ]
        curator = PlanCurator(enriched_graph, mock)
        result = await curator.curate(
            "# Plan\n1. Delete src/auth/legacy.py"
        )
        assert "Adjusted Plan" in result
        # Verify LLM received module info with importers
        second_call = mock.send.call_args_list[1]
        user_prompt = second_call[0][1]
        assert "src/auth/legacy.py" in user_prompt

    @pytest.mark.asyncio
    async def test_plan_with_multiple_affected_files(
        self, enriched_graph: GraphManager
    ) -> None:
        """Plan affects multiple files, LLM navigates through graph."""
        mock = AsyncMock()
        mock.send.side_effect = [
            _tool_call("get_project_overview"),
            _tool_call(
                "zoom_to_package",
                {"package_path": "src/auth"},
            ),
            _tool_call(
                "zoom_to_module",
                {"file_path": "src/auth/legacy.py"},
            ),
            _final_answer(
                "# Deep Analysis Plan\n"
                "1. Migrate legacy.py consumers first\n"
                "2. Refactor auth package"
            ),
        ]
        curator = PlanCurator(enriched_graph, mock)
        result = await curator.curate(
            "# Plan\n1. Restructure entire auth package"
        )
        assert "Deep Analysis Plan" in result
        assert mock.send.call_count == 4


class TestCurateEndToEnd:
    """End-to-end tests with realistic plans on real MapBuilder graph."""

    @pytest.mark.asyncio
    async def test_realistic_auth_refactoring_plan(
        self, real_enriched_graph: GraphManager
    ) -> None:
        """Complex plan: refactor auth/legacy.py, LLM detects 2 importers."""
        mock = AsyncMock()
        mock.send.side_effect = [
            _tool_call(
                "zoom_to_module",
                {"file_path": "src/auth/legacy.py"},
            ),
            _tool_call(
                "zoom_to_symbol",
                {
                    "file_path": "src/auth/legacy.py",
                    "symbol_name": "old_authenticate",
                },
            ),
            _final_answer(
                "# Revised Refactoring Plan\n"
                "## Vorbereitungsschritte\n"
                "1. Update src/auth/login.py to use new auth API\n"
                "2. Update src/api/auth.py to use new auth API\n"
                "## Hauptänderungen\n"
                "3. Refactor src/auth/legacy.py"
            ),
        ]
        curator = PlanCurator(real_enriched_graph, mock)
        result = await curator.curate(
            "# Refactoring Plan\n1. Refactor auth/legacy.py"
        )
        assert "Vorbereitungsschritte" in result
        assert "login.py" in result
        assert "api/auth.py" in result
        assert mock.send.call_count == 3

    @pytest.mark.asyncio
    async def test_realistic_deletion_plan_with_dependencies(
        self, real_enriched_graph: GraphManager
    ) -> None:
        """Plan deletes module, LLM detects via zoom_to_module that it's imported."""
        mock = AsyncMock()
        mock.send.side_effect = [
            _tool_call(
                "zoom_to_module",
                {"file_path": "src/auth/legacy.py"},
            ),
            _final_answer(
                "# Adjusted Deletion Plan\n"
                "1. Migrate consumers of legacy.py:\n"
                "   - src/auth/login.py\n"
                "   - src/api/auth.py\n"
                "2. Delete src/auth/legacy.py"
            ),
        ]
        curator = PlanCurator(real_enriched_graph, mock)
        result = await curator.curate(
            "# Deletion Plan\n1. Delete src/auth/legacy.py"
        )
        assert "Adjusted Deletion Plan" in result
        assert "Migrate consumers" in result

    @pytest.mark.asyncio
    async def test_realistic_package_restructuring(
        self, real_enriched_graph: GraphManager
    ) -> None:
        """Plan restructures package, LLM checks inter-package imports."""
        mock = AsyncMock()
        mock.send.side_effect = [
            _tool_call("get_project_overview"),
            _tool_call(
                "zoom_to_package",
                {"package_path": "src/auth"},
            ),
            _tool_call(
                "zoom_to_package",
                {"package_path": "src/api"},
            ),
            _final_answer(
                "# Package Restructuring Plan\n"
                "1. Create src/auth/v2/ package\n"
                "2. Move authentication to v2\n"
                "3. Update src/api/auth.py imports"
            ),
        ]
        curator = PlanCurator(real_enriched_graph, mock)
        result = await curator.curate(
            "# Plan\n1. Move auth into new package structure"
        )
        assert "Package Restructuring Plan" in result
        assert mock.send.call_count == 4


class TestCurateErrorHandling:
    """Tests for error propagation from CuratorAgent."""

    @pytest.mark.asyncio
    async def test_llm_api_error_propagated(
        self, enriched_graph: GraphManager
    ) -> None:
        """openai.RateLimitError is propagated through PlanCurator."""
        mock = AsyncMock()
        mock.send.side_effect = openai.RateLimitError(
            "Rate limit exceeded",
            response=MagicMock(),
            body=None,
        )
        curator = PlanCurator(enriched_graph, mock)
        with pytest.raises(openai.RateLimitError):
            await curator.curate("# Plan")

    @pytest.mark.asyncio
    async def test_llm_connection_error_propagated(
        self, enriched_graph: GraphManager
    ) -> None:
        """openai.APIConnectionError is propagated through PlanCurator."""
        mock = AsyncMock()
        mock.send.side_effect = openai.APIConnectionError(
            request=MagicMock(),
        )
        curator = PlanCurator(enriched_graph, mock)
        with pytest.raises(openai.APIConnectionError):
            await curator.curate("# Plan")

    @pytest.mark.asyncio
    async def test_max_iterations_error_propagated(
        self, enriched_graph: GraphManager
    ) -> None:
        """ValueError from max_iterations is propagated through PlanCurator."""
        mock = AsyncMock()
        mock.send.return_value = _tool_call("get_project_overview")
        curator = PlanCurator(enriched_graph, mock)
        # CuratorAgent default max_iterations=10, will exhaust
        with pytest.raises(ValueError, match="finalisieren"):
            await curator.curate("# Infinite Plan")
