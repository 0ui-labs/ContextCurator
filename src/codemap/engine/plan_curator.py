"""PlanCurator for orchestrating plan analysis with code graph context.

This module provides the PlanCurator class that orchestrates MapRenderer,
CuratorTools, and CuratorAgent to analyze and revise implementation plans
based on code graph insights.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from codemap.core.llm import LLMProvider
    from codemap.graph import GraphManager

from codemap.engine.curator_agent import CuratorAgent
from codemap.engine.curator_tools import CuratorTools
from codemap.engine.map_renderer import MapRenderer


class PlanCurator:
    """Orchestrates plan analysis with code graph context.

    Coordinates MapRenderer, CuratorTools, and CuratorAgent to analyze
    implementation plans and revise them based on code graph insights
    (dependencies, risks, side-effects).

    Architecture:
        PlanCurator -> CuratorAgent -> CuratorTools -> MapRenderer -> GraphManager

    The curator takes a plan string, uses the LLM agent to navigate the
    code graph via tools, and returns a revised plan that addresses
    identified risks and dependencies.

    Example:
        >>> from pathlib import Path
        >>> from codemap.engine import MapBuilder, PlanCurator
        >>> from codemap.core.llm import get_provider
        >>>
        >>> # Build enriched graph
        >>> builder = MapBuilder()
        >>> graph = builder.build(Path("src"))
        >>> # ... enrich graph with summaries and risks ...
        >>>
        >>> # Curate plan
        >>> llm = get_provider("cerebras")
        >>> curator = PlanCurator(graph, llm, root_path=Path("src"))
        >>> original_plan = "# Plan\\n1. Delete auth/legacy.py"
        >>> revised_plan = await curator.curate(original_plan)
        >>> print(revised_plan)
        # Revised Plan
        1. Update imports in login.py and api/auth.py
        2. Then delete auth/legacy.py
    """

    def __init__(
        self,
        graph_manager: GraphManager,
        llm_provider: LLMProvider,
        *,
        root_path: Path | None = None,
    ) -> None:
        """Initialize PlanCurator with dependencies.

        Args:
            graph_manager: GraphManager with enriched graph (summaries, risks).
            llm_provider: LLMProvider for AI-powered plan analysis.
            root_path: Optional project root for Level 4 code extraction.
        """
        self._graph = graph_manager
        self._llm = llm_provider
        self._renderer = MapRenderer(graph_manager, root_path=root_path)
        self._tools = CuratorTools(self._renderer)
        self._agent = CuratorAgent(llm_provider, self._tools)

    async def curate(self, plan: str) -> str:
        """Analyze and revise implementation plan with code graph context.

        Delegates to CuratorAgent which navigates the code graph via
        CuratorTools to understand dependencies, risks, and side-effects,
        then returns a revised plan that addresses identified issues.

        Args:
            plan: Original implementation plan (Markdown).

        Returns:
            Revised plan (Markdown) with risk mitigation steps.

        Raises:
            ValueError: If agent cannot finalize plan after max_iterations.
            openai.RateLimitError: If LLM API rate limit exceeded.
            openai.APIConnectionError: If LLM API connection fails.
            openai.APIError: If other LLM API errors occur.
        """
        return await self._agent.analyze_plan(plan)
