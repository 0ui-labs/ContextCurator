"""HierarchyEnricher for bottom-up hierarchical summary aggregation.

This module provides the HierarchyEnricher class for aggregating semantic
summaries upward through the code graph hierarchy. It processes nodes
bottom-up (Code -> File -> Package -> Project), using existing code-level
summaries from GraphEnricher as input to produce higher-level summaries.
"""

import asyncio
import json
import logging
from collections import defaultdict

from codemap.core.llm import LLMProvider
from codemap.graph import GraphManager

logger = logging.getLogger(__name__)


class HierarchyEnricher:
    """Aggregate semantic summaries bottom-up through the graph hierarchy.

    Processes the hierarchy built by GraphManager.build_hierarchy() and
    uses LLM calls to aggregate child summaries into parent summaries.
    Processing order follows levels from highest (code) to lowest
    (project, level 0).

    Attributes:
        _graph_manager: GraphManager instance containing the hierarchical graph.
        _llm_provider: LLMProvider instance for AI-powered summary aggregation.
    """

    def __init__(self, graph_manager: GraphManager, llm_provider: LLMProvider) -> None:
        """Initialize HierarchyEnricher with dependencies.

        Args:
            graph_manager: GraphManager containing a graph with hierarchy levels.
            llm_provider: LLMProvider for generating aggregated summaries.

        Example:
            >>> manager = GraphManager()
            >>> provider = LLMProvider(...)
            >>> enricher = HierarchyEnricher(manager, provider)
        """
        self._graph_manager = graph_manager
        self._llm_provider = llm_provider

    async def aggregate_summaries(self) -> None:
        """Aggregate summaries bottom-up through the hierarchy.

        Groups nodes by level attribute, then iterates from the highest
        child level down to level 0. For each parent node at a given level,
        collects summaries from CONTAINS children and calls the LLM to
        produce an aggregated summary. Skips parent nodes whose children
        have no summaries.

        Example:
            >>> enricher = HierarchyEnricher(graph_manager, llm_provider)
            >>> await enricher.aggregate_summaries()
            >>> graph_manager.graph.nodes["project::MyProject"]["summary"]
            'Project overview summary...'
        """
        graph = self._graph_manager.graph

        # Group nodes by level
        nodes_by_level: dict[int, list[str]] = defaultdict(list)
        for node_id, attrs in graph.nodes(data=True):
            level = attrs.get("level")
            if level is not None:
                nodes_by_level[int(level)].append(node_id)

        if not nodes_by_level:
            return

        max_level = max(nodes_by_level.keys())

        # Process from second-highest level down to 0
        # (highest level nodes are leaves that already have summaries)
        for level in range(max_level - 1, -1, -1):
            parent_nodes = nodes_by_level.get(level, [])
            tasks = [self._aggregate_node(parent_id) for parent_id in parent_nodes]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for parent_id, result in zip(parent_nodes, results):
                if isinstance(result, Exception):
                    logger.warning("Unexpected error aggregating %s: %s", parent_id, result)

    async def _aggregate_node(self, node_id: str) -> None:
        """Aggregate summaries for a single parent node from its CONTAINS children.

        Collects summaries from children connected via CONTAINS edges.
        If no children have summaries, the node is skipped. Otherwise,
        builds a prompt with child summaries, calls the LLM, and sets
        the aggregated summary on the parent node.

        Args:
            node_id: The parent node ID to aggregate summaries for.
        """
        graph = self._graph_manager.graph

        # Collect children with summaries via CONTAINS edges
        children_with_summaries: list[tuple[str, str]] = []
        for _, child_id, edge_data in graph.out_edges(node_id, data=True):
            if edge_data.get("relationship") != "CONTAINS":
                continue
            summary = graph.nodes[child_id].get("summary")
            if summary:
                children_with_summaries.append((child_id, summary))

        if not children_with_summaries:
            return

        # Build prompt with child node IDs in the user message
        node_attrs = graph.nodes[node_id]
        node_type = node_attrs.get("type", "unknown")
        node_name = node_attrs.get("name", node_id)

        system_prompt = (
            "You are a code analysis assistant. Summarize the following "
            "child components into a single cohesive summary for the parent. "
            'Return JSON: [{"node_id": "...", "summary": "..."}]'
        )

        child_lines = [f"- {child_id}: {summary}" for child_id, summary in children_with_summaries]

        user_prompt = (
            f"Summarize these components of {node_type} '{node_name}':\n\n"
            + "\n".join(child_lines)
            + f"\n\nReturn summary for node_id: {node_id}"
        )

        try:
            response = await self._llm_provider.send(system_prompt, user_prompt)
        except Exception as e:
            logger.warning("LLM call failed for %s: %s", node_id, e)
            return

        try:
            results: list[dict[str, str]] = json.loads(response)

            for result in results:
                if result.get("node_id") == node_id:
                    graph.nodes[node_id]["summary"] = result["summary"]
                    break
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Failed to aggregate summary for %s: %s", node_id, e)
