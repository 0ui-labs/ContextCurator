"""Unit tests for codemap.core module."""

from codemap import core


class TestCoreModule:
    """Test suite for core module."""

    def test_core_module_exports_empty_all(self) -> None:
        """Test that core module exports an empty __all__ list."""
        # Act & Assert
        assert hasattr(core, "__all__")
        assert core.__all__ == []
