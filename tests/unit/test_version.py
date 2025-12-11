"""Unit tests for version information."""

import codemap
from codemap import core


def test_version_exists() -> None:
    """Test that __version__ attribute exists and has the correct value."""
    assert hasattr(codemap, "__version__")
    assert isinstance(codemap.__version__, str)
    assert codemap.__version__ == "0.1.0"


def test_core_module_exists() -> None:
    """Test that core module is importable."""
    assert core is not None
