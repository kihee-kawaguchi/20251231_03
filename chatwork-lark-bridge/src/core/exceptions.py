"""Custom exceptions for the application."""


class BridgeException(Exception):
    """Base exception for all bridge errors."""

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details  # Keep None if None is passed
        super().__init__(self.message)


class RetryableError(BridgeException):
    """Error that can be retried."""

    pass


class NonRetryableError(BridgeException):
    """Error that should not be retried."""

    pass


# API Errors
class APIError(BridgeException):
    """Base class for API-related errors."""

    def __init__(self, message: str, status_code: int | None = None, details: dict | None = None):
        super().__init__(message, details)
        self.status_code = status_code


class RateLimitError(RetryableError):
    """API rate limit exceeded."""

    def __init__(self, platform: str, retry_after: int | None = None):
        message = f"{platform} API rate limit exceeded"
        details = {"platform": platform, "retry_after": retry_after}
        super().__init__(message, details)
        self.platform = platform
        self.retry_after = retry_after


class AuthenticationError(NonRetryableError):
    """Authentication failed."""

    pass


class AuthorizationError(NonRetryableError):
    """Authorization failed (insufficient permissions)."""

    pass


class BadRequestError(NonRetryableError):
    """Bad request to API."""

    pass


class ResourceNotFoundError(NonRetryableError):
    """Resource not found."""

    pass


class ServerError(RetryableError):
    """Server-side error (5xx)."""

    pass


class NetworkError(RetryableError):
    """Network connectivity error."""

    pass


# Webhook Errors
class WebhookError(BridgeException):
    """Base class for webhook-related errors."""

    pass


class SignatureVerificationError(NonRetryableError):
    """Webhook signature verification failed."""

    def __init__(self, platform: str):
        message = f"{platform} signature verification failed"
        details = {"platform": platform}
        super().__init__(message, details)


class WebhookTimeoutError(WebhookError):
    """Webhook processing timed out."""

    pass


# Message Processing Errors
class MessageProcessingError(BridgeException):
    """Base class for message processing errors."""

    pass


class LoopDetectedError(NonRetryableError):
    """Message loop detected - message originated from bridge."""

    def __init__(self, message: str = "Message loop detected"):
        super().__init__(message)


class MessageTooLongError(NonRetryableError):
    """Message exceeds maximum length."""

    def __init__(self, length: int, max_length: int):
        message = f"Message length ({length}) exceeds maximum ({max_length})"
        details = {"length": length, "max_length": max_length}
        super().__init__(message, details)


class UnsupportedMessageTypeError(NonRetryableError):
    """Message type is not supported."""

    pass


# Data Store Errors
class DataStoreError(BridgeException):
    """Base class for data store errors."""

    pass


class RedisConnectionError(RetryableError):
    """Redis connection failed."""

    pass


class MappingNotFoundError(NonRetryableError):
    """Room or user mapping not found."""

    def __init__(self, platform: str, room_id: str):
        message = f"{platform} room mapping not found for room: {room_id}"
        details = {"platform": platform, "room_id": room_id}
        super().__init__(message, details)
