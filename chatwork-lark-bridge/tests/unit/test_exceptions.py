"""Unit tests for custom exceptions."""

import pytest

from src.core.exceptions import (
    BridgeException,
    RetryableError,
    NonRetryableError,
    RateLimitError,
    SignatureVerificationError,
    LoopDetectedError,
    MappingNotFoundError,
)


@pytest.mark.unit
class TestBridgeException:
    """Test base exception class."""

    def test_bridge_exception_creation(self):
        """Test creating a base exception."""
        exc = BridgeException("Test error", {"key": "value"})

        assert exc.message == "Test error"
        assert exc.details == {"key": "value"}
        assert str(exc) == "Test error"

    def test_bridge_exception_without_details(self):
        """Test creating exception without details."""
        exc = BridgeException("Simple error")

        assert exc.message == "Simple error"
        assert exc.details is None


@pytest.mark.unit
class TestRetryableError:
    """Test retryable error exceptions."""

    def test_retryable_error_creation(self):
        """Test creating retryable error."""
        exc = RetryableError("Temporary failure", {"attempt": 1})

        assert exc.message == "Temporary failure"
        assert exc.details == {"attempt": 1}
        assert isinstance(exc, BridgeException)

    def test_rate_limit_error(self):
        """Test rate limit error."""
        exc = RateLimitError("chatwork", retry_after=30)

        assert "rate limit" in exc.message.lower()
        assert exc.details["platform"] == "chatwork"
        assert exc.details["retry_after"] == 30
        assert isinstance(exc, RetryableError)

    def test_rate_limit_error_without_retry_after(self):
        """Test rate limit error without retry_after."""
        exc = RateLimitError("lark")

        assert "rate limit" in exc.message.lower()
        assert exc.details["platform"] == "lark"
        assert exc.details["retry_after"] is None


@pytest.mark.unit
class TestNonRetryableError:
    """Test non-retryable error exceptions."""

    def test_non_retryable_error_creation(self):
        """Test creating non-retryable error."""
        exc = NonRetryableError("Permanent failure")

        assert exc.message == "Permanent failure"
        assert isinstance(exc, BridgeException)

    def test_signature_verification_error(self):
        """Test signature verification error."""
        exc = SignatureVerificationError("chatwork")

        assert "signature" in exc.message.lower()
        assert exc.details["platform"] == "chatwork"
        assert isinstance(exc, NonRetryableError)

    def test_loop_detected_error(self):
        """Test loop detection error."""
        exc = LoopDetectedError("Message already processed")

        assert "already processed" in exc.message.lower()
        assert isinstance(exc, NonRetryableError)

    def test_mapping_not_found_error(self):
        """Test mapping not found error."""
        exc = MappingNotFoundError("chatwork", "12345678")

        assert "not found" in exc.message.lower()
        assert exc.details["platform"] == "chatwork"
        assert exc.details["room_id"] == "12345678"
        assert isinstance(exc, NonRetryableError)
