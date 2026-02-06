"""Integration tests for PlanCurator with real MapBuilder graph.

Tests that PlanCurator correctly uses MapBuilder-generated graphs to
produce risk-aware and dependency-aware plan revisions. Uses a Fake/Stub
LLM that makes tool calls and returns a final plan addressing identified
risks and dependencies from the enriched graph.

Test Organization:
    - TestPlanCuratorRiskMitigation: Verify tool results contain real
      risk/dependency data and final plan addresses them.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock

import pytest

from codemap.engine.builder import MapBuilder
from codemap.engine.plan_curator import PlanCurator

if TYPE_CHECKING:
    from pathlib import Path

    from codemap.graph import GraphManager


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
def enriched_project(tmp_path: Path) -> tuple[GraphManager, Path]:
    """Build enriched graph from real Python files via MapBuilder.

    Creates a sample project with import dependencies and risks:
        src/auth/legacy.py - deprecated auth with risks
        src/auth/login.py  - modern auth, imports legacy
        src/api/auth.py    - API auth, imports legacy

    Returns:
        (GraphManager with enrichment, project root path)
    """
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

    return gm, tmp_path


class TestPlanCuratorRiskMitigation:
    """Integration tests: PlanCurator addresses risks from real graph."""

    @pytest.mark.asyncio
    async def test_curate_with_realistic_plan_addresses_risks(
        self, enriched_project: tuple[GraphManager, Path]
    ) -> None:
        """Fake-LLM explores graph, discovers risks, returns risk-aware plan."""
        gm, root = enriched_project

        mock_llm = AsyncMock()
        mock_llm.send.side_effect = [
            # Step 1: LLM explores the risky module
            _tool_call(
                "zoom_to_module",
                {"file_path": "src/auth/legacy.py"},
            ),
            # Step 2: LLM checks the risky symbol
            _tool_call(
                "zoom_to_symbol",
                {
                    "file_path": "src/auth/legacy.py",
                    "symbol_name": "old_authenticate",
                },
            ),
            # Step 3: LLM returns plan addressing discovered risks
            _final_answer(
                "# Überarbeiteter Plan\n"
                "## Risiko-Mitigation\n"
                "- Deprecated code in legacy.py muss migriert werden\n"
                "- Security vulnerabilities durch neue Auth beheben\n"
                "- No password hashing in old_authenticate ersetzen\n"
                "## Abhängigkeiten\n"
                "- src/auth/login.py importiert legacy.py\n"
                "- src/api/auth.py importiert legacy.py\n"
                "## Schritte\n"
                "1. src/auth/login.py auf neue Auth-API umstellen\n"
                "2. src/api/auth.py auf neue Auth-API umstellen\n"
                "3. src/auth/legacy.py refactoren"
            ),
        ]

        curator = PlanCurator(gm, mock_llm, root_path=root)
        result = await curator.curate(
            "# Mehrstufiger Refactoring-Plan\n"
            "1. Refactor legacy authentication in src/auth/legacy.py\n"
            "2. Update all consumers of legacy auth\n"
            "3. Add password hashing to auth system"
        )

        # Verify risks from graph are addressed in final plan
        assert "Deprecated code" in result
        assert "Security vulnerabilities" in result
        assert "No password hashing" in result

        # Verify dependencies are addressed
        assert "login.py" in result
        assert "auth.py" in result

        # Verify tool results contained real risk data from graph
        second_prompt = mock_llm.send.call_args_list[1][0][1]
        assert "Deprecated code" in second_prompt
        assert "Security vulnerabilities" in second_prompt

        third_prompt = mock_llm.send.call_args_list[2][0][1]
        assert "No password hashing" in third_prompt

    @pytest.mark.asyncio
    async def test_tool_results_contain_real_import_edges(
        self, enriched_project: tuple[GraphManager, Path]
    ) -> None:
        """Tool results reflect real IMPORTS edges from MapBuilder."""
        gm, root = enriched_project

        mock_llm = AsyncMock()
        mock_llm.send.side_effect = [
            _tool_call(
                "zoom_to_module",
                {"file_path": "src/auth/legacy.py"},
            ),
            _final_answer("# Plan\n1. Done"),
        ]

        curator = PlanCurator(gm, mock_llm, root_path=root)
        await curator.curate("# Plan\n1. Refactor legacy.py")

        # Tool result for zoom_to_module shows real importers
        second_prompt = mock_llm.send.call_args_list[1][0][1]
        assert "src/auth/login.py" in second_prompt
        assert "src/api/auth.py" in second_prompt

    @pytest.mark.asyncio
    async def test_multi_step_plan_with_overview_and_risks(
        self, enriched_project: tuple[GraphManager, Path]
    ) -> None:
        """Full navigation: overview -> package -> module -> risk-aware plan."""
        gm, root = enriched_project

        mock_llm = AsyncMock()
        mock_llm.send.side_effect = [
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
                "# Revidierter Migrations-Plan\n"
                "## Erkannte Risiken\n"
                "- Deprecated code in legacy.py\n"
                "- Security vulnerabilities in Auth-Modul\n"
                "## Abhängigkeitsanalyse\n"
                "- login.py und api/auth.py hängen von legacy.py ab\n"
                "## Migrationsschritte\n"
                "1. Neue Auth-Implementierung erstellen\n"
                "2. login.py migrieren\n"
                "3. api/auth.py migrieren\n"
                "4. legacy.py entfernen"
            ),
        ]

        curator = PlanCurator(gm, mock_llm, root_path=root)
        result = await curator.curate(
            "# Migrations-Plan\n"
            "1. Legacy Auth-System migrieren\n"
            "2. Alle Abhängigkeiten aktualisieren"
        )

        # Verify risks are addressed
        assert "Deprecated code" in result
        assert "Security vulnerabilities" in result

        # Verify dependency analysis
        assert "login.py" in result
        assert "auth.py" in result

        # Verify full navigation happened
        assert mock_llm.send.call_count == 4

        # Verify overview contained real project data
        second_prompt = mock_llm.send.call_args_list[1][0][1]
        assert "TestProject" in second_prompt

        # Verify package view contained real module data
        third_prompt = mock_llm.send.call_args_list[2][0][1]
        assert "legacy.py" in third_prompt
