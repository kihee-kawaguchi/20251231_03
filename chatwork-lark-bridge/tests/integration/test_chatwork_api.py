"""Integration tests for Chatwork webhook endpoint."""

import base64
import hashlib
import hmac
import json
import pytest
from unittest.mock import patch, AsyncMock

from src.core.config import settings


@pytest.mark.integration
class TestChatworkWebhook:
    """Test Chatwork webhook endpoint."""

    @pytest.mark.asyncio
    async def test_chatwork_webhook_success(
        self,
        async_client,
        chatwork_webhook_data,
        fake_redis,
    ):
        """Test successful Chatwork webhook processing."""
        # Setup room mapping in Redis
        await fake_redis.setex(
            "room:chatwork:12345678",
            86400,
            "oc_test_chat",
        )

        # Generate valid signature
        body = json.dumps(chatwork_webhook_data).encode()
        secret = settings.chatwork_webhook_secret
        decoded_secret = base64.b64decode(secret)
        digest = hmac.new(decoded_secret, body, hashlib.sha256).digest()
        signature = base64.b64encode(digest).decode()

        # Mock the message processor
        with patch("src.api.chatwork.message_processor") as mock_processor:
            mock_processor.process_chatwork_message = AsyncMock(
                return_value="om_lark_123"
            )

            response = await async_client.post(
                "/webhook/chatwork/",
                json=chatwork_webhook_data,
                headers={"X-ChatWorkWebhookSignature": signature},
            )

            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

            # Verify processor was called
            mock_processor.process_chatwork_message.assert_called_once()
            call_args = mock_processor.process_chatwork_message.call_args
            assert call_args.kwargs["room_id"] == "12345678"
            assert call_args.kwargs["message_id"] == "999"

    @pytest.mark.asyncio
    async def test_chatwork_webhook_invalid_signature(
        self, async_client, chatwork_webhook_data
    ):
        """Test Chatwork webhook with invalid signature."""
        response = await async_client.post(
            "/webhook/chatwork/",
            json=chatwork_webhook_data,
            headers={"X-ChatWorkWebhookSignature": "invalid_signature"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_chatwork_webhook_missing_signature(
        self, async_client, chatwork_webhook_data
    ):
        """Test Chatwork webhook without signature header."""
        response = await async_client.post(
            "/webhook/chatwork/",
            json=chatwork_webhook_data,
        )

        assert response.status_code == 422  # Missing required header

    @pytest.mark.asyncio
    async def test_chatwork_webhook_loop_detected(
        self,
        async_client,
        chatwork_webhook_with_lark_prefix,
        fake_redis,
    ):
        """Test Chatwork webhook with looped message."""
        # Setup room mapping
        await fake_redis.setex(
            "room:chatwork:12345678",
            86400,
            "oc_test_chat",
        )

        # Generate valid signature
        body = json.dumps(chatwork_webhook_with_lark_prefix).encode()
        secret = settings.chatwork_webhook_secret
        decoded_secret = base64.b64decode(secret)
        digest = hmac.new(decoded_secret, body, hashlib.sha256).digest()
        signature = base64.b64encode(digest).decode()

        with patch("src.api.chatwork.message_processor") as mock_processor:
            from src.core.exceptions import LoopDetectedError

            mock_processor.process_chatwork_message = AsyncMock(
                side_effect=LoopDetectedError("Loop detected")
            )

            response = await async_client.post(
                "/webhook/chatwork/",
                json=chatwork_webhook_with_lark_prefix,
                headers={"X-ChatWorkWebhookSignature": signature},
            )

            # Should return 200 OK even with loop detection
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_chatwork_webhook_room_not_mapped(
        self, async_client, chatwork_webhook_data
    ):
        """Test Chatwork webhook for unmapped room."""
        # Generate valid signature
        body = json.dumps(chatwork_webhook_data).encode()
        secret = settings.chatwork_webhook_secret
        decoded_secret = base64.b64decode(secret)
        digest = hmac.new(decoded_secret, body, hashlib.sha256).digest()
        signature = base64.b64encode(digest).decode()

        with patch("src.api.chatwork.message_processor") as mock_processor:
            from src.core.exceptions import MappingNotFoundError

            mock_processor.process_chatwork_message = AsyncMock(
                side_effect=MappingNotFoundError("chatwork", "12345678")
            )

            response = await async_client.post(
                "/webhook/chatwork/",
                json=chatwork_webhook_data,
                headers={"X-ChatWorkWebhookSignature": signature},
            )

            # Should return 200 OK to avoid retry
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_chatwork_webhook_non_message_event(
        self, async_client
    ):
        """Test Chatwork webhook with non-message event."""
        event_data = {
            "webhook_setting_id": "12345",
            "webhook_event_type": "room_member_added",
            "webhook_event_time": 1234567890,
            "webhook_event": {},
        }

        # Generate valid signature
        body = json.dumps(event_data).encode()
        secret = settings.chatwork_webhook_secret
        decoded_secret = base64.b64decode(secret)
        digest = hmac.new(decoded_secret, body, hashlib.sha256).digest()
        signature = base64.b64encode(digest).decode()

        response = await async_client.post(
            "/webhook/chatwork/",
            json=event_data,
            headers={"X-ChatWorkWebhookSignature": signature},
        )

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
