"""LLM-powered advisor for analyzing directory structures.

This module provides StructureAdvisor class that uses LLM providers to analyze
TreeReport objects and identify non-source files/folders. The class accepts
LLMProvider via dependency injection for testability and flexibility.
"""

from codemap.core.llm import LLMProvider
from codemap.scout.models import TreeReport

# System prompt for LLM to analyze directory structures
SYSTEM_PROMPT: str = (
    "Du bist ein Experte für Software-Architektur. Analysiere den folgenden "
    "Dateibaum. Identifiziere Ordner/Dateien, die KEINEN Quellcode enthalten "
    "oder generiert sind (z.B. node_modules, venv, dist, assets, images, "
    "documentation). Gib NUR die Liste der Pfade im .gitignore Format zurück. "
    "Keine Erklärungen."
)


class StructureAdvisor:
    """Analyzes TreeReport to identify non-source files/folders using LLM.

    This class uses dependency injection to accept any LLMProvider implementation,
    enabling deterministic testing with mocks and real LLM usage in production.
    The analyze method sends the tree structure to the LLM and parses the response
    to extract gitignore-style patterns for files/folders that should be ignored.

    Attributes:
        _provider: The LLM provider implementation used for analysis.

    Example:
        >>> from codemap.core.llm import MockProvider
        >>> from codemap.scout.models import TreeReport
        >>> provider = MockProvider()
        >>> advisor = StructureAdvisor(provider)
        >>> report = TreeReport(
        ...     tree_string="project/\\n├── src/\\n└── node_modules/",
        ...     total_files=0,
        ...     total_folders=2,
        ...     estimated_tokens=15
        ... )
        >>> patterns = advisor.analyze(report)
        >>> print(patterns)
        ['node_modules/', 'dist/', '.venv/']
    """

    def __init__(self, provider: LLMProvider) -> None:
        """Initialize StructureAdvisor with LLM provider.

        Args:
            provider: LLM provider implementation conforming to LLMProvider protocol.
                Used to send prompts and receive analysis results.
        """
        self._provider = provider

    def analyze(self, report: TreeReport) -> list[str]:
        """Analyze TreeReport and return list of gitignore patterns.

        Sends the tree structure to the LLM provider with system prompt requesting
        identification of non-source files/folders. Parses the LLM response by:
        1. Stripping markdown code block markers (```gitignore, ```)
        2. Splitting response into lines
        3. Filtering out empty lines
        4. Returning list of gitignore-style patterns

        Args:
            report: TreeReport containing tree_string to analyze.

        Returns:
            List of gitignore-style patterns identifying files/folders to ignore.
            Empty list if LLM returns empty or whitespace-only response.

        Example:
            >>> advisor = StructureAdvisor(MockProvider())
            >>> report = TreeReport(
            ...     tree_string="project/\\n├── node_modules/",
            ...     total_files=0,
            ...     total_folders=1,
            ...     estimated_tokens=10
            ... )
            >>> patterns = advisor.analyze(report)
            >>> 'node_modules/' in patterns
            True
        """
        # Construct user prompt with tree structure
        user_prompt = f"Hier ist der Dateibaum:\n\n{report.tree_string}"

        # Call LLM provider
        response = self._provider.send(SYSTEM_PROMPT, user_prompt)

        # Parse response: strip markdown code blocks and filter empty lines
        lines = response.strip().split("\n")

        # Filter out markdown code block markers and empty lines
        result = []
        for line in lines:
            stripped = line.strip()
            # Skip markdown code block markers
            if stripped.startswith("```"):
                continue
            # Keep non-empty lines
            if stripped:
                result.append(stripped)

        return result
