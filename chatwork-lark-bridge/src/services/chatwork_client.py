"""Chatwork API client service."""

from typing import Optional
import httpx

from ..core.config import settings
from ..core.logging import get_logger
from ..core.exceptions import (
    RateLimitError,
    AuthenticationError,
    ServerError,
    BadRequestError,
    ResourceNotFoundError,
)
from ..core.retry import retry_with_rate_limit_handling

logger = get_logger(__name__)


class ChatworkAPIClient:
    """Client for interacting with Chatwork API."""

    def __init__(self):
        """Initialize Chatwork API client."""
        self.base_url = settings.chatwork_api_base_url
        self.headers = {
            "X-ChatWorkToken": settings.chatwork_api_token,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        self.client = httpx.AsyncClient(headers=self.headers, timeout=30.0)

        logger.info("chatwork_client_initialized")

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def send_message(
        self,
        room_id: str,
        body: str,
        self_unread: bool = False,
    ) -> str:
        """
        Send a message to a Chatwork room.

        Args:
            room_id: Chatwork room ID
            body: Message body text
            self_unread: Mark as unread for sender (default: False)

        Returns:
            Message ID of the sent message

        Raises:
            RateLimitError: If rate limit is exceeded
            AuthenticationError: If authentication fails
            ServerError: If server error occurs
            BadRequestError: If request is invalid
        """
        try:
            # Prepare request data
            data = {
                "body": body,
                "self_unread": "1" if self_unread else "0",
            }

            # Send with retry handling
            response_data = await retry_with_rate_limit_handling(
                self._post_message,
                room_id,
                data,
            )

            message_id = response_data.get("message_id")

            logger.info(
                "chatwork_message_sent",
                room_id=room_id,
                message_id=message_id,
                body_preview=body[:50] + "..." if len(body) > 50 else body,
            )

            return str(message_id)

        except Exception as e:
            logger.error(
                "chatwork_message_send_failed",
                room_id=room_id,
                error=str(e),
            )
            raise

    async def _post_message(self, room_id: str, data: dict) -> dict:
        """
        Internal method to POST message to Chatwork API.

        Handles HTTP errors and raises appropriate exceptions.
        """
        url = f"{self.base_url}/rooms/{room_id}/messages"

        response = await self.client.post(url, data=data)

        # Handle errors
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 10))
            logger.warning(
                "chatwork_rate_limit",
                room_id=room_id,
                retry_after=retry_after,
            )
            raise RateLimitError(platform="chatwork", retry_after=retry_after)

        elif response.status_code == 401:
            raise AuthenticationError("Chatwork API authentication failed")

        elif response.status_code == 404:
            raise ResourceNotFoundError(f"Room not found: {room_id}")

        elif 400 <= response.status_code < 500:
            error_msg = response.text
            raise BadRequestError(f"Chatwork bad request: {error_msg}")

        elif response.status_code >= 500:
            raise ServerError(f"Chatwork server error: {response.status_code}")

        # Check success
        response.raise_for_status()

        return response.json()

    async def get_room_members(self, room_id: str) -> list[dict]:
        """
        Get members of a Chatwork room.

        Args:
            room_id: Chatwork room ID

        Returns:
            List of member information
        """
        url = f"{self.base_url}/rooms/{room_id}/members"

        response = await self.client.get(url)
        response.raise_for_status()

        return response.json()

    async def get_message(self, room_id: str, message_id: str) -> dict:
        """
        Get a specific message from a room.

        Args:
            room_id: Chatwork room ID
            message_id: Message ID

        Returns:
            Message data
        """
        url = f"{self.base_url}/rooms/{room_id}/messages/{message_id}"

        response = await self.client.get(url)

        if response.status_code == 404:
            raise ResourceNotFoundError(f"Message not found: {message_id}")

        response.raise_for_status()

        return response.json()

    def format_message_from_lark(
        self,
        sender_name: str,
        message_text: str,
    ) -> str:
        """
        Format a message from Lark for display in Chatwork.

        Args:
            sender_name: Name of the Lark sender
            message_text: Original message text

        Returns:
            Formatted message with prefix
        """
        prefix = settings.message_prefix_lark
        return f"{prefix} {sender_name}:\n{message_text}"


# Global Chatwork client instance
chatwork_client = ChatworkAPIClient()
