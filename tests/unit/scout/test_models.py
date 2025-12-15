"""Unit tests for scout.models module."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from codemap.scout.models import FileEntry, TreeReport


class TestTreeReport:
    """Test suite for TreeReport dataclass."""

    def test_tree_report_creation(self):
        """Test TreeReport can be instantiated with all attributes."""
        report = TreeReport(
            tree_string="project/\n├── src/\n└── README.md",
            total_files=1,
            total_folders=1,
            estimated_tokens=10,
        )
        assert report.tree_string == "project/\n├── src/\n└── README.md"
        assert report.total_files == 1
        assert report.total_folders == 1
        assert report.estimated_tokens == 10

    def test_tree_report_is_frozen(self):
        """Test TreeReport is immutable (frozen)."""
        report = TreeReport(tree_string="test", total_files=0, total_folders=0, estimated_tokens=0)
        with pytest.raises(FrozenInstanceError):
            report.tree_string = "modified"


class TestFileEntry:
    """Test suite for FileEntry dataclass."""

    def test_file_entry_creation_with_path_object(self):
        """Test FileEntry can be instantiated with Path object."""
        path = Path("/project/src/main.py")
        entry = FileEntry(path=path, size=1024, token_est=292)
        assert entry.path == path
        assert entry.size == 1024
        assert entry.token_est == 292

    def test_file_entry_creation_with_string_path(self):
        """Test FileEntry can be instantiated with string path (auto-converted)."""
        entry = FileEntry(path=Path("/project/README.md"), size=512, token_est=146)
        assert isinstance(entry.path, Path)
        assert entry.path == Path("/project/README.md")

    def test_file_entry_is_frozen(self):
        """Test FileEntry is immutable (frozen)."""
        entry = FileEntry(path=Path("/test.py"), size=100, token_est=28)
        with pytest.raises(FrozenInstanceError):
            entry.size = 200

    def test_file_entry_all_attributes_accessible(self):
        """Test all FileEntry attributes are accessible."""
        path = Path("/project/data/config.json")
        entry = FileEntry(path=path, size=2048, token_est=585)
        # Verify all attributes can be read
        assert hasattr(entry, "path")
        assert hasattr(entry, "size")
        assert hasattr(entry, "token_est")
        # Verify values
        assert entry.path == path
        assert entry.size == 2048
        assert entry.token_est == 585

    def test_file_entry_with_relative_path(self):
        """Test FileEntry works with relative paths."""
        path = Path("src/utils/helper.py")
        entry = FileEntry(path=path, size=750, token_est=214)
        assert entry.path == path
        assert not entry.path.is_absolute()

    def test_file_entry_equality(self):
        """Test FileEntry equality comparison."""
        entry1 = FileEntry(path=Path("/test.py"), size=100, token_est=28)
        entry2 = FileEntry(path=Path("/test.py"), size=100, token_est=28)
        entry3 = FileEntry(path=Path("/other.py"), size=100, token_est=28)
        assert entry1 == entry2
        assert entry1 != entry3
