"""File content reader with encoding fallback support.

This module provides robust file reading capabilities with automatic
encoding detection and fallback handling for common encoding issues.
"""

from pathlib import Path


class ContentReadError(Exception):
    """Raised when file content cannot be read with supported encodings."""

    pass


class ContentReader:
    """Read file content with automatic encoding fallback.

    This class provides robust file reading with UTF-8 as primary encoding
    and Latin-1 as fallback. Handles common encoding issues gracefully.

    Encoding strategy:
    1. Try UTF-8 (most common, supports all Unicode)
    2. Fallback to Latin-1 (covers Western European encodings)
    3. Raise ContentReadError if both fail

    Example:
        >>> reader = ContentReader()
        >>> content = reader.read_file(Path("src/main.py"))
        >>> print(content)
        def main():
            pass
    """

    def __init__(self) -> None:
        """Initialize ContentReader."""
        pass

    def read_file(self, path: Path) -> str:
        """Read file content with encoding fallback.

        Attempts to read file with UTF-8 encoding first. If that fails with
        UnicodeDecodeError, falls back to Latin-1. If file doesn't exist,
        contains binary data (null bytes), or both encodings fail, raises
        ContentReadError.

        Args:
            path: Path to file to read.

        Returns:
            File content as string.

        Raises:
            ContentReadError: If file doesn't exist, cannot be read (e.g.,
                permission denied), contains binary data, or cannot be
                decoded with UTF-8 or Latin-1.
        """
        # Check if file exists
        if not path.exists():
            raise ContentReadError(f"File does not exist: {path}")

        # Read raw bytes with OSError handling for permission issues etc.
        try:
            raw_bytes = path.read_bytes()
        except OSError as e:
            raise ContentReadError(f"Cannot read file {path}: {e}") from e

        # Check for binary content (null bytes indicate binary file)
        if b"\x00" in raw_bytes:
            raise ContentReadError(f"File appears to be binary: {path}")

        # Try UTF-8 first
        try:
            return raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            # Fallback to Latin-1 (always succeeds as it accepts all byte values)
            return raw_bytes.decode("latin-1")
