"""Message processing and synchronization logic."""

from typing import Optional
from datetime import datetime, timezone

from ..core.config import settings
from ..core.logging import get_logger
from ..core.exceptions import (
    LoopDetectedError,
    MessageTooLongError,
    MappingNotFoundError,
)
from ..services.redis_client import redis_client
from ..services.lark_client import lark_client
from ..services.chatwork_client import chatwork_client

logger = get_logger(__name__)


class MessageProcessor:
    """Handles message processing and synchronization."""

    def __init__(self):
        """Initialize message processor."""
        self.redis = redis_client
        self.lark = lark_client
        self.chatwork = chatwork_client

    async def process_chatwork_message(
        self,
        room_id: str,
        message_id: str,
        sender_name: str,
        message_body: str,
    ) -> Optional[str]:
        """
        Process a message from Chatwork and sync to Lark.

        Args:
            room_id: Chatwork room ID
            message_id: Chatwork message ID
            sender_name: Sender's name
            message_body: Message text

        Returns:
            Lark message ID if sent, None if skipped

        Raises:
            LoopDetectedError: If message originated from bridge
            MappingNotFoundError: If room mapping not found
        """
        logger.info(
            "processing_chatwork_message",
            room_id=room_id,
            message_id=message_id,
            sender=sender_name,
        )

        # 1. Check if already processed
        if await self.redis.is_message_processed("chatwork", message_id):
            logger.debug(
                "message_already_processed",
                platform="chatwork",
                message_id=message_id,
            )
            return None

        # 2. Loop detection - check message prefix
        if self._is_from_bridge(message_body, "lark"):
            logger.info(
                "loop_detected_skipping",
                platform="chatwork",
                message_id=message_id,
                reason="message_from_lark",
            )
            raise LoopDetectedError("Message originated from Lark bridge")

        # 3. Get room mapping
        lark_chat_id = await self.redis.get_room_mapping("chatwork", room_id)

        if not lark_chat_id:
            logger.warning(
                "room_mapping_not_found",
                platform="chatwork",
                room_id=room_id,
            )
            raise MappingNotFoundError("room", room_id)

        # 4. Format message for Lark
        formatted_message = self.lark.format_message_from_chatwork(
            sender_name,
            message_body,
        )

        # 5. Check message length
        if len(formatted_message) > settings.max_message_length:
            logger.warning(
                "message_too_long",
                length=len(formatted_message),
                max_length=settings.max_message_length,
            )
            # Truncate message
            formatted_message = formatted_message[:settings.max_message_length - 100] + \
                "\n\n[Message truncated due to length limit]"

        # 6. Send to Lark
        try:
            lark_message_id = await self.lark.send_text_message(
                lark_chat_id,
                formatted_message,
            )

            # 7. Save mapping for loop detection
            await self.redis.save_message_mapping(
                source_platform="chatwork",
                source_message_id=message_id,
                target_platform="lark",
                target_message_id=lark_message_id,
                room_mapping_id=f"cw_{room_id}_lark_{lark_chat_id}",
            )

            logger.info(
                "message_synced_successfully",
                source="chatwork",
                target="lark",
                chatwork_message_id=message_id,
                lark_message_id=lark_message_id,
            )

            return lark_message_id

        except Exception as e:
            # Save to DLQ
            await self.redis.add_to_failed_queue(
                source_platform="chatwork",
                target_platform="lark",
                message_data={
                    "room_id": room_id,
                    "message_id": message_id,
                    "sender_name": sender_name,
                    "message_body": message_body,
                },
                error=str(e),
            )
            raise

    async def process_lark_message(
        self,
        chat_id: str,
        message_id: str,
        sender_name: str,
        message_text: str,
    ) -> Optional[str]:
        """
        Process a message from Lark and sync to Chatwork.

        Args:
            chat_id: Lark chat ID
            message_id: Lark message ID
            sender_name: Sender's name
            message_text: Message text

        Returns:
            Chatwork message ID if sent, None if skipped
        """
        logger.info(
            "processing_lark_message",
            chat_id=chat_id,
            message_id=message_id,
            sender=sender_name,
        )

        # 1. Check if already processed
        if await self.redis.is_message_processed("lark", message_id):
            logger.debug(
                "message_already_processed",
                platform="lark",
                message_id=message_id,
            )
            return None

        # 2. Loop detection
        if self._is_from_bridge(message_text, "chatwork"):
            logger.info(
                "loop_detected_skipping",
                platform="lark",
                message_id=message_id,
                reason="message_from_chatwork",
            )
            raise LoopDetectedError("Message originated from Chatwork bridge")

        # 3. Get room mapping
        chatwork_room_id = await self.redis.get_room_mapping("lark", chat_id)

        if not chatwork_room_id:
            logger.warning(
                "room_mapping_not_found",
                platform="lark",
                chat_id=chat_id,
            )
            raise MappingNotFoundError("room", chat_id)

        # 4. Format message for Chatwork
        formatted_message = self.chatwork.format_message_from_lark(
            sender_name,
            message_text,
        )

        # 5. Check message length
        if len(formatted_message) > settings.max_message_length:
            logger.warning(
                "message_too_long",
                length=len(formatted_message),
                max_length=settings.max_message_length,
            )
            formatted_message = formatted_message[:settings.max_message_length - 100] + \
                "\n\n[Message truncated due to length limit]"

        # 6. Send to Chatwork
        try:
            chatwork_message_id = await self.chatwork.send_message(
                chatwork_room_id,
                formatted_message,
            )

            # 7. Save mapping
            await self.redis.save_message_mapping(
                source_platform="lark",
                source_message_id=message_id,
                target_platform="chatwork",
                target_message_id=chatwork_message_id,
                room_mapping_id=f"lark_{chat_id}_cw_{chatwork_room_id}",
            )

            logger.info(
                "message_synced_successfully",
                source="lark",
                target="chatwork",
                lark_message_id=message_id,
                chatwork_message_id=chatwork_message_id,
            )

            return chatwork_message_id

        except Exception as e:
            # Save to DLQ
            await self.redis.add_to_failed_queue(
                source_platform="lark",
                target_platform="chatwork",
                message_data={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "sender_name": sender_name,
                    "message_text": message_text,
                },
                error=str(e),
            )
            raise

    def _is_from_bridge(self, message_text: str, source_platform: str) -> bool:
        """
        Check if message originated from the bridge.

        Args:
            message_text: Message text to check
            source_platform: Platform to check prefix for ("chatwork" or "lark")

        Returns:
            True if message is from bridge, False otherwise
        """
        if not settings.enable_loop_detection:
            return False

        if source_platform == "chatwork":
            prefix = settings.message_prefix_chatwork
        elif source_platform == "lark":
            prefix = settings.message_prefix_lark
        else:
            return False

        # Case-insensitive prefix check
        return message_text.lower().startswith(prefix.lower())


# Global message processor instance
message_processor = MessageProcessor()
