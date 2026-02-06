"""CuratorAgent for semantic plan analysis with LLM tool-calling.

This module provides the CuratorAgent class that implements a prompt-based
tool-calling loop. The LLM analyzes implementation plans by navigating the
code graph through CuratorTools, then produces a revised plan with
risk assessments and dependency analysis.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

import openai
import orjson

if TYPE_CHECKING:
    from codemap.core.llm import LLMProvider
    from codemap.engine.curator_tools import CuratorTools

logger = logging.getLogger(__name__)


class CuratorAgent:
    """LLM-Agent für semantische Plan-Analyse mit Tool-Calling.

    Implementiert einen Prompt-basierten Tool-Calling-Loop:
    1. System-Prompt beschreibt verfügbare Tools im JSON-Format
    2. LLM antwortet mit tool_call oder final_answer
    3. Agent führt Tool aus, fügt Ergebnis zur Conversation hinzu
    4. Wiederholt bis final_answer oder max_iterations

    Attributes:
        _llm: LLMProvider for AI-powered analysis.
        _tools: CuratorTools for code graph navigation.
        _max_iterations: Maximum loop iterations before abort.
    """

    SYSTEM_PROMPT = (
        "Du bist der Curator Agent für eine Codebase. Deine Aufgabe ist es, "
        "Implementierungspläne zu analysieren und mit Kontext aus der Codebase "
        "anzureichern. Du hast Zugriff auf Tools zum Navigieren im Code-Graphen.\n\n"
        "## Verfügbare Tools\n\n"
        "1. get_project_overview()\n"
        "   - Beschreibung: Zeigt Projektübersicht mit Hauptbereichen und Architektur-Hinweisen\n"
        "   - Args: keine\n\n"
        "2. zoom_to_package(package_path: str)\n"
        "   - Beschreibung: Zoomt in ein Package, zeigt Module und Abhängigkeiten\n"
        '   - Args: {"package_path": "src/auth"}\n\n'
        "3. zoom_to_module(file_path: str)\n"
        "   - Beschreibung: Zoomt in ein Modul, zeigt Funktionen/Klassen und Imports\n"
        '   - Args: {"file_path": "src/auth/login.py"}\n\n'
        "4. zoom_to_symbol(file_path: str, symbol_name: str)\n"
        "   - Beschreibung: Zoomt in eine Funktion/Klasse, zeigt Signatur und Aufrufer\n"
        '   - Args: {"file_path": "src/auth/login.py", "symbol_name": "authenticate"}\n\n'
        "5. show_code(file_path: str, symbol_name: str)\n"
        "   - Beschreibung: Zeigt den Quellcode eines Symbols mit Zeilennummern\n"
        '   - Args: {"file_path": "src/auth/login.py", "symbol_name": "authenticate"}\n\n'
        "## Response-Format\n\n"
        "Antworte IMMER mit einem JSON-Objekt:\n\n"
        'Tool-Call: {"action": "tool_call", "tool": "TOOL_NAME", "args": {...}}\n'
        'Final-Answer: {"action": "final_answer", "plan": "MARKDOWN_PLAN"}\n\n'
        "## Anweisungen\n\n"
        "1. Analysiere den Plan auf betroffene Dateien und potenzielle Risiken\n"
        "2. Nutze Tools um Abhängigkeiten und Impact zu verstehen\n"
        "3. Gib ausschließlich den finalen, überarbeiteten Plan als final_answer zurück, "
        "ohne Warnungen oder Meta-Hinweise\n"
    )

    def __init__(
        self,
        llm_provider: LLMProvider,
        curator_tools: CuratorTools,
        *,
        max_iterations: int = 10,
    ) -> None:
        """Initialize CuratorAgent with dependencies.

        Args:
            llm_provider: LLMProvider instance for AI-powered analysis.
            curator_tools: CuratorTools instance for code graph navigation.
            max_iterations: Maximum loop iterations before abort (default: 10).
        """
        self._llm = llm_provider
        self._tools = curator_tools
        self._max_iterations = max_iterations

    async def analyze_plan(self, plan: str) -> str:
        """Analysiert Plan und gibt überarbeiteten Plan zurück.

        Args:
            plan: Ursprünglicher Implementierungsplan (Markdown).

        Returns:
            Überarbeiteter Plan (Markdown).

        Raises:
            ValueError: Bei ungültigem LLM-Response nach max_iterations.
            openai.RateLimitError: Bei API-Rate-Limiting.
            openai.APIConnectionError: Bei Verbindungsproblemen.
            openai.APIError: Bei sonstigen API-Fehlern.
        """
        conversation: list[dict[str, str]] = [
            {"role": "user", "content": f"Analysiere diesen Plan:\n\n{plan}"},
        ]

        for iteration in range(self._max_iterations):
            try:
                user_prompt = self._build_user_prompt(conversation)
                response = await self._llm.send(self.SYSTEM_PROMPT, user_prompt)

                action_data = self._parse_response(response)

                if action_data["action"] == "final_answer":
                    return str(action_data["plan"])

                if action_data["action"] == "tool_call":
                    tool_result = self._execute_tool(
                        str(action_data["tool"]),
                        action_data.get("args", {}),
                    )
                    conversation.append(
                        {
                            "role": "assistant",
                            "content": f"Tool-Call: {action_data['tool']}",
                        }
                    )
                    conversation.append(
                        {
                            "role": "user",
                            "content": f"Tool-Result:\n{tool_result}",
                        }
                    )
                else:
                    action = action_data["action"]
                    msg = f"Unknown action: {action}"
                    raise ValueError(msg)

            except ValueError as e:
                logger.warning("Iteration %d: %s", iteration, e)
                conversation.append(
                    {"role": "user", "content": f"Error: {e}"}
                )
                continue

            except (
                openai.RateLimitError,
                openai.APIConnectionError,
                openai.APIError,
            ) as e:
                logger.warning("LLM API error: %s", e)
                raise

        logger.warning("Max iterations (%d) reached", self._max_iterations)
        msg = "Agent konnte Plan nicht finalisieren"
        raise ValueError(msg)

    def _build_user_prompt(self, conversation: list[dict[str, str]]) -> str:
        """Baut User-Prompt aus Conversation-History.

        Args:
            conversation: Liste von Message-Dicts mit role und content.

        Returns:
            Formatierter Prompt-String.
        """
        lines: list[str] = []
        for msg in conversation:
            role = msg["role"]
            content = msg["content"]
            lines.append(f"[{role.upper()}]")
            lines.append(content)
            lines.append("")
        return "\n".join(lines)

    def _parse_response(self, response: str) -> dict[str, Any]:
        """Parsed LLM-Response zu Action-Dict.

        Args:
            response: Raw LLM response string.

        Returns:
            Dict mit action-Feld und zugehörigen Daten.

        Raises:
            ValueError: Bei ungültigem JSON oder fehlendem action-Feld.
        """
        try:
            data: dict[str, Any] = orjson.loads(response)
        except orjson.JSONDecodeError:
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                data = orjson.loads(json_match.group(0))
            else:
                msg = f"Invalid JSON response: {response[:100]}"
                raise ValueError(msg) from None

        if "action" not in data:
            msg = "Response missing 'action' field"
            raise ValueError(msg)

        return data

    def _execute_tool(self, tool_name: str, args: dict[str, Any]) -> str:
        """Führt Tool aus und gibt Result zurück.

        Args:
            tool_name: Name des auszuführenden Tools.
            args: Argumente für das Tool.

        Returns:
            Tool-Ergebnis als String.

        Raises:
            ValueError: Bei unbekanntem Tool oder ungültigen Args.
        """
        if tool_name == "get_project_overview":
            return self._tools.get_project_overview()

        if tool_name == "zoom_to_package":
            package_path = args.get("package_path")
            if not package_path:
                msg = "zoom_to_package requires 'package_path' arg"
                raise ValueError(msg)
            return self._tools.zoom_to_package(str(package_path))

        if tool_name == "zoom_to_module":
            file_path = args.get("file_path")
            if not file_path:
                msg = "zoom_to_module requires 'file_path' arg"
                raise ValueError(msg)
            return self._tools.zoom_to_module(str(file_path))

        if tool_name == "zoom_to_symbol":
            file_path = args.get("file_path")
            symbol_name = args.get("symbol_name")
            if not file_path or not symbol_name:
                msg = "zoom_to_symbol requires 'file_path' and 'symbol_name'"
                raise ValueError(msg)
            return self._tools.zoom_to_symbol(str(file_path), str(symbol_name))

        if tool_name == "show_code":
            file_path = args.get("file_path")
            symbol_name = args.get("symbol_name")
            if not file_path or not symbol_name:
                msg = "show_code requires 'file_path' and 'symbol_name'"
                raise ValueError(msg)
            return self._tools.show_code(str(file_path), str(symbol_name))

        msg = f"Unknown tool: {tool_name}"
        raise ValueError(msg)
