"""Unit tests for TreeGenerator in codemap.scout.tree module."""

from pathlib import Path

import pytest

from codemap.scout.tree import TreeGenerator


class TestTreeGeneratorBasic:
    """Test suite for basic TreeGenerator functionality."""

    def test_generate_returns_string(self, tmp_path: Path) -> None:
        """Test that generate method returns a string."""
        # Arrange
        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert
        assert isinstance(result, str)

    def test_generate_empty_directory(self, tmp_path: Path) -> None:
        """Test tree generation for empty directory."""
        # Arrange
        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert
        assert isinstance(result, str)
        assert f"{tmp_path.name}/" in result

    def test_generate_single_file(self, tmp_path: Path) -> None:
        """Test tree generation for directory with single file."""
        # Arrange
        (tmp_path / "README.md").write_text("content")
        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert
        assert isinstance(result, str)
        assert "README.md" in result

    def test_generate_single_directory(self, tmp_path: Path) -> None:
        """Test tree generation for directory with single subdirectory."""
        # Arrange
        (tmp_path / "src").mkdir()
        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)

        # Assert
        assert isinstance(result, str)
        assert "src/" in result


class TestTreeGeneratorMaxDepth:
    """Test suite for max_depth parameter functionality."""

    def test_generate_respects_max_depth_default(self, tmp_path: Path) -> None:
        """Test that default max_depth=2 is respected."""
        # Arrange
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("content")
        (tmp_path / "src" / "utils").mkdir()
        (tmp_path / "src" / "utils" / "helper.py").write_text("content")  # Depth 2
        (tmp_path / "src" / "utils" / "deep").mkdir()
        (tmp_path / "src" / "utils" / "deep" / "nested.py").write_text(
            "content"
        )  # Depth 3

        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path)  # default max_depth=2

        # Assert
        assert "main.py" in result
        assert "utils/" in result
        assert "helper.py" in result
        assert "nested.py" not in result  # Depth 3 should not be shown

    def test_generate_max_depth_zero(self, tmp_path: Path) -> None:
        """Test tree generation with max_depth=0 shows only root."""
        # Arrange
        (tmp_path / "README.md").write_text("content")
        (tmp_path / "src").mkdir()
        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path, max_depth=0)

        # Assert
        assert f"{tmp_path.name}/" in result
        assert "README.md" not in result
        assert "src/" not in result

    def test_generate_max_depth_one(self, tmp_path: Path) -> None:
        """Test tree generation with max_depth=1 shows root and direct children."""
        # Arrange
        (tmp_path / "README.md").write_text("content")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("content")
        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path, max_depth=1)

        # Assert
        assert "README.md" in result
        assert "src/" in result
        assert "main.py" not in result  # Depth 2, should not be shown

    def test_generate_max_depth_three(self, tmp_path: Path) -> None:
        """Test tree generation with max_depth=3 shows deeper nesting."""
        # Arrange
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "utils").mkdir()
        (tmp_path / "src" / "utils" / "deep").mkdir()
        (tmp_path / "src" / "utils" / "deep" / "nested.py").write_text("content")
        (tmp_path / "src" / "utils" / "deep" / "very_deep").mkdir()
        (tmp_path / "src" / "utils" / "deep" / "very_deep" / "file.py").write_text(
            "content"
        )

        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path, max_depth=3)

        # Assert
        assert "utils/" in result
        assert "deep/" in result
        assert "nested.py" in result
        assert "file.py" not in result  # Depth 4, should not be shown


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
        result = generator.generate(tmp_path, max_depth=5)

        # Assert
        assert ".git" not in result
        assert "config" not in result
        assert "README.md" in result

    def test_generate_ignores_venv_directory(self, tmp_path: Path) -> None:
        """Test that .venv directory is always ignored."""
        # Arrange
        (tmp_path / ".venv").mkdir()
        (tmp_path / ".venv" / "lib").mkdir()
        (tmp_path / ".venv" / "lib" / "python.py").write_text("content")
        (tmp_path / "main.py").write_text("content")

        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path, max_depth=5)

        # Assert
        assert ".venv" not in result
        assert "lib" not in result
        assert "python.py" not in result
        assert "main.py" in result

    def test_generate_ignores_pycache_directory(self, tmp_path: Path) -> None:
        """Test that __pycache__ directory is always ignored."""
        # Arrange
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "module.pyc").write_text("content")
        (tmp_path / "module.py").write_text("content")

        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path, max_depth=5)

        # Assert
        assert "__pycache__" not in result
        assert "module.pyc" not in result
        assert "module.py" in result

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
        result = generator.generate(tmp_path, max_depth=5)

        # Assert
        assert ".git" not in result
        assert ".venv" not in result
        assert "__pycache__" not in result
        assert "config" not in result
        assert "lib" not in result
        assert "cache.pyc" not in result
        assert "README.md" in result
        assert "src/" in result
        assert "main.py" in result


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
        lines = result.strip().split("\n")
        alpha_idx = next(i for i, line in enumerate(lines) if "alpha.py" in line)
        beta_idx = next(i for i, line in enumerate(lines) if "beta.py" in line)
        zebra_idx = next(i for i, line in enumerate(lines) if "zebra.py" in line)

        assert (
            alpha_idx < beta_idx < zebra_idx
        ), "Files should be sorted alphabetically"

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
        lines = result.strip().split("\n")
        alpha_idx = next(i for i, line in enumerate(lines) if "alpha/" in line)
        beta_idx = next(i for i, line in enumerate(lines) if "beta/" in line)
        zebra_idx = next(i for i, line in enumerate(lines) if "zebra/" in line)

        assert (
            alpha_idx < beta_idx < zebra_idx
        ), "Directories should be sorted alphabetically"

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
        lines = result.strip().split("\n")
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

        # Act
        result = generator.generate(tmp_path, max_depth=2)

        # Assert
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
        assert result.strip().splitlines() == expected.splitlines(), (
            f"Tree structure mismatch.\nExpected:\n{expected}\n\nGot:\n{result.strip()}"
        )

        # Verify that .git is not in output
        assert ".git" not in result

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
        assert "├──" in result, "Should contain branch symbol ├──"
        assert "└──" in result, "Should contain last item symbol └──"

    def test_generate_indentation_consistency(self, tmp_path: Path) -> None:
        """Test that indentation is consistent across levels."""
        # Arrange
        (tmp_path / "level1").mkdir()
        (tmp_path / "level1" / "level2").mkdir()
        (tmp_path / "level1" / "level2" / "file.py").write_text("content")

        generator = TreeGenerator()

        # Act
        result = generator.generate(tmp_path, max_depth=3)

        # Assert
        lines = result.strip().split("\n")

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

    def test_generate_raises_error_for_negative_max_depth(self, tmp_path: Path) -> None:
        """Test that generate raises ValueError for negative max_depth."""
        # Arrange
        generator = TreeGenerator()

        # Act & Assert
        with pytest.raises(ValueError, match="max_depth must be non-negative"):
            generator.generate(tmp_path, max_depth=-1)

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
        assert "file-with-dashes.py" in result
        assert "file_with_underscores.py" in result
        assert "file.with.dots.py" in result
        assert "folder-name/" in result
