"""Unit tests for FileWalker in codemap.scout.walker module.

This module tests the FileWalker class which discovers files in a directory
and returns FileEntry objects with metadata. Tests cover:
- Basic file discovery and FileEntry object structure
- Pattern matching for file exclusion (custom patterns)
- Default ignore patterns (.git, .venv, __pycache__)
- Metadata calculation (size, token estimation)
- Alphabetical sorting of results
- Edge cases and error handling (permission errors, deep nesting, etc.)
- Handling of empty directories and single files
"""

import os
from pathlib import Path

import pytest

from codemap.scout.models import FileEntry
from codemap.scout.walker import FileWalker


class TestFileWalkerBasic:
    """Test suite for basic FileWalker functionality."""

    def test_walker_returns_file_entries(self, tmp_path: Path) -> None:
        """Test that walk method returns list of FileEntry objects."""
        # Arrange
        (tmp_path / "file1.py").write_text("content1")
        (tmp_path / "file2.py").write_text("content2")
        (tmp_path / "file3.txt").write_text("content3")
        walker = FileWalker()

        # Act
        result = walker.walk(tmp_path, [])

        # Assert
        assert isinstance(result, list)
        assert len(result) == 3
        for entry in result:
            assert isinstance(entry, FileEntry)
            assert hasattr(entry, "path")
            assert hasattr(entry, "size")
            assert hasattr(entry, "token_est")

    def test_walker_empty_directory(self, tmp_path: Path) -> None:
        """Test walk on empty directory returns empty list."""
        # Arrange
        walker = FileWalker()

        # Act
        result = walker.walk(tmp_path, [])

        # Assert
        assert isinstance(result, list)
        assert len(result) == 0

    def test_walker_without_ignore_patterns(self, tmp_path: Path) -> None:
        """Test walk with default ignore_patterns (None)."""
        # Arrange
        (tmp_path / "main.py").write_text("content")
        walker = FileWalker()

        # Act - call without ignore_patterns argument
        result = walker.walk(tmp_path)

        # Assert
        assert len(result) == 1
        assert result[0].path.name == "main.py"

    def test_walker_single_file(self, tmp_path: Path) -> None:
        """Test walk on directory with single file."""
        # Arrange
        test_content = "This is test content"
        (tmp_path / "README.md").write_text(test_content)
        walker = FileWalker()

        # Act
        result = walker.walk(tmp_path, [])

        # Assert
        assert len(result) == 1
        entry = result[0]
        assert isinstance(entry, FileEntry)
        assert entry.path == Path("README.md")
        assert entry.size > 0

    def test_walker_nested_structure(self, tmp_path: Path) -> None:
        """Test walk on nested directory structure returns correct relative paths."""
        # Arrange
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("content")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_main.py").write_text("content")
        walker = FileWalker()

        # Act
        result = walker.walk(tmp_path, [])

        # Assert
        assert len(result) == 2
        paths = [entry.path for entry in result]
        assert Path("src/main.py") in paths
        assert Path("tests/test_main.py") in paths


class TestFileWalkerPatterns:
    """Test suite for pattern matching functionality."""

    def test_walker_respects_patterns(self, tmp_path: Path) -> None:
        """Test that walker excludes files matching patterns."""
        # Arrange
        (tmp_path / "test.tmp").write_text("temporary")
        (tmp_path / "main.py").write_text("code")
        walker = FileWalker()

        # Act
        result = walker.walk(tmp_path, ["*.tmp"])

        # Assert
        assert len(result) == 1
        assert result[0].path == Path("main.py")
        # Verify test.tmp was excluded
        paths = [entry.path for entry in result]
        assert Path("test.tmp") not in paths

    def test_walker_respects_multiple_patterns(self, tmp_path: Path) -> None:
        """Test that walker excludes files matching multiple patterns."""
        # Arrange
        (tmp_path / "test.log").write_text("log")
        (tmp_path / "debug.tmp").write_text("temp")
        (tmp_path / "main.py").write_text("code")
        walker = FileWalker()

        # Act
        result = walker.walk(tmp_path, ["*.log", "*.tmp"])

        # Assert
        assert len(result) == 1
        assert result[0].path == Path("main.py")
        # Verify both exclusions worked
        paths = [entry.path for entry in result]
        assert Path("test.log") not in paths
        assert Path("debug.tmp") not in paths

    def test_walker_respects_directory_patterns(self, tmp_path: Path) -> None:
        """Test that walker excludes entire directories matching patterns."""
        # Arrange
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "package.json").write_text("content")
        (tmp_path / "node_modules" / "lib").mkdir()
        (tmp_path / "node_modules" / "lib" / "index.js").write_text("content")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("content")
        walker = FileWalker()

        # Act
        result = walker.walk(tmp_path, ["node_modules/"])

        # Assert
        paths = [entry.path for entry in result]
        assert Path("src/main.py") in paths
        # Verify entire node_modules directory excluded
        for path in paths:
            assert not str(path).startswith("node_modules")

    def test_walker_respects_wildcard_patterns(self, tmp_path: Path) -> None:
        """Test that walker excludes files matching wildcard patterns."""
        # Arrange
        (tmp_path / "test_unit.py").write_text("content")
        (tmp_path / "test_integration.py").write_text("content")
        (tmp_path / "main.py").write_text("content")
        walker = FileWalker()

        # Act
        result = walker.walk(tmp_path, ["test_*.py"])

        # Assert
        assert len(result) == 1
        assert result[0].path == Path("main.py")
        # Verify test files were excluded
        paths = [entry.path for entry in result]
        assert Path("test_unit.py") not in paths
        assert Path("test_integration.py") not in paths


class TestFileWalkerDefaultIgnores:
    """Test suite for default ignore patterns."""

    def test_walker_respects_default_ignores(self, tmp_path: Path) -> None:
        """Test that walker ignores default hidden directories."""
        # Arrange
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("content")
        (tmp_path / ".venv").mkdir()
        (tmp_path / ".venv" / "lib").mkdir()
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "cache.pyc").write_text("content")
        (tmp_path / "main.py").write_text("content")
        walker = FileWalker()

        # Act
        result = walker.walk(tmp_path, [])

        # Assert
        assert len(result) == 1
        assert result[0].path == Path("main.py")
        # Verify all default ignores excluded
        paths = [entry.path for entry in result]
        for path in paths:
            path_str = str(path)
            assert not path_str.startswith(".git")
            assert not path_str.startswith(".venv")
            assert not path_str.startswith("__pycache__")

    def test_walker_ignores_git_directory(self, tmp_path: Path) -> None:
        """Test that .git directory is always ignored."""
        # Arrange
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("content")
        (tmp_path / "README.md").write_text("content")
        walker = FileWalker()

        # Act
        result = walker.walk(tmp_path, [])

        # Assert
        paths = [entry.path for entry in result]
        assert Path("README.md") in paths
        assert len(result) == 1
        for path in paths:
            assert not str(path).startswith(".git")

    def test_walker_ignores_venv_directory(self, tmp_path: Path) -> None:
        """Test that .venv directory is always ignored."""
        # Arrange
        (tmp_path / ".venv").mkdir()
        (tmp_path / ".venv" / "lib").mkdir()
        (tmp_path / ".venv" / "lib" / "python.py").write_text("content")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("content")
        walker = FileWalker()

        # Act
        result = walker.walk(tmp_path, [])

        # Assert
        paths = [entry.path for entry in result]
        assert Path("src/main.py") in paths
        for path in paths:
            assert not str(path).startswith(".venv")

    def test_walker_ignores_pycache_directory(self, tmp_path: Path) -> None:
        """Test that __pycache__ directory is always ignored."""
        # Arrange
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "module.pyc").write_text("content")
        (tmp_path / "module.py").write_text("content")
        walker = FileWalker()

        # Act
        result = walker.walk(tmp_path, [])

        # Assert
        paths = [entry.path for entry in result]
        assert Path("module.py") in paths
        for path in paths:
            assert not str(path).startswith("__pycache__")


class TestFileWalkerMetadata:
    """Test suite for metadata calculation."""

    def test_walker_calculates_metadata(self, tmp_path: Path) -> None:
        """Test that walker calculates correct size and token_est."""
        # Arrange
        test_content = "x" * 100  # 100 bytes
        test_file = tmp_path / "test.txt"
        test_file.write_text(test_content)
        walker = FileWalker()

        # Act
        result = walker.walk(tmp_path, [])

        # Assert
        assert len(result) == 1
        entry = result[0]
        expected_size = test_file.stat().st_size
        assert entry.size == expected_size
        assert entry.token_est == expected_size // 4

    def test_walker_token_estimation_formula(self, tmp_path: Path) -> None:
        """Test that token_est follows formula: size // 4."""
        # Arrange
        (tmp_path / "small.txt").write_text("x" * 50)  # 50 bytes
        (tmp_path / "medium.txt").write_text("x" * 200)  # 200 bytes
        (tmp_path / "large.txt").write_text("x" * 1000)  # 1000 bytes
        walker = FileWalker()

        # Act
        result = walker.walk(tmp_path, [])

        # Assert
        assert len(result) == 3
        for entry in result:
            assert entry.token_est == entry.size // 4

    def test_walker_relative_paths(self, tmp_path: Path) -> None:
        """Test that walker returns paths relative to root."""
        # Arrange
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "utils").mkdir()
        (tmp_path / "src" / "utils" / "helper.py").write_text("content")
        walker = FileWalker()

        # Act
        result = walker.walk(tmp_path, [])

        # Assert
        assert len(result) == 1
        assert result[0].path == Path("src/utils/helper.py")

    def test_walker_calculates_size_correctly(self, tmp_path: Path) -> None:
        """Test that walker calculates file sizes correctly for multiple files."""
        # Arrange
        (tmp_path / "small.txt").write_text("x" * 50)
        (tmp_path / "medium.txt").write_text("x" * 200)
        (tmp_path / "large.txt").write_text("x" * 1000)
        walker = FileWalker()

        # Act
        result = walker.walk(tmp_path, [])

        # Assert
        assert len(result) == 3
        sizes = {entry.path.name: entry.size for entry in result}
        assert sizes["small.txt"] == 50
        assert sizes["medium.txt"] == 200
        assert sizes["large.txt"] == 1000

    def test_walker_handles_empty_files(self, tmp_path: Path) -> None:
        """Test that walker handles empty files correctly."""
        # Arrange
        (tmp_path / "empty.txt").write_text("")
        walker = FileWalker()

        # Act
        result = walker.walk(tmp_path, [])

        # Assert
        assert len(result) == 1
        entry = result[0]
        assert entry.size == 0
        assert entry.token_est == 0


class TestFileWalkerSorting:
    """Test suite for alphabetical sorting."""

    def test_walker_sorts_alphabetically(self, tmp_path: Path) -> None:
        """Test that results are sorted alphabetically by path."""
        # Arrange
        (tmp_path / "zebra.py").write_text("content")
        (tmp_path / "alpha.py").write_text("content")
        (tmp_path / "beta.py").write_text("content")
        walker = FileWalker()

        # Act
        result = walker.walk(tmp_path, [])

        # Assert
        assert len(result) == 3
        paths = [entry.path for entry in result]
        assert paths[0] == Path("alpha.py")
        assert paths[1] == Path("beta.py")
        assert paths[2] == Path("zebra.py")

    def test_walker_sorts_nested_files(self, tmp_path: Path) -> None:
        """Test that nested files are sorted alphabetically."""
        # Arrange
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "zebra.py").write_text("content")
        (tmp_path / "src" / "alpha.py").write_text("content")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "beta_test.py").write_text("content")
        (tmp_path / "README.md").write_text("content")
        walker = FileWalker()

        # Act
        result = walker.walk(tmp_path, [])

        # Assert
        paths = [entry.path for entry in result]
        # Verify alphabetical order including nested paths
        assert paths == sorted(paths)

    def test_walker_sorting_is_deterministic(self, tmp_path: Path) -> None:
        """Test that walk produces identical order on repeated calls."""
        # Arrange
        (tmp_path / "zebra.py").write_text("content")
        (tmp_path / "alpha.py").write_text("content")
        (tmp_path / "beta.py").write_text("content")
        walker = FileWalker()

        # Act
        result1 = walker.walk(tmp_path, [])
        result2 = walker.walk(tmp_path, [])

        # Assert
        paths1 = [entry.path for entry in result1]
        paths2 = [entry.path for entry in result2]
        assert paths1 == paths2


class TestFileWalkerEdgeCases:
    """Test suite for edge cases and error handling."""

    def test_walker_handles_permission_error_on_is_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that walker gracefully handles OSError during is_dir check."""
        # Arrange
        (tmp_path / "readable.py").write_text("content")
        (tmp_path / "unreadable.py").write_text("content")
        (tmp_path / "other.py").write_text("content")
        walker = FileWalker()

        # Store original is_dir
        original_is_dir = Path.is_dir

        # Mock is_dir to raise PermissionError for specific file
        def mock_is_dir(self: Path) -> bool:
            if self.name == "unreadable.py":
                raise PermissionError("Permission denied")
            return original_is_dir(self)

        monkeypatch.setattr(Path, "is_dir", mock_is_dir)

        # Act
        result = walker.walk(tmp_path, [])

        # Assert - Should continue and process other files
        paths = [entry.path for entry in result]
        assert Path("readable.py") in paths
        assert Path("other.py") in paths
        # unreadable.py should be skipped due to is_dir error
        assert Path("unreadable.py") not in paths

    def test_walker_handles_permission_error_on_stat(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that walker gracefully handles OSError during metadata stat call."""
        # Arrange
        (tmp_path / "readable.py").write_text("content")
        (tmp_path / "problematic.py").write_text("content")
        (tmp_path / "other.py").write_text("content")
        walker = FileWalker()

        # Store original stat
        original_stat = Path.stat

        # Track stat calls per file to distinguish is_dir() call from metadata call
        stat_calls: dict[str, int] = {}

        # Mock stat to raise OSError only on second call (metadata call) for specific file
        # First call is from is_dir(), second is for file size metadata
        def mock_stat(self: Path, *, follow_symlinks: bool = True) -> "os.stat_result":
            if self.name == "problematic.py":
                stat_calls[self.name] = stat_calls.get(self.name, 0) + 1
                # First call is from is_dir(), let it pass
                # Second call is for metadata, fail it
                if stat_calls[self.name] > 1:
                    raise OSError("Cannot read file metadata")
            return original_stat(self, follow_symlinks=follow_symlinks)

        monkeypatch.setattr(Path, "stat", mock_stat)

        # Act
        result = walker.walk(tmp_path, [])

        # Assert - Should continue and process other files
        paths = [entry.path for entry in result]
        assert Path("readable.py") in paths
        assert Path("other.py") in paths
        # problematic.py should be skipped due to stat error during metadata collection
        assert Path("problematic.py") not in paths

    def test_walker_handles_deep_nesting(self, tmp_path: Path) -> None:
        """Test that walker handles deeply nested directory structures."""
        # Arrange - Create 10 levels deep
        current = tmp_path
        folder_names = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
        for folder_name in folder_names:
            current = current / folder_name
            current.mkdir()
        (current / "deep_file.py").write_text("content")
        walker = FileWalker()

        # Act
        result = walker.walk(tmp_path, [])

        # Assert
        assert len(result) == 1
        assert result[0].path == Path("a/b/c/d/e/f/g/h/i/j/deep_file.py")

    def test_walker_handles_special_characters(self, tmp_path: Path) -> None:
        """Test that walker handles files with special characters."""
        # Arrange
        (tmp_path / "file-with-dashes.py").write_text("content")
        (tmp_path / "file_with_underscores.py").write_text("content")
        (tmp_path / "file.with.dots.py").write_text("content")
        walker = FileWalker()

        # Act
        result = walker.walk(tmp_path, [])

        # Assert
        assert len(result) == 3
        paths = [entry.path for entry in result]
        assert Path("file-with-dashes.py") in paths
        assert Path("file_with_underscores.py") in paths
        assert Path("file.with.dots.py") in paths

    def test_walker_nonexistent_path(self) -> None:
        """Test that walk raises ValueError for non-existent path."""
        # Arrange
        walker = FileWalker()
        nonexistent_path = Path("/nonexistent/path/that/does/not/exist")

        # Act & Assert
        with pytest.raises(ValueError, match="Path does not exist"):
            walker.walk(nonexistent_path, [])

    def test_walker_file_as_root_raises_error(self, tmp_path: Path) -> None:
        """Test that walk raises ValueError when path is a file, not directory."""
        # Arrange
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")
        walker = FileWalker()

        # Act & Assert
        with pytest.raises(ValueError, match="not a directory"):
            walker.walk(file_path, [])

    def test_walker_ignores_directories_only_files(self, tmp_path: Path) -> None:
        """Test that walker only returns files, not directories."""
        # Arrange
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "nested").mkdir()
        (tmp_path / "main.py").write_text("content")
        walker = FileWalker()

        # Act
        result = walker.walk(tmp_path, [])

        # Assert
        assert len(result) == 1
        assert result[0].path == Path("main.py")
        # Verify no directories in results
        for entry in result:
            assert not (tmp_path / entry.path).is_dir()
