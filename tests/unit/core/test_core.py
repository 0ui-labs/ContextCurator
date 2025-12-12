"""Unit tests for codemap.core module."""

from codemap import core
from codemap.core import CerebrasProvider, LLMProvider, MockProvider, get_provider


class TestCoreModule:
    """Test suite for core module."""

    def test_core_module_exports_llm_components(self) -> None:
        """Test that core module exports LLM provider components."""
        # Act & Assert
        assert hasattr(core, "__all__")
        assert "LLMProvider" in core.__all__
        assert "MockProvider" in core.__all__
        assert "CerebrasProvider" in core.__all__
        assert "get_provider" in core.__all__

    def test_core_module_exports_are_importable(self) -> None:
        """Test that all exported components can be imported from codemap.core."""
        # Assert that imports work (they were imported at module level)
        assert LLMProvider is not None
        assert MockProvider is not None
        assert CerebrasProvider is not None
        assert get_provider is not None

    def test_core_module_get_provider_returns_mock_by_default(self) -> None:
        """Test that get_provider from core module returns MockProvider by default."""
        provider = get_provider()
        assert isinstance(provider, MockProvider)
