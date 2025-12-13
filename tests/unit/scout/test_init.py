"""Tests for scout module __init__.py exports."""

import codemap.scout


def test_file_entry_is_exported():
    """Test that FileEntry can be imported from codemap.scout."""
    assert hasattr(codemap.scout, "FileEntry")


def test_file_entry_in_all():
    """Test that FileEntry is in the __all__ list."""
    assert "FileEntry" in codemap.scout.__all__


def test_all_list_alphabetical_order():
    """Test that __all__ list is in alphabetical order."""
    all_list = codemap.scout.__all__
    assert all_list == sorted(all_list)


def test_all_expected_exports():
    """Test that all expected exports are present in __all__."""
    expected = ["FileEntry", "FileWalker", "StructureAdvisor", "TreeGenerator", "TreeReport"]
    assert set(codemap.scout.__all__) == set(expected)
