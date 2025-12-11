"""Automated setup verification script for Codemap project.

This script verifies the entire toolchain configuration by running
all quality checks: tests, coverage, type checking, linting, and
documentation build.
"""

import subprocess
import sys


def run_command(cmd: list[str], description: str) -> bool:
    """Execute a command and report success or failure.

    Args:
        cmd: Command to execute as a list of strings
        description: Human-readable description of the command

    Returns:
        True if command succeeded (returncode == 0), False otherwise
    """
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"✓ {description}")
        return True
    else:
        print(f"✗ {description}")
        if result.stderr:
            print(f"  Error: {result.stderr}")
        return False


def main() -> int:
    """Run all setup verification checks.

    Returns:
        0 if all checks passed, 1 otherwise
    """
    print("🔍 Codemap Setup Verification")
    print("=" * 50)

    checks_passed = []

    # Step 1: Check Python version
    print("\nChecking Python version...")
    if sys.version_info[:2] >= (3, 11):
        print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} (>= 3.11)")
        checks_passed.append(True)
    else:
        print(
            f"✗ Python {sys.version_info.major}.{sys.version_info.minor} "
            f"(requires >= 3.11)"
        )
        checks_passed.append(False)

    # Step 2: Install dependencies
    print("\nInstalling dependencies...")
    checks_passed.append(
        run_command(
            [sys.executable, "-m", "pip", "install", "-r", "requirements-dev.txt"],
            "Installing dependencies",
        )
    )

    # Step 3: Run pytest with coverage
    print("\nRunning tests...")
    checks_passed.append(
        run_command(["pytest"], "Running tests with coverage")
    )

    # Step 4: Check coverage threshold (already handled by pytest with fail_under)
    # The pytest command above will fail if coverage is below 100%

    # Step 5: Run mypy type checking
    print("\nType checking...")
    checks_passed.append(
        run_command(["mypy", "src/"], "Type checking with mypy")
    )

    # Step 6: Run ruff linting
    print("\nLinting...")
    checks_passed.append(
        run_command(
            ["ruff", "check", "src/", "tests/"],
            "Linting with ruff",
        )
    )

    # Step 7: Build documentation
    print("\nBuilding documentation...")
    checks_passed.append(
        run_command(
            ["mkdocs", "build", "--strict"],
            "Building documentation",
        )
    )

    # Print summary
    print("\n" + "=" * 50)
    if all(checks_passed):
        print("✅ All checks passed! Project is ready to code.")
        return 0
    else:
        print("❌ Some checks failed. See errors above.")
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
