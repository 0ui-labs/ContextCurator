"""LLM-powered advisor for analyzing directory structures.

This module provides StructureAdvisor class that uses LLM providers to analyze
TreeReport objects and identify non-source files/folders. The class accepts
LLMProvider via dependency injection for testability and flexibility.
"""

import logging
import re

from codemap.core.llm import LLMProvider
from codemap.scout.models import TreeReport

logger = logging.getLogger(__name__)

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
        >>> import asyncio
        >>> from codemap.core.llm import MockProvider
        >>> from codemap.scout.models import TreeReport
        >>> async def example():
        ...     provider = MockProvider()
        ...     advisor = StructureAdvisor(provider)
        ...     report = TreeReport(
        ...         tree_string="project/\\n├── src/\\n└── node_modules/",
        ...         total_files=0,
        ...         total_folders=2,
        ...         estimated_tokens=15
        ...     )
        ...     patterns = await advisor.analyze(report)
        ...     return patterns
        >>> # patterns = asyncio.run(example())
        >>> # ['node_modules/', 'dist/', '.venv/']
    """

    def __init__(self, provider: LLMProvider) -> None:
        """Initialize StructureAdvisor with LLM provider.

        Args:
            provider: LLM provider implementation conforming to LLMProvider protocol.
                Used to send prompts and receive analysis results.
        """
        self._provider = provider

    async def analyze(self, report: TreeReport) -> list[str]:
        """Analyze TreeReport and return list of valid gitignore patterns only.

        Dies ist eine asynchrone Methode und muss mit await aufgerufen werden.

        Sends the tree structure to the LLM provider with system prompt requesting
        identification of non-source files/folders. Parses the LLM response by:
        1. Stripping markdown code block markers (```gitignore, ```)
        2. Splitting response into lines
        3. Filtering out empty lines and comment lines (starting with #)
        4. Normalizing lines (removing bullet points, numbered list prefixes)
        5. Filtering out explanatory/meta text (lines without pattern characteristics)
        6. Returning only valid gitignore-style patterns

        Valid patterns must contain at least one of: slash (/), asterisk (*),
        dot prefix (.), or be a simple directory/file name. Lines containing
        explanatory text or meta phrases are excluded.

        Args:
            report: TreeReport containing tree_string to analyze.

        Returns:
            List of valid gitignore-style patterns identifying files/folders to ignore.
            Only patterns with typical gitignore characteristics are included.
            Explanatory text from LLM responses is filtered out.
            Empty list if LLM returns empty or whitespace-only response,
            or if an API error occurs (ValueError from provider).

        Raises:
            No exceptions are raised; API errors result in empty list return.

        Example:
            >>> async def example():
            ...     advisor = StructureAdvisor(MockProvider())
            ...     report = TreeReport(
            ...         tree_string="project/\\n├── node_modules/",
            ...         total_files=0,
            ...         total_folders=1,
            ...         estimated_tokens=10
            ...     )
            ...     patterns = await advisor.analyze(report)
            ...     return 'node_modules/' in patterns
        """
        # Construct user prompt with tree structure
        user_prompt = f"Hier ist der Dateibaum:\n\n{report.tree_string}"

        # Call LLM provider with error handling for API failures
        try:
            response = await self._provider.send(SYSTEM_PROMPT, user_prompt)
        except ValueError as e:
            logger.warning("LLM provider returned invalid response: %s", e)
            return []

        # Parse response: strip markdown code blocks and filter empty lines
        lines = response.strip().split("\n")

        # Filter out markdown code block markers, empty lines, and explanatory text
        result = []
        for line in lines:
            stripped = line.strip()
            # Skip markdown code block markers
            if stripped.startswith("```"):
                continue
            # Skip empty lines
            if not stripped:
                continue
            # Skip comment lines (starting with #)
            if stripped.startswith("#"):
                continue
            # Normalize line (remove bullet points, numbered list prefixes)
            normalized = self._normalize_line(stripped)
            # Skip if normalization results in empty string
            if not normalized:
                continue
            # Skip explanatory/meta text lines
            if not self._is_valid_pattern(normalized):
                continue
            result.append(normalized)

        return result

    def _is_valid_pattern(self, line: str) -> bool:
        """Check if a line is a valid gitignore pattern.

        Valid patterns have typical gitignore characteristics:
        - Contains slash (/) for paths
        - Contains asterisk (*) for wildcards
        - Starts with dot (.) for hidden files/folders
        - Is a simple word without spaces (directory/file name)

        Lines with explanatory text (containing spaces and no pattern chars)
        are considered invalid.

        Args:
            line: The line to validate.

        Returns:
            True if the line appears to be a valid gitignore pattern.
        """
        # Pattern characteristics
        has_slash = "/" in line
        has_asterisk = "*" in line
        has_dot_prefix = line.startswith(".")
        has_space = " " in line

        # If it has typical pattern characters, it's valid
        if has_slash or has_asterisk or has_dot_prefix:
            return True

        # If it has no spaces, it's likely a simple directory/file name
        if not has_space:
            return True

        # Lines with spaces but no pattern characters are explanatory text
        return False

    def _normalize_line(self, line: str) -> str:
        """Normalize a line by removing common LLM formatting artifacts.

        Removes leading bullet points and numbered list prefixes that LLMs
        often add to their responses. This includes:
        - Bullet points: "- item", "* item"
        - Numbered lists: "1. item", "2. item", etc.

        Args:
            line: The line to normalize.

        Returns:
            The normalized line with formatting artifacts removed.
            Returns empty string if the line becomes empty after normalization.
        """
        # Remove leading bullet points (- or *)
        # Pattern matches "- ", "* " or standalone "-"/"*" at end of string
        normalized = re.sub(r"^[-*](?:\s+|$)", "", line)

        # Remove leading numbered list prefixes (1., 2., etc.)
        # Pattern matches "1. ", "2. ", "10. " or standalone "1.", "2." at end of string
        normalized = re.sub(r"^\d+\.(?:\s+|$)", "", normalized)

        return normalized.strip()
