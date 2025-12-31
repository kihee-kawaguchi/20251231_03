"""Unit tests for retry logic."""

import pytest
from unittest.mock import AsyncMock
from tenacity import RetryError

from src.core.retry import (
    create_retry_decorator,
    retry_with_rate_limit_handling,
)
from src.core.exceptions import (
    RetryableError,
    NonRetryableError,
    RateLimitError,
)


@pytest.mark.unit
class TestRetryDecorator:
    """Test retry decorator creation."""

    def test_create_retry_decorator_default_params(self):
        """Test creating retry decorator with default parameters."""
        decorator = create_retry_decorator()

        assert decorator is not None
        # Decorator should be callable
        assert callable(decorator)

    def test_create_retry_decorator_custom_params(self):
        """Test creating retry decorator with custom parameters."""
        decorator = create_retry_decorator(
            max_attempts=3, min_wait=2, max_wait=10
        )

        assert decorator is not None
        assert callable(decorator)


@pytest.mark.unit
class TestRetryLogic:
    """Test retry logic behavior."""

    @pytest.mark.asyncio
    async def test_successful_execution_no_retry(self):
        """Test successful execution without retries."""
        mock_func = AsyncMock(return_value="success")

        result = await retry_with_rate_limit_handling(mock_func)

        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_retryable_error(self):
        """Test retry on retryable error."""
        mock_func = AsyncMock(
            side_effect=[
                RetryableError("Temporary error"),
                RetryableError("Still failing"),
                "success",
            ]
        )

        result = await retry_with_rate_limit_handling(mock_func)

        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable_error(self):
        """Test no retry on non-retryable error."""
        mock_func = AsyncMock(side_effect=NonRetryableError("Permanent error"))

        with pytest.raises(NonRetryableError):
            await retry_with_rate_limit_handling(mock_func)

        # Should fail immediately without retries
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_exhaustion(self):
        """Test retry exhaustion after max attempts."""
        mock_func = AsyncMock(
            side_effect=RetryableError("Always fails")
        )

        with pytest.raises((RetryError, RetryableError)):
            await retry_with_rate_limit_handling(mock_func)

        # Should retry up to max attempts (default 5)
        assert mock_func.call_count == 5

    @pytest.mark.asyncio
    async def test_retry_with_rate_limit_error(self):
        """Test retry handling rate limit errors."""
        mock_func = AsyncMock(
            side_effect=[
                RateLimitError("chatwork", retry_after=1),
                "success",
            ]
        )

        result = await retry_with_rate_limit_handling(mock_func)

        assert result == "success"
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_function_with_args(self):
        """Test retry with function arguments."""
        mock_func = AsyncMock(return_value="result")

        result = await retry_with_rate_limit_handling(
            mock_func, "arg1", "arg2", kwarg1="value1"
        )

        assert result == "result"
        mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1")

    @pytest.mark.asyncio
    async def test_mixed_errors(self):
        """Test handling mixed error types."""
        mock_func = AsyncMock(
            side_effect=[
                RetryableError("Retry 1"),
                RateLimitError("chatwork"),
                RetryableError("Retry 2"),
                "success",
            ]
        )

        result = await retry_with_rate_limit_handling(mock_func)

        assert result == "success"
        assert mock_func.call_count == 4
