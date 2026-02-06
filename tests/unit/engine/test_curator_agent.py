"""Unit tests for engine.curator_agent module.

Test suite for CuratorAgent - LLM-Agent for semantic plan analysis with tool-calling.
Follows AAA (Arrange-Act-Assert) pattern and TDD methodology.

Test Organization:
    - TestCuratorAgentInit: Verify constructor with dependency injection
    - TestAnalyzePlanSimple: Simple plan without risks - direct final answer
    - TestAnalyzePlanWithToolCalls: Plan with risks - LLM uses tools then final answer
    - TestAnalyzePlanWithDeletion: Plan deletes file - LLM detects dependencies
    - TestToolExecutionErrors: ValueError on invalid tool args handled gracefully
    - TestLLMAPIErrors: openai errors are logged and propagated
    - TestMaxIterations: Loop breaks after max_iterations with ValueError
    - TestConversationHistory: Verify tool results added to conversation
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import openai
import pytest

from codemap.engine.curator_agent import CuratorAgent
from codemap.engine.curator_tools import CuratorTools
from codemap.engine.map_renderer import MapRenderer
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
def simple_graph() -> GraphManager:
    """Graph with src/auth/login.py, src/auth/models.py, src/utils/helpers.py.

    login.py imports models.py and helpers.py.
    """
    gm = GraphManager()

    gm.add_file(FileEntry(Path("src/auth/login.py"), size=500, token_est=125))
    gm.add_file(FileEntry(Path("src/auth/models.py"), size=300, token_est=75))
    gm.add_file(
        FileEntry(Path("src/utils/helpers.py"), size=200, token_est=50)
    )

    gm.add_node(
        "src/auth/login.py", CodeNode("function", "authenticate", 1, 20)
    )
    gm.add_node(
        "src/auth/login.py", CodeNode("class", "LoginValidator", 22, 50)
    )
    gm.add_node("src/auth/models.py", CodeNode("class", "User", 1, 30))
    gm.add_node(
        "src/utils/helpers.py", CodeNode("function", "format_date", 1, 10)
    )

    gm.build_hierarchy("TestProject")

    gm.graph.nodes["project::TestProject"]["summary"] = (
        "A test authentication project"
    )
    gm.graph.nodes["src"]["summary"] = "Source code root"
    gm.graph.nodes["src/auth"]["summary"] = "Authentication package"
    gm.graph.nodes["src/utils"]["summary"] = "Utility functions"
    gm.graph.nodes["src/auth/login.py"]["summary"] = (
        "Login and authentication logic"
    )
    gm.graph.nodes["src/auth/models.py"]["summary"] = (
        "Data models for auth"
    )
    gm.graph.nodes["src/utils/helpers.py"]["summary"] = (
        "Helper utility functions"
    )
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
    gm.graph.nodes["src/auth/models.py::User"]["summary"] = (
        "User data model"
    )
    gm.graph.nodes["src/auth/models.py::User"]["risks"] = []
    gm.graph.nodes["src/utils/helpers.py::format_date"]["summary"] = (
        "Formats dates to ISO string"
    )
    gm.graph.nodes["src/utils/helpers.py::format_date"]["risks"] = []

    gm.add_dependency("src/auth/login.py", "src/utils/helpers.py")
    gm.add_dependency("src/auth/login.py", "src/auth/models.py")

    return gm


@pytest.fixture
def curator_tools(simple_graph: GraphManager) -> CuratorTools:
    """CuratorTools with simple graph hierarchy."""
    renderer = MapRenderer(simple_graph)
    return CuratorTools(renderer)


@pytest.fixture
def mock_llm_simple() -> AsyncMock:
    """LLM that returns a direct final answer."""
    mock = AsyncMock()
    mock.send.return_value = _final_answer("# Plan\n1. Step")
    return mock


@pytest.fixture
def mock_llm_with_tools() -> AsyncMock:
    """LLM that first calls a tool, then returns final answer."""
    mock = AsyncMock()
    mock.send.side_effect = [
        _tool_call("get_project_overview"),
        _final_answer("# Revised Plan\n1. Step"),
    ]
    return mock


class TestCuratorAgentInit:
    """Tests for initialization and dependency injection."""

    def test_init_stores_llm_provider(
        self, mock_llm_simple: AsyncMock, curator_tools: CuratorTools
    ) -> None:
        """CuratorAgent stores LLMProvider as _llm attribute."""
        agent = CuratorAgent(mock_llm_simple, curator_tools)
        assert agent._llm is mock_llm_simple

    def test_init_stores_curator_tools(
        self, mock_llm_simple: AsyncMock, curator_tools: CuratorTools
    ) -> None:
        """CuratorAgent stores CuratorTools as _tools attribute."""
        agent = CuratorAgent(mock_llm_simple, curator_tools)
        assert agent._tools is curator_tools

    def test_init_default_max_iterations(
        self, mock_llm_simple: AsyncMock, curator_tools: CuratorTools
    ) -> None:
        """Default max_iterations is 10."""
        agent = CuratorAgent(mock_llm_simple, curator_tools)
        assert agent._max_iterations == 10

    def test_init_custom_max_iterations(
        self, mock_llm_simple: AsyncMock, curator_tools: CuratorTools
    ) -> None:
        """Custom max_iterations is stored correctly."""
        agent = CuratorAgent(
            mock_llm_simple, curator_tools, max_iterations=5
        )
        assert agent._max_iterations == 5


class TestAnalyzePlanSimple:
    """Tests for simple plan analysis - LLM gives direct final answer."""

    @pytest.mark.asyncio
    async def test_returns_plan_from_final_answer(
        self, mock_llm_simple: AsyncMock, curator_tools: CuratorTools
    ) -> None:
        """Returns plan string from final_answer action."""
        agent = CuratorAgent(mock_llm_simple, curator_tools)
        result = await agent.analyze_plan(
            "# Simple Plan\n1. Do something"
        )
        assert result == "# Plan\n1. Step"

    @pytest.mark.asyncio
    async def test_calls_llm_with_system_and_user_prompt(
        self, mock_llm_simple: AsyncMock, curator_tools: CuratorTools
    ) -> None:
        """LLM send is called with system prompt and user prompt."""
        agent = CuratorAgent(mock_llm_simple, curator_tools)
        await agent.analyze_plan("# Test Plan")
        mock_llm_simple.send.assert_called_once()
        call_args = mock_llm_simple.send.call_args
        system_prompt = call_args[0][0]
        user_prompt = call_args[0][1]
        assert "Curator Agent" in system_prompt
        assert "# Test Plan" in user_prompt

    @pytest.mark.asyncio
    async def test_single_llm_call_for_direct_answer(
        self, mock_llm_simple: AsyncMock, curator_tools: CuratorTools
    ) -> None:
        """Only 1 LLM call when direct final answer."""
        agent = CuratorAgent(mock_llm_simple, curator_tools)
        await agent.analyze_plan("# Simple Plan")
        assert mock_llm_simple.send.call_count == 1


class TestAnalyzePlanWithToolCalls:
    """Tests for plan analysis with tool calls before final answer."""

    @pytest.mark.asyncio
    async def test_returns_revised_plan_after_tool_calls(
        self,
        mock_llm_with_tools: AsyncMock,
        curator_tools: CuratorTools,
    ) -> None:
        """Returns revised plan after tool exploration."""
        agent = CuratorAgent(mock_llm_with_tools, curator_tools)
        result = await agent.analyze_plan("# Plan with risks")
        assert result == "# Revised Plan\n1. Step"

    @pytest.mark.asyncio
    async def test_multiple_llm_calls_for_tool_usage(
        self,
        mock_llm_with_tools: AsyncMock,
        curator_tools: CuratorTools,
    ) -> None:
        """2 LLM calls: tool_call + final_answer."""
        agent = CuratorAgent(mock_llm_with_tools, curator_tools)
        await agent.analyze_plan("# Plan")
        assert mock_llm_with_tools.send.call_count == 2

    @pytest.mark.asyncio
    async def test_tool_result_included_in_next_prompt(
        self,
        mock_llm_with_tools: AsyncMock,
        curator_tools: CuratorTools,
    ) -> None:
        """Tool result is included in the second LLM call."""
        agent = CuratorAgent(mock_llm_with_tools, curator_tools)
        await agent.analyze_plan("# Plan")
        second_call = mock_llm_with_tools.send.call_args_list[1]
        user_prompt = second_call[0][1]
        assert "Tool-Result:" in user_prompt

    @pytest.mark.asyncio
    async def test_zoom_to_module_tool_call(
        self, curator_tools: CuratorTools
    ) -> None:
        """LLM can call zoom_to_module and get module details."""
        mock = AsyncMock()
        mock.send.side_effect = [
            _tool_call(
                "zoom_to_module",
                {"file_path": "src/auth/login.py"},
            ),
            _final_answer("# Updated Plan"),
        ]
        agent = CuratorAgent(mock, curator_tools)
        result = await agent.analyze_plan("# Plan")
        assert result == "# Updated Plan"
        second_call = mock.send.call_args_list[1]
        user_prompt = second_call[0][1]
        assert "src/auth/login.py" in user_prompt

    @pytest.mark.asyncio
    async def test_zoom_to_package_tool_call(
        self, curator_tools: CuratorTools
    ) -> None:
        """LLM can call zoom_to_package and get package details."""
        mock = AsyncMock()
        mock.send.side_effect = [
            _tool_call(
                "zoom_to_package",
                {"package_path": "src/auth"},
            ),
            _final_answer("# Updated"),
        ]
        agent = CuratorAgent(mock, curator_tools)
        result = await agent.analyze_plan("# Plan")
        assert result == "# Updated"

    @pytest.mark.asyncio
    async def test_zoom_to_symbol_tool_call(
        self, curator_tools: CuratorTools
    ) -> None:
        """LLM can call zoom_to_symbol and get symbol details."""
        mock = AsyncMock()
        mock.send.side_effect = [
            _tool_call(
                "zoom_to_symbol",
                {
                    "file_path": "src/auth/login.py",
                    "symbol_name": "authenticate",
                },
            ),
            _final_answer("# Symbol Plan"),
        ]
        agent = CuratorAgent(mock, curator_tools)
        result = await agent.analyze_plan("# Plan")
        assert result == "# Symbol Plan"

    @pytest.mark.asyncio
    async def test_multiple_tool_calls_before_final(
        self, curator_tools: CuratorTools
    ) -> None:
        """LLM calls multiple tools before giving final answer."""
        mock = AsyncMock()
        mock.send.side_effect = [
            _tool_call("get_project_overview"),
            _tool_call(
                "zoom_to_module",
                {"file_path": "src/auth/login.py"},
            ),
            _final_answer("# Deep Plan"),
        ]
        agent = CuratorAgent(mock, curator_tools)
        result = await agent.analyze_plan("# Complex Plan")
        assert result == "# Deep Plan"
        assert mock.send.call_count == 3


class TestAnalyzePlanWithDeletion:
    """Tests for plans that delete files - LLM detects dependencies."""

    @pytest.mark.asyncio
    async def test_deletion_plan_triggers_dependency_check(
        self, curator_tools: CuratorTools
    ) -> None:
        """LLM inspects module before approving file deletion."""
        mock = AsyncMock()
        mock.send.side_effect = [
            _tool_call(
                "zoom_to_module",
                {"file_path": "src/auth/models.py"},
            ),
            _final_answer(
                "# Adjusted Plan\nModels.py has dependents - keep it"
            ),
        ]
        agent = CuratorAgent(mock, curator_tools)
        result = await agent.analyze_plan(
            "# Plan\n1. Delete src/auth/models.py"
        )
        assert "Adjusted Plan" in result
        second_call = mock.send.call_args_list[1]
        user_prompt = second_call[0][1]
        assert "src/auth/models.py" in user_prompt


class TestToolExecutionErrors:
    """Tests for ValueError on invalid tool arguments."""

    @pytest.mark.asyncio
    async def test_unknown_tool_error_sent_to_llm(
        self, curator_tools: CuratorTools
    ) -> None:
        """Unknown tool name sends error message back to LLM."""
        mock = AsyncMock()
        mock.send.side_effect = [
            _tool_call("nonexistent_tool"),
            _final_answer("# Fallback Plan"),
        ]
        agent = CuratorAgent(mock, curator_tools)
        result = await agent.analyze_plan("# Plan")
        assert result == "# Fallback Plan"
        second_call = mock.send.call_args_list[1]
        user_prompt = second_call[0][1]
        assert "Error:" in user_prompt

    @pytest.mark.asyncio
    async def test_missing_args_error_sent_to_llm(
        self, curator_tools: CuratorTools
    ) -> None:
        """Missing required args sends error message back to LLM."""
        mock = AsyncMock()
        mock.send.side_effect = [
            _tool_call("zoom_to_module"),
            _final_answer("# Fixed Plan"),
        ]
        agent = CuratorAgent(mock, curator_tools)
        result = await agent.analyze_plan("# Plan")
        assert result == "# Fixed Plan"
        second_call = mock.send.call_args_list[1]
        user_prompt = second_call[0][1]
        assert "Error:" in user_prompt

    @pytest.mark.asyncio
    async def test_invalid_package_path_error_sent_to_llm(
        self, curator_tools: CuratorTools
    ) -> None:
        """Invalid package path ValueError sends error to LLM."""
        mock = AsyncMock()
        mock.send.side_effect = [
            _tool_call(
                "zoom_to_package",
                {"package_path": "nonexistent/pkg"},
            ),
            _final_answer("# Recovered Plan"),
        ]
        agent = CuratorAgent(mock, curator_tools)
        result = await agent.analyze_plan("# Plan")
        assert result == "# Recovered Plan"

    @pytest.mark.asyncio
    async def test_invalid_json_response_error_handled(
        self, curator_tools: CuratorTools
    ) -> None:
        """Invalid JSON response is handled, error sent to LLM."""
        mock = AsyncMock()
        mock.send.side_effect = [
            "This is not valid JSON at all",
            _final_answer("# Recovery Plan"),
        ]
        agent = CuratorAgent(mock, curator_tools)
        result = await agent.analyze_plan("# Plan")
        assert result == "# Recovery Plan"

    @pytest.mark.asyncio
    async def test_json_missing_action_field_error_handled(
        self, curator_tools: CuratorTools
    ) -> None:
        """JSON without action field is handled, error sent to LLM."""
        mock = AsyncMock()
        mock.send.side_effect = [
            '{"tool": "get_project_overview"}',
            _final_answer("# Fixed"),
        ]
        agent = CuratorAgent(mock, curator_tools)
        result = await agent.analyze_plan("# Plan")
        assert result == "# Fixed"

    @pytest.mark.asyncio
    async def test_unknown_action_type_error_handled(
        self, curator_tools: CuratorTools
    ) -> None:
        """Unknown action type is handled, error sent to LLM."""
        mock = AsyncMock()
        mock.send.side_effect = [
            '{"action": "unknown_action"}',
            _final_answer("# Fixed"),
        ]
        agent = CuratorAgent(mock, curator_tools)
        result = await agent.analyze_plan("# Plan")
        assert result == "# Fixed"


class TestLLMAPIErrors:
    """Tests for openai API errors - logged and propagated."""

    @pytest.mark.asyncio
    async def test_rate_limit_error_propagated(
        self, curator_tools: CuratorTools
    ) -> None:
        """openai.RateLimitError is raised to caller."""
        mock = AsyncMock()
        mock.send.side_effect = openai.RateLimitError(
            "Rate limit exceeded",
            response=MagicMock(),
            body=None,
        )
        agent = CuratorAgent(mock, curator_tools)
        with pytest.raises(openai.RateLimitError):
            await agent.analyze_plan("# Plan")

    @pytest.mark.asyncio
    async def test_api_connection_error_propagated(
        self, curator_tools: CuratorTools
    ) -> None:
        """openai.APIConnectionError is raised to caller."""
        mock = AsyncMock()
        mock.send.side_effect = openai.APIConnectionError(
            request=MagicMock(),
        )
        agent = CuratorAgent(mock, curator_tools)
        with pytest.raises(openai.APIConnectionError):
            await agent.analyze_plan("# Plan")

    @pytest.mark.asyncio
    async def test_api_error_propagated(
        self, curator_tools: CuratorTools
    ) -> None:
        """openai.APIError is raised to caller."""
        mock = AsyncMock()
        mock.send.side_effect = openai.APIError(
            message="Server error",
            request=MagicMock(),
            body=None,
        )
        agent = CuratorAgent(mock, curator_tools)
        with pytest.raises(openai.APIError):
            await agent.analyze_plan("# Plan")


class TestMaxIterations:
    """Tests for max iterations limit."""

    @pytest.mark.asyncio
    async def test_raises_value_error_after_max_iterations(
        self, curator_tools: CuratorTools
    ) -> None:
        """ValueError raised when max_iterations exceeded."""
        mock = AsyncMock()
        mock.send.return_value = _tool_call("get_project_overview")
        agent = CuratorAgent(
            mock, curator_tools, max_iterations=3
        )
        with pytest.raises(ValueError, match="finalisieren"):
            await agent.analyze_plan("# Infinite Plan")

    @pytest.mark.asyncio
    async def test_max_iterations_limits_llm_calls(
        self, curator_tools: CuratorTools
    ) -> None:
        """LLM is called exactly max_iterations times before error."""
        mock = AsyncMock()
        mock.send.return_value = _tool_call("get_project_overview")
        agent = CuratorAgent(
            mock, curator_tools, max_iterations=5
        )
        with pytest.raises(ValueError):
            await agent.analyze_plan("# Plan")
        assert mock.send.call_count == 5


class TestConversationHistory:
    """Tests for correct conversation history management."""

    @pytest.mark.asyncio
    async def test_initial_conversation_contains_plan(
        self, mock_llm_simple: AsyncMock, curator_tools: CuratorTools
    ) -> None:
        """First LLM call contains the original plan."""
        agent = CuratorAgent(mock_llm_simple, curator_tools)
        await agent.analyze_plan("# My Plan\n1. Do X")
        first_call = mock_llm_simple.send.call_args_list[0]
        user_prompt = first_call[0][1]
        assert "# My Plan" in user_prompt
        assert "1. Do X" in user_prompt

    @pytest.mark.asyncio
    async def test_tool_result_in_conversation_after_tool_call(
        self,
        mock_llm_with_tools: AsyncMock,
        curator_tools: CuratorTools,
    ) -> None:
        """Second LLM call includes tool result from first call."""
        agent = CuratorAgent(mock_llm_with_tools, curator_tools)
        await agent.analyze_plan("# Plan")
        second_call = mock_llm_with_tools.send.call_args_list[1]
        user_prompt = second_call[0][1]
        assert "Tool-Result:" in user_prompt
        assert "TestProject" in user_prompt

    @pytest.mark.asyncio
    async def test_assistant_tool_call_in_conversation(
        self,
        mock_llm_with_tools: AsyncMock,
        curator_tools: CuratorTools,
    ) -> None:
        """Second LLM call includes assistant's tool call action."""
        agent = CuratorAgent(mock_llm_with_tools, curator_tools)
        await agent.analyze_plan("# Plan")
        second_call = mock_llm_with_tools.send.call_args_list[1]
        user_prompt = second_call[0][1]
        assert "get_project_overview" in user_prompt

    @pytest.mark.asyncio
    async def test_error_in_conversation_after_tool_error(
        self, curator_tools: CuratorTools
    ) -> None:
        """Tool execution error is added to conversation."""
        mock = AsyncMock()
        mock.send.side_effect = [
            _tool_call("unknown_tool"),
            _final_answer("# OK"),
        ]
        agent = CuratorAgent(mock, curator_tools)
        await agent.analyze_plan("# Plan")
        second_call = mock.send.call_args_list[1]
        user_prompt = second_call[0][1]
        assert "Error:" in user_prompt
        assert "Unknown tool" in user_prompt

    @pytest.mark.asyncio
    async def test_json_in_markdown_block_parsed(
        self, curator_tools: CuratorTools
    ) -> None:
        """JSON embedded in markdown code block is correctly parsed."""
        raw = _final_answer("# Parsed")
        mock = AsyncMock()
        mock.send.side_effect = [f"```json\n{raw}\n```"]
        agent = CuratorAgent(mock, curator_tools)
        result = await agent.analyze_plan("# Plan")
        assert result == "# Parsed"

    @pytest.mark.asyncio
    async def test_show_code_tool_missing_args_error(
        self, curator_tools: CuratorTools
    ) -> None:
        """show_code with missing args sends error to LLM."""
        mock = AsyncMock()
        mock.send.side_effect = [
            _tool_call(
                "show_code",
                {"file_path": "src/auth/login.py"},
            ),
            _final_answer("# Fixed"),
        ]
        agent = CuratorAgent(mock, curator_tools)
        result = await agent.analyze_plan("# Plan")
        assert result == "# Fixed"
        second_call = mock.send.call_args_list[1]
        user_prompt = second_call[0][1]
        assert "Error:" in user_prompt

    @pytest.mark.asyncio
    async def test_zoom_to_symbol_missing_args_error(
        self, curator_tools: CuratorTools
    ) -> None:
        """zoom_to_symbol with missing symbol_name sends error."""
        mock = AsyncMock()
        mock.send.side_effect = [
            _tool_call(
                "zoom_to_symbol",
                {"file_path": "src/auth/login.py"},
            ),
            _final_answer("# Fixed"),
        ]
        agent = CuratorAgent(mock, curator_tools)
        result = await agent.analyze_plan("# Plan")
        assert result == "# Fixed"

    @pytest.mark.asyncio
    async def test_zoom_to_package_missing_args_error(
        self, curator_tools: CuratorTools
    ) -> None:
        """zoom_to_package with missing package_path sends error."""
        mock = AsyncMock()
        mock.send.side_effect = [
            _tool_call("zoom_to_package"),
            _final_answer("# Fixed"),
        ]
        agent = CuratorAgent(mock, curator_tools)
        result = await agent.analyze_plan("# Plan")
        assert result == "# Fixed"
        second_call = mock.send.call_args_list[1]
        user_prompt = second_call[0][1]
        assert "Error:" in user_prompt

    @pytest.mark.asyncio
    async def test_show_code_successful_call(
        self, simple_graph: GraphManager, tmp_path: Path
    ) -> None:
        """show_code with valid args returns code content."""
        auth_dir = tmp_path / "src" / "auth"
        auth_dir.mkdir(parents=True)
        (auth_dir / "login.py").write_text(
            "def authenticate(user, password):\n"
            "    return True\n"
            + "\n" * 48
        )

        renderer = MapRenderer(simple_graph, root_path=tmp_path)
        tools = CuratorTools(renderer)

        mock = AsyncMock()
        mock.send.side_effect = [
            _tool_call(
                "show_code",
                {
                    "file_path": "src/auth/login.py",
                    "symbol_name": "authenticate",
                },
            ),
            _final_answer("# Code Plan"),
        ]
        agent = CuratorAgent(mock, tools)
        result = await agent.analyze_plan("# Plan")
        assert result == "# Code Plan"
        second_call = mock.send.call_args_list[1]
        user_prompt = second_call[0][1]
        assert "authenticate" in user_prompt
