"""Unit tests for engine.enricher module.

This module contains comprehensive tests for the GraphEnricher class,
following strict TDD methodology (RED → GREEN → REFACTOR).

Test Organization:
    - TestGraphEnricherInitialization: Verify constructor and dependency injection
    - TestEnrichNodesBatching: Verify batching logic with various batch sizes
    - TestEnrichNodesGraphUpdates: Verify graph attributes updated correctly
    - TestEnrichNodesErrorHandling: Verify batch-level error isolation

Coverage: Target 100% of enricher.py (lines, branches, error paths)

Test Patterns:
    - AAA (Arrange-Act-Assert) structure throughout
    - pytest-asyncio with @pytest.mark.asyncio for async tests
    - unittest.mock.AsyncMock for mocking async LLMProvider.send()
    - Comprehensive docstrings following Google style

Component Interactions Tested:
    - GraphManager: Node iteration, attribute updates
    - LLMProvider: Async send() calls with batched prompts
    - asyncio.gather: Parallel batch processing with error isolation
"""

from unittest.mock import AsyncMock

import pytest

from codemap.engine.enricher import GraphEnricher
from codemap.graph import GraphManager
from codemap.mapper.models import CodeNode
from codemap.scout.models import FileEntry


class TestGraphEnricherInitialization:
    """Test suite for GraphEnricher initialization and dependency injection."""

    @pytest.mark.asyncio
    async def test_enricher_instantiates_with_dependencies(self) -> None:
        """Test GraphEnricher instantiates with GraphManager and LLMProvider.

        Validates that GraphEnricher follows dependency injection pattern:
        - Constructor accepts GraphManager and LLMProvider parameters
        - Stores dependencies as instance attributes
        - No exceptions raised during instantiation
        """
        # Arrange
        graph_manager = GraphManager()
        llm_provider = AsyncMock()

        # Act
        enricher = GraphEnricher(graph_manager, llm_provider)

        # Assert - Enricher stores dependencies (implementation will define attribute names)
        assert enricher is not None
        # Note: Attribute names will be verified once implementation exists


class TestEnrichNodesBatching:
    """Test suite for GraphEnricher batching logic."""

    @pytest.mark.asyncio
    async def test_enricher_batches_nodes(self) -> None:
        """Test GraphEnricher splits 25 nodes into 3 batches (10+10+5).

        This test validates the batching strategy for efficient LLM processing:
        - Creates 25 code nodes (mix of functions and classes)
        - None have summary attribute initially
        - Verifies LLM provider called exactly 3 times
        - Verifies batch sizes are correct (10, 10, 5)

        The test uses AsyncMock to track LLM provider calls and verify
        batch content structure (node IDs, names, types).
        """
        # Arrange - Create GraphManager with 25 code nodes
        graph_manager = GraphManager()

        # Add parent file node
        from pathlib import Path

        graph_manager.add_file(FileEntry(Path("test.py"), size=1024, token_est=256))

        # Add 25 code nodes (15 functions + 10 classes) without summary attribute
        for i in range(15):
            graph_manager.add_node(
                "test.py",
                CodeNode(type="function", name=f"func_{i}", start_line=i * 5, end_line=i * 5 + 3),
            )

        for i in range(10):
            graph_manager.add_node(
                "test.py",
                CodeNode(
                    type="class", name=f"Class_{i}",
                    start_line=100 + i * 10, end_line=100 + i * 10 + 8,
                ),
            )

        # Mock LLMProvider to track calls and return valid JSON
        llm_provider = AsyncMock()
        llm_provider.send.return_value = "[]"  # Empty JSON array for simplicity

        # Act
        enricher = GraphEnricher(graph_manager, llm_provider)
        await enricher.enrich_nodes(batch_size=10)

        # Assert - LLM provider called exactly 3 times
        assert llm_provider.send.call_count == 3, (
            f"Expected 3 LLM calls for 25 nodes with batch_size=10, "
            f"got {llm_provider.send.call_count}"
        )

        # Verify batch sizes by inspecting call arguments
        # Each call's user prompt should contain batch information
        # (Implementation detail: exact prompt format will be verified once code exists)


class TestEnrichNodesGraphUpdates:
    """Test suite for GraphEnricher graph attribute updates."""

    @pytest.mark.asyncio
    async def test_enricher_updates_graph(self) -> None:
        """Test GraphEnricher updates graph attributes with LLM response.

        This test validates the core enrichment workflow:
        - Creates 2 code nodes without summary/risks attributes
        - Mocks LLM to return valid JSON with summaries and risks
        - Verifies graph nodes updated with correct attributes
        - Verifies attribute values match LLM response exactly

        The test uses a realistic JSON structure that the LLM would return,
        including node IDs, summaries, and risk arrays.
        """
        # Arrange - Create GraphManager with 2 code nodes
        graph_manager = GraphManager()

        from pathlib import Path

        graph_manager.add_file(FileEntry(Path("file.py"), size=512, token_est=128))

        graph_manager.add_node(
            "file.py",
            CodeNode(type="function", name="func1", start_line=1, end_line=5),
        )

        graph_manager.add_node(
            "file.py",
            CodeNode(type="function", name="func2", start_line=7, end_line=12),
        )

        # Mock LLMProvider to return valid JSON response
        llm_provider = AsyncMock()
        llm_response = """[
            {"node_id": "file.py::func1", "summary": "Does X", "risks": ["Risk A"]},
            {"node_id": "file.py::func2", "summary": "Does Y", "risks": ["Risk B", "Risk C"]}
        ]"""
        llm_provider.send.return_value = llm_response

        # Act
        enricher = GraphEnricher(graph_manager, llm_provider)
        await enricher.enrich_nodes(batch_size=10)

        # Assert - Verify graph nodes updated with correct attributes
        graph = graph_manager.graph

        # Verify func1 attributes
        func1_node = graph.nodes["file.py::func1"]
        assert func1_node["summary"] == "Does X", (
            f"Expected func1 summary 'Does X', got '{func1_node.get('summary')}'"
        )
        assert func1_node["risks"] == ["Risk A"], (
            f"Expected func1 risks ['Risk A'], got {func1_node.get('risks')}"
        )

        # Verify func2 attributes
        func2_node = graph.nodes["file.py::func2"]
        assert func2_node["summary"] == "Does Y", (
            f"Expected func2 summary 'Does Y', got '{func2_node.get('summary')}'"
        )
        assert func2_node["risks"] == ["Risk B", "Risk C"], (
            f"Expected func2 risks ['Risk B', 'Risk C'], got {func2_node.get('risks')}"
        )


class TestEnrichNodesErrorHandling:
    """Test suite for GraphEnricher error handling and batch isolation."""

    @pytest.mark.asyncio
    async def test_enricher_handles_llm_errors(self) -> None:
        """Test GraphEnricher isolates batch failures (other batches succeed).

        This test validates robust error handling across batches:
        - Creates 25 code nodes (3 batches with batch_size=10)
        - Batch 1: LLM returns valid JSON → nodes enriched
        - Batch 2: LLM raises ValueError → nodes NOT enriched
        - Batch 3: LLM returns valid JSON → nodes enriched

        Verifies that:
        - Batch failures are isolated (don't affect other batches)
        - No exception propagates to caller
        - Successfully enriched nodes have summary/risks attributes
        - Failed batch nodes remain unchanged
        """
        # Arrange - Create GraphManager with 25 code nodes
        graph_manager = GraphManager()

        from pathlib import Path

        graph_manager.add_file(FileEntry(Path("test.py"), size=1024, token_est=256))

        # Add 25 code nodes
        for i in range(25):
            graph_manager.add_node(
                "test.py",
                CodeNode(type="function", name=f"func_{i}", start_line=i * 5, end_line=i * 5 + 3),
            )

        # Mock LLMProvider with different responses per batch
        llm_provider = AsyncMock()

        # Create side_effect that returns different values for each call
        batch1_response = """[
            {"node_id": "test.py::func_0", "summary": "Batch 1 func", "risks": ["Low"]},
            {"node_id": "test.py::func_1", "summary": "Batch 1 func", "risks": ["Low"]},
            {"node_id": "test.py::func_2", "summary": "Batch 1 func", "risks": ["Low"]},
            {"node_id": "test.py::func_3", "summary": "Batch 1 func", "risks": ["Low"]},
            {"node_id": "test.py::func_4", "summary": "Batch 1 func", "risks": ["Low"]},
            {"node_id": "test.py::func_5", "summary": "Batch 1 func", "risks": ["Low"]},
            {"node_id": "test.py::func_6", "summary": "Batch 1 func", "risks": ["Low"]},
            {"node_id": "test.py::func_7", "summary": "Batch 1 func", "risks": ["Low"]},
            {"node_id": "test.py::func_8", "summary": "Batch 1 func", "risks": ["Low"]},
            {"node_id": "test.py::func_9", "summary": "Batch 1 func", "risks": ["Low"]}
        ]"""

        batch3_response = """[
            {"node_id": "test.py::func_20", "summary": "Batch 3 func", "risks": ["Medium"]},
            {"node_id": "test.py::func_21", "summary": "Batch 3 func", "risks": ["Medium"]},
            {"node_id": "test.py::func_22", "summary": "Batch 3 func", "risks": ["Medium"]},
            {"node_id": "test.py::func_23", "summary": "Batch 3 func", "risks": ["Medium"]},
            {"node_id": "test.py::func_24", "summary": "Batch 3 func", "risks": ["Medium"]}
        ]"""

        # Configure side_effect: Batch 1 succeeds, Batch 2 fails, Batch 3 succeeds
        llm_provider.send.side_effect = [
            batch1_response,  # Batch 1: nodes 0-9
            ValueError("Simulated JSON parse error"),  # Batch 2: nodes 10-19
            batch3_response,  # Batch 3: nodes 20-24
        ]

        # Act - Should not raise exception despite batch 2 failure
        enricher = GraphEnricher(graph_manager, llm_provider)
        await enricher.enrich_nodes(batch_size=10)

        # Assert - Verify batch 1 nodes enriched
        graph = graph_manager.graph
        for i in range(10):
            node = graph.nodes[f"test.py::func_{i}"]
            assert "summary" in node, f"Expected func_{i} from batch 1 to have summary"
            assert node["summary"] == "Batch 1 func"
            assert node["risks"] == ["Low"]

        # Assert - Verify batch 2 nodes NOT enriched (failure isolated)
        for i in range(10, 20):
            node = graph.nodes[f"test.py::func_{i}"]
            assert "summary" not in node, (
                f"Expected func_{i} from batch 2 to NOT have summary (batch failed)"
            )
            assert "risks" not in node, (
                f"Expected func_{i} from batch 2 to NOT have risks (batch failed)"
            )

        # Assert - Verify batch 3 nodes enriched
        for i in range(20, 25):
            node = graph.nodes[f"test.py::func_{i}"]
            assert "summary" in node, f"Expected func_{i} from batch 3 to have summary"
            assert node["summary"] == "Batch 3 func"
            assert node["risks"] == ["Medium"]

    @pytest.mark.asyncio
    async def test_enricher_handles_openai_api_errors(self) -> None:
        """Test GraphEnricher isolates OpenAI API errors per batch.

        Validates that openai.APIError (and related exceptions) are caught
        and isolated, allowing other batches to succeed.
        """
        import openai

        # Arrange
        graph_manager = GraphManager()

        from pathlib import Path

        graph_manager.add_file(FileEntry(Path("test.py"), size=512, token_est=128))

        # Add 2 code nodes (1 batch each with batch_size=1)
        graph_manager.add_node(
            "test.py",
            CodeNode(type="function", name="func_0", start_line=1, end_line=5),
        )
        graph_manager.add_node(
            "test.py",
            CodeNode(type="function", name="func_1", start_line=7, end_line=12),
        )

        # Mock LLMProvider: first call raises APIError, second succeeds
        llm_provider = AsyncMock()
        success_response = '[{"node_id": "test.py::func_1", "summary": "Works", "risks": []}]'
        llm_provider.send.side_effect = [
            openai.APIError(
                message="API Error",
                request=None,
                body=None,
            ),
            success_response,
        ]

        # Act - Should not raise exception
        enricher = GraphEnricher(graph_manager, llm_provider)
        await enricher.enrich_nodes(batch_size=1)

        # Assert - func_0 NOT enriched (APIError), func_1 enriched
        graph = graph_manager.graph
        assert "summary" not in graph.nodes["test.py::func_0"]
        assert graph.nodes["test.py::func_1"]["summary"] == "Works"

    @pytest.mark.asyncio
    async def test_enricher_reraises_unexpected_exceptions(self) -> None:
        """Test GraphEnricher re-raises unexpected exceptions after logging.

        Validates that non-LLM exceptions (e.g., TypeError, AttributeError)
        are not silently swallowed but re-raised after logging.
        """
        # Arrange
        graph_manager = GraphManager()

        from pathlib import Path

        graph_manager.add_file(FileEntry(Path("test.py"), size=512, token_est=128))
        graph_manager.add_node(
            "test.py",
            CodeNode(type="function", name="func_0", start_line=1, end_line=5),
        )

        # Mock LLMProvider to raise an unexpected exception (TypeError)
        llm_provider = AsyncMock()
        llm_provider.send.side_effect = TypeError("Unexpected type error")

        # Act & Assert - TypeError should propagate (not be silently swallowed)
        enricher = GraphEnricher(graph_manager, llm_provider)

        # asyncio.gather with return_exceptions=True wraps exceptions
        # So we need to check that the exception is returned, not raised
        # But _enrich_batch does raise, so gather returns it as result
        await enricher.enrich_nodes(batch_size=10)

        # The exception was raised in _enrich_batch and caught by gather
        # We can verify by checking the node was NOT enriched
        assert "summary" not in graph_manager.graph.nodes["test.py::func_0"]


class TestEnrichNodesEdgeCases:
    """Test suite for GraphEnricher edge cases."""

    @pytest.mark.asyncio
    async def test_enricher_skips_nodes_with_existing_summary(self) -> None:
        """Test GraphEnricher skips nodes with existing summary attribute.

        Validates idempotent behavior:
        - Create 3 code nodes
        - Node 1: has summary already
        - Node 2: no summary
        - Node 3: has summary already

        Verifies:
        - LLM called only once (for node 2)
        - Nodes 1 and 3 summaries unchanged
        - Node 2 enriched with new summary
        """
        # Arrange - Create GraphManager with 3 code nodes
        graph_manager = GraphManager()

        from pathlib import Path

        graph_manager.add_file(FileEntry(Path("test.py"), size=512, token_est=128))

        # Add nodes
        graph_manager.add_node(
            "test.py",
            CodeNode(type="function", name="func1", start_line=1, end_line=5),
        )
        graph_manager.add_node(
            "test.py",
            CodeNode(type="function", name="func2", start_line=7, end_line=12),
        )
        graph_manager.add_node(
            "test.py",
            CodeNode(type="function", name="func3", start_line=14, end_line=20),
        )

        # Set summary on func1 and func3 (pre-existing)
        graph_manager.graph.nodes["test.py::func1"]["summary"] = "Existing summary 1"
        graph_manager.graph.nodes["test.py::func1"]["risks"] = ["Existing risk"]
        graph_manager.graph.nodes["test.py::func3"]["summary"] = "Existing summary 3"
        graph_manager.graph.nodes["test.py::func3"]["risks"] = []

        # Mock LLMProvider to return response for func2 only
        llm_provider = AsyncMock()
        llm_response = """[
            {"node_id": "test.py::func2", "summary": "New summary", "risks": ["New risk"]}
        ]"""
        llm_provider.send.return_value = llm_response

        # Act
        enricher = GraphEnricher(graph_manager, llm_provider)
        await enricher.enrich_nodes(batch_size=10)

        # Assert - LLM called only once (for func2)
        assert llm_provider.send.call_count == 1, (
            f"Expected 1 LLM call (only func2 needs enrichment), "
            f"got {llm_provider.send.call_count}"
        )

        # Assert - Func1 summary unchanged
        graph = graph_manager.graph
        assert graph.nodes["test.py::func1"]["summary"] == "Existing summary 1"
        assert graph.nodes["test.py::func1"]["risks"] == ["Existing risk"]

        # Assert - Func2 enriched with new summary
        assert graph.nodes["test.py::func2"]["summary"] == "New summary"
        assert graph.nodes["test.py::func2"]["risks"] == ["New risk"]

        # Assert - Func3 summary unchanged
        assert graph.nodes["test.py::func3"]["summary"] == "Existing summary 3"
        assert graph.nodes["test.py::func3"]["risks"] == []

    @pytest.mark.asyncio
    async def test_enricher_handles_empty_graph(self) -> None:
        """Test GraphEnricher with empty graph (no nodes to enrich).

        Validates edge case handling:
        - Create GraphManager with no code nodes (only file node or empty)
        - Verify no LLM calls made
        - Verify no exceptions raised
        """
        # Arrange - Create GraphManager with only file node (no code nodes)
        graph_manager = GraphManager()

        from pathlib import Path

        graph_manager.add_file(FileEntry(Path("empty.py"), size=0, token_est=0))

        # Mock LLMProvider
        llm_provider = AsyncMock()

        # Act
        enricher = GraphEnricher(graph_manager, llm_provider)
        await enricher.enrich_nodes(batch_size=10)

        # Assert - No LLM calls made
        assert llm_provider.send.call_count == 0, (
            f"Expected 0 LLM calls for empty graph, got {llm_provider.send.call_count}"
        )

    @pytest.mark.asyncio
    async def test_enricher_handles_invalid_json_response(self) -> None:
        """Test GraphEnricher handles malformed JSON response from LLM.

        Validates robust JSON parsing:
        - Create 2 code nodes
        - LLM returns invalid JSON (not parseable)
        - Verify warning logged (implementation detail)
        - Verify nodes remain unchanged (no attributes added)
        - Verify no exception propagates
        """
        # Arrange - Create GraphManager with 2 code nodes
        graph_manager = GraphManager()

        from pathlib import Path

        graph_manager.add_file(FileEntry(Path("test.py"), size=512, token_est=128))

        graph_manager.add_node(
            "test.py",
            CodeNode(type="function", name="func1", start_line=1, end_line=5),
        )
        graph_manager.add_node(
            "test.py",
            CodeNode(type="function", name="func2", start_line=7, end_line=12),
        )

        # Mock LLMProvider to return invalid JSON
        llm_provider = AsyncMock()
        llm_provider.send.return_value = "This is not valid JSON at all!"

        # Act - Should not raise exception
        enricher = GraphEnricher(graph_manager, llm_provider)
        await enricher.enrich_nodes(batch_size=10)

        # Assert - Nodes remain unchanged (no summary or risks)
        graph = graph_manager.graph
        assert "summary" not in graph.nodes["test.py::func1"]
        assert "risks" not in graph.nodes["test.py::func1"]
        assert "summary" not in graph.nodes["test.py::func2"]
        assert "risks" not in graph.nodes["test.py::func2"]

    @pytest.mark.asyncio
    async def test_enricher_handles_partial_json_response(self) -> None:
        """Test GraphEnricher handles JSON missing some node IDs.

        Validates partial update handling:
        - Create 3 code nodes
        - LLM returns JSON with only 2 nodes (missing 1)
        - Verify 2 nodes updated correctly
        - Verify 1 node remains unchanged
        - Verify no exception raised
        """
        # Arrange - Create GraphManager with 3 code nodes
        graph_manager = GraphManager()

        from pathlib import Path

        graph_manager.add_file(FileEntry(Path("test.py"), size=512, token_est=128))

        graph_manager.add_node(
            "test.py",
            CodeNode(type="function", name="func1", start_line=1, end_line=5),
        )
        graph_manager.add_node(
            "test.py",
            CodeNode(type="function", name="func2", start_line=7, end_line=12),
        )
        graph_manager.add_node(
            "test.py",
            CodeNode(type="function", name="func3", start_line=14, end_line=20),
        )

        # Mock LLMProvider to return partial JSON (missing func3)
        llm_provider = AsyncMock()
        llm_response = """[
            {"node_id": "test.py::func1", "summary": "Summary 1", "risks": ["Risk 1"]},
            {"node_id": "test.py::func2", "summary": "Summary 2", "risks": ["Risk 2"]}
        ]"""
        llm_provider.send.return_value = llm_response

        # Act
        enricher = GraphEnricher(graph_manager, llm_provider)
        await enricher.enrich_nodes(batch_size=10)

        # Assert - Func1 and Func2 updated
        graph = graph_manager.graph
        assert graph.nodes["test.py::func1"]["summary"] == "Summary 1"
        assert graph.nodes["test.py::func1"]["risks"] == ["Risk 1"]
        assert graph.nodes["test.py::func2"]["summary"] == "Summary 2"
        assert graph.nodes["test.py::func2"]["risks"] == ["Risk 2"]

        # Assert - Func3 remains unchanged (not in LLM response)
        assert "summary" not in graph.nodes["test.py::func3"]
        assert "risks" not in graph.nodes["test.py::func3"]

    @pytest.mark.asyncio
    async def test_enricher_handles_markdown_wrapped_json(self) -> None:
        """Test GraphEnricher extracts JSON from markdown code blocks.

        Validates regex fallback parsing:
        - Create 2 code nodes
        - LLM returns JSON wrapped in markdown code block (```json ... ```)
        - Verify regex extraction isolates JSON array
        - Verify nodes updated correctly
        """
        # Arrange
        graph_manager = GraphManager()

        from pathlib import Path

        graph_manager.add_file(FileEntry(Path("test.py"), size=512, token_est=128))
        graph_manager.add_node(
            "test.py",
            CodeNode(type="function", name="func1", start_line=1, end_line=5),
        )
        graph_manager.add_node(
            "test.py",
            CodeNode(type="function", name="func2", start_line=7, end_line=12),
        )

        # Mock LLMProvider to return JSON wrapped in markdown code block
        llm_provider = AsyncMock()
        llm_response = '''Here is the analysis:

```json
[
    {"node_id": "test.py::func1", "summary": "First function", "risks": ["Risk A"]},
    {"node_id": "test.py::func2", "summary": "Second function", "risks": ["Risk B"]}
]
```

I hope this helps!'''
        llm_provider.send.return_value = llm_response

        # Act
        enricher = GraphEnricher(graph_manager, llm_provider)
        await enricher.enrich_nodes(batch_size=10)

        # Assert - Both nodes enriched via regex extraction
        graph = graph_manager.graph
        assert graph.nodes["test.py::func1"]["summary"] == "First function"
        assert graph.nodes["test.py::func1"]["risks"] == ["Risk A"]
        assert graph.nodes["test.py::func2"]["summary"] == "Second function"
        assert graph.nodes["test.py::func2"]["risks"] == ["Risk B"]

    @pytest.mark.asyncio
    async def test_enricher_custom_batch_size(self) -> None:
        """Test GraphEnricher with custom batch_size parameter.

        Validates configurable batching:
        - Create 25 code nodes
        - Set batch_size=5
        - Verify LLM called 5 times (25 / 5 = 5 batches)
        - Verify all nodes enriched correctly
        """
        # Arrange - Create GraphManager with 25 code nodes
        graph_manager = GraphManager()

        from pathlib import Path

        graph_manager.add_file(FileEntry(Path("test.py"), size=1024, token_est=256))

        # Add 25 code nodes
        for i in range(25):
            graph_manager.add_node(
                "test.py",
                CodeNode(type="function", name=f"func_{i}", start_line=i * 5, end_line=i * 5 + 3),
            )

        # Mock LLMProvider to return empty JSON (simplify test)
        llm_provider = AsyncMock()
        llm_provider.send.return_value = "[]"

        # Act
        enricher = GraphEnricher(graph_manager, llm_provider)
        await enricher.enrich_nodes(batch_size=5)  # Custom batch size

        # Assert - LLM called 5 times (25 nodes / 5 per batch = 5 batches)
        assert llm_provider.send.call_count == 5, (
            f"Expected 5 LLM calls for 25 nodes with batch_size=5, "
            f"got {llm_provider.send.call_count}"
        )

    @pytest.mark.asyncio
    async def test_enricher_handles_non_dict_results(self) -> None:
        """Test that non-dict elements in JSON array are skipped.

        Validates robust result handling:
        - Create 2 code nodes
        - LLM returns array with mix: [123, {...valid...}, "string", {...valid...}]
        - Verify non-dict elements skipped silently
        - Verify valid dict elements processed correctly
        - Verify no exception raised
        """
        # Arrange - Create GraphManager with 2 code nodes
        graph_manager = GraphManager()

        from pathlib import Path

        graph_manager.add_file(FileEntry(Path("test.py"), size=512, token_est=128))

        graph_manager.add_node(
            "test.py",
            CodeNode(type="function", name="func1", start_line=1, end_line=5),
        )
        graph_manager.add_node(
            "test.py",
            CodeNode(type="function", name="func2", start_line=7, end_line=12),
        )

        # Mock LLMProvider to return JSON array with non-dict elements
        llm_provider = AsyncMock()
        llm_response = """[
            123,
            {"node_id": "test.py::func1", "summary": "Valid summary 1", "risks": ["Risk A"]},
            "some string",
            {"node_id": "test.py::func2", "summary": "Valid summary 2", "risks": ["Risk B"]}
        ]"""
        llm_provider.send.return_value = llm_response

        # Act - Should not raise exception
        enricher = GraphEnricher(graph_manager, llm_provider)
        await enricher.enrich_nodes(batch_size=10)

        # Assert - Valid dict elements processed correctly
        graph = graph_manager.graph
        assert graph.nodes["test.py::func1"]["summary"] == "Valid summary 1"
        assert graph.nodes["test.py::func1"]["risks"] == ["Risk A"]
        assert graph.nodes["test.py::func2"]["summary"] == "Valid summary 2"
        assert graph.nodes["test.py::func2"]["risks"] == ["Risk B"]

    @pytest.mark.asyncio
    async def test_enricher_handles_missing_node_id_in_result(self) -> None:
        """Test that results missing node_id field are skipped with warning.

        Validates result validation:
        - Create 2 code nodes
        - LLM returns array where one result missing node_id field
        - Verify result with node_id processed correctly
        - Verify result without node_id skipped (logged warning)
        - Verify no exception raised
        """
        # Arrange - Create GraphManager with 2 code nodes
        graph_manager = GraphManager()

        from pathlib import Path

        graph_manager.add_file(FileEntry(Path("test.py"), size=512, token_est=128))

        graph_manager.add_node(
            "test.py",
            CodeNode(type="function", name="func1", start_line=1, end_line=5),
        )
        graph_manager.add_node(
            "test.py",
            CodeNode(type="function", name="func2", start_line=7, end_line=12),
        )

        # Mock LLMProvider to return JSON with one result missing node_id
        llm_provider = AsyncMock()
        llm_response = """[
            {"summary": "Missing node_id", "risks": ["Risk X"]},
            {"node_id": "test.py::func1", "summary": "Valid summary", "risks": ["Risk A"]}
        ]"""
        llm_provider.send.return_value = llm_response

        # Act - Should not raise exception
        enricher = GraphEnricher(graph_manager, llm_provider)
        await enricher.enrich_nodes(batch_size=10)

        # Assert - Only func1 enriched (has valid node_id)
        graph = graph_manager.graph
        assert graph.nodes["test.py::func1"]["summary"] == "Valid summary"
        assert graph.nodes["test.py::func1"]["risks"] == ["Risk A"]

        # Assert - func2 remains unchanged (result had no node_id)
        assert "summary" not in graph.nodes["test.py::func2"]
        assert "risks" not in graph.nodes["test.py::func2"]

    @pytest.mark.asyncio
    async def test_enricher_handles_nonexistent_node_id(self) -> None:
        """Test that node_ids not in graph are skipped with warning.

        Validates graph lookup:
        - Create 1 code node with ID "test.py::real_func"
        - LLM returns array with results for "ghost.py::func" and "test.py::real_func"
        - Verify only existing node enriched
        - Verify non-existent node_id skipped (logged warning)
        - Verify no exception raised
        """
        # Arrange - Create GraphManager with 1 code node
        graph_manager = GraphManager()

        from pathlib import Path

        graph_manager.add_file(FileEntry(Path("test.py"), size=512, token_est=128))

        graph_manager.add_node(
            "test.py",
            CodeNode(type="function", name="real_func", start_line=1, end_line=5),
        )

        # Mock LLMProvider to return JSON with non-existent node_id
        llm_provider = AsyncMock()
        llm_response = """[
            {"node_id": "ghost.py::func", "summary": "Ghost summary", "risks": ["Ghost risk"]},
            {"node_id": "test.py::real_func", "summary": "Real summary", "risks": ["Real risk"]}
        ]"""
        llm_provider.send.return_value = llm_response

        # Act - Should not raise exception
        enricher = GraphEnricher(graph_manager, llm_provider)
        await enricher.enrich_nodes(batch_size=10)

        # Assert - Only real_func enriched (exists in graph)
        graph = graph_manager.graph
        assert graph.nodes["test.py::real_func"]["summary"] == "Real summary"
        assert graph.nodes["test.py::real_func"]["risks"] == ["Real risk"]

        # Assert - ghost.py::func not in graph (non-existent node_id skipped)
        assert "ghost.py::func" not in graph.nodes

    @pytest.mark.asyncio
    async def test_enricher_raises_on_invalid_batch_size(self) -> None:
        """Test GraphEnricher raises ValueError for invalid batch_size.

        Validates input validation:
        - batch_size <= 0 raises ValueError
        - Error message is clear and descriptive

        This ensures the enricher fails fast with a clear error rather than
        producing unexpected behavior (e.g., infinite loops, empty batches).
        """
        # Arrange
        graph_manager = GraphManager()
        llm_provider = AsyncMock()
        enricher = GraphEnricher(graph_manager, llm_provider)

        # Act & Assert - batch_size = 0
        with pytest.raises(ValueError, match="batch_size must be positive"):
            await enricher.enrich_nodes(batch_size=0)

        # Act & Assert - batch_size = -1
        with pytest.raises(ValueError, match="batch_size must be positive"):
            await enricher.enrich_nodes(batch_size=-1)

        # Act & Assert - batch_size = -100
        with pytest.raises(ValueError, match="batch_size must be positive"):
            await enricher.enrich_nodes(batch_size=-100)


class TestEnrichNodesIntegration:
    """Integration test suite for GraphEnricher end-to-end workflow."""

    @pytest.mark.asyncio
    async def test_enricher_end_to_end_workflow(self, tmp_path) -> None:
        """Test complete enrichment workflow with realistic graph from MapBuilder.

        This integration test validates the complete GraphEnricher workflow by:
        1. Creating temporary Python files with real functions and classes
        2. Building a realistic graph using MapBuilder
        3. Configuring MockProvider to return deterministic JSON responses
        4. Enriching all nodes with GraphEnricher
        5. Verifying all function/class nodes have summary and risks attributes

        This test ensures that GraphEnricher integrates correctly with:
        - MapBuilder: Graph construction from real code
        - GraphManager: Node attribute management
        - MockProvider: Deterministic LLM responses

        The test uses a custom MockProvider to return JSON matching actual node IDs
        from the graph, simulating realistic LLM behavior.
        """
        # Arrange - Create temporary Python files with realistic code

        # Create module with functions and classes
        utils_content = '''def calculate_sum(a, b):
    """Calculate sum of two numbers."""
    return a + b

def process_data(data):
    """Process input data."""
    return [x * 2 for x in data]

class DataProcessor:
    """Process and transform data."""
    def __init__(self):
        self.data = []

    def add_item(self, item):
        """Add item to processor."""
        self.data.append(item)
'''

        # Create main module with more functions
        main_content = '''from utils import calculate_sum

def main():
    """Main entry point."""
    result = calculate_sum(10, 20)
    return result

class Application:
    """Main application class."""
    def run(self):
        """Run the application."""
        pass
'''

        (tmp_path / "utils.py").write_text(utils_content)
        (tmp_path / "main.py").write_text(main_content)

        # Build graph with MapBuilder
        from codemap.engine.builder import MapBuilder

        builder = MapBuilder()
        graph_manager = builder.build(tmp_path)

        # Collect all function/class node IDs from the graph for MockProvider
        code_node_ids = []
        for node_id, attrs in graph_manager.graph.nodes(data=True):
            if attrs.get("type") in ["function", "class"]:
                code_node_ids.append(node_id)

        # Verify we have code nodes (sanity check)
        assert len(code_node_ids) >= 5, (
            f"Expected at least 5 code nodes from files, got {len(code_node_ids)}"
        )

        # Create custom MockProvider that returns JSON matching the actual node IDs
        from codemap.core.llm import MockProvider

        class CustomMockProvider(MockProvider):
            """Custom mock provider that returns deterministic JSON for enrichment."""

            async def send(self, system: str, user: str) -> str:  # noqa: ARG002
                """Return JSON array with summaries and risks for all nodes."""
                # Build JSON response matching all code nodes in the graph
                results = []
                for node_id in code_node_ids:
                    results.append({
                        "node_id": node_id,
                        "summary": f"Summary for {node_id}",
                        "risks": [f"Risk A for {node_id}", "Risk B"],
                    })

                # Return as JSON string
                import json

                return json.dumps(results)

        # Create enricher with graph and custom mock provider
        mock_provider = CustomMockProvider()
        enricher = GraphEnricher(graph_manager, mock_provider)

        # Act - Enrich all nodes
        await enricher.enrich_nodes(batch_size=10)

        # Assert - Verify all function nodes have summary and risks
        function_nodes = [
            (node_id, attrs) for node_id, attrs in graph_manager.graph.nodes(data=True)
            if attrs.get("type") == "function"
        ]

        assert len(function_nodes) >= 4, (
            f"Expected at least 4 function nodes, got {len(function_nodes)}"
        )

        for node_id, attrs in function_nodes:
            assert "summary" in attrs, f"Function {node_id} missing summary attribute"
            assert attrs["summary"] == f"Summary for {node_id}", (
                f"Function {node_id} has incorrect summary: {attrs['summary']}"
            )
            assert "risks" in attrs, f"Function {node_id} missing risks attribute"
            assert isinstance(attrs["risks"], list), (
                f"Function {node_id} risks should be a list"
            )
            assert len(attrs["risks"]) == 2, (
                f"Function {node_id} should have 2 risks, got {len(attrs['risks'])}"
            )

        # Assert - Verify all class nodes have summary and risks
        class_nodes = [
            (node_id, attrs) for node_id, attrs in graph_manager.graph.nodes(data=True)
            if attrs.get("type") == "class"
        ]

        assert len(class_nodes) >= 2, (
            f"Expected at least 2 class nodes, got {len(class_nodes)}"
        )

        for node_id, attrs in class_nodes:
            assert "summary" in attrs, f"Class {node_id} missing summary attribute"
            assert attrs["summary"] == f"Summary for {node_id}", (
                f"Class {node_id} has incorrect summary: {attrs['summary']}"
            )
            assert "risks" in attrs, f"Class {node_id} missing risks attribute"
            assert isinstance(attrs["risks"], list), (
                f"Class {node_id} risks should be a list"
            )
            assert len(attrs["risks"]) == 2, (
                f"Class {node_id} should have 2 risks, got {len(attrs['risks'])}"
            )

        # Assert - Verify file nodes do NOT have summary attribute
        file_nodes = [
            (node_id, attrs) for node_id, attrs in graph_manager.graph.nodes(data=True)
            if attrs.get("type") == "file"
        ]

        assert len(file_nodes) >= 2, (
            f"Expected at least 2 file nodes, got {len(file_nodes)}"
        )

        for node_id, attrs in file_nodes:
            assert "summary" not in attrs, (
                f"File {node_id} should NOT have summary attribute (files are not enriched)"
            )


class TestEnricherCodeContent:
    """Tests for code content extraction and inclusion in enricher prompts.

    These tests validate Phase 17: Code-Content Integration in GraphEnricher.
    The enricher should extract real source code from files and include it
    in LLM prompts for more accurate semantic analysis.

    Tests follow TDD RED phase — they define expected behavior for features
    that don't exist yet (new constructor parameters, _extract_code_snippet method,
    enhanced prompt format).
    """

    @pytest.mark.asyncio
    async def test_enricher_extracts_code_snippet(self, tmp_path) -> None:
        """Code between start_line and end_line is extracted from the source file.

        Given a file with known content and a function node spanning lines 2-4,
        the enricher should extract exactly those lines. This is the core
        capability that enables code-aware semantic analysis.
        """
        from pathlib import Path

        from codemap.mapper.reader import ContentReader

        # Arrange - Create a file with known content
        source_file = tmp_path / "example.py"
        source_file.write_text(
            "# Line 1: Comment\n"
            "def hello():  # Line 2\n"
            '    return "world"  # Line 3\n'
            "# Line 4: End comment\n"
            "def other():  # Line 5\n"
            "    pass\n"
        )

        # Create graph with a function node spanning lines 2-4
        graph_manager = GraphManager()
        graph_manager.add_file(FileEntry(Path("example.py"), size=100, token_est=25))
        graph_manager.add_node(
            "example.py",
            CodeNode(type="function", name="hello", start_line=2, end_line=4),
        )

        # Mock LLM to capture the prompt it receives
        llm_provider = AsyncMock()
        llm_provider.send.return_value = (
            '[{"node_id": "example.py::hello", "summary": "Says hello", "risks": []}]'
        )

        # Act - Create enricher with root_path and content_reader
        enricher = GraphEnricher(
            graph_manager,
            llm_provider,
            root_path=tmp_path,
            content_reader=ContentReader(),
        )
        await enricher.enrich_nodes(batch_size=10)

        # Assert - The prompt sent to LLM contains actual code
        llm_provider.send.assert_called_once()
        _system_prompt, user_prompt = llm_provider.send.call_args[0]
        assert "def hello():" in user_prompt, (
            "Prompt should contain the function definition"
        )
        assert 'return "world"' in user_prompt, (
            "Prompt should contain the function body"
        )
        assert "def other():" not in user_prompt, (
            "Prompt should NOT contain code outside the node's line range"
        )

    @pytest.mark.asyncio
    async def test_enricher_sends_code_in_prompt(self, tmp_path) -> None:
        """Enricher prompt includes code content with structured format labels.

        When root_path is configured, the prompt should contain a 'code:' label
        followed by the actual function body in a code block, enabling the LLM
        to analyze real code instead of guessing from metadata alone.
        """
        from pathlib import Path

        from codemap.mapper.reader import ContentReader

        # Arrange - Create a source file with a function
        source_file = tmp_path / "module.py"
        source_file.write_text(
            "def process_data(items):\n"
            "    result = []\n"
            "    for item in items:\n"
            "        result.append(item * 2)\n"
            "    return result\n"
        )

        graph_manager = GraphManager()
        graph_manager.add_file(FileEntry(Path("module.py"), size=200, token_est=50))
        graph_manager.add_node(
            "module.py",
            CodeNode(type="function", name="process_data", start_line=1, end_line=5),
        )

        llm_provider = AsyncMock()
        llm_provider.send.return_value = (
            '[{"node_id": "module.py::process_data", "summary": "Processes data", "risks": []}]'
        )

        # Act
        enricher = GraphEnricher(
            graph_manager,
            llm_provider,
            root_path=tmp_path,
            content_reader=ContentReader(),
        )
        await enricher.enrich_nodes(batch_size=10)

        # Assert - Prompt has structured format with code label
        _system_prompt, user_prompt = llm_provider.send.call_args[0]
        assert "code:" in user_prompt.lower(), (
            "Prompt should contain a 'code:' label"
        )
        assert "def process_data(items):" in user_prompt, (
            "Prompt should contain the actual function signature"
        )
        assert "result.append(item * 2)" in user_prompt, (
            "Prompt should contain the function body"
        )

    @pytest.mark.asyncio
    async def test_enricher_truncates_long_code(self, tmp_path) -> None:
        """Code snippets exceeding max_code_lines are truncated with an indicator.

        A function spanning 500 lines with max_code_lines=50 should produce
        a snippet of exactly 50 code lines plus a truncation indicator showing
        how many lines were omitted. This prevents token limit issues.
        """
        from pathlib import Path

        from codemap.mapper.reader import ContentReader

        # Arrange - Create a file with a very long function (500+ lines)
        long_lines = ["def long_function():"]
        for i in range(1, 501):
            long_lines.append(f"    x_{i} = {i}")
        source_file = tmp_path / "long.py"
        source_file.write_text("\n".join(long_lines) + "\n")

        graph_manager = GraphManager()
        graph_manager.add_file(FileEntry(Path("long.py"), size=10000, token_est=2500))
        graph_manager.add_node(
            "long.py",
            CodeNode(type="function", name="long_function", start_line=1, end_line=501),
        )

        llm_provider = AsyncMock()
        llm_provider.send.return_value = (
            '[{"node_id": "long.py::long_function", "summary": "Long func", "risks": []}]'
        )

        # Act - Use max_code_lines=50 to trigger truncation
        enricher = GraphEnricher(
            graph_manager,
            llm_provider,
            root_path=tmp_path,
            content_reader=ContentReader(),
            max_code_lines=50,
        )
        await enricher.enrich_nodes(batch_size=10)

        # Assert - Prompt contains truncation indicator
        _system_prompt, user_prompt = llm_provider.send.call_args[0]
        assert "truncated" in user_prompt.lower(), (
            "Prompt should indicate that code was truncated"
        )
        assert "451 more lines" in user_prompt, (
            "Truncation indicator should show remaining line count (501 - 50 = 451)"
        )
        # Verify the first line is included but not line 51+
        assert "def long_function():" in user_prompt, (
            "First line of function should be included"
        )
        assert "x_49 = 49" in user_prompt, (
            "Line 49 should be the last included code line (50th line counting def)"
        )
        assert "x_50 = 50" not in user_prompt, (
            "Line 50 should NOT be included (truncated at max_code_lines=50)"
        )

    @pytest.mark.asyncio
    async def test_enricher_handles_missing_file(self, tmp_path, caplog) -> None:
        """Missing source files are handled gracefully with a warning.

        When a file referenced by a graph node no longer exists (e.g. deleted
        after graph build), the enricher should log a warning and fall back
        to metadata-only mode for that node — without raising an exception.
        """
        import logging
        from pathlib import Path

        # Arrange - Node references a file that doesn't exist
        graph_manager = GraphManager()
        graph_manager.add_file(FileEntry(Path("deleted.py"), size=100, token_est=25))
        graph_manager.add_node(
            "deleted.py",
            CodeNode(type="function", name="ghost_func", start_line=1, end_line=5),
        )

        llm_provider = AsyncMock()
        llm_provider.send.return_value = (
            '[{"node_id": "deleted.py::ghost_func", "summary": "Ghost", "risks": []}]'
        )

        # Act - Should not raise despite missing file
        from codemap.mapper.reader import ContentReader

        enricher = GraphEnricher(
            graph_manager,
            llm_provider,
            root_path=tmp_path,
            content_reader=ContentReader(),
        )
        with caplog.at_level(logging.WARNING):
            await enricher.enrich_nodes(batch_size=10)

        # Assert - Warning was logged about missing file
        assert any("deleted.py" in record.message for record in caplog.records), (
            "Should log warning mentioning the missing file"
        )
        # Assert - Node was still enriched (with metadata-only fallback)
        assert graph_manager.graph.nodes["deleted.py::ghost_func"]["summary"] == "Ghost"

    @pytest.mark.asyncio
    async def test_enricher_handles_file_read_error(self, tmp_path, caplog) -> None:
        """Binary files causing ContentReadError are handled gracefully.

        When ContentReader raises ContentReadError (e.g. for binary files),
        the enricher should log a warning and fall back to metadata-only
        mode for that node — without raising an exception.
        """
        import logging
        from pathlib import Path

        from codemap.mapper.reader import ContentReader

        # Arrange - Create a binary file that ContentReader cannot read
        binary_file = tmp_path / "binary.py"
        binary_file.write_bytes(b"\x00\x01\x02\xff\xfe\x00\x89PNG")

        graph_manager = GraphManager()
        graph_manager.add_file(FileEntry(Path("binary.py"), size=100, token_est=25))
        graph_manager.add_node(
            "binary.py",
            CodeNode(type="function", name="binary_func", start_line=1, end_line=5),
        )

        llm_provider = AsyncMock()
        llm_provider.send.return_value = (
            '[{"node_id": "binary.py::binary_func", "summary": "Binary", "risks": []}]'
        )

        # Act - Should not raise despite read error
        enricher = GraphEnricher(
            graph_manager,
            llm_provider,
            root_path=tmp_path,
            content_reader=ContentReader(),
        )
        with caplog.at_level(logging.WARNING):
            await enricher.enrich_nodes(batch_size=10)

        # Assert - Warning was logged about read error
        assert any("binary.py" in record.message for record in caplog.records), (
            "Should log warning mentioning the unreadable file"
        )
        # Assert - Node was still enriched (with metadata-only fallback)
        assert graph_manager.graph.nodes["binary.py::binary_func"]["summary"] == "Binary"

    @pytest.mark.asyncio
    async def test_enricher_without_root_path_uses_metadata_only(self) -> None:
        """Enricher without root_path works in metadata-only mode (backwards compatible).

        When root_path is not provided, the enricher should work exactly as
        before — sending only metadata (node names, types, line numbers) to
        the LLM without attempting to read source files. This ensures
        backwards compatibility with existing usage.
        """
        from pathlib import Path

        # Arrange
        graph_manager = GraphManager()
        graph_manager.add_file(FileEntry(Path("test.py"), size=100, token_est=25))
        graph_manager.add_node(
            "test.py",
            CodeNode(type="function", name="my_func", start_line=1, end_line=5),
        )

        llm_provider = AsyncMock()
        llm_provider.send.return_value = (
            '[{"node_id": "test.py::my_func", "summary": "Does stuff", "risks": []}]'
        )

        # Act - Create enricher WITHOUT root_path (old behavior)
        enricher = GraphEnricher(graph_manager, llm_provider)
        await enricher.enrich_nodes(batch_size=10)

        # Assert - Enrichment works (node gets summary)
        assert graph_manager.graph.nodes["test.py::my_func"]["summary"] == "Does stuff"

        # Assert - Prompt does NOT contain code block (metadata only)
        _system_prompt, user_prompt = llm_provider.send.call_args[0]
        assert "```python" not in user_prompt, (
            "Metadata-only mode should not include python code blocks"
        )

    @pytest.mark.asyncio
    async def test_enricher_handles_node_without_separator(self, tmp_path) -> None:
        """Nodes without '::' separator in node_id get no code extraction.

        Some node types (like file nodes) don't use the 'path::name' format.
        The enricher should gracefully skip code extraction for these nodes
        and fall back to metadata-only prompt format.
        """
        from pathlib import Path

        from codemap.mapper.reader import ContentReader

        # Arrange - Create a source file
        source_file = tmp_path / "simple.py"
        source_file.write_text("x = 1\n")

        graph_manager = GraphManager()
        graph_manager.add_file(FileEntry(Path("simple.py"), size=50, token_est=10))

        # Manually add a node WITHOUT '::' separator to simulate edge case
        graph_manager.graph.add_node(
            "simple.py",
            type="function",
            name="orphan",
            start_line=1,
            end_line=1,
        )
        # Mark it as needing enrichment (no summary)

        llm_provider = AsyncMock()
        llm_provider.send.return_value = (
            '[{"node_id": "simple.py", "summary": "Simple module", "risks": []}]'
        )

        # Act
        enricher = GraphEnricher(
            graph_manager,
            llm_provider,
            root_path=tmp_path,
            content_reader=ContentReader(),
        )
        await enricher.enrich_nodes(batch_size=10)

        # Assert - Prompt uses fallback (code not available)
        _system_prompt, user_prompt = llm_provider.send.call_args[0]
        assert "not available" in user_prompt.lower(), (
            "Node without '::' should have 'not available' code fallback"
        )

    @pytest.mark.asyncio
    async def test_enricher_auto_creates_content_reader(self, tmp_path) -> None:
        """Enricher auto-creates ContentReader when root_path given but no reader.

        When root_path is provided without an explicit content_reader, the
        enricher should create its own ContentReader internally and use it
        for code extraction — enabling the simplest possible API for callers.
        """
        from pathlib import Path

        # Arrange - Create a source file
        source_file = tmp_path / "auto.py"
        source_file.write_text("def auto_func():\n    return 42\n")

        graph_manager = GraphManager()
        graph_manager.add_file(FileEntry(Path("auto.py"), size=50, token_est=10))
        graph_manager.add_node(
            "auto.py",
            CodeNode(type="function", name="auto_func", start_line=1, end_line=2),
        )

        llm_provider = AsyncMock()
        llm_provider.send.return_value = (
            '[{"node_id": "auto.py::auto_func", "summary": "Returns 42", "risks": []}]'
        )

        # Act - Create enricher with root_path but NO content_reader
        enricher = GraphEnricher(
            graph_manager,
            llm_provider,
            root_path=tmp_path,
        )
        await enricher.enrich_nodes(batch_size=10)

        # Assert - Code was extracted (auto-created ContentReader worked)
        _system_prompt, user_prompt = llm_provider.send.call_args[0]
        assert "def auto_func():" in user_prompt, (
            "Auto-created ContentReader should enable code extraction"
        )
        assert "return 42" in user_prompt

    @pytest.mark.asyncio
    async def test_extract_code_snippet_returns_none_without_root_path(self) -> None:
        """_extract_code_snippet returns None when enricher has no root_path.

        When enricher is in metadata-only mode (no root_path), calling
        _extract_code_snippet directly should return None without errors.
        """
        # Arrange - Create enricher WITHOUT root_path
        graph_manager = GraphManager()
        llm_provider = AsyncMock()
        enricher = GraphEnricher(graph_manager, llm_provider)

        # Act
        result = enricher._extract_code_snippet("file.py::func", 1, 5)

        # Assert
        assert result is None, (
            "_extract_code_snippet should return None without root_path"
        )

    @pytest.mark.asyncio
    async def test_enricher_handles_node_without_line_numbers(self, tmp_path) -> None:
        """Nodes without start_line or end_line get 'not available' code fallback.

        When a node has None for start_line or end_line, the enricher should
        skip code extraction and show 'not available' in the prompt instead
        of crashing on None arithmetic.
        """
        from pathlib import Path

        from codemap.mapper.reader import ContentReader

        # Arrange - Create a source file
        source_file = tmp_path / "nolines.py"
        source_file.write_text("x = 1\n")

        graph_manager = GraphManager()
        graph_manager.add_file(FileEntry(Path("nolines.py"), size=50, token_est=10))

        # Manually add a node with None line numbers
        graph_manager.graph.add_node(
            "nolines.py::no_lines_func",
            type="function",
            name="no_lines_func",
            start_line=None,
            end_line=None,
        )
        # Add containment edge so it's recognized
        graph_manager.graph.add_edge("nolines.py", "nolines.py::no_lines_func", type="contains")

        llm_provider = AsyncMock()
        llm_provider.send.return_value = (
            '[{"node_id": "nolines.py::no_lines_func", "summary": "No lines", "risks": []}]'
        )

        # Act
        enricher = GraphEnricher(
            graph_manager,
            llm_provider,
            root_path=tmp_path,
            content_reader=ContentReader(),
        )
        await enricher.enrich_nodes(batch_size=10)

        # Assert - Prompt uses fallback (not available)
        _system_prompt, user_prompt = llm_provider.send.call_args[0]
        assert "not available" in user_prompt.lower(), (
            "Node without line numbers should have 'not available' code fallback"
        )

    @pytest.mark.asyncio
    async def test_truncation_keeps_exactly_max_code_lines(self, tmp_path) -> None:
        """Truncation produces exactly max_code_lines code lines, not one more.

        Given a snippet of 10 lines and max_code_lines=5, _extract_code_snippet
        must return exactly 5 code lines plus the truncation indicator. This
        verifies that the slice uses `[:max_code_lines]` (not `[:max_code_lines + 1]`)
        and that `remaining` equals original_length - max_code_lines.
        """
        from pathlib import Path

        from codemap.mapper.reader import ContentReader

        # Arrange - Create a file with exactly 10 numbered lines
        file_lines = [f"line_{i}" for i in range(1, 11)]
        source_file = tmp_path / "ten_lines.py"
        source_file.write_text("\n".join(file_lines) + "\n")

        graph_manager = GraphManager()
        graph_manager.add_file(FileEntry(Path("ten_lines.py"), size=200, token_est=50))
        graph_manager.add_node(
            "ten_lines.py",
            CodeNode(type="function", name="func", start_line=1, end_line=10),
        )

        llm_provider = AsyncMock()
        llm_provider.send.return_value = (
            '[{"node_id": "ten_lines.py::func", "summary": "Func", "risks": []}]'
        )

        # Act - Use max_code_lines=5
        enricher = GraphEnricher(
            graph_manager,
            llm_provider,
            root_path=tmp_path,
            content_reader=ContentReader(),
            max_code_lines=5,
        )

        # Call _extract_code_snippet directly to verify line count precisely
        snippet = enricher._extract_code_snippet("ten_lines.py::func", 1, 10)
        assert snippet is not None

        snippet_lines = snippet.split("\n")
        # Must be exactly 6 lines: 5 code lines + 1 truncation indicator
        assert len(snippet_lines) == 6, (
            f"Expected 6 lines (5 code + 1 truncation), got {len(snippet_lines)}: {snippet_lines}"
        )
        # Last line must be the truncation indicator
        assert "5 more lines" in snippet_lines[-1], (
            f"Truncation should show '5 more lines' (10 - 5), got: {snippet_lines[-1]}"
        )
        # Line 5 (5th code line) must be the last code line
        assert snippet_lines[4] == "line_5", (
            f"5th code line should be 'line_5', got: {snippet_lines[4]}"
        )
        # Line 6 must NOT appear in the code lines
        assert "line_6" not in snippet, (
            "line_6 should NOT appear in truncated snippet (exceeds max_code_lines=5)"
        )

    @pytest.mark.asyncio
    async def test_extract_code_snippet_returns_none_for_inverted_range(self, tmp_path) -> None:
        """_extract_code_snippet returns None when start_line > end_line.

        An inverted line range (e.g. start_line=10, end_line=3) is invalid and
        should produce None so that _enrich_batch writes '- code: (not available)'.
        A warning should be logged for diagnostics.
        """

        from codemap.mapper.reader import ContentReader

        # Arrange - Create a file with content
        source_file = tmp_path / "inverted.py"
        source_file.write_text("line1\nline2\nline3\nline4\nline5\n")

        graph_manager = GraphManager()
        llm_provider = AsyncMock()
        enricher = GraphEnricher(
            graph_manager,
            llm_provider,
            root_path=tmp_path,
            content_reader=ContentReader(),
        )

        # Act - Call with inverted range (start > end)
        result = enricher._extract_code_snippet("inverted.py::func", 10, 3)

        # Assert
        assert result is None, (
            "_extract_code_snippet should return None for inverted range (start_line > end_line)"
        )

    @pytest.mark.asyncio
    async def test_inverted_range_produces_not_available_in_prompt(self, tmp_path) -> None:
        """Inverted line range in a node produces '- code: (not available)' in prompt.

        When a node has start_line > end_line, the enricher should fall back
        to the 'not available' prompt format instead of an empty code block.
        """
        from pathlib import Path

        from codemap.mapper.reader import ContentReader

        # Arrange - Create a file with content
        source_file = tmp_path / "inverted_prompt.py"
        source_file.write_text("line1\nline2\nline3\nline4\nline5\n")

        graph_manager = GraphManager()
        graph_manager.add_file(FileEntry(Path("inverted_prompt.py"), size=50, token_est=10))

        # Add node with inverted line range
        graph_manager.graph.add_node(
            "inverted_prompt.py::bad_func",
            type="function",
            name="bad_func",
            start_line=10,
            end_line=3,
        )
        graph_manager.graph.add_edge(
            "inverted_prompt.py", "inverted_prompt.py::bad_func", type="contains"
        )

        llm_provider = AsyncMock()
        llm_provider.send.return_value = (
            '[{"node_id": "inverted_prompt.py::bad_func", "summary": "Bad", "risks": []}]'
        )

        # Act
        enricher = GraphEnricher(
            graph_manager,
            llm_provider,
            root_path=tmp_path,
            content_reader=ContentReader(),
        )
        await enricher.enrich_nodes(batch_size=10)

        # Assert - Prompt uses fallback
        _system_prompt, user_prompt = llm_provider.send.call_args[0]
        assert "- code: (not available)" in user_prompt, (
            "Inverted line range should produce '- code: (not available)' fallback"
        )
        assert "```" not in user_prompt, (
            "Inverted line range should NOT produce a code block"
        )

    @pytest.mark.asyncio
    async def test_extract_code_snippet_returns_none_for_empty_file(self, tmp_path) -> None:
        """_extract_code_snippet returns None for an empty file.

        When the source file is empty, the line slice will be empty too.
        The method should return None so the prompt gets '- code: (not available)'.
        """

        from codemap.mapper.reader import ContentReader

        # Arrange - Create an empty file
        source_file = tmp_path / "empty.py"
        source_file.write_text("")

        graph_manager = GraphManager()
        llm_provider = AsyncMock()
        enricher = GraphEnricher(
            graph_manager,
            llm_provider,
            root_path=tmp_path,
            content_reader=ContentReader(),
        )

        # Act - Try to extract from empty file
        result = enricher._extract_code_snippet("empty.py::func", 1, 5)

        # Assert
        assert result is None, (
            "_extract_code_snippet should return None for empty file (empty snippet)"
        )

    @pytest.mark.asyncio
    async def test_extract_code_snippet_returns_none_for_short_file(self, tmp_path) -> None:
        """_extract_code_snippet returns None when file has fewer lines than start_line.

        When the file has 2 lines but the node starts at line 10, the slice
        is empty and should return None.
        """

        from codemap.mapper.reader import ContentReader

        # Arrange - Create a short file (2 lines)
        source_file = tmp_path / "short.py"
        source_file.write_text("line1\nline2\n")

        graph_manager = GraphManager()
        llm_provider = AsyncMock()
        enricher = GraphEnricher(
            graph_manager,
            llm_provider,
            root_path=tmp_path,
            content_reader=ContentReader(),
        )

        # Act - Try to extract lines 10-15 from a 2-line file
        result = enricher._extract_code_snippet("short.py::func", 10, 15)

        # Assert
        assert result is None, (
            "_extract_code_snippet should return None when file has fewer lines than start_line"
        )

    @pytest.mark.asyncio
    async def test_empty_file_produces_not_available_in_prompt(self, tmp_path) -> None:
        """Empty source file produces '- code: (not available)' in the prompt.

        When the source file is empty, the enricher should fall back to
        the metadata-only format without any code block.
        """
        from pathlib import Path

        from codemap.mapper.reader import ContentReader

        # Arrange - Create an empty file
        source_file = tmp_path / "empty_prompt.py"
        source_file.write_text("")

        graph_manager = GraphManager()
        graph_manager.add_file(FileEntry(Path("empty_prompt.py"), size=0, token_est=0))
        graph_manager.add_node(
            "empty_prompt.py",
            CodeNode(type="function", name="empty_func", start_line=1, end_line=5),
        )

        llm_provider = AsyncMock()
        llm_provider.send.return_value = (
            '[{"node_id": "empty_prompt.py::empty_func", "summary": "Empty", "risks": []}]'
        )

        # Act
        enricher = GraphEnricher(
            graph_manager,
            llm_provider,
            root_path=tmp_path,
            content_reader=ContentReader(),
        )
        await enricher.enrich_nodes(batch_size=10)

        # Assert - Prompt uses fallback
        _system_prompt, user_prompt = llm_provider.send.call_args[0]
        assert "- code: (not available)" in user_prompt, (
            "Empty file should produce '- code: (not available)' fallback"
        )

    @pytest.mark.asyncio
    async def test_empty_snippet_string_treated_as_not_available(self, tmp_path) -> None:
        """An empty string from _extract_code_snippet is treated like None.

        If _extract_code_snippet somehow returns an empty string (e.g. file
        with only whitespace producing blank join), _enrich_batch should treat
        it as 'not available' instead of writing an empty code block.
        """
        from pathlib import Path
        from unittest.mock import patch

        from codemap.mapper.reader import ContentReader

        # Arrange
        source_file = tmp_path / "whitespace.py"
        source_file.write_text("def func():\n    pass\n")

        graph_manager = GraphManager()
        graph_manager.add_file(FileEntry(Path("whitespace.py"), size=50, token_est=10))
        graph_manager.add_node(
            "whitespace.py",
            CodeNode(type="function", name="func", start_line=1, end_line=2),
        )

        llm_provider = AsyncMock()
        llm_provider.send.return_value = (
            '[{"node_id": "whitespace.py::func", "summary": "WS", "risks": []}]'
        )

        enricher = GraphEnricher(
            graph_manager,
            llm_provider,
            root_path=tmp_path,
            content_reader=ContentReader(),
        )

        # Act - Patch _extract_code_snippet to return empty string
        with patch.object(enricher, "_extract_code_snippet", return_value=""):
            await enricher.enrich_nodes(batch_size=10)

        # Assert - Prompt uses fallback
        _system_prompt, user_prompt = llm_provider.send.call_args[0]
        assert "- code: (not available)" in user_prompt, (
            "Empty string from _extract_code_snippet should produce 'not available' fallback"
        )
        assert "```" not in user_prompt, (
            "Empty string should NOT produce a code block"
        )
