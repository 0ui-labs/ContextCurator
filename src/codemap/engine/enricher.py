"""GraphEnricher for semantic code analysis with AI-powered batch processing.

This module provides the GraphEnricher class for enriching code graphs with
semantic information using LLM providers. It processes code nodes in batches
for efficient API usage and provides robust error handling.

The enricher supports two modes:
    - **Metadata-only mode** (default): Sends node names, types, and line
      numbers to the LLM for analysis.
    - **Code-content mode**: When ``root_path`` is provided, extracts actual
      source code from files and includes it in LLM prompts, enabling more
      accurate semantic summaries and risk assessments.
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Any

import openai
import orjson

from codemap.core.llm import LLMProvider
from codemap.graph import GraphManager
from codemap.mapper.reader import ContentReader, ContentReadError

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
        - Supports code-content extraction for accurate LLM analysis

    The class enriches only nodes with type "function" or "class" that don't
    already have a "summary" attribute, ensuring idempotent behavior.

    Attributes:
        _graph_manager: GraphManager instance containing the code graph to enrich.
        _llm_provider: LLMProvider instance for AI-powered semantic analysis.
        _root_path: Project root for resolving source file paths (None for
            metadata-only mode).
        _content_reader: ContentReader for reading source files (auto-created
            when root_path is set).
        _max_code_lines: Maximum lines per code snippet before truncation.

    Example:
        Metadata-only mode (backwards compatible)::

            enricher = GraphEnricher(graph_manager, llm_provider)
            await enricher.enrich_nodes(batch_size=10)

        Code-content mode (includes real source code in prompts)::

            enricher = GraphEnricher(
                graph_manager, llm_provider, root_path=Path("/my/project")
            )
            await enricher.enrich_nodes(batch_size=10)
    """

    def __init__(
        self,
        graph_manager: GraphManager,
        llm_provider: LLMProvider,
        *,
        root_path: Path | None = None,
        content_reader: ContentReader | None = None,
        max_code_lines: int = 100,
    ) -> None:
        """Initialize GraphEnricher with dependencies.

        Follows the Dependency Injection pattern to enable testability and
        flexibility in swapping graph managers and LLM providers.

        Args:
            graph_manager: GraphManager instance containing the code graph to enrich.
            llm_provider: LLMProvider instance for AI-powered semantic analysis.
            root_path: Project root for code extraction. When None, enricher
                operates in metadata-only mode (backwards compatible).
            content_reader: File reader for source code. Auto-created when
                root_path is given but content_reader is None.
            max_code_lines: Maximum lines per code snippet before truncation.

        Example:
            >>> from codemap.graph import GraphManager
            >>> from codemap.core.llm import MockProvider
            >>> manager = GraphManager()
            >>> provider = MockProvider()
            >>> enricher = GraphEnricher(manager, provider)

            With code content::

                enricher = GraphEnricher(manager, provider, root_path=Path("."))
        """
        self._graph_manager = graph_manager
        self._llm_provider = llm_provider
        self._root_path = root_path
        self._max_code_lines = max_code_lines

        if root_path is not None and content_reader is None:
            self._content_reader: ContentReader | None = ContentReader()
        else:
            self._content_reader = content_reader

    def _extract_code_snippet(self, node_id: str, start_line: int, end_line: int) -> str | None:
        """Extract code snippet from source file for a given node.

        Parses the node_id to determine the file path, reads the file,
        and extracts the relevant line range. Truncates if exceeding
        max_code_lines.

        Args:
            node_id: Node identifier in format "path/file.py::symbol_name".
            start_line: Start line number (1-indexed).
            end_line: End line number (1-indexed, inclusive).

        Returns:
            The extracted code snippet as a string, or None if extraction
            fails (missing file, read error, or node_id without '::').
        """
        if self._root_path is None or self._content_reader is None:
            return None

        if "::" not in node_id:
            return None

        if start_line > end_line:
            logger.warning(
                f"Invalid line range for code extraction ({node_id}): "
                f"start_line={start_line} > end_line={end_line}"
            )
            return None

        file_path = node_id.split("::")[0]
        abs_path = self._root_path / file_path

        try:
            content = self._content_reader.read_file(abs_path)
        except (FileNotFoundError, ContentReadError) as e:
            logger.warning(f"Could not read file for code extraction ({file_path}): {e}")
            return None

        lines = content.splitlines()
        snippet_lines = lines[start_line - 1 : end_line]

        if not snippet_lines:
            logger.warning(
                f"Empty code snippet for {node_id} "
                f"(lines {start_line}-{end_line}, file has {len(lines)} lines)"
            )
            return None

        if len(snippet_lines) > self._max_code_lines:
            original_length = len(snippet_lines)
            snippet_lines = snippet_lines[: self._max_code_lines]
            remaining = original_length - len(snippet_lines)
            snippet_lines.append(f"... (truncated, {remaining} more lines)")

        return "\n".join(snippet_lines)

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

            user_prompt_lines = ["Analyze these code elements:", ""]
            for idx, (node_id, attrs) in enumerate(batch, start=1):
                start_line = attrs.get("start_line")
                end_line = attrs.get("end_line")

                user_prompt_lines.append(f"### {idx}. {node_id}")
                user_prompt_lines.append(f"- type: {attrs.get('type')}")
                user_prompt_lines.append(f"- name: {attrs.get('name')}")
                user_prompt_lines.append(f"- lines: {start_line}-{end_line}")

                if self._root_path is not None:
                    code = None
                    if start_line is not None and end_line is not None:
                        code = self._extract_code_snippet(node_id, start_line, end_line)
                    if code:
                        file_path_part = node_id.split("::")[0] if "::" in node_id else node_id
                        ext = Path(file_path_part).suffix.lstrip(".")
                        lang_map = {"py": "python", "js": "javascript", "ts": "typescript"}
                        lang = lang_map.get(ext, ext)
                        user_prompt_lines.append("- code:")
                        user_prompt_lines.append(f"```{lang}")
                        user_prompt_lines.append(code)
                        user_prompt_lines.append("```")
                    else:
                        user_prompt_lines.append("- code: (not available)")

                user_prompt_lines.append("")

            user_prompt_lines.append(
                'Return JSON array: [{"node_id": "...", "summary": "...", "risks": ["..."]}]'
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
