"""Lark webhook endpoints."""

from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from ..core.logging import get_logger
from ..core.config import settings
from ..core.exceptions import (
    SignatureVerificationError,
    LoopDetectedError,
    MappingNotFoundError,
)
from ..utils.webhook_verification import verify_lark_verification_token
from ..services.message_processor import message_processor

logger = get_logger(__name__)
router = APIRouter()


class LarkEventHeader(BaseModel):
    """Lark event header model."""

    event_id: str
    event_type: str
    create_time: str
    token: str
    app_id: str
    tenant_key: str


class LarkMessageEvent(BaseModel):
    """Lark message event model."""

    sender: dict
    message: dict
    chat_id: Optional[str] = None


@router.post("/")
async def lark_webhook(request: Request):
    """
    Lark event subscription endpoint.

    Receives event notifications from Lark and syncs messages to Chatwork.
    """
    event_data = await request.json()

    # Handle URL verification challenge
    if event_data.get("type") == "url_verification":
        challenge = event_data.get("challenge")
        logger.info("lark_url_verification_received")

        # Verify token
        try:
            token = event_data.get("token")
            verify_lark_verification_token(token)
        except SignatureVerificationError as e:
            logger.warning("lark_verification_failed", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid verification token",
            )

        return {"challenge": challenge}

    # Handle event callback
    header = event_data.get("header", {})
    event_type = header.get("event_type")
    event_id = header.get("event_id")

    logger.info(
        "lark_event_received",
        event_type=event_type,
        event_id=event_id,
    )

    # Process message received events
    if event_type == "im.message.receive_v1":
        try:
            # Extract event data
            event = event_data.get("event", {})

            # Get message info
            message = event.get("message", {})
            message_id = message.get("message_id")
            message_type = message.get("message_type")
            chat_id = message.get("chat_id")
            content_str = message.get("content", "{}")

            # Get sender info
            sender = event.get("sender", {})
            sender_id = sender.get("sender_id", {})
            open_id = sender_id.get("open_id")
            user_id = sender_id.get("user_id")

            # For now, use user_id or open_id as sender name
            sender_name = f"User {user_id or open_id}"

            logger.info(
                "lark_message_received",
                message_id=message_id,
                message_type=message_type,
                chat_id=chat_id,
                sender=sender_name,
            )

            # Only process text messages for now
            if message_type != "text":
                logger.info(
                    "lark_message_type_unsupported",
                    message_id=message_id,
                    message_type=message_type,
                    reason="only_text_supported",
                )
                return {"status": "ok"}

            # Parse message content
            import json
            try:
                content = json.loads(content_str)
                message_text = content.get("text", "")
            except json.JSONDecodeError as e:
                logger.warning(
                    "lark_message_content_parse_error",
                    message_id=message_id,
                    error=str(e),
                )
                message_text = content_str

            # Process and sync to Chatwork
            chatwork_message_id = await message_processor.process_lark_message(
                chat_id=chat_id,
                message_id=message_id,
                sender_name=sender_name,
                message_text=message_text,
            )

            if chatwork_message_id:
                logger.info(
                    "lark_message_processed",
                    lark_message_id=message_id,
                    chatwork_message_id=chatwork_message_id,
                )
            else:
                logger.debug(
                    "lark_message_skipped",
                    message_id=message_id,
                    reason="already_processed_or_filtered",
                )

        except LoopDetectedError as e:
            # This is expected - just log and return success
            logger.debug(
                "lark_message_loop_detected",
                message_id=event.get("message", {}).get("message_id"),
            )

        except MappingNotFoundError as e:
            logger.warning(
                "lark_room_mapping_not_found",
                chat_id=event.get("message", {}).get("chat_id"),
                error=str(e),
            )
            # Return success to avoid retry

        except Exception as e:
            logger.error(
                "lark_message_processing_error",
                message_id=event.get("message", {}).get("message_id"),
                error=str(e),
                error_type=type(e).__name__,
            )
            # Return 500 to signal error
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process message",
            )

    elif event_type == "im.message.message_read_v1":
        # TODO: Handle message read events
        logger.debug(
            "lark_message_read_event_ignored",
            event_id=event_id,
            reason="read_sync_not_implemented",
        )

    else:
        logger.info(
            "lark_unknown_event_type",
            event_type=event_type,
            event_id=event_id,
        )

    # Always return 200 OK to Lark
    return {"status": "ok"}
