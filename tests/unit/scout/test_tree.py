"""Unit tests for TreeGenerator in codemap.scout.tree module.

This module tests the TreeGenerator class which produces TreeReport objects
containing directory tree visualizations and statistics. Tests cover:
- Basic functionality and TreeReport object structure
- Hidden directory filtering (.git, .venv, __pycache__)
- Alphabetical sorting of files and directories
- Tree structure formatting with correct symbols and indentation
- Edge cases and error handling
- .gitignore integration for excluding files/directories
- Unlimited depth traversal (no artificial limits)
"""

from collections.abc import Iterator
from pathlib import Path

import pytest

from codemap.scout.models import TreeReport
from codemap.scout.tree import TreeGenerator


class TestTreeGeneratorBasic:
    """Test suite for basic TreeGenerator functionality."""

    def test_generate_returns_tree_report(self, tmp_path: Path) -> None:
        """Test that generate method returns a TreeReport object."""
        # Arrange
        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert
        assert isinstance(result, TreeReport)
        assert isinstance(result.tree_string, str)
        assert result.total_files >= 0
        assert result.total_folders >= 0

    def test_generate_empty_directory(self, tmp_path: Path) -> None:
        """Test tree generation for empty directory."""
        # Arrange
        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert
        assert isinstance(result, TreeReport)
        assert f"{tmp_path.name}/" in result.tree_string
        assert result.total_files == 0
        assert result.total_folders == 0

    def test_generate_single_file(self, tmp_path: Path) -> None:
        """Test tree generation for directory with single file."""
        # Arrange
        (tmp_path / "README.md").write_text("content")
        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert
        assert isinstance(result, TreeReport)
        assert "README.md" in result.tree_string
        assert result.total_files == 1
        assert result.total_folders == 0

    def test_generate_single_directory(self, tmp_path: Path) -> None:
        """Test tree generation for directory with single subdirectory."""
        # Arrange
        (tmp_path / "src").mkdir()
        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert
        assert isinstance(result, TreeReport)
        assert "src/" in result.tree_string
        assert result.total_files == 0
        assert result.total_folders == 1

    def test_returns_report_object(self, tmp_path: Path) -> None:
        """Test A: Verify TreeReport with exact file counts and token estimation."""
        # Arrange - Create exactly 3 files
        (tmp_path / "file1.py").write_text("content")
        (tmp_path / "file2.py").write_text("content")
        (tmp_path / "file3.py").write_text("content")
        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert
        assert isinstance(result, TreeReport)
        assert result.total_files == 3
        assert result.total_folders == 0
        assert "file1.py" in result.tree_string
        assert "file2.py" in result.tree_string
        assert "file3.py" in result.tree_string
        assert result.estimated_tokens > 0

    def test_estimated_tokens_matches_formula(self, tmp_path: Path) -> None:
        """Test that estimated_tokens equals int(len(tree_string) / 3.5)."""
        # Arrange - Create a simple deterministic structure
        (tmp_path / "a.py").write_text("content")
        (tmp_path / "b.py").write_text("content")
        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert - Verify the formula: int(len(tree_string) / 3.5)
        expected_tokens = int(len(result.tree_string) / 3.5)
        assert result.estimated_tokens == expected_tokens
        # Sanity check: tokens should be roughly 1/3.5 of string length
        assert result.estimated_tokens > 0
        assert result.estimated_tokens < len(result.tree_string)

    def test_deep_nesting(self, tmp_path: Path) -> None:
        """Test B: Verify unlimited depth traversal with 10-level nesting."""
        # Arrange - Create 10 levels deep nested structure
        current = tmp_path
        folder_names = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
        for folder_name in folder_names:
            current = current / folder_name
            current.mkdir()
        (current / "deep_file.py").write_text("content")

        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert - Proves no depth limit exists
        assert "deep_file.py" in result.tree_string
        assert result.total_files == 1
        assert result.total_folders == 10
        # Verify all intermediate folder names appear
        for folder_name in folder_names:
            assert f"{folder_name}/" in result.tree_string

    def test_respects_gitignore(self, tmp_path: Path) -> None:
        """Test C: Verify .gitignore rules are applied to exclude files."""
        # Arrange
        (tmp_path / ".gitignore").write_text("*.txt\n")
        (tmp_path / "secret.txt").write_text("secret content")
        (tmp_path / "allowed.py").write_text("allowed content")
        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert - gitignore rule applied
        assert "secret.txt" not in result.tree_string
        assert "allowed.py" in result.tree_string
        assert result.total_files == 1  # Only allowed.py counted
        # .gitignore itself should not appear in tree (meta-file)
        assert ".gitignore" not in result.tree_string

    def test_gitignore_directory_pattern(self, tmp_path: Path) -> None:
        """Test .gitignore directory patterns exclude entire directories."""
        # Arrange
        (tmp_path / ".gitignore").write_text("node_modules/\n")
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "package.json").write_text("content")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("content")
        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert
        assert "node_modules" not in result.tree_string
        assert "package.json" not in result.tree_string
        assert "src/" in result.tree_string
        assert "main.py" in result.tree_string

    def test_gitignore_unreadable_continues_traversal(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that unreadable .gitignore is gracefully ignored and traversal continues."""
        # Arrange
        (tmp_path / ".gitignore").write_text("*.txt\n")
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "file.py").write_text("content")
        generator = TreeGenerator()

        # Mock read_text to raise OSError
        def mock_read_text(*args: object, **kwargs: object) -> str:
            raise OSError("Permission denied")

        monkeypatch.setattr(Path, "read_text", mock_read_text)

        # Act
        result = generator.generate(tmp_path)

        # Assert - Both files should appear (gitignore not applied due to read error)
        assert "file.txt" in result.tree_string
        assert "file.py" in result.tree_string
        assert result.total_files == 2


class TestTreeGeneratorIgnoreHidden:
    """Test suite for hidden directory and file filtering."""

    def test_generate_ignores_git_directory(self, tmp_path: Path) -> None:
        """Test that .git directory is always ignored."""
        # Arrange
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("content")
        (tmp_path / "README.md").write_text("content")

        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert
        assert ".git" not in result.tree_string
        assert "config" not in result.tree_string
        assert "README.md" in result.tree_string

    def test_generate_ignores_venv_directory(self, tmp_path: Path) -> None:
        """Test that .venv directory is always ignored."""
        # Arrange
        (tmp_path / ".venv").mkdir()
        (tmp_path / ".venv" / "lib").mkdir()
        (tmp_path / ".venv" / "lib" / "python.py").write_text("content")
        (tmp_path / "main.py").write_text("content")

        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert
        assert ".venv" not in result.tree_string
        assert "lib" not in result.tree_string
        assert "python.py" not in result.tree_string
        assert "main.py" in result.tree_string

    def test_generate_ignores_pycache_directory(self, tmp_path: Path) -> None:
        """Test that __pycache__ directory is always ignored."""
        # Arrange
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "module.pyc").write_text("content")
        (tmp_path / "module.py").write_text("content")

        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert
        assert "__pycache__" not in result.tree_string
        assert "module.pyc" not in result.tree_string
        assert "module.py" in result.tree_string

    def test_generate_ignores_multiple_hidden(self, tmp_path: Path) -> None:
        """Test that multiple hidden directories are ignored simultaneously."""
        # Arrange
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("content")
        (tmp_path / ".venv").mkdir()
        (tmp_path / ".venv" / "lib").mkdir()
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "cache.pyc").write_text("content")
        (tmp_path / "README.md").write_text("content")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("content")

        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert
        assert ".git" not in result.tree_string
        assert ".venv" not in result.tree_string
        assert "__pycache__" not in result.tree_string
        assert "config" not in result.tree_string
        assert "lib" not in result.tree_string
        assert "cache.pyc" not in result.tree_string
        assert "README.md" in result.tree_string
        assert "src/" in result.tree_string
        assert "main.py" in result.tree_string

    def test_generate_ignores_system_scm_directories(self, tmp_path: Path) -> None:
        """Test that system/SCM directories (.svn, .hg, .DS_Store) are ignored."""
        # Arrange
        (tmp_path / ".svn").mkdir()
        (tmp_path / ".svn" / "entries").write_text("content")
        (tmp_path / ".hg").mkdir()
        (tmp_path / ".hg" / "dirstate").write_text("content")
        (tmp_path / ".DS_Store").mkdir()
        (tmp_path / "Thumbs.db").mkdir()
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("content")

        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert - System/SCM directories are hidden
        assert ".svn" not in result.tree_string
        assert "entries" not in result.tree_string
        assert ".hg" not in result.tree_string
        assert "dirstate" not in result.tree_string
        assert ".DS_Store" not in result.tree_string
        assert "Thumbs.db" not in result.tree_string
        # Real source code should be visible
        assert "src/" in result.tree_string
        assert "main.py" in result.tree_string

    def test_generate_ignores_build_directories(self, tmp_path: Path) -> None:
        """Test that build directories (dist, build, out, target) are ignored."""
        # Arrange
        (tmp_path / "dist").mkdir()
        (tmp_path / "dist" / "bundle.js").write_text("content")
        (tmp_path / "build").mkdir()
        (tmp_path / "build" / "output.jar").write_text("content")
        (tmp_path / "out").mkdir()
        (tmp_path / "out" / "compiled.exe").write_text("content")
        (tmp_path / "target").mkdir()
        (tmp_path / "target" / "release").mkdir()
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("content")

        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert - Build directories are hidden (check for directory markers to avoid false positives)
        assert "dist/" not in result.tree_string
        assert "bundle.js" not in result.tree_string
        assert "build/" not in result.tree_string
        assert "output.jar" not in result.tree_string
        assert "out/" not in result.tree_string
        assert "compiled.exe" not in result.tree_string
        assert "target/" not in result.tree_string
        assert "release" not in result.tree_string
        # Real source code should be visible
        assert "src/" in result.tree_string
        assert "main.py" in result.tree_string

    def test_generate_ignores_node_web_directories(self, tmp_path: Path) -> None:
        """Test that Node/Web directories (bower_components, .next, .cache) are ignored."""
        # Arrange
        (tmp_path / "bower_components").mkdir()
        (tmp_path / "bower_components" / "jquery").mkdir()
        (tmp_path / ".next").mkdir()
        (tmp_path / ".next" / "static").mkdir()
        (tmp_path / ".cache").mkdir()
        (tmp_path / ".cache" / "webpack").mkdir()
        (tmp_path / ".nuxt").mkdir()
        (tmp_path / "coverage").mkdir()
        (tmp_path / "coverage" / "lcov.info").write_text("content")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.js").write_text("content")

        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert - Node/Web directories are hidden
        assert "bower_components" not in result.tree_string
        assert "jquery" not in result.tree_string
        assert ".next" not in result.tree_string
        assert "static" not in result.tree_string
        assert ".cache" not in result.tree_string
        assert "webpack" not in result.tree_string
        assert ".nuxt" not in result.tree_string
        assert "coverage" not in result.tree_string
        assert "lcov.info" not in result.tree_string
        # Real source code should be visible
        assert "src/" in result.tree_string
        assert "app.js" in result.tree_string

    def test_generate_ignores_python_directories(self, tmp_path: Path) -> None:
        """Test that Python directories (venv, .pytest_cache, htmlcov) are ignored."""
        # Arrange
        (tmp_path / "venv").mkdir()
        (tmp_path / "venv" / "lib").mkdir()
        (tmp_path / ".pytest_cache").mkdir()
        (tmp_path / ".pytest_cache" / "v").mkdir()
        (tmp_path / "htmlcov").mkdir()
        (tmp_path / "htmlcov" / "index.html").write_text("content")
        (tmp_path / ".mypy_cache").mkdir()
        (tmp_path / ".ruff_cache").mkdir()
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("content")

        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert - Python directories are hidden
        assert "venv" not in result.tree_string or "venv/" not in result.tree_string
        assert ".pytest_cache" not in result.tree_string
        assert "htmlcov" not in result.tree_string
        assert "index.html" not in result.tree_string
        assert ".mypy_cache" not in result.tree_string
        assert ".ruff_cache" not in result.tree_string
        # Real source code should be visible
        assert "src/" in result.tree_string
        assert "main.py" in result.tree_string

    def test_generate_ignores_ide_directories(self, tmp_path: Path) -> None:
        """Test that IDE directories (.idea, .vscode) are ignored."""
        # Arrange
        (tmp_path / ".idea").mkdir()
        (tmp_path / ".idea" / "workspace.xml").write_text("content")
        (tmp_path / ".vscode").mkdir()
        (tmp_path / ".vscode" / "settings.json").write_text("content")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("content")

        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert - IDE directories are hidden
        assert ".idea" not in result.tree_string
        assert "workspace.xml" not in result.tree_string
        assert ".vscode" not in result.tree_string
        assert "settings.json" not in result.tree_string
        # Real source code should be visible
        assert "src/" in result.tree_string
        assert "main.py" in result.tree_string


class TestTreeGeneratorSorting:
    """Test suite for alphabetical sorting of files and directories."""

    def test_generate_sorts_files_alphabetically(self, tmp_path: Path) -> None:
        """Test that files are sorted alphabetically."""
        # Arrange
        (tmp_path / "zebra.py").write_text("content")
        (tmp_path / "alpha.py").write_text("content")
        (tmp_path / "beta.py").write_text("content")

        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert
        lines = result.tree_string.strip().split("\n")
        alpha_idx = next(i for i, line in enumerate(lines) if "alpha.py" in line)
        beta_idx = next(i for i, line in enumerate(lines) if "beta.py" in line)
        zebra_idx = next(i for i, line in enumerate(lines) if "zebra.py" in line)

        assert alpha_idx < beta_idx < zebra_idx, "Files should be sorted alphabetically"

    def test_generate_sorts_directories_alphabetically(self, tmp_path: Path) -> None:
        """Test that directories are sorted alphabetically."""
        # Arrange
        (tmp_path / "zebra").mkdir()
        (tmp_path / "alpha").mkdir()
        (tmp_path / "beta").mkdir()

        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert
        lines = result.tree_string.strip().split("\n")
        alpha_idx = next(i for i, line in enumerate(lines) if "alpha/" in line)
        beta_idx = next(i for i, line in enumerate(lines) if "beta/" in line)
        zebra_idx = next(i for i, line in enumerate(lines) if "zebra/" in line)

        assert alpha_idx < beta_idx < zebra_idx, "Directories should be sorted alphabetically"

    def test_generate_sorts_mixed_deterministically(self, tmp_path: Path) -> None:
        """Test that files and directories are sorted alphabetically together."""
        # Arrange
        (tmp_path / "zebra.py").write_text("content")
        (tmp_path / "alpha").mkdir()
        (tmp_path / "beta.py").write_text("content")
        (tmp_path / "gamma").mkdir()

        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert
        lines = result.tree_string.strip().split("\n")
        alpha_idx = next(i for i, line in enumerate(lines) if "alpha/" in line)
        beta_idx = next(i for i, line in enumerate(lines) if "beta.py" in line)
        gamma_idx = next(i for i, line in enumerate(lines) if "gamma/" in line)
        zebra_idx = next(i for i, line in enumerate(lines) if "zebra.py" in line)

        assert alpha_idx < beta_idx < gamma_idx < zebra_idx, (
            "Files and directories should be sorted alphabetically together"
        )


class TestTreeGeneratorFormat:
    """Test suite for tree structure formatting and indentation."""

    def test_generate_tree_structure_format(self, tmp_path: Path) -> None:
        """Test complete tree structure with correct indentation and symbols."""
        # Arrange
        (tmp_path / ".git").mkdir()  # should be ignored
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("content")
        (tmp_path / "src" / "utils").mkdir()
        (tmp_path / "src" / "utils" / "helper.py").write_text("content")
        (tmp_path / "README.md").write_text("content")

        generator = TreeGenerator()

        # Act - No max_depth parameter, full depth traversal
        result = generator.generate(tmp_path)

        # Assert - Full depth including helper.py
        expected_lines = [
            f"{tmp_path.name}/",
            "├── README.md",
            "└── src/",
            "    ├── main.py",
            "    └── utils/",
            "        └── helper.py",
        ]
        expected = "\n".join(expected_lines)

        # Verify exact match including order and completeness
        assert result.tree_string.strip().splitlines() == expected.splitlines(), (
            f"Tree structure mismatch.\nExpected:\n{expected}\n\nGot:\n{result.tree_string.strip()}"
        )

        # Verify that .git is not in output
        assert ".git" not in result.tree_string

    def test_generate_uses_tree_symbols(self, tmp_path: Path) -> None:
        """Test that correct tree symbols are used for structure."""
        # Arrange
        (tmp_path / "first.py").write_text("content")
        (tmp_path / "second.py").write_text("content")
        (tmp_path / "third.py").write_text("content")

        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert
        assert "├──" in result.tree_string, "Should contain branch symbol ├──"
        assert "└──" in result.tree_string, "Should contain last item symbol └──"

    def test_generate_indentation_consistency(self, tmp_path: Path) -> None:
        """Test that indentation is consistent across levels."""
        # Arrange
        (tmp_path / "level1").mkdir()
        (tmp_path / "level1" / "level2").mkdir()
        (tmp_path / "level1" / "level2" / "file.py").write_text("content")

        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert
        lines = result.tree_string.strip().split("\n")

        # Define valid tree prefix patterns
        # Level 1: starts directly with tree symbol
        level1_prefixes = ("├── ", "└── ")
        # Level 2: one indent unit (4 chars: spaces or vertical line) + tree symbol
        level2_prefixes = ("    ├── ", "    └── ", "│   ├── ", "│   └── ")
        # Level 3: two indent units (8 chars) + tree symbol
        level3_prefixes = (
            "        ├── ",
            "        └── ",
            "    │   ├── ",
            "    │   └── ",
            "│   │   ├── ",
            "│   │   └── ",
            "│       ├── ",
            "│       └── ",
        )

        level1_line = None
        level2_line = None
        level3_line = None

        for line in lines:
            if "level1/" in line:
                level1_line = line
                # Level 1 should start with tree symbol (no prefix)
                assert any(line.startswith(p) for p in level1_prefixes), (
                    f"Level 1 should start with tree symbol, got: {line}"
                )
            elif "level2/" in line:
                level2_line = line
                # Level 2 should have valid prefix pattern (one indent unit)
                assert any(line.startswith(p) for p in level2_prefixes), (
                    f"Level 2 should have valid indent prefix, got: {line}"
                )
            elif "file.py" in line:
                level3_line = line
                # Level 3 should have valid prefix pattern (two indent units)
                assert any(line.startswith(p) for p in level3_prefixes), (
                    f"Level 3 should have valid indent prefix, got: {line}"
                )

        # Verify deeper levels have more indentation than shallower levels
        if level1_line and level2_line:
            level1_indent = len(level1_line) - len(level1_line.lstrip())
            level2_indent = len(level2_line) - len(level2_line.lstrip())
            assert level2_indent > level1_indent, (
                "Level 2 should have more indentation than level 1"
            )

        if level2_line and level3_line:
            level2_indent = len(level2_line) - len(level2_line.lstrip())
            level3_indent = len(level3_line) - len(level3_line.lstrip())
            assert level3_indent > level2_indent, (
                "Level 3 should have more indentation than level 2"
            )


class TestTreeGeneratorEdgeCases:
    """Test suite for edge cases and error handling."""

    def test_generate_with_nonexistent_path(self) -> None:
        """Test that generate raises ValueError for non-existent path."""
        # Arrange
        generator = TreeGenerator()
        nonexistent_path = Path("/nonexistent/path/that/does/not/exist")

        # Act & Assert
        with pytest.raises(ValueError, match="Path does not exist"):
            generator.generate(nonexistent_path)

    def test_generate_with_file_instead_of_directory(self, tmp_path: Path) -> None:
        """Test that generate raises ValueError when path is a file, not directory."""
        # Arrange
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")
        generator = TreeGenerator()

        # Act & Assert
        with pytest.raises(ValueError, match="Path is not a directory"):
            generator.generate(file_path)

    def test_generate_with_special_characters_in_names(self, tmp_path: Path) -> None:
        """Test tree generation with special characters in file/directory names."""
        # Arrange
        (tmp_path / "file-with-dashes.py").write_text("content")
        (tmp_path / "file_with_underscores.py").write_text("content")
        (tmp_path / "file.with.dots.py").write_text("content")
        (tmp_path / "folder-name").mkdir()

        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert
        assert "file-with-dashes.py" in result.tree_string
        assert "file_with_underscores.py" in result.tree_string
        assert "file.with.dots.py" in result.tree_string
        assert "folder-name/" in result.tree_string

    def test_generate_skips_unreadable_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that unreadable directories are silently skipped during traversal."""
        # Arrange
        (tmp_path / "readable").mkdir()
        (tmp_path / "readable" / "file.py").write_text("content")
        (tmp_path / "unreadable").mkdir()
        (tmp_path / "other.py").write_text("content")
        generator = TreeGenerator()

        # Store original iterdir
        original_iterdir = Path.iterdir

        # Mock iterdir to raise PermissionError for 'unreadable' directory
        def mock_iterdir(self: Path) -> "Iterator[Path]":
            if self.name == "unreadable":
                raise PermissionError("Permission denied")
            return original_iterdir(self)

        monkeypatch.setattr(Path, "iterdir", mock_iterdir)

        # Act
        result = generator.generate(tmp_path)

        # Assert - Traversal continues, unreadable dir is shown but empty
        assert "readable/" in result.tree_string
        assert "file.py" in result.tree_string
        assert "unreadable/" in result.tree_string  # Dir itself is listed
        assert "other.py" in result.tree_string
        # The unreadable directory should be counted but its contents skipped
        assert result.total_folders == 2  # readable and unreadable
