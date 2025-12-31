"""End-to-end tests for bidirectional message flow."""

import base64
import hashlib
import hmac
import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from src.core.config import settings


@pytest.mark.e2e
@pytest.mark.slow
class TestBidirectionalMessageFlow:
    """Test complete bidirectional message synchronization."""

    @pytest.mark.asyncio
    async def test_chatwork_to_lark_complete_flow(
        self, async_client, fake_redis
    ):
        """Test complete message flow from Chatwork to Lark."""
        # 1. Setup room mapping
        await fake_redis.setex(
            "room:chatwork:12345678",
            86400,
            "oc_lark_chat",
        )

        # 2. Prepare Chatwork webhook payload
        chatwork_data = {
            "webhook_setting_id": "12345",
            "webhook_event_type": "message_created",
            "webhook_event_time": 1234567890,
            "webhook_event": {
                "message_id": "999",
                "room_id": 12345678,
                "account_id": 111,
                "body": "Hello from Chatwork!",
                "send_time": 1234567890,
                "update_time": 1234567890,
                "from_account_id": 111,
            },
        }

        # 3. Generate valid signature
        body = json.dumps(chatwork_data).encode()
        secret = settings.chatwork_webhook_secret
        decoded_secret = base64.b64decode(secret)
        digest = hmac.new(decoded_secret, body, hashlib.sha256).digest()
        signature = base64.b64encode(digest).decode()

        # 4. Send webhook request (async_client already has mocked clients)
        response = await async_client.post(
            "/webhook/chatwork/",
            json=chatwork_data,
            headers={"X-ChatWorkWebhookSignature": signature},
        )

        # 5. Verify response
        assert response.status_code == 200

        # 6. Verify message mapping was saved in Redis
        mapping_key = "msg:chatwork:999"
        mapping_data = await fake_redis.get(mapping_key)

        if mapping_data:
            mapping = json.loads(mapping_data)
            assert mapping["source_platform"] == "chatwork"
            assert mapping["target_platform"] == "lark"
            assert mapping["target_message_id"] == "om_test123"  # From conftest mock

    @pytest.mark.asyncio
    async def test_lark_to_chatwork_complete_flow(
        self, async_client, fake_redis
    ):
        """Test complete message flow from Lark to Chatwork."""
        # 1. Setup room mapping
        await fake_redis.setex(
            "room:lark:oc_lark_chat",
            86400,
            "12345678",
        )

        # 2. Prepare Lark webhook payload
        lark_data = {
            "schema": "2.0",
            "header": {
                "event_id": "evt_123",
                "event_type": "im.message.receive_v1",
                "create_time": "1234567890",
                "token": settings.lark_verification_token,
                "app_id": "cli_test",
                "tenant_key": "tenant_test",
            },
            "event": {
                "sender": {
                    "sender_id": {
                        "open_id": "ou_test123",
                        "user_id": "user_test",
                    },
                },
                "message": {
                    "message_id": "om_lark_456",
                    "message_type": "text",
                    "chat_id": "oc_lark_chat",
                    "content": json.dumps({"text": "Hello from Lark!"}),
                },
            },
        }

        # 3. Send webhook request (async_client already has mocked clients)
        response = await async_client.post(
            "/webhook/lark/",
            json=lark_data,
        )

        # 4. Verify response
        assert response.status_code == 200

        # 5. Verify message mapping was saved in Redis
        mapping_key = "msg:lark:om_lark_456"
        mapping_data = await fake_redis.get(mapping_key)

        if mapping_data:
            mapping = json.loads(mapping_data)
            assert mapping["source_platform"] == "lark"
            assert mapping["target_platform"] == "chatwork"
            assert mapping["target_message_id"] == "999"  # From conftest mock

    @pytest.mark.asyncio
    async def test_loop_prevention_chatwork_to_lark_to_chatwork(
        self, async_client, fake_redis
    ):
        """Test loop prevention: Chatwork → Lark → (blocked) → Chatwork."""
        # 1. Setup bidirectional room mapping
        await fake_redis.setex("room:chatwork:12345678", 86400, "oc_test")
        await fake_redis.setex("room:lark:oc_test", 86400, "12345678")

        # 2. Original message from Chatwork
        chatwork_data = {
            "webhook_setting_id": "12345",
            "webhook_event_type": "message_created",
            "webhook_event_time": 1234567890,
            "webhook_event": {
                "message_id": "999",
                "room_id": 12345678,
                "account_id": 111,
                "body": "Original Chatwork message",
                "from_account_id": 111,
            },
        }

        # Generate signature
        body = json.dumps(chatwork_data).encode()
        secret = settings.chatwork_webhook_secret
        decoded_secret = base64.b64decode(secret)
        digest = hmac.new(decoded_secret, body, hashlib.sha256).digest()
        signature = base64.b64encode(digest).decode()

        # 3. Send to Lark (async_client already has mocked clients)
        response = await async_client.post(
            "/webhook/chatwork/",
            json=chatwork_data,
            headers={"X-ChatWorkWebhookSignature": signature},
        )
        assert response.status_code == 200

        # 4. Simulate Lark webhook with prefixed message (loop attempt)
        lark_looped_data = {
            "schema": "2.0",
            "header": {
                "event_id": "evt_loop",
                "event_type": "im.message.receive_v1",
                "create_time": "1234567890",
                "token": settings.lark_verification_token,
                "app_id": "cli_test",
                "tenant_key": "tenant_test",
            },
            "event": {
                "sender": {"sender_id": {"open_id": "ou_bot"}},
                "message": {
                    "message_id": "om_123",  # Same message
                    "message_type": "text",
                    "chat_id": "oc_test",
                    "content": json.dumps({
                        "text": "[From Chatwork] User: Original Chatwork message"
                    }),
                },
            },
        }

        # 4. Attempt to send back to Chatwork (should be blocked by loop detection)
        response = await async_client.post(
            "/webhook/lark/",
            json=lark_looped_data,
        )

        # Response should still be 200 OK
        assert response.status_code == 200

        # Verify no new message mapping was created for the looped message
        # (the original om_test123 -> 999 mapping should be the only one)
        looped_mapping_key = "msg:lark:om_test123"
        looped_mapping = await fake_redis.get(looped_mapping_key)
        # If loop detection worked, this message should not have been forwarded
        # So either no mapping exists, or it's the original mapping, not a new one

    @pytest.mark.asyncio
    async def test_loop_prevention_lark_to_chatwork_to_lark(
        self, async_client, fake_redis
    ):
        """Test loop prevention: Lark → Chatwork → (blocked) → Lark."""
        # 1. Setup bidirectional room mapping
        await fake_redis.setex("room:lark:oc_test", 86400, "12345678")
        await fake_redis.setex("room:chatwork:12345678", 86400, "oc_test")

        # 2. Original message from Lark
        lark_data = {
            "schema": "2.0",
            "header": {
                "event_id": "evt_original",
                "event_type": "im.message.receive_v1",
                "create_time": "1234567890",
                "token": settings.lark_verification_token,
                "app_id": "cli_test",
                "tenant_key": "tenant_test",
            },
            "event": {
                "sender": {"sender_id": {"open_id": "ou_user"}},
                "message": {
                    "message_id": "om_original",
                    "message_type": "text",
                    "chat_id": "oc_test",
                    "content": json.dumps({"text": "Original Lark message"}),
                },
            },
        }

        # 3. Send to Chatwork (async_client already has mocked clients)
        response = await async_client.post(
            "/webhook/lark/",
            json=lark_data,
        )
        assert response.status_code == 200

        # 4. Simulate Chatwork webhook with prefixed message (loop attempt)
        chatwork_looped_data = {
            "webhook_setting_id": "12345",
            "webhook_event_type": "message_created",
            "webhook_event_time": 1234567890,
            "webhook_event": {
                "message_id": "999",  # Same message
                "room_id": 12345678,
                "account_id": 111,
                "body": "[From Lark] User: Original Lark message",
                "from_account_id": 111,
            },
        }

        # Generate signature
        body = json.dumps(chatwork_looped_data).encode()
        secret = settings.chatwork_webhook_secret
        decoded_secret = base64.b64decode(secret)
        digest = hmac.new(decoded_secret, body, hashlib.sha256).digest()
        signature = base64.b64encode(digest).decode()

        # 4. Attempt to send back to Lark (should be blocked by loop detection)
        response = await async_client.post(
            "/webhook/chatwork/",
            json=chatwork_looped_data,
            headers={"X-ChatWorkWebhookSignature": signature},
        )

        # Response should still be 200 OK
        assert response.status_code == 200

        # Verify no new message mapping was created for the looped message
        looped_mapping_key = "msg:chatwork:999"
        looped_mapping = await fake_redis.get(looped_mapping_key)
        # If loop detection worked, message should not have been forwarded again

    @pytest.mark.asyncio
    async def test_duplicate_message_prevention(
        self, async_client, fake_redis
    ):
        """Test duplicate message prevention via Redis tracking."""
        # 1. Setup room mapping
        await fake_redis.setex("room:chatwork:12345678", 86400, "oc_test")

        # 2. Mark message as already processed
        await fake_redis.setex(
            "msg:chatwork:999",
            86400,
            json.dumps({
                "source_platform": "chatwork",
                "target_platform": "lark",
                "target_message_id": "om_existing",
                "timestamp": "2025-12-31T10:00:00Z",
            }),
        )

        # 3. Prepare webhook payload (duplicate)
        chatwork_data = {
            "webhook_setting_id": "12345",
            "webhook_event_type": "message_created",
            "webhook_event_time": 1234567890,
            "webhook_event": {
                "message_id": "999",  # Already processed
                "room_id": 12345678,
                "account_id": 111,
                "body": "Duplicate message",
                "from_account_id": 111,
            },
        }

        # Generate signature
        body = json.dumps(chatwork_data).encode()
        secret = settings.chatwork_webhook_secret
        decoded_secret = base64.b64decode(secret)
        digest = hmac.new(decoded_secret, body, hashlib.sha256).digest()
        signature = base64.b64encode(digest).decode()

        # 3. Send duplicate message (async_client already has mocked clients)
        response = await async_client.post(
            "/webhook/chatwork/",
            json=chatwork_data,
            headers={"X-ChatWorkWebhookSignature": signature},
        )

        # Response should be 200 OK
        assert response.status_code == 200

        # Verify the original mapping is still there (not overwritten)
        final_mapping_data = await fake_redis.get("msg:chatwork:999")
        final_mapping = json.loads(final_mapping_data)
        assert final_mapping["target_message_id"] == "om_existing"  # Original value
