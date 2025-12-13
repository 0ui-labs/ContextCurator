"""File walker for discovering files in a directory with pattern matching.

This module provides FileWalker class for discovering files in a directory
and returning FileEntry objects with metadata (path, size, token estimation).
Supports pattern-based exclusion using gitignore-style wildcards.
"""

from pathlib import Path

import pathspec

from codemap.scout.models import FileEntry

# Hard ignores: directories that should NEVER be re-included via negation patterns.
# These are system/tooling directories that should always be excluded for performance
# and safety reasons. Early pruning is applied to these directories.
HARD_IGNORES: set[str] = {
    ".git",
    ".venv",
    "__pycache__",
}

# Files to always ignore (meta-files).
# These are configuration/control files that should not be treated as project content.
# Consistent with TreeGenerator.IGNORED_FILES for uniform behavior across scout modules.
IGNORED_FILES: set[str] = {".gitignore"}

# Directories to ignore by default (polyglot defaults for common ecosystems).
# These can be re-included via negation patterns in .gitignore or user patterns.
# All matching is done via PathSpec to support gitignore-style negation (e.g., !dist/keep.txt).
DEFAULT_IGNORES: set[str] = {
    # --- System / SCM ---
    ".git",
    ".svn",
    ".hg",
    ".fslckout",
    "_darcs",
    ".bzr",
    ".DS_Store",
    "Thumbs.db",
    # --- General Build / Dependencies ---
    "dist",
    "build",
    "out",
    "target",
    "bin",
    "obj",
    "vendor",  # PHP (Composer), Go, Ruby
    # --- Node / Web / JS / TS ---
    "node_modules",
    "bower_components",
    ".npm",
    ".yarn",
    ".pnpm-store",
    ".next",
    ".nuxt",
    ".output",
    ".astro",
    ".svelte-kit",
    ".vercel",
    ".netlify",
    ".cache",
    ".parcel-cache",
    ".turbo",
    "coverage",
    ".nyc_output",
    # --- Python ---
    ".venv",
    "venv",
    "env",
    ".env",
    "virtualenv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".hypothesize",
    "htmlcov",
    ".coverage",
    "cover",
    ".tox",
    ".nox",
    "site-packages",
    # --- PHP / WordPress ---
    ".phpunit.cache",
    ".php-cs-fixer.cache",
    "wp-admin",
    "wp-includes",  # WordPress Core
    # --- Dart / Flutter ---
    ".dart_tool",
    ".pub-cache",
    ".flutter-plugins",
    ".flutter-plugins-dependencies",
    # --- Java / JVM ---
    ".gradle",
    "gradle",
    ".settings",
    ".classpath",
    ".project",
    # --- .NET ---
    "packages",
    "TestResults",
    ".vs",
    # --- C / C++ ---
    "cmake-build-debug",
    "cmake-build-release",
    "CMakeFiles",
    # --- Go ---
    "pkg",
    # --- IDEs ---
    ".idea",
    ".vscode",
}

# Wildcard patterns that require pathspec matching (cannot be used for direct name comparison)
# These are applied via PathSpec.from_lines() only, not in early pruning optimization
DEFAULT_PATHSPEC_PATTERNS: list[str] = [
    "*.egg-info",  # Python egg metadata directories (e.g., mypackage.egg-info)
]


class FileWalker:
    """Discover files in a directory and return FileEntry objects with metadata.

    This class walks a directory tree and collects file information, excluding
    files and directories based on multiple ignore sources combined additively.

    Ignore sources (all applied together):
    1. HARD_IGNORES - Directories that are ALWAYS excluded and cannot be re-included:
       - .git, .venv, __pycache__
       These are excluded early for performance and safety reasons.
    2. IGNORED_FILES - Meta-files that are always excluded:
       - .gitignore
       Consistent with TreeGenerator.IGNORED_FILES for uniform behavior.
    3. DEFAULT_IGNORES - Built-in patterns for common junk directories across
       multiple programming ecosystems. These CAN be re-included via negation
       patterns (e.g., !dist/keep.txt):
       - System/SCM: .git, .svn, .hg, .bzr, .DS_Store, Thumbs.db
       - Build: dist, build, out, target, bin, obj
       - Node/Web: node_modules, bower_components, .next, .nuxt, coverage
       - Python: .venv, venv, __pycache__, .pytest_cache, .mypy_cache, htmlcov
       - PHP/WordPress: wp-admin, wp-includes, .phpunit.cache
       - Dart/Flutter: .dart_tool, .pub-cache
       - Java/JVM: .gradle, .settings, .classpath, .project
       - .NET: packages, TestResults, .vs
       - C/C++: cmake-build-debug, cmake-build-release, CMakeFiles
       - Go: pkg
       - IDEs: .idea, .vscode
    4. Local .gitignore - Patterns from .gitignore file in root directory
       (always read if present, regardless of ignore_patterns argument).
       Supports negation patterns (e.g., !dist/keep.txt) to re-include files.
    5. User patterns - Additional patterns passed via ignore_patterns argument

    Pattern matching uses pathspec library for gitignore-style wildcards:
    - *.tmp - matches all .tmp files
    - *.log - matches all .log files
    - node_modules/ - matches entire directory
    - test_*.py - matches files with wildcards
    - !dist/keep.txt - negation pattern to re-include specific files

    Returns:
    - List of FileEntry objects sorted alphabetically by path
    - Each FileEntry contains: path (relative Path), size (bytes), token_est (size // 4)
    """

    def __init__(self) -> None:
        """Initialize FileWalker."""

    def _load_gitignore(self, root: Path) -> list[str]:
        """Load patterns from .gitignore file in root directory.

        Args:
            root: Root directory to check for .gitignore file.

        Returns:
            List of patterns from .gitignore, or empty list if file doesn't exist.
        """
        gitignore_path = root / ".gitignore"
        if not gitignore_path.exists():
            return []

        patterns: list[str] = []
        try:
            content = gitignore_path.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith("#"):
                    patterns.append(line)
        except (OSError, UnicodeError):
            # If we can't read the file, just return empty list
            return []

        return patterns

    def walk(self, root: Path, ignore_patterns: list[str] | None = None) -> list[FileEntry]:
        """Walk directory tree and collect file information.

        Traverses the directory tree starting from root, collecting FileEntry
        objects for each file found. Results are sorted alphabetically.

        Exclusion behavior:
        Files and directories are excluded based on three sources combined
        additively: DEFAULT_IGNORES + local .gitignore + ignore_patterns.
        The .gitignore file is always read from root directory if present,
        regardless of whether ignore_patterns is provided.

        Args:
            root: Root directory to walk (must exist and be a directory).
            ignore_patterns: Optional list of additional gitignore-style patterns
                to exclude files/dirs. These are applied ON TOP OF DEFAULT_IGNORES
                and local .gitignore patterns. Defaults to None.
                Examples: ["*.tmp", "*.log", "node_modules/", "test_*.py"]

        Returns:
            List of FileEntry objects sorted alphabetically by path.
            Each entry contains relative path, size in bytes, and estimated tokens.

        Raises:
            ValueError: If root does not exist or is not a directory.
        """
        # Normalize ignore_patterns to empty list if None
        if ignore_patterns is None:
            ignore_patterns = []

        # Input validation
        if not root.exists():
            msg = f"Path does not exist: {root}"
            raise ValueError(msg)

        if not root.is_dir():
            msg = f"Path is not a directory: {root}"
            raise ValueError(msg)

        # Load patterns from local .gitignore file
        gitignore_patterns = self._load_gitignore(root)

        # Compile patterns: DEFAULT_IGNORES + pathspec wildcards + .gitignore + user patterns
        all_patterns = (
            list(DEFAULT_IGNORES) + DEFAULT_PATHSPEC_PATTERNS + gitignore_patterns + ignore_patterns
        )
        spec = pathspec.PathSpec.from_lines("gitwildmatch", all_patterns)

        entries: list[FileEntry] = []

        # Directory traversal
        for path in root.rglob("*"):
            # Skip directories - only collect files
            # Handle OSError in case is_dir() fails (e.g., permission denied)
            try:
                is_directory = path.is_dir()
            except OSError:
                continue
            if is_directory:
                continue

            # Calculate relative path
            relative_path = path.relative_to(root)

            # Early pruning: skip files within hard-ignored directories (.git, .venv, __pycache__)
            # These directories should NEVER be re-included via negation patterns.
            # Other DEFAULT_IGNORES are handled by PathSpec to support re-includes.
            if any(part in HARD_IGNORES for part in relative_path.parts):
                continue

            # Skip meta-files (e.g., .gitignore) - consistent with TreeGenerator.IGNORED_FILES
            if relative_path.name in IGNORED_FILES:
                continue

            # Normalize for cross-platform pattern matching
            pattern_path = str(relative_path).replace("\\", "/")

            # Check against pathspec (user-specified patterns)
            if spec.match_file(pattern_path):
                continue

            # Collect metadata with error handling for inaccessible files
            try:
                size = path.stat().st_size
                token_est = size // 4
                entries.append(FileEntry(path=relative_path, size=size, token_est=token_est))
            except OSError:
                # Skip files that become inaccessible (permission errors, etc.)
                continue

        # Sort alphabetically by path (case-sensitive string comparison)
        entries.sort(key=lambda e: str(e.path))

        return entries
