"""Unit tests for LLMProvider Protocol in codemap.core.llm module.

This module tests the LLMProvider Protocol which defines the interface for
all LLM provider implementations. Tests cover:
- Protocol existence and importability
- Method signature verification (send method)
- Parameter type annotations
- Return type annotations
- Comprehensive docstring presence
"""

import os
from typing import Protocol, get_type_hints
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from codemap.core.llm import CerebrasProvider, LLMProvider, MockProvider, get_provider


class TestLLMProviderProtocol:
    """Test suite for LLMProvider Protocol definition."""

    def test_llm_provider_is_protocol(self) -> None:
        """Test that LLMProvider is a Protocol class.

        Note: We check for the _is_protocol attribute which is set by typing.Protocol
        at class creation time. This is the runtime-safe way to verify Protocol status
        since issubclass(X, Protocol) doesn't work with mypy strict mode.
        """
        # Assert - Protocol classes have _is_protocol attribute set to True
        assert getattr(LLMProvider, "_is_protocol", False) is True

    def test_llm_provider_has_send_method(self) -> None:
        """Test that LLMProvider Protocol defines send method."""
        # Assert
        assert hasattr(LLMProvider, "send")
        assert callable(getattr(LLMProvider, "send"))

    def test_send_method_signature(self) -> None:
        """Test that send method has correct parameter and return type annotations."""
        # Arrange
        send_method = getattr(LLMProvider, "send")
        type_hints = get_type_hints(send_method)

        # Assert - Check parameter types
        assert "system" in type_hints
        assert type_hints["system"] is str
        assert "user" in type_hints
        assert type_hints["user"] is str

        # Assert - Check return type
        assert "return" in type_hints
        assert type_hints["return"] is str

    def test_llm_provider_has_docstring(self) -> None:
        """Test that LLMProvider Protocol has comprehensive docstring."""
        # Assert
        assert LLMProvider.__doc__ is not None
        assert len(LLMProvider.__doc__.strip()) > 0
        # Verify docstring mentions core concept (flexible wording)
        doc_lower = LLMProvider.__doc__.lower()
        assert "llm" in doc_lower or "provider" in doc_lower

    def test_send_method_has_docstring(self) -> None:
        """Test that send method has comprehensive docstring."""
        # Arrange
        send_method = getattr(LLMProvider, "send")

        # Assert
        assert send_method.__doc__ is not None
        assert len(send_method.__doc__.strip()) > 0
        # Verify docstring mentions input concept (flexible wording)
        doc_lower = send_method.__doc__.lower()
        assert "prompt" in doc_lower or "eingabe" in doc_lower or "args" in doc_lower


class TestLLMProviderProtocolImplementation:
    """Test suite for verifying Protocol can be implemented by classes."""

    @pytest.mark.asyncio
    async def test_concrete_class_implements_protocol(self) -> None:
        """Test that a concrete class can implement LLMProvider Protocol."""

        # Arrange - Create concrete implementation
        class MockLLMProvider:
            """Mock implementation of LLMProvider for testing."""

            async def send(self, system: str, user: str) -> str:
                """Mock send method."""
                return f"System: {system}, User: {user}"

        # Act
        instance = MockLLMProvider()

        # Assert - Protocol conformance is structural (duck typing)
        # As long as the class has the right method signature, it conforms
        assert hasattr(instance, "send")
        assert callable(instance.send)

        # Verify it works
        result = await instance.send("test_system", "test_user")
        assert isinstance(result, str)

    def test_protocol_enforces_return_type(self) -> None:
        """Test that Protocol expects str return type from send method."""
        # Arrange
        send_method = getattr(LLMProvider, "send")
        type_hints = get_type_hints(send_method)

        # Assert
        assert type_hints["return"] is str

    def test_protocol_requires_two_str_parameters(self) -> None:
        """Test that Protocol requires exactly two str parameters."""
        # Arrange
        send_method = getattr(LLMProvider, "send")
        type_hints = get_type_hints(send_method)

        # Assert - Exactly 2 parameters plus return
        # Note: 'self' is not in type_hints for Protocol methods
        param_hints = {k: v for k, v in type_hints.items() if k != "return"}
        assert len(param_hints) == 2
        assert all(v is str for v in param_hints.values())


class TestMockProvider:
    """Test suite for MockProvider implementation."""

    def test_mock_provider_exists(self) -> None:
        """Test that MockProvider class exists and can be instantiated."""
        # Act
        provider = MockProvider()

        # Assert
        assert provider is not None
        assert isinstance(provider, MockProvider)

    def test_mock_provider_has_init(self) -> None:
        """Test that MockProvider has __init__ method."""
        # Assert
        assert hasattr(MockProvider, "__init__")
        assert callable(getattr(MockProvider, "__init__"))

    def test_mock_provider_init_no_parameters(self) -> None:
        """Test that MockProvider.__init__ requires no parameters."""
        # Act
        provider = MockProvider()

        # Assert - Should instantiate without errors
        assert provider is not None

    def test_mock_provider_has_send_method(self) -> None:
        """Test that MockProvider has send method."""
        # Arrange
        provider = MockProvider()

        # Assert
        assert hasattr(provider, "send")
        assert callable(getattr(provider, "send"))

    def test_mock_provider_send_signature(self) -> None:
        """Test that send method has correct parameter and return type annotations.

        MockProvider uses the same parameter names as the LLMProvider protocol
        (system, user) for consistency, even though the values are ignored.
        """
        # Arrange
        send_method = getattr(MockProvider, "send")
        type_hints = get_type_hints(send_method)

        # Assert - Check parameter types match protocol signature
        assert "system" in type_hints
        assert type_hints["system"] is str
        assert "user" in type_hints
        assert type_hints["user"] is str

        # Assert - Check return type
        assert "return" in type_hints
        assert type_hints["return"] is str

    @pytest.mark.asyncio
    async def test_mock_provider_send_returns_deterministic_string(self) -> None:
        """Test that send method returns a deterministic string."""
        # Arrange
        provider = MockProvider()

        # Act
        result = await provider.send("system prompt", "user prompt")

        # Assert
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_mock_provider_send_returns_gitignore_format(self) -> None:
        """Test that send method returns gitignore-formatted string."""
        # Arrange
        provider = MockProvider()

        # Act
        result = await provider.send("any system", "any user")

        # Assert
        assert isinstance(result, str)
        # Should contain newlines (multi-line gitignore format)
        assert "\n" in result

    @pytest.mark.asyncio
    async def test_mock_provider_send_is_deterministic(self) -> None:
        """Test that send method always returns the same result."""
        # Arrange
        provider = MockProvider()

        # Act
        result1 = await provider.send("sys1", "user1")
        result2 = await provider.send("sys2", "user2")
        result3 = await provider.send("sys1", "user1")

        # Assert - Same output regardless of input (deterministic mock)
        assert result1 == result2
        assert result1 == result3

    @pytest.mark.asyncio
    async def test_mock_provider_send_expected_content(self) -> None:
        """Test that send method returns expected gitignore content."""
        # Arrange
        provider = MockProvider()

        # Act
        result = await provider.send("system", "user")

        # Assert - Should contain typical gitignore patterns
        assert "node_modules/" in result
        assert "dist/" in result
        assert ".venv/" in result

    @pytest.mark.asyncio
    async def test_mock_provider_conforms_to_protocol(self) -> None:
        """Test that MockProvider conforms to LLMProvider Protocol."""
        # Arrange
        provider = MockProvider()

        # Act & Assert - Protocol conformance is structural
        assert hasattr(provider, "send")
        assert callable(provider.send)

        # Verify it works with Protocol signature
        result = await provider.send("test_system", "test_user")
        assert isinstance(result, str)

    def test_mock_provider_has_docstring(self) -> None:
        """Test that MockProvider has comprehensive docstring."""
        # Assert
        assert MockProvider.__doc__ is not None
        assert len(MockProvider.__doc__.strip()) > 0
        # Verify key docstring components (German)
        doc = MockProvider.__doc__.lower()
        assert "mock" in doc or "test" in doc
        assert "deterministic" in doc or "deterministisch" in doc

    def test_mock_provider_send_has_docstring(self) -> None:
        """Test that send method has comprehensive docstring."""
        # Arrange
        send_method = getattr(MockProvider, "send")

        # Assert
        assert send_method.__doc__ is not None
        assert len(send_method.__doc__.strip()) > 0


class TestCerebrasProvider:
    """Test suite for CerebrasProvider stub implementation."""

    @patch.dict(os.environ, {"CEREBRAS_API_KEY": "test-key"}, clear=True)
    @patch("codemap.core.llm.AsyncOpenAI")
    def test_cerebras_provider_exists(self, mock_openai_cls: MagicMock) -> None:
        """Test that CerebrasProvider class exists and can be instantiated."""
        # Act
        provider = CerebrasProvider()

        # Assert
        assert provider is not None
        assert isinstance(provider, CerebrasProvider)

    def test_cerebras_provider_has_init(self) -> None:
        """Test that CerebrasProvider has __init__ method."""
        # Assert
        assert hasattr(CerebrasProvider, "__init__")
        assert callable(getattr(CerebrasProvider, "__init__"))

    @patch.dict(os.environ, {"CEREBRAS_API_KEY": "test-key"}, clear=True)
    @patch("codemap.core.llm.AsyncOpenAI")
    def test_cerebras_provider_init_requires_api_key(self, mock_openai_cls: MagicMock) -> None:
        """Test that CerebrasProvider can be instantiated when API key is set."""
        # Arrange
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        # Act
        provider = CerebrasProvider()

        # Assert - Should instantiate without errors
        assert provider is not None

        # Verify AsyncOpenAI client is initialized with correct parameters
        mock_openai_cls.assert_called_once_with(
            api_key="test-key",
            base_url="https://api.cerebras.ai/v1"
        )

        # Verify model is set to "llama-3.3-70b"
        assert provider.model == "llama-3.3-70b"

    @patch.dict(os.environ, {}, clear=True)
    def test_cerebras_provider_init_missing_api_key(self) -> None:
        """Test that CerebrasProvider raises ValueError when API key is missing."""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            CerebrasProvider()

        assert str(exc_info.value) == "CEREBRAS_API_KEY environment variable not set"

    @patch.dict(os.environ, {"CEREBRAS_API_KEY": ""}, clear=True)
    def test_cerebras_provider_init_empty_api_key(self) -> None:
        """Test that CerebrasProvider raises ValueError when API key is empty."""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            CerebrasProvider()

        assert str(exc_info.value) == "CEREBRAS_API_KEY environment variable not set"

    @patch.dict(os.environ, {"CEREBRAS_API_KEY": "test-key"}, clear=True)
    @patch("codemap.core.llm.AsyncOpenAI")
    def test_cerebras_provider_has_send_method(self, mock_openai_cls: MagicMock) -> None:
        """Test that CerebrasProvider has send method."""
        # Arrange
        provider = CerebrasProvider()

        # Assert
        assert hasattr(provider, "send")
        assert callable(getattr(provider, "send"))

    def test_cerebras_provider_send_signature(self) -> None:
        """Test that send method has correct parameter and return type annotations."""
        # Arrange
        send_method = getattr(CerebrasProvider, "send")
        type_hints = get_type_hints(send_method)

        # Assert - Check parameter types
        assert "system" in type_hints
        assert type_hints["system"] is str
        assert "user" in type_hints
        assert type_hints["user"] is str

        # Assert - Check return type
        assert "return" in type_hints
        assert type_hints["return"] is str

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"CEREBRAS_API_KEY": "test-key"}, clear=True)
    @patch("codemap.core.llm.AsyncOpenAI")
    async def test_cerebras_provider_send_calls_openai_api(self, mock_openai_cls: MagicMock) -> None:
        """Test that send method calls AsyncOpenAI API with correct parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        # Create mock response structure
        mock_message = MagicMock()
        mock_message.content = "mocked response"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        # Use AsyncMock for the async API call
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        provider = CerebrasProvider()

        # Act
        result = await provider.send("system prompt", "user prompt")

        # Assert
        # Verify chat.completions.create was called with correct parameters
        mock_client.chat.completions.create.assert_called_once_with(
            model="llama-3.3-70b",
            messages=[
                {"role": "system", "content": "system prompt"},
                {"role": "user", "content": "user prompt"}
            ],
            temperature=0.2
        )

        # Verify returned value is "mocked response"
        assert result == "mocked response"

    @patch.dict(os.environ, {"CEREBRAS_API_KEY": "test-key"}, clear=True)
    @patch("codemap.core.llm.AsyncOpenAI")
    def test_cerebras_provider_conforms_to_protocol(self, mock_openai_cls: MagicMock) -> None:
        """Test that CerebrasProvider conforms to LLMProvider Protocol."""
        # Arrange
        provider = CerebrasProvider()

        # Act & Assert - Protocol conformance is structural
        assert hasattr(provider, "send")
        assert callable(provider.send)

    def test_cerebras_provider_has_docstring(self) -> None:
        """Test that CerebrasProvider has comprehensive docstring."""
        # Assert
        assert CerebrasProvider.__doc__ is not None
        assert len(CerebrasProvider.__doc__.strip()) > 0
        # Verify key docstring components (mentions Cerebras and API)
        doc = CerebrasProvider.__doc__.lower()
        assert "cerebras" in doc
        assert "api" in doc

    def test_cerebras_provider_send_has_docstring(self) -> None:
        """Test that send method has comprehensive docstring."""
        # Arrange
        send_method = getattr(CerebrasProvider, "send")

        # Assert
        assert send_method.__doc__ is not None
        assert len(send_method.__doc__.strip()) > 0
        # Verify mentions API or Cerebras
        doc = send_method.__doc__.lower()
        assert "api" in doc or "cerebras" in doc


class TestCerebrasProviderRetry:
    """Test suite for CerebrasProvider retry behavior with tenacity."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"CEREBRAS_API_KEY": "test-key"}, clear=True)
    @patch("codemap.core.llm.AsyncOpenAI")
    async def test_retry_on_rate_limit_error(self, mock_openai_cls: MagicMock) -> None:
        """Test that send retries on RateLimitError."""
        # Arrange
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        # Create mock response for successful call
        mock_message = MagicMock()
        mock_message.content = "success after retry"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        # First call raises RateLimitError, second succeeds
        import openai
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                openai.RateLimitError("rate limit", response=MagicMock(), body=None),
                mock_response
            ]
        )

        provider = CerebrasProvider()

        # Act
        result = await provider.send("system", "user")

        # Assert - should succeed after retry
        assert result == "success after retry"
        assert mock_client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"CEREBRAS_API_KEY": "test-key"}, clear=True)
    @patch("codemap.core.llm.AsyncOpenAI")
    async def test_retry_on_api_connection_error(self, mock_openai_cls: MagicMock) -> None:
        """Test that send retries on APIConnectionError."""
        # Arrange
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        # Create mock response for successful call
        mock_message = MagicMock()
        mock_message.content = "success after connection retry"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        # First call raises APIConnectionError, second succeeds
        import openai
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                openai.APIConnectionError(request=MagicMock()),
                mock_response
            ]
        )

        provider = CerebrasProvider()

        # Act
        result = await provider.send("system", "user")

        # Assert - should succeed after retry
        assert result == "success after connection retry"
        assert mock_client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"CEREBRAS_API_KEY": "test-key"}, clear=True)
    @patch("codemap.core.llm.AsyncOpenAI")
    async def test_max_retries_exhausted_raises(self, mock_openai_cls: MagicMock) -> None:
        """Test that after 3 attempts, error is raised."""
        # Arrange
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        # All 3 calls fail with RateLimitError
        import openai
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                openai.RateLimitError("rate limit 1", response=MagicMock(), body=None),
                openai.RateLimitError("rate limit 2", response=MagicMock(), body=None),
                openai.RateLimitError("rate limit 3", response=MagicMock(), body=None),
            ]
        )

        provider = CerebrasProvider()

        # Act & Assert - should raise after 3 attempts
        with pytest.raises(openai.RateLimitError):
            await provider.send("system", "user")

        # Verify all 3 attempts were made
        assert mock_client.chat.completions.create.call_count == 3

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"CEREBRAS_API_KEY": "test-key"}, clear=True)
    @patch("codemap.core.llm.AsyncOpenAI")
    async def test_no_retry_on_value_error(self, mock_openai_cls: MagicMock) -> None:
        """Test that ValueError (empty response) is NOT retried."""
        # Arrange
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        # Return empty choices - should raise ValueError immediately
        mock_response = MagicMock()
        mock_response.choices = []

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        provider = CerebrasProvider()

        # Act & Assert - should raise ValueError immediately without retry
        with pytest.raises(ValueError) as exc_info:
            await provider.send("system", "user")

        # Verify error message
        assert str(exc_info.value) == "Empty response from Cerebras API"

        # Verify only 1 attempt was made (no retries for ValueError)
        assert mock_client.chat.completions.create.call_count == 1


class TestGetProviderFactory:
    """Test suite for get_provider factory function."""

    def test_get_provider_exists(self) -> None:
        """Test that get_provider function exists and is callable."""
        # Assert
        assert callable(get_provider)

    def test_get_provider_default_returns_mock_provider(self) -> None:
        """Test that get_provider() with no args returns MockProvider instance."""
        # Act
        provider = get_provider()

        # Assert
        assert isinstance(provider, MockProvider)
        # Verify it conforms to LLMProvider Protocol
        assert hasattr(provider, "send")
        assert callable(provider.send)

    def test_get_provider_mock_returns_mock_provider(self) -> None:
        """Test that get_provider('mock') returns MockProvider instance."""
        # Act
        provider = get_provider("mock")

        # Assert
        assert isinstance(provider, MockProvider)
        assert hasattr(provider, "send")
        assert callable(provider.send)

    @patch.dict(os.environ, {"CEREBRAS_API_KEY": "test-key"}, clear=True)
    @patch("codemap.core.llm.AsyncOpenAI")
    def test_get_provider_cerebras_returns_cerebras_provider(self, mock_openai_cls: MagicMock) -> None:
        """Test that get_provider('cerebras') returns CerebrasProvider instance."""
        # Act
        provider = get_provider("cerebras")

        # Assert
        assert isinstance(provider, CerebrasProvider)
        assert hasattr(provider, "send")
        assert callable(provider.send)

    def test_get_provider_unknown_raises_value_error(self) -> None:
        """Test that get_provider with unknown name raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            get_provider("unknown_provider")

        # Verify error message contains relevant information
        error_msg = str(exc_info.value)
        assert "Unknown provider" in error_msg
        assert "unknown_provider" in error_msg

    def test_get_provider_invalid_provider_raises_value_error(self) -> None:
        """Test that get_provider with various invalid names raises ValueError."""
        # Arrange - Various invalid provider names
        invalid_names = ["openai", "anthropic", "invalid", "", "123"]

        # Act & Assert
        for invalid_name in invalid_names:
            with pytest.raises(ValueError) as exc_info:
                get_provider(invalid_name)
            error_msg = str(exc_info.value)
            assert "Unknown provider" in error_msg
            assert invalid_name in error_msg

    def test_get_provider_return_type_annotation(self) -> None:
        """Test that get_provider has correct return type annotation."""
        # Arrange
        type_hints = get_type_hints(get_provider)

        # Assert - Return type should be LLMProvider
        assert "return" in type_hints
        assert type_hints["return"] == LLMProvider

    def test_get_provider_parameter_type_annotation(self) -> None:
        """Test that get_provider has correct parameter type annotations."""
        # Arrange
        type_hints = get_type_hints(get_provider)

        # Assert - name parameter should be str
        assert "name" in type_hints
        assert type_hints["name"] is str

    def test_get_provider_has_docstring(self) -> None:
        """Test that get_provider has comprehensive docstring."""
        # Assert
        assert get_provider.__doc__ is not None
        assert len(get_provider.__doc__.strip()) > 0

    def test_get_provider_docstring_mentions_factory_pattern(self) -> None:
        """Test that docstring mentions Factory Pattern."""
        # Assert
        doc = get_provider.__doc__
        assert doc is not None
        doc_lower = doc.lower()
        assert "factory" in doc_lower

    def test_get_provider_docstring_lists_available_providers(self) -> None:
        """Test that docstring lists available providers."""
        # Assert
        doc = get_provider.__doc__
        assert doc is not None
        doc_lower = doc.lower()
        # Should mention both mock and cerebras
        assert "mock" in doc_lower
        assert "cerebras" in doc_lower

    def test_get_provider_docstring_has_examples_section(self) -> None:
        """Test that docstring includes Examples section."""
        # Assert
        doc = get_provider.__doc__
        assert doc is not None
        # German or English examples section
        assert "examples:" in doc.lower() or "beispiele:" in doc.lower()

    def test_get_provider_docstring_has_mock_example(self) -> None:
        """Test that docstring includes example for MockProvider."""
        # Assert
        doc = get_provider.__doc__
        assert doc is not None
        # Should show how to use mock provider
        assert 'get_provider("mock")' in doc or "get_provider()" in doc

    def test_get_provider_docstring_has_cerebras_example(self) -> None:
        """Test that docstring includes example for CerebrasProvider."""
        # Assert
        doc = get_provider.__doc__
        assert doc is not None
        # Should show how to use cerebras provider
        assert 'get_provider("cerebras")' in doc

    @pytest.mark.asyncio
    async def test_get_provider_returned_mock_works_correctly(self) -> None:
        """Test that MockProvider instance returned by factory works correctly."""
        # Act
        provider = get_provider("mock")
        result = await provider.send("system", "user")

        # Assert
        assert isinstance(result, str)
        assert "node_modules/" in result

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"CEREBRAS_API_KEY": "test-key"}, clear=True)
    @patch("codemap.core.llm.AsyncOpenAI")
    async def test_get_provider_returned_cerebras_works_with_mock(self, mock_openai_cls: MagicMock) -> None:
        """Test that CerebrasProvider instance returned by factory works with mocked API."""
        # Arrange
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        # Create mock response structure
        mock_message = MagicMock()
        mock_message.content = "mocked response"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        # Use AsyncMock for the async API call
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Act
        provider = get_provider("cerebras")
        result = await provider.send("system", "user")

        # Assert
        assert result == "mocked response"

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"CEREBRAS_API_KEY": "test-key"}, clear=True)
    @patch("codemap.core.llm.AsyncOpenAI")
    async def test_factory_returns_protocol_conformant_provider(self, mock_openai_cls: MagicMock) -> None:
        """Test that get_provider returns objects conforming to LLMProvider protocol.

        This test demonstrates that the static type LLMProvider is correct for
        factory return values and ensures protocol conformance in the factory
        context without introducing additional runtime type checks.
        """

        # Arrange - Define helper that accepts LLMProvider protocol type
        async def use_provider(provider: LLMProvider) -> str:
            """Use a provider through the protocol interface."""
            return await provider.send("system prompt", "user prompt")

        # Act & Assert - MockProvider works through protocol interface
        mock_provider = get_provider("mock")
        result = await use_provider(mock_provider)
        assert isinstance(result, str)
        assert len(result) > 0

        # Arrange - Mock AsyncOpenAI client for CerebrasProvider
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        # Create mock response structure
        mock_message = MagicMock()
        mock_message.content = "cerebras mocked response"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        # Use AsyncMock for the async API call
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Act & Assert - CerebrasProvider works through protocol interface
        cerebras_provider = get_provider("cerebras")
        cerebras_result = await use_provider(cerebras_provider)
        assert cerebras_result == "cerebras mocked response"
