"""Tests for setup_check.py verification script.

This module tests the automated setup verification script that validates
the project's toolchain configuration.
"""

from unittest.mock import MagicMock, patch


class TestRunCommand:
    """Test suite for the run_command function."""

    @patch("subprocess.run")
    def test_run_command_success(self, mock_run: MagicMock) -> None:
        """Test run_command returns True when command succeeds."""
        # Arrange
        from setup_check import run_command

        mock_run.return_value = MagicMock(returncode=0, stderr="")

        # Act
        result = run_command(["echo", "test"], "Test command")

        # Assert
        assert result is True
        mock_run.assert_called_once_with(
            ["echo", "test"], capture_output=True, text=True
        )

    @patch("subprocess.run")
    def test_run_command_failure(self, mock_run: MagicMock) -> None:
        """Test run_command returns False when command fails."""
        # Arrange
        from setup_check import run_command

        mock_run.return_value = MagicMock(returncode=1, stderr="Error occurred")

        # Act
        result = run_command(["false"], "Failing command")

        # Assert
        assert result is False
        mock_run.assert_called_once_with(
            ["false"], capture_output=True, text=True
        )

    @patch("subprocess.run")
    @patch("builtins.print")
    def test_run_command_prints_success_message(
        self, mock_print: MagicMock, mock_run: MagicMock
    ) -> None:
        """Test run_command prints success message with checkmark."""
        # Arrange
        from setup_check import run_command

        mock_run.return_value = MagicMock(returncode=0, stderr="")

        # Act
        run_command(["echo", "test"], "Test command")

        # Assert
        # Check that print was called with success indicator
        calls = [str(call) for call in mock_print.call_args_list]
        assert any("✓" in call or "Test command" in call for call in calls)

    @patch("subprocess.run")
    @patch("builtins.print")
    def test_run_command_prints_failure_message(
        self, mock_print: MagicMock, mock_run: MagicMock
    ) -> None:
        """Test run_command prints failure message with X mark."""
        # Arrange
        from setup_check import run_command

        mock_run.return_value = MagicMock(returncode=1, stderr="Error occurred")

        # Act
        run_command(["false"], "Failing command")

        # Assert
        # Check that print was called with failure indicator
        calls = [str(call) for call in mock_print.call_args_list]
        assert any("✗" in call or "Error occurred" in call for call in calls)


class TestMain:
    """Test suite for the main function."""

    @patch("setup_check.run_command")
    @patch("sys.version_info")
    def test_main_success_all_checks_pass(
        self, mock_version_info: MagicMock, mock_run_command: MagicMock
    ) -> None:
        """Test main returns 0 when all checks pass."""
        # Arrange
        from setup_check import main

        mock_version_info.major = 3
        mock_version_info.minor = 11
        mock_version_info.__getitem__ = lambda _, key: (3, 11)[key]
        mock_run_command.return_value = True

        # Act
        result = main()

        # Assert
        assert result == 0
        # Verify all expected commands were run
        assert mock_run_command.call_count >= 5  # At least 5 checks

    @patch("setup_check.run_command")
    @patch("sys.version_info")
    def test_main_failure_when_check_fails(
        self, mock_version_info: MagicMock, mock_run_command: MagicMock
    ) -> None:
        """Test main returns 1 when any check fails."""
        # Arrange
        from setup_check import main

        mock_version_info.major = 3
        mock_version_info.minor = 11
        mock_version_info.__getitem__ = lambda _, key: (3, 11)[key]
        # First command succeeds, second fails
        mock_run_command.side_effect = [True, False, True, True, True]

        # Act
        result = main()

        # Assert
        assert result == 1

    @patch("setup_check.run_command")
    @patch("sys.version_info")
    def test_main_checks_python_version(
        self, mock_version_info: MagicMock, mock_run_command: MagicMock
    ) -> None:
        """Test main checks Python version is >= 3.11."""
        # Arrange
        from setup_check import main

        mock_version_info.major = 3
        mock_version_info.minor = 10  # Below minimum
        mock_version_info.__getitem__ = lambda _, key: (3, 10)[key]
        mock_run_command.return_value = True

        # Act
        result = main()

        # Assert
        assert result == 1  # Should fail due to version

    @patch("setup_check.run_command")
    @patch("sys.version_info")
    def test_main_runs_pip_install(
        self, mock_version_info: MagicMock, mock_run_command: MagicMock
    ) -> None:
        """Test main runs pip install command."""
        # Arrange
        from setup_check import main

        mock_version_info.major = 3
        mock_version_info.minor = 11
        mock_version_info.__getitem__ = lambda _, key: (3, 11)[key]
        mock_run_command.return_value = True

        # Act
        main()

        # Assert
        # Check that pip install was called
        calls = [call[0][0] for call in mock_run_command.call_args_list]
        assert any("pip" in cmd for cmd in calls if isinstance(cmd, list))

    @patch("setup_check.run_command")
    @patch("sys.version_info")
    def test_main_runs_pytest(
        self, mock_version_info: MagicMock, mock_run_command: MagicMock
    ) -> None:
        """Test main runs pytest command."""
        # Arrange
        from setup_check import main

        mock_version_info.major = 3
        mock_version_info.minor = 11
        mock_version_info.__getitem__ = lambda _, key: (3, 11)[key]
        mock_run_command.return_value = True

        # Act
        main()

        # Assert
        # Check that pytest was called
        calls = [call[0][0] for call in mock_run_command.call_args_list]
        assert any("pytest" in cmd for cmd in calls if isinstance(cmd, list))

    @patch("setup_check.run_command")
    @patch("sys.version_info")
    def test_main_runs_mypy(
        self, mock_version_info: MagicMock, mock_run_command: MagicMock
    ) -> None:
        """Test main runs mypy command."""
        # Arrange
        from setup_check import main

        mock_version_info.major = 3
        mock_version_info.minor = 11
        mock_version_info.__getitem__ = lambda _, key: (3, 11)[key]
        mock_run_command.return_value = True

        # Act
        main()

        # Assert
        # Check that mypy was called
        calls = [call[0][0] for call in mock_run_command.call_args_list]
        assert any("mypy" in cmd for cmd in calls if isinstance(cmd, list))

    @patch("setup_check.run_command")
    @patch("sys.version_info")
    def test_main_runs_ruff(
        self, mock_version_info: MagicMock, mock_run_command: MagicMock
    ) -> None:
        """Test main runs ruff check command."""
        # Arrange
        from setup_check import main

        mock_version_info.major = 3
        mock_version_info.minor = 11
        mock_version_info.__getitem__ = lambda _, key: (3, 11)[key]
        mock_run_command.return_value = True

        # Act
        main()

        # Assert
        # Check that ruff was called
        calls = [call[0][0] for call in mock_run_command.call_args_list]
        assert any("ruff" in cmd for cmd in calls if isinstance(cmd, list))

    @patch("setup_check.run_command")
    @patch("sys.version_info")
    def test_main_runs_mkdocs(
        self, mock_version_info: MagicMock, mock_run_command: MagicMock
    ) -> None:
        """Test main runs mkdocs build command."""
        # Arrange
        from setup_check import main

        mock_version_info.major = 3
        mock_version_info.minor = 11
        mock_version_info.__getitem__ = lambda _, key: (3, 11)[key]
        mock_run_command.return_value = True

        # Act
        main()

        # Assert
        # Check that mkdocs was called
        calls = [call[0][0] for call in mock_run_command.call_args_list]
        assert any("mkdocs" in cmd for cmd in calls if isinstance(cmd, list))

    @patch("setup_check.run_command")
    @patch("sys.version_info")
    @patch("builtins.print")
    def test_main_prints_header(
        self,
        mock_print: MagicMock,
        mock_version_info: MagicMock,
        mock_run_command: MagicMock,
    ) -> None:
        """Test main prints header message."""
        # Arrange
        from setup_check import main

        mock_version_info.major = 3
        mock_version_info.minor = 11
        mock_version_info.__getitem__ = lambda _, key: (3, 11)[key]
        mock_run_command.return_value = True

        # Act
        main()

        # Assert
        calls = [str(call) for call in mock_print.call_args_list]
        assert any("Codemap Setup Verification" in call for call in calls)

    @patch("setup_check.run_command")
    @patch("sys.version_info")
    @patch("builtins.print")
    def test_main_prints_success_summary(
        self,
        mock_print: MagicMock,
        mock_version_info: MagicMock,
        mock_run_command: MagicMock,
    ) -> None:
        """Test main prints success summary when all checks pass."""
        # Arrange
        from setup_check import main

        mock_version_info.major = 3
        mock_version_info.minor = 11
        mock_version_info.__getitem__ = lambda _, key: (3, 11)[key]
        mock_run_command.return_value = True

        # Act
        main()

        # Assert
        calls = [str(call) for call in mock_print.call_args_list]
        assert any("All checks passed" in call for call in calls)

    @patch("setup_check.run_command")
    @patch("sys.version_info")
    @patch("builtins.print")
    def test_main_prints_failure_summary(
        self,
        mock_print: MagicMock,
        mock_version_info: MagicMock,
        mock_run_command: MagicMock,
    ) -> None:
        """Test main prints failure summary when any check fails."""
        # Arrange
        from setup_check import main

        mock_version_info.major = 3
        mock_version_info.minor = 11
        mock_version_info.__getitem__ = lambda _, key: (3, 11)[key]
        mock_run_command.return_value = False

        # Act
        main()

        # Assert
        calls = [str(call) for call in mock_print.call_args_list]
        assert any("failed" in call.lower() for call in calls)
