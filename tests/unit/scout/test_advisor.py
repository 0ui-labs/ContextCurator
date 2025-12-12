"""Unit tests for StructureAdvisor in codemap.scout.advisor module.

This module tests the StructureAdvisor class which analyzes TreeReport objects
to identify non-source files/folders using LLM provider. Tests cover:
- Class initialization with LLMProvider
- analyze() method with various response formats
- Response parsing (markdown code blocks, prefix text, empty responses)
- Prompt construction verification
"""

from codemap.scout.models import TreeReport


class TestMockProvider:
    """Test-double implementation of LLMProvider for deterministic testing.

    This mock provider returns a predefined, deterministic response in
    .gitignore format. It is used as the standard stub for generic
    initialization and documentation tests, ensuring tests do not depend
    on the behavior of the global MockProvider in codemap.core.llm.

    The response contains typical gitignore patterns that would be returned
    by a real LLM when analyzing a project structure.

    Attributes:
        last_system_prompt: The last system prompt passed to send().
        last_user_prompt: The last user prompt passed to send().

    Example:
        >>> provider = TestMockProvider()
        >>> result = provider.send("system prompt", "user prompt")
        >>> print(result)
        node_modules/
        dist/
        .venv/
    """

    __test__ = False  # Prevent pytest from collecting this as a test class

    def __init__(self) -> None:
        """Initialize TestMockProvider with empty prompt tracking."""
        self.last_system_prompt: str | None = None
        self.last_user_prompt: str | None = None

    def send(self, system: str, user: str) -> str:
        """Return a deterministic gitignore-format response.

        Stores the prompts for later verification and returns a fixed
        set of typical gitignore patterns.

        Args:
            system: System prompt (stored for verification).
            user: User prompt (stored for verification).

        Returns:
            A deterministic string with typical gitignore patterns:
            "node_modules/\\ndist/\\n.venv/"
        """
        self.last_system_prompt = system
        self.last_user_prompt = user
        return "node_modules/\ndist/\n.venv/"


class TestStructureAdvisorInitialization:
    """Test suite for StructureAdvisor initialization."""

    def test_structure_advisor_exists(self) -> None:
        """Test that StructureAdvisor class exists and can be imported."""
        # Act & Assert
        from codemap.scout.advisor import StructureAdvisor

        assert StructureAdvisor is not None

    def test_structure_advisor_has_init(self) -> None:
        """Test that StructureAdvisor has __init__ method."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        # Assert
        assert hasattr(StructureAdvisor, "__init__")
        assert callable(getattr(StructureAdvisor, "__init__"))

    def test_structure_advisor_init_with_provider(self) -> None:
        """Test that StructureAdvisor can be initialized with a provider."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        provider = TestMockProvider()

        # Act
        advisor = StructureAdvisor(provider)

        # Assert
        assert advisor is not None

    def test_structure_advisor_stores_provider(self) -> None:
        """Test that StructureAdvisor stores provider as instance variable."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        provider = TestMockProvider()

        # Act
        advisor = StructureAdvisor(provider)

        # Assert
        assert hasattr(advisor, "_provider")
        assert advisor._provider is provider

    def test_structure_advisor_accepts_any_llm_provider(self) -> None:
        """Test that StructureAdvisor accepts any LLMProvider implementation."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        class CustomProvider:
            """Custom provider for testing."""

            def send(self, system: str, user: str) -> str:
                return "test output"

        provider = CustomProvider()

        # Act
        advisor = StructureAdvisor(provider)

        # Assert
        assert advisor._provider is provider


class TestStructureAdvisorAnalyzeMethod:
    """Test suite for StructureAdvisor.analyze() method."""

    def test_analyze_method_exists(self) -> None:
        """Test that analyze method exists."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        provider = TestMockProvider()
        advisor = StructureAdvisor(provider)

        # Assert
        assert hasattr(advisor, "analyze")
        assert callable(getattr(advisor, "analyze"))

    def test_analyze_with_clean_response(self) -> None:
        """Test analyze with clean response (no markdown, no prefix)."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        class CleanProvider:
            def send(self, system: str, user: str) -> str:
                return "node_modules/\ndist/\n.venv/"

        provider = CleanProvider()
        advisor = StructureAdvisor(provider)
        report = TreeReport(
            tree_string="project/\n├── src/\n└── README.md",
            total_files=1,
            total_folders=1,
            estimated_tokens=10,
        )

        # Act
        result = advisor.analyze(report)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 3
        assert "node_modules/" in result
        assert "dist/" in result
        assert ".venv/" in result

    def test_analyze_strips_markdown_code_blocks_with_language(self) -> None:
        """Test analyze strips markdown code blocks with language identifier."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        class MarkdownProvider:
            def send(self, system: str, user: str) -> str:
                return "```gitignore\nnode_modules/\ndist/\n```"

        provider = MarkdownProvider()
        advisor = StructureAdvisor(provider)
        report = TreeReport(
            tree_string="project/\n├── src/",
            total_files=0,
            total_folders=1,
            estimated_tokens=5,
        )

        # Act
        result = advisor.analyze(report)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 2
        assert "node_modules/" in result
        assert "dist/" in result
        # Ensure markdown code block markers are removed
        assert "```gitignore" not in result
        assert "```" not in result

    def test_analyze_strips_markdown_code_blocks_without_language(self) -> None:
        """Test analyze strips markdown code blocks without language identifier."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        class MarkdownProvider:
            def send(self, system: str, user: str) -> str:
                return "```\nnode_modules/\n.venv/\n```"

        provider = MarkdownProvider()
        advisor = StructureAdvisor(provider)
        report = TreeReport(
            tree_string="project/",
            total_files=0,
            total_folders=0,
            estimated_tokens=2,
        )

        # Act
        result = advisor.analyze(report)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 2
        assert "node_modules/" in result
        assert ".venv/" in result

    def test_analyze_filters_prefix_text(self) -> None:
        """Test analyze filters out explanatory prefix text from LLM response."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        class PrefixProvider:
            def send(self, system: str, user: str) -> str:
                return "Hier ist die Liste:\nnode_modules/\ndist/"

        provider = PrefixProvider()
        advisor = StructureAdvisor(provider)
        report = TreeReport(
            tree_string="project/",
            total_files=0,
            total_folders=0,
            estimated_tokens=2,
        )

        # Act
        result = advisor.analyze(report)

        # Assert
        assert isinstance(result, list)
        # Should only include valid patterns, not explanatory text
        assert "Hier ist die Liste:" not in result
        assert "node_modules/" in result
        assert "dist/" in result
        assert len(result) == 2

    def test_analyze_filters_empty_lines(self) -> None:
        """Test analyze filters out empty lines."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        class EmptyLinesProvider:
            def send(self, system: str, user: str) -> str:
                return "node_modules/\n\n\ndist/\n\n.venv/\n"

        provider = EmptyLinesProvider()
        advisor = StructureAdvisor(provider)
        report = TreeReport(
            tree_string="project/",
            total_files=0,
            total_folders=0,
            estimated_tokens=2,
        )

        # Act
        result = advisor.analyze(report)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 3
        assert "" not in result
        assert "node_modules/" in result
        assert "dist/" in result
        assert ".venv/" in result

    def test_analyze_accepts_simple_filenames_without_pattern_chars(self) -> None:
        """Test analyze accepts simple filenames without slash/asterisk/dot prefix."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        class SimpleNameProvider:
            def send(self, system: str, user: str) -> str:
                return "Makefile\nLICENSE\nDockerfile"

        provider = SimpleNameProvider()
        advisor = StructureAdvisor(provider)
        report = TreeReport(
            tree_string="project/",
            total_files=0,
            total_folders=0,
            estimated_tokens=2,
        )

        # Act
        result = advisor.analyze(report)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 3
        assert "Makefile" in result
        assert "LICENSE" in result
        assert "Dockerfile" in result

    def test_analyze_empty_response_returns_empty_list(self) -> None:
        """Test analyze returns empty list for empty response."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        class EmptyProvider:
            def send(self, system: str, user: str) -> str:
                return ""

        provider = EmptyProvider()
        advisor = StructureAdvisor(provider)
        report = TreeReport(
            tree_string="project/",
            total_files=0,
            total_folders=0,
            estimated_tokens=2,
        )

        # Act
        result = advisor.analyze(report)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 0

    def test_analyze_whitespace_only_returns_empty_list(self) -> None:
        """Test analyze returns empty list for whitespace-only response."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        class WhitespaceProvider:
            def send(self, system: str, user: str) -> str:
                return "   \n\n   \n   "

        provider = WhitespaceProvider()
        advisor = StructureAdvisor(provider)
        report = TreeReport(
            tree_string="project/",
            total_files=0,
            total_folders=0,
            estimated_tokens=2,
        )

        # Act
        result = advisor.analyze(report)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 0

    def test_analyze_complex_response_with_markdown_and_prefix(self) -> None:
        """Test analyze with complex response combining markdown and prefix."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        class ComplexProvider:
            def send(self, system: str, user: str) -> str:
                return (
                    "Hier ist die Liste der zu ignorierenden Pfade:\n"
                    "```gitignore\n"
                    "node_modules/\n"
                    "dist/\n"
                    ".venv/\n"
                    "```"
                )

        provider = ComplexProvider()
        advisor = StructureAdvisor(provider)
        report = TreeReport(
            tree_string="project/\n├── src/\n└── node_modules/",
            total_files=0,
            total_folders=2,
            estimated_tokens=15,
        )

        # Act
        result = advisor.analyze(report)

        # Assert
        assert isinstance(result, list)
        # Should contain only valid patterns, not prefix or markdown markers
        assert "Hier ist die Liste der zu ignorierenden Pfade:" not in result
        assert "node_modules/" in result
        assert "dist/" in result
        assert ".venv/" in result
        assert "```gitignore" not in result
        assert "```" not in result
        assert len(result) == 3

    def test_analyze_normalizes_bullet_list_with_dash(self) -> None:
        """Test analyze removes leading dash bullet points from patterns."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        class BulletDashProvider:
            def send(self, system: str, user: str) -> str:
                return "- node_modules/\n- dist/\n- .venv/"

        provider = BulletDashProvider()
        advisor = StructureAdvisor(provider)
        report = TreeReport(
            tree_string="project/",
            total_files=0,
            total_folders=0,
            estimated_tokens=2,
        )

        # Act
        result = advisor.analyze(report)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 3
        assert "node_modules/" in result
        assert "dist/" in result
        assert ".venv/" in result
        # Ensure bullet points are removed
        assert "- node_modules/" not in result

    def test_analyze_normalizes_bullet_list_with_asterisk(self) -> None:
        """Test analyze removes leading asterisk bullet points from patterns."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        class BulletAsteriskProvider:
            def send(self, system: str, user: str) -> str:
                return "* node_modules/\n* dist/\n* .venv/"

        provider = BulletAsteriskProvider()
        advisor = StructureAdvisor(provider)
        report = TreeReport(
            tree_string="project/",
            total_files=0,
            total_folders=0,
            estimated_tokens=2,
        )

        # Act
        result = advisor.analyze(report)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 3
        assert "node_modules/" in result
        assert "dist/" in result
        assert ".venv/" in result
        # Ensure bullet points are removed
        assert "* node_modules/" not in result

    def test_analyze_normalizes_numbered_list(self) -> None:
        """Test analyze removes numbered list prefixes from patterns."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        class NumberedListProvider:
            def send(self, system: str, user: str) -> str:
                return "1. node_modules/\n2. dist/\n3. .venv/\n10. __pycache__/"

        provider = NumberedListProvider()
        advisor = StructureAdvisor(provider)
        report = TreeReport(
            tree_string="project/",
            total_files=0,
            total_folders=0,
            estimated_tokens=2,
        )

        # Act
        result = advisor.analyze(report)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 4
        assert "node_modules/" in result
        assert "dist/" in result
        assert ".venv/" in result
        assert "__pycache__/" in result
        # Ensure numbered prefixes are removed
        assert "1. node_modules/" not in result
        assert "10. __pycache__/" not in result

    def test_analyze_filters_comment_lines(self) -> None:
        """Test analyze filters out comment lines starting with #."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        class CommentProvider:
            def send(self, system: str, user: str) -> str:
                return "# This is a comment\nnode_modules/\n# Another comment\ndist/"

        provider = CommentProvider()
        advisor = StructureAdvisor(provider)
        report = TreeReport(
            tree_string="project/",
            total_files=0,
            total_folders=0,
            estimated_tokens=2,
        )

        # Act
        result = advisor.analyze(report)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 2
        assert "node_modules/" in result
        assert "dist/" in result
        # Ensure comment lines are filtered out
        assert "# This is a comment" not in result
        assert "# Another comment" not in result

    def test_analyze_mixed_formatting(self) -> None:
        """Test analyze handles mixed formatting styles correctly."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        class MixedFormattingProvider:
            def send(self, system: str, user: str) -> str:
                return (
                    "Hier sind die Pfade:\n"
                    "- node_modules/\n"
                    "1. dist/\n"
                    "* .venv/\n"
                    "# Comment\n"
                    "__pycache__/"
                )

        provider = MixedFormattingProvider()
        advisor = StructureAdvisor(provider)
        report = TreeReport(
            tree_string="project/",
            total_files=0,
            total_folders=0,
            estimated_tokens=2,
        )

        # Act
        result = advisor.analyze(report)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 4
        assert "node_modules/" in result
        assert "dist/" in result
        assert ".venv/" in result
        assert "__pycache__/" in result
        # Ensure formatting artifacts are removed
        assert "Hier sind die Pfade:" not in result
        assert "# Comment" not in result

    def test_analyze_filters_empty_bullet_points(self) -> None:
        """Test analyze filters out empty bullet points after normalization."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        class EmptyBulletProvider:
            def send(self, system: str, user: str) -> str:
                return "- \n-\n* \n1. \nnode_modules/\ndist/"

        provider = EmptyBulletProvider()
        advisor = StructureAdvisor(provider)
        report = TreeReport(
            tree_string="project/",
            total_files=0,
            total_folders=0,
            estimated_tokens=2,
        )

        # Act
        result = advisor.analyze(report)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 2
        assert "node_modules/" in result
        assert "dist/" in result
        # Ensure empty bullets are filtered out
        assert "" not in result


class TestStructureAdvisorPromptConstruction:
    """Test suite for verifying prompt construction in analyze method."""

    def test_analyze_uses_system_prompt(self) -> None:
        """Test that analyze passes SYSTEM_PROMPT to provider.send()."""
        # Arrange
        from codemap.scout.advisor import SYSTEM_PROMPT, StructureAdvisor

        captured_system = None

        class CaptureProvider:
            def send(self, system: str, user: str) -> str:
                nonlocal captured_system
                captured_system = system
                return "node_modules/"

        provider = CaptureProvider()
        advisor = StructureAdvisor(provider)
        report = TreeReport(
            tree_string="project/",
            total_files=0,
            total_folders=0,
            estimated_tokens=2,
        )

        # Act
        advisor.analyze(report)

        # Assert
        assert captured_system == SYSTEM_PROMPT

    def test_analyze_user_prompt_includes_tree_string(self) -> None:
        """Test that analyze includes report.tree_string in user prompt."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        captured_user = None

        class CaptureProvider:
            def send(self, system: str, user: str) -> str:
                nonlocal captured_user
                captured_user = user
                return "node_modules/"

        provider = CaptureProvider()
        advisor = StructureAdvisor(provider)
        tree_string = "project/\n├── src/\n└── README.md"
        report = TreeReport(
            tree_string=tree_string,
            total_files=1,
            total_folders=1,
            estimated_tokens=10,
        )

        # Act
        advisor.analyze(report)

        # Assert
        assert captured_user is not None
        assert tree_string in captured_user

    def test_analyze_user_prompt_format(self) -> None:
        """Test that analyze formats user prompt correctly."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        captured_user = None

        class CaptureProvider:
            def send(self, system: str, user: str) -> str:
                nonlocal captured_user
                captured_user = user
                return "node_modules/"

        provider = CaptureProvider()
        advisor = StructureAdvisor(provider)
        tree_string = "project/\n├── src/"
        report = TreeReport(
            tree_string=tree_string,
            total_files=0,
            total_folders=1,
            estimated_tokens=5,
        )

        # Act
        advisor.analyze(report)

        # Assert
        assert captured_user is not None
        assert "Hier ist der Dateibaum:" in captured_user
        assert tree_string in captured_user


class TestStructureAdvisorSystemPromptConstant:
    """Test suite for SYSTEM_PROMPT constant."""

    def test_system_prompt_exists(self) -> None:
        """Test that SYSTEM_PROMPT constant exists."""
        # Act & Assert
        from codemap.scout.advisor import SYSTEM_PROMPT

        assert SYSTEM_PROMPT is not None

    def test_system_prompt_is_string(self) -> None:
        """Test that SYSTEM_PROMPT is a string."""
        # Arrange
        from codemap.scout.advisor import SYSTEM_PROMPT

        # Assert
        assert isinstance(SYSTEM_PROMPT, str)

    def test_system_prompt_is_not_empty(self) -> None:
        """Test that SYSTEM_PROMPT is not empty."""
        # Arrange
        from codemap.scout.advisor import SYSTEM_PROMPT

        # Assert
        assert len(SYSTEM_PROMPT) > 0

    def test_system_prompt_contains_key_instructions(self) -> None:
        """Test that SYSTEM_PROMPT contains key instructions."""
        # Arrange
        from codemap.scout.advisor import SYSTEM_PROMPT

        # Assert
        assert "Dateibaum" in SYSTEM_PROMPT or "Verzeichnis" in SYSTEM_PROMPT
        assert "gitignore" in SYSTEM_PROMPT


class TestStructureAdvisorDocumentation:
    """Test suite for StructureAdvisor documentation."""

    def test_module_has_docstring(self) -> None:
        """Test that advisor module has comprehensive docstring."""
        # Arrange
        import codemap.scout.advisor

        # Assert
        assert codemap.scout.advisor.__doc__ is not None
        assert len(codemap.scout.advisor.__doc__.strip()) > 0

    def test_class_has_docstring(self) -> None:
        """Test that StructureAdvisor class has comprehensive docstring."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        # Assert
        assert StructureAdvisor.__doc__ is not None
        assert len(StructureAdvisor.__doc__.strip()) > 0

    def test_init_has_docstring(self) -> None:
        """Test that __init__ method has comprehensive docstring."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        # Assert
        assert StructureAdvisor.__init__.__doc__ is not None
        assert len(StructureAdvisor.__init__.__doc__.strip()) > 0

    def test_analyze_has_docstring(self) -> None:
        """Test that analyze method has comprehensive docstring."""
        # Arrange
        from codemap.scout.advisor import StructureAdvisor

        provider = TestMockProvider()
        advisor = StructureAdvisor(provider)

        # Assert
        assert advisor.analyze.__doc__ is not None
        assert len(advisor.analyze.__doc__.strip()) > 0


class TestStructureAdvisorTypeHints:
    """Test suite for StructureAdvisor type hints."""

    def test_init_has_type_hints(self) -> None:
        """Test that __init__ has complete type hints."""
        # Arrange
        from typing import get_type_hints

        from codemap.scout.advisor import StructureAdvisor

        # Act
        type_hints = get_type_hints(StructureAdvisor.__init__)

        # Assert
        assert "provider" in type_hints
        assert "return" in type_hints

    def test_analyze_has_type_hints(self) -> None:
        """Test that analyze has complete type hints."""
        # Arrange
        from typing import get_type_hints

        from codemap.scout.advisor import StructureAdvisor

        # Act
        type_hints = get_type_hints(StructureAdvisor.analyze)

        # Assert
        assert "report" in type_hints
        assert type_hints["report"] == TreeReport
        assert "return" in type_hints
        # Check that return type is list[str]
        return_type = type_hints["return"]
        assert hasattr(return_type, "__origin__")
        assert return_type.__origin__ is list
