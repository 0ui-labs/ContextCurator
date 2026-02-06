"""Unit tests for HierarchyEnricher (hierarchical summary aggregation).

Tests cover:
- Initialization with GraphManager and LLMProvider
- Bottom-up aggregation (Code -> File -> Package -> Project)
- Level-based processing order
- Handling of nodes without child summaries
"""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from codemap.core.llm import LLMProvider
from codemap.engine.hierarchy_enricher import HierarchyEnricher
from codemap.graph import GraphManager
from codemap.mapper.models import CodeNode
from codemap.scout.models import FileEntry


@pytest.fixture
def graph_with_hierarchy() -> GraphManager:
    """Build a complete hierarchy graph simulating GraphEnricher output.

    Creates the following structure:

        project::TestProject (level=0)
        +-- src (level=1, package)
            +-- src/auth (level=1, package)
            |   +-- src/auth/login.py (level=2, file)
            |       +-- src/auth/login.py::authenticate (level=3, summary)
            |       +-- src/auth/login.py::validate_token (level=3, summary)
            +-- src/api (level=1, package)
                +-- src/api/routes.py (level=2, file)
                    +-- src/api/routes.py::UserRouter (level=3, summary)
                    +-- src/api/routes.py::get_user (level=3, summary)
    """
    manager = GraphManager()

    # Add file nodes
    manager.add_file(FileEntry(Path("src/auth/login.py"), size=100, token_est=25))
    manager.add_file(FileEntry(Path("src/api/routes.py"), size=100, token_est=25))

    # Add code nodes for src/auth/login.py
    manager.add_node("src/auth/login.py", CodeNode("function", "authenticate", 1, 10))
    manager.add_node("src/auth/login.py", CodeNode("function", "validate_token", 12, 20))

    # Add code nodes for src/api/routes.py
    manager.add_node("src/api/routes.py", CodeNode("class", "UserRouter", 1, 15))
    manager.add_node("src/api/routes.py", CodeNode("function", "get_user", 17, 25))

    # Build hierarchy: creates project, package nodes with levels and CONTAINS edges
    manager.build_hierarchy("TestProject")

    # Simulate GraphEnricher output: add summaries to code-level nodes only
    manager.graph.nodes["src/auth/login.py::authenticate"]["summary"] = "Authenticates user credentials"
    manager.graph.nodes["src/auth/login.py::validate_token"]["summary"] = "Validates JWT tokens"
    manager.graph.nodes["src/api/routes.py::UserRouter"]["summary"] = "Handles user-related routes"
    manager.graph.nodes["src/api/routes.py::get_user"]["summary"] = "Retrieves user by ID"

    return manager


class TestHierarchyEnricherInit:
    """Test suite for HierarchyEnricher initialization and dependency injection.

    Validates that HierarchyEnricher follows the same dependency injection
    pattern as GraphEnricher, accepting GraphManager and LLMProvider and
    storing them as private attributes.
    """

    def test_init_stores_dependencies(self) -> None:
        """HierarchyEnricher stores GraphManager and LLMProvider as private attributes."""
        # Arrange
        graph_manager = GraphManager()
        llm_provider = AsyncMock(spec=LLMProvider)

        # Act
        enricher = HierarchyEnricher(graph_manager, llm_provider)

        # Assert
        assert enricher._graph_manager is graph_manager
        assert enricher._llm_provider is llm_provider


class TestAggregationBottomUp:
    """Test suite for bottom-up hierarchical summary aggregation.

    Validates that HierarchyEnricher aggregates summaries from leaf nodes
    upward through the hierarchy: Code (level 3) -> File (level 2) ->
    Package (level 1) -> Project (level 0). Tests verify correct processing
    order and handling of missing summaries.
    """

    @pytest.mark.asyncio
    async def test_aggregate_file_summary_from_code_nodes(
        self, graph_with_hierarchy: GraphManager
    ) -> None:
        """File node receives aggregated summary from its code-level children."""
        # Arrange
        provider = AsyncMock(spec=LLMProvider)
        provider.send.return_value = (
            '[{"node_id": "src/auth/login.py", "summary": "Authentication module providing credential verification and JWT token validation"}]'
        )
        enricher = HierarchyEnricher(graph_with_hierarchy, provider)

        # Act
        await enricher.aggregate_summaries()

        # Assert
        assert "summary" in graph_with_hierarchy.graph.nodes["src/auth/login.py"]

    @pytest.mark.asyncio
    async def test_aggregate_package_summary_from_file_nodes(
        self, graph_with_hierarchy: GraphManager
    ) -> None:
        """Package node receives aggregated summary from its file-level children."""
        # Arrange
        provider = AsyncMock(spec=LLMProvider)
        provider.send.side_effect = [
            # Level 3->File: login.py aggregation (code -> file)
            '[{"node_id": "src/auth/login.py", "summary": "Authentication module"}]',
            # Level 3->File: routes.py aggregation (code -> file)
            '[{"node_id": "src/api/routes.py", "summary": "API routing module"}]',
            # Level 2->Package: auth package aggregation (file -> package)
            '[{"node_id": "src/auth", "summary": "Auth package handling user authentication and token validation"}]',
            # Level 2->Package: api package aggregation (file -> package)
            '[{"node_id": "src/api", "summary": "API package"}]',
            # Level 1->Package: src package aggregation (package -> package)
            '[{"node_id": "src", "summary": "Source root"}]',
            # Level 0->Project: project aggregation (package -> project)
            '[{"node_id": "project::TestProject", "summary": "Test project"}]',
        ]
        enricher = HierarchyEnricher(graph_with_hierarchy, provider)

        # Act
        await enricher.aggregate_summaries()

        # Assert
        assert "summary" in graph_with_hierarchy.graph.nodes["src/auth"]

    @pytest.mark.asyncio
    async def test_aggregation_processes_levels_bottom_to_top(
        self, graph_with_hierarchy: GraphManager
    ) -> None:
        """Aggregation processes highest level (code) before lower levels (package)."""
        # Arrange
        call_order: list[str] = []

        async def track_calls(_system: str, user: str) -> str:
            # Extract which parent node is being aggregated from the prompt
            if "src/auth/login.py::" in user:
                call_order.append("level_3_to_file")
                return '[{"node_id": "src/auth/login.py", "summary": "test file summary"}]'
            if "src/api/routes.py::" in user:
                return '[{"node_id": "src/api/routes.py", "summary": "test file summary"}]'
            if "src/auth/login.py" in user and "::" not in user:
                call_order.append("level_2_to_package")
                return '[{"node_id": "src/auth", "summary": "test package summary"}]'
            return '[{"node_id": "dummy", "summary": "test"}]'

        provider = AsyncMock(spec=LLMProvider)
        provider.send.side_effect = track_calls
        enricher = HierarchyEnricher(graph_with_hierarchy, provider)

        # Act
        await enricher.aggregate_summaries()

        # Assert
        assert call_order.index("level_3_to_file") < call_order.index("level_2_to_package")

    @pytest.mark.asyncio
    async def test_skips_nodes_without_children_summaries(
        self, graph_with_hierarchy: GraphManager
    ) -> None:
        """Nodes are skipped when their children lack summaries."""
        # Arrange - remove ALL summaries from code nodes so no LLM calls are legitimate
        del graph_with_hierarchy.graph.nodes["src/auth/login.py::authenticate"]["summary"]
        del graph_with_hierarchy.graph.nodes["src/auth/login.py::validate_token"]["summary"]
        del graph_with_hierarchy.graph.nodes["src/api/routes.py::UserRouter"]["summary"]
        del graph_with_hierarchy.graph.nodes["src/api/routes.py::get_user"]["summary"]

        provider = AsyncMock(spec=LLMProvider)
        enricher = HierarchyEnricher(graph_with_hierarchy, provider)

        # Act
        await enricher.aggregate_summaries()

        # Assert - no file node should receive a summary since no children have summaries
        assert "summary" not in graph_with_hierarchy.graph.nodes["src/auth/login.py"]
        assert "summary" not in graph_with_hierarchy.graph.nodes["src/api/routes.py"]
        provider.send.assert_not_called()


class TestProjectLevelAggregation:
    """Test suite for project-level (level 0) summary aggregation.

    Validates that the project node receives an aggregated summary derived
    from top-level package summaries. The project summary represents the
    highest abstraction level in the hierarchy.
    """

    @pytest.mark.asyncio
    async def test_project_summary_aggregates_top_packages(
        self, graph_with_hierarchy: GraphManager
    ) -> None:
        """Project node receives aggregated summary from top-level package summaries."""
        # Arrange - add summaries to all hierarchy levels below project
        graph_with_hierarchy.graph.nodes["src/auth/login.py"]["summary"] = (
            "Authentication module providing credential verification"
            " and JWT token validation"
        )
        graph_with_hierarchy.graph.nodes["src/api/routes.py"]["summary"] = (
            "API routing module with user endpoints"
        )
        graph_with_hierarchy.graph.nodes["src/auth"]["summary"] = (
            "Auth package handling user authentication and token validation"
        )
        graph_with_hierarchy.graph.nodes["src/api"]["summary"] = (
            "API package providing REST endpoints"
        )
        graph_with_hierarchy.graph.nodes["src"]["summary"] = (
            "Source root containing auth and api packages"
        )

        provider = AsyncMock(spec=LLMProvider)
        provider.send.return_value = (
            '[{"node_id": "project::TestProject",'
            ' "summary": "Code mapping and analysis tool'
            ' for Python projects"}]'
        )
        enricher = HierarchyEnricher(graph_with_hierarchy, provider)

        # Act
        await enricher.aggregate_summaries()

        # Assert
        project_node = graph_with_hierarchy.graph.nodes["project::TestProject"]
        assert "summary" in project_node
        assert "Code mapping" in project_node["summary"]
