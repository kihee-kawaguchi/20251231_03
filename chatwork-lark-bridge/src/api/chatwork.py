"""Chatwork webhook endpoints."""

from fastapi import APIRouter, Request, Header, HTTPException, status
from pydantic import BaseModel

from ..core.logging import get_logger
from ..utils.webhook_verification import verify_chatwork_signature
from ..core.exceptions import (
    SignatureVerificationError,
    LoopDetectedError,
    MappingNotFoundError,
)
from ..services.message_processor import message_processor

logger = get_logger(__name__)
router = APIRouter()


class ChatworkWebhookEvent(BaseModel):
    """Chatwork webhook event model."""

    webhook_setting_id: str
    webhook_event_type: str
    webhook_event_time: int
    webhook_event: dict


@router.post("/")
async def chatwork_webhook(
    request: Request,
    x_chatworkwebhooksignature: str = Header(..., alias="X-ChatWorkWebhookSignature"),
):
    """
    Chatwork webhook endpoint.

    Receives webhook events from Chatwork and syncs messages to Lark.
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify signature
    try:
        verify_chatwork_signature(body, x_chatworkwebhooksignature)
    except SignatureVerificationError as e:
        logger.warning("chatwork_webhook_signature_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook signature",
        )

    # Parse JSON body
    event_data = await request.json()

    event_type = event_data.get("webhook_event_type")
    event = event_data.get("webhook_event", {})

    logger.info(
        "chatwork_webhook_received",
        event_type=event_type,
        webhook_id=event_data.get("webhook_setting_id"),
        room_id=event.get("room_id"),
    )

    # Process message_created events
    if event_type == "message_created":
        try:
            # Extract message data
            room_id = str(event.get("room_id"))
            message_id = str(event.get("message_id"))
            sender_account_id = event.get("from_account_id")
            message_body = event.get("body", "")

            # Get sender name (from account info)
            # For now, use account_id as name; can enhance with API call
            sender_name = f"User {sender_account_id}"

            # Process and sync to Lark
            lark_message_id = await message_processor.process_chatwork_message(
                room_id=room_id,
                message_id=message_id,
                sender_name=sender_name,
                message_body=message_body,
            )

            if lark_message_id:
                logger.info(
                    "chatwork_message_processed",
                    chatwork_message_id=message_id,
                    lark_message_id=lark_message_id,
                )
            else:
                logger.debug(
                    "chatwork_message_skipped",
                    message_id=message_id,
                    reason="already_processed_or_filtered",
                )

        except LoopDetectedError as e:
            # This is expected - just log and return success
            logger.debug(
                "chatwork_message_loop_detected",
                message_id=event.get("message_id"),
            )

        except MappingNotFoundError as e:
            logger.warning(
                "chatwork_room_mapping_not_found",
                room_id=event.get("room_id"),
                error=str(e),
            )
            # Return success to avoid webhook retry
            # Could also return 404, but that would trigger retries

        except Exception as e:
            logger.error(
                "chatwork_message_processing_error",
                message_id=event.get("message_id"),
                error=str(e),
                error_type=type(e).__name__,
            )
            # Return 500 to signal error
            # Note: Chatwork doesn't retry failed webhooks
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process message",
            )

    elif event_type == "message_updated":
        # TODO: Handle message edits
        logger.info(
            "chatwork_message_updated_ignored",
            message_id=event.get("message_id"),
            reason="edit_sync_not_implemented",
        )

    elif event_type == "mention_to_me":
        # TODO: Handle mentions
        logger.info(
            "chatwork_mention_received_ignored",
            message_id=event.get("message_id"),
            reason="mention_sync_not_implemented",
        )

    else:
        logger.warning(
            "chatwork_unknown_event_type",
            event_type=event_type,
        )

    # Always return 200 OK to Chatwork
    return {"status": "ok"}
