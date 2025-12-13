"""Unit tests for mapper.reader module."""

import pytest
from pathlib import Path

from codemap.mapper.reader import ContentReader, ContentReadError


class TestContentReader:
    """Test suite for ContentReader class."""

    def test_read_utf8_file(self, tmp_path):
        """Test reading UTF-8 encoded file with emoji."""
        test_file = tmp_path / "test_utf8.py"
        content = "# Python code with emoji 🚀\ndef hello():\n    print('Hello, World!')\n"
        test_file.write_text(content, encoding="utf-8")

        reader = ContentReader()
        result = reader.read_file(test_file)
        assert result == content
        assert "🚀" in result

    def test_read_latin1_fallback(self, tmp_path):
        """Test reading Latin-1 encoded file with umlauts (fallback)."""
        test_file = tmp_path / "test_latin1.py"
        content = "# German umlauts: ä, ö, ü\ndef grüße():\n    print('Hällö')\n"
        test_file.write_bytes(content.encode("latin-1"))

        reader = ContentReader()
        result = reader.read_file(test_file)
        assert "ä" in result
        assert "ö" in result
        assert "ü" in result
        assert "grüße" in result

    def test_read_nonexistent_file_raises_error(self):
        """Test reading non-existent file raises ContentReadError."""
        reader = ContentReader()
        nonexistent_path = Path("/nonexistent/file/path.py")

        with pytest.raises(ContentReadError):
            reader.read_file(nonexistent_path)

    def test_read_binary_file_raises_error(self, tmp_path):
        """Test reading binary file raises ContentReadError."""
        test_file = tmp_path / "test_binary.bin"
        test_file.write_bytes(bytes([0xFF, 0xFE, 0x00, 0x01, 0x80, 0x90]))

        reader = ContentReader()
        with pytest.raises(ContentReadError):
            reader.read_file(test_file)

    def test_read_empty_file(self, tmp_path):
        """Test reading empty file returns empty string."""
        test_file = tmp_path / "empty.py"
        test_file.write_text("", encoding="utf-8")

        reader = ContentReader()
        result = reader.read_file(test_file)
        assert result == ""
