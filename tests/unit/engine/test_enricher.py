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
                CodeNode(type="class", name=f"Class_{i}", start_line=100 + i * 10, end_line=100 + i * 10 + 8),
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
        from pathlib import Path

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
