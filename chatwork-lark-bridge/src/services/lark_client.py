"""Lark API client service."""

from typing import Optional
import json

from lark_oapi import Client
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
)
from lark_oapi.core.model import RawResponse

from ..core.config import settings
from ..core.logging import get_logger
from ..core.exceptions import (
    APIError,
    RateLimitError,
    AuthenticationError,
    ServerError,
    BadRequestError,
)
from ..core.retry import retry_with_rate_limit_handling

logger = get_logger(__name__)


class LarkAPIClient:
    """Client for interacting with Lark API."""

    def __init__(self):
        """Initialize Lark API client."""
        self.client = Client.builder() \
            .app_id(settings.lark_app_id) \
            .app_secret(settings.lark_app_secret) \
            .build()

        logger.info("lark_client_initialized", app_id=settings.lark_app_id)

    async def send_text_message(
        self,
        chat_id: str,
        text: str,
        msg_type: str = "text",
    ) -> str:
        """
        Send a text message to a Lark chat.

        Args:
            chat_id: Lark chat ID (e.g., "oc_xxx")
            text: Message text content
            msg_type: Message type (default: "text")

        Returns:
            Message ID of the sent message

        Raises:
            RateLimitError: If rate limit is exceeded
            AuthenticationError: If authentication fails
            ServerError: If server error occurs
            BadRequestError: If request is invalid
        """
        try:
            # Prepare message content
            content = json.dumps({"text": text})

            # Create request
            request = CreateMessageRequest.builder() \
                .receive_id_type("chat_id") \
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(chat_id)
                    .msg_type(msg_type)
                    .content(content)
                    .build()
                ) \
                .build()

            # Send message with retry handling
            response = await retry_with_rate_limit_handling(
                self._send_message_request,
                request,
            )

            logger.info(
                "lark_message_sent",
                chat_id=chat_id,
                message_id=response.data.message_id,
                text_preview=text[:50] + "..." if len(text) > 50 else text,
            )

            return response.data.message_id

        except Exception as e:
            logger.error(
                "lark_message_send_failed",
                chat_id=chat_id,
                error=str(e),
            )
            raise

    async def _send_message_request(
        self, request: CreateMessageRequest
    ) -> RawResponse:
        """
        Internal method to send message request.

        Handles error codes and raises appropriate exceptions.
        """
        response = self.client.im.v1.message.create(request)

        # Check for errors
        if not response.success():
            error_code = response.code
            error_msg = response.msg

            logger.warning(
                "lark_api_error",
                code=error_code,
                message=error_msg,
            )

            # Map error codes to exceptions
            if error_code == 99991663:  # Rate limit
                raise RateLimitError(platform="lark", retry_after=60)
            elif error_code in [99991661, 99991662]:  # Auth errors
                raise AuthenticationError(f"Lark authentication failed: {error_msg}")
            elif 99991000 <= error_code < 99992000:  # Client errors
                raise BadRequestError(f"Lark bad request: {error_msg}")
            elif error_code >= 99992000:  # Server errors
                raise ServerError(f"Lark server error: {error_msg}")
            else:
                raise APIError(f"Lark API error: {error_msg}", status_code=error_code)

        return response

    async def send_rich_text_message(
        self,
        chat_id: str,
        title: str,
        content: list[dict],
    ) -> str:
        """
        Send a rich text message (with formatting).

        Args:
            chat_id: Lark chat ID
            title: Message title
            content: Rich text content elements

        Returns:
            Message ID
        """
        rich_content = json.dumps({
            "title": title,
            "content": content,
        })

        request = CreateMessageRequest.builder() \
            .receive_id_type("chat_id") \
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(chat_id)
                .msg_type("post")
                .content(rich_content)
                .build()
            ) \
            .build()

        response = await retry_with_rate_limit_handling(
            self._send_message_request,
            request,
        )

        logger.info(
            "lark_rich_message_sent",
            chat_id=chat_id,
            message_id=response.data.message_id,
            title=title,
        )

        return response.data.message_id

    def format_message_from_chatwork(
        self,
        sender_name: str,
        message_text: str,
    ) -> str:
        """
        Format a message from Chatwork for display in Lark.

        Args:
            sender_name: Name of the Chatwork sender
            message_text: Original message text

        Returns:
            Formatted message with prefix
        """
        prefix = settings.message_prefix_chatwork
        return f"{prefix} {sender_name}:\n{message_text}"


# Global Lark client instance
lark_client = LarkAPIClient()
