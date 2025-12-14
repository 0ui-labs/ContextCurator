"""Tests for codemap.engine module exports."""


def test_mapbuilder_import():
    """Test that MapBuilder is accessible from codemap.engine."""
    from codemap.engine import MapBuilder

    # Verify MapBuilder is importable
    assert MapBuilder is not None


def test_module_all_exports():
    """Test that __all__ contains expected exports."""
    from codemap import engine

    # Verify __all__ is defined
    assert hasattr(engine, "__all__")

    # Verify MapBuilder is in __all__
    assert "MapBuilder" in engine.__all__

    # Verify only expected exports
    assert engine.__all__ == ["MapBuilder"]


def test_mapbuilder_is_correct_class():
    """Test that imported MapBuilder is the correct class from builder module."""
    from codemap.engine import MapBuilder
    from codemap.engine.builder import MapBuilder as BuilderMapBuilder

    # Verify it's the same class
    assert MapBuilder is BuilderMapBuilder
