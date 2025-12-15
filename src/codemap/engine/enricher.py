"""GraphEnricher for semantic code analysis with AI-powered batch processing.

This module provides the GraphEnricher class for enriching code graphs with
semantic information using LLM providers. It processes code nodes in batches
for efficient API usage and provides robust error handling.
"""

import asyncio
import logging
import re
from typing import Any

import openai
import orjson

from codemap.core.llm import LLMProvider
from codemap.graph import GraphManager

logger = logging.getLogger(__name__)


class GraphEnricher:
    """Enrich code graph with semantic summaries and risk analysis using LLMs.

    This class provides batch-based enrichment of code nodes with semantic
    information (summaries and risk assessments) using LLM providers. It follows
    the Dependency Injection pattern for testability and implements parallel
    batch processing for efficiency.

    Architecture:
        - Processes code nodes in batches to optimize LLM API usage
        - Uses asyncio.gather for parallel batch processing
        - Implements batch-level error isolation (one batch failure doesn't affect others)
        - Updates graph nodes with summary and risks attributes

    The class enriches only nodes with type "function" or "class" that don't
    already have a "summary" attribute, ensuring idempotent behavior.

    Attributes:
        _graph_manager: GraphManager instance containing the code graph to enrich.
        _llm_provider: LLMProvider instance for AI-powered semantic analysis.

    Example:
        Basic usage with GraphManager and LLMProvider::

            from codemap.graph import GraphManager
            from codemap.core.llm import get_provider
            from codemap.engine.enricher import GraphEnricher

            # Initialize dependencies
            graph_manager = GraphManager()
            llm_provider = get_provider("cerebras")

            # Create enricher and process nodes
            enricher = GraphEnricher(graph_manager, llm_provider)
            await enricher.enrich_nodes(batch_size=10)

            # Check enriched attributes
            for node_id, attrs in graph_manager.graph.nodes(data=True):
                if attrs.get("type") in ["function", "class"]:
                    print(f"{node_id}: {attrs.get('summary')}")
    """

    def __init__(self, graph_manager: GraphManager, llm_provider: LLMProvider) -> None:
        """Initialize GraphEnricher with dependencies.

        Follows the Dependency Injection pattern to enable testability and
        flexibility in swapping graph managers and LLM providers.

        Args:
            graph_manager: GraphManager instance containing the code graph to enrich.
            llm_provider: LLMProvider instance for AI-powered semantic analysis.

        Example:
            >>> from codemap.graph import GraphManager
            >>> from codemap.core.llm import MockProvider
            >>> manager = GraphManager()
            >>> provider = MockProvider()
            >>> enricher = GraphEnricher(manager, provider)
        """
        self._graph_manager = graph_manager
        self._llm_provider = llm_provider

    async def enrich_nodes(self, batch_size: int = 10) -> None:
        """Enrich code nodes with semantic information in batches.

        This method processes all unenriched code nodes (functions and classes)
        in the graph, splitting them into batches for efficient LLM processing.
        Each batch is processed in parallel using asyncio.gather.

        The method is idempotent: nodes with existing "summary" attributes are
        skipped, allowing safe re-execution without duplicating work.

        Process:
            1. Collect all unenriched nodes (type="function" or "class", no "summary")
            2. Split nodes into batches of size batch_size
            3. Process batches in parallel with asyncio.gather
            4. Each batch calls LLM and updates graph attributes

        Args:
            batch_size: Number of nodes to process per batch (default: 10).
                Larger batches reduce API calls but may hit token limits.

        Returns:
            None. Updates graph nodes in-place with "summary" and "risks" attributes.

        Example:
            >>> enricher = GraphEnricher(graph_manager, llm_provider)
            >>> await enricher.enrich_nodes(batch_size=5)  # Process 5 nodes per batch

        Raises:
            ValueError: If batch_size is less than or equal to 0.
        """
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")

        # Step 1: Collect unenriched nodes
        nodes = []
        for node_id, attrs in self._graph_manager.graph.nodes(data=True):
            if attrs.get("type") in ["function", "class"] and "summary" not in attrs:
                nodes.append((node_id, attrs))

        if not nodes:
            logger.info("No nodes to enrich")
            return

        # Step 2: Create batches
        batches = [nodes[i : i + batch_size] for i in range(0, len(nodes), batch_size)]

        logger.info(f"Enriching {len(nodes)} nodes in {len(batches)} batches")

        # Step 3: Process batches in parallel
        tasks = [self._enrich_batch(batch) for batch in batches]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _enrich_batch(self, batch: list[tuple[str, dict[str, Any]]]) -> None:
        """Enrich a single batch of code nodes with LLM analysis.

        This private helper method processes one batch by:
        1. Building a prompt with all node information
        2. Calling the LLM provider
        3. Parsing the JSON response
        4. Updating graph attributes

        The LLM is expected to return a JSON array of objects, each containing:
        - node_id: The identifier matching a node in the graph
        - summary: A brief description of the code element
        - risks: A list of potential risks or concerns

        Example expected response::

            [
                {"node_id": "file.py::func", "summary": "Does X", "risks": ["Risk A"]},
                {"node_id": "file.py::Class", "summary": "Does Y", "risks": []}
            ]

        Error handling is batch-level for expected LLM errors:
        - ValueError, openai.RateLimitError, openai.APIConnectionError, openai.APIError
          are caught, logged as warnings, and isolated per batch.
        - Unexpected exceptions are logged as errors and re-raised to surface
          programming bugs during development/testing.

        Args:
            batch: List of tuples (node_id, attributes_dict) to process.

        Returns:
            None. Updates graph nodes in-place or logs warnings on failure.

        Raises:
            Exception: Re-raises unexpected exceptions after logging.
        """
        try:
            # Step 1: Build prompt
            system_prompt = (
                "You are a code analysis assistant. Analyze the following code elements "
                "and return a JSON array with summary and risks for each."
            )

            user_prompt_lines = ["Analyze these code elements:"]
            for idx, (node_id, attrs) in enumerate(batch, start=1):
                start_line = attrs.get('start_line')
                end_line = attrs.get('end_line')
                user_prompt_lines.append(
                    f"{idx}. node_id: {node_id}, type: {attrs.get('type')}, "
                    f"name: {attrs.get('name')}, lines: {start_line}-{end_line}"
                )

            user_prompt_lines.append("")
            user_prompt_lines.append(
                'Return JSON array: '
                '[{"node_id": "...", "summary": "...", "risks": ["..."]}]'
            )
            user_prompt = "\n".join(user_prompt_lines)

            # Step 2: Call LLM
            response = await self._llm_provider.send(system_prompt, user_prompt)

            # Step 3: Parse JSON response
            # Strategy: Try direct parsing first for clean responses, then fall back
            # to regex extraction for responses with markdown code blocks or extra text.
            try:
                # First attempt: Direct parse (works for clean JSON responses)
                try:
                    results = orjson.loads(response)
                except orjson.JSONDecodeError as direct_parse_error:
                    # Fallback: Use regex to isolate JSON array from markdown code blocks
                    # (e.g., ```json [...] ```) or responses with surrounding text.
                    json_match = re.search(r"\[.*\]", response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        results = orjson.loads(json_str)
                    else:
                        # No JSON array found in response, re-raise original error
                        raise direct_parse_error

                # Step 4: Update graph attributes
                for result in results:
                    if not isinstance(result, dict):
                        continue

                    result_node_id = result.get("node_id")
                    if not result_node_id:
                        logger.warning("Result missing node_id field")
                        continue

                    if result_node_id not in self._graph_manager.graph.nodes:
                        logger.warning(f"Node ID {result_node_id} not found in graph")
                        continue

                    # Update node attributes
                    node = self._graph_manager.graph.nodes[result_node_id]
                    node["summary"] = result.get("summary", "")
                    node["risks"] = result.get("risks", [])

            except orjson.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON response for batch: {e}")

        except ValueError as e:
            # Expected: LLM returns empty/null response
            logger.warning(f"LLM returned invalid response for batch: {e}")
        except (
            openai.RateLimitError,
            openai.APIConnectionError,
            openai.APIError,
        ) as e:
            # Expected: LLM API errors (rate limiting, connection issues, etc.)
            logger.warning(f"LLM API error processing batch: {e}")
        except Exception as e:
            # Unexpected: Re-raise after logging to surface programming errors
            logger.error(f"Unexpected error processing batch: {e}")
            raise
