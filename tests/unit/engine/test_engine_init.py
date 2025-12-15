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

    # Verify GraphEnricher is in __all__
    assert "GraphEnricher" in engine.__all__

    # Verify only expected exports
    assert engine.__all__ == ["MapBuilder", "GraphEnricher"]


def test_mapbuilder_is_correct_class():
    """Test that imported MapBuilder is the correct class from builder module."""
    from codemap.engine import MapBuilder
    from codemap.engine.builder import MapBuilder as BuilderMapBuilder

    # Verify it's the same class
    assert MapBuilder is BuilderMapBuilder


def test_graphenricher_import():
    """Test that GraphEnricher is accessible from codemap.engine."""
    from codemap.engine import GraphEnricher

    # Verify GraphEnricher is importable
    assert GraphEnricher is not None


def test_graphenricher_is_correct_class():
    """Test that imported GraphEnricher is the correct class from enricher module."""
    from codemap.engine import GraphEnricher
    from codemap.engine.enricher import GraphEnricher as EnricherGraphEnricher

    # Verify it's the same class
    assert GraphEnricher is EnricherGraphEnricher
