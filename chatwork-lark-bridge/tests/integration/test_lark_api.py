"""Integration tests for Lark webhook endpoint."""

import json
import pytest
from unittest.mock import patch, AsyncMock

from src.core.config import settings


@pytest.mark.integration
class TestLarkWebhook:
    """Test Lark webhook endpoint."""

    @pytest.mark.asyncio
    async def test_lark_url_verification(
        self, async_client, lark_url_verification_data
    ):
        """Test Lark URL verification challenge."""
        response = await async_client.post(
            "/webhook/lark/",
            json=lark_url_verification_data,
        )

        assert response.status_code == 200
        json_response = response.json()
        assert json_response["challenge"] == "test_challenge_string"

    @pytest.mark.asyncio
    async def test_lark_url_verification_invalid_token(
        self, async_client, monkeypatch
    ):
        """Test Lark URL verification with invalid token."""
        monkeypatch.setenv("LARK_VERIFICATION_TOKEN", "correct_token")

        verification_data = {
            "type": "url_verification",
            "challenge": "test_challenge",
            "token": "wrong_token",
        }

        response = await async_client.post(
            "/webhook/lark/",
            json=verification_data,
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_lark_message_event_success(
        self, async_client, lark_webhook_data, fake_redis
    ):
        """Test successful Lark message event processing."""
        # Setup room mapping
        await fake_redis.setex(
            "room:lark:oc_a1b2c3d4e5f6",
            86400,
            "12345678",
        )

        with patch("src.api.lark.message_processor") as mock_processor:
            mock_processor.process_lark_message = AsyncMock(
                return_value="999"
            )

            response = await async_client.post(
                "/webhook/lark/",
                json=lark_webhook_data,
            )

            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

            # Verify processor was called
            mock_processor.process_lark_message.assert_called_once()
            call_args = mock_processor.process_lark_message.call_args
            assert call_args.kwargs["chat_id"] == "oc_a1b2c3d4e5f6"
            assert call_args.kwargs["message_id"] == "om_test123"
            assert call_args.kwargs["message_text"] == "Hello from Lark!"

    @pytest.mark.asyncio
    async def test_lark_message_event_loop_detected(
        self, async_client, lark_webhook_with_chatwork_prefix, fake_redis
    ):
        """Test Lark message event with looped message."""
        # Setup room mapping
        await fake_redis.setex(
            "room:lark:oc_a1b2c3d4e5f6",
            86400,
            "12345678",
        )

        with patch("src.api.lark.message_processor") as mock_processor:
            from src.core.exceptions import LoopDetectedError

            mock_processor.process_lark_message = AsyncMock(
                side_effect=LoopDetectedError("Loop detected")
            )

            response = await async_client.post(
                "/webhook/lark/",
                json=lark_webhook_with_chatwork_prefix,
            )

            # Should return 200 OK even with loop detection
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_lark_message_event_room_not_mapped(
        self, async_client, lark_webhook_data
    ):
        """Test Lark message event for unmapped room."""
        with patch("src.api.lark.message_processor") as mock_processor:
            from src.core.exceptions import MappingNotFoundError

            mock_processor.process_lark_message = AsyncMock(
                side_effect=MappingNotFoundError("lark", "oc_a1b2c3d4e5f6")
            )

            response = await async_client.post(
                "/webhook/lark/",
                json=lark_webhook_data,
            )

            # Should return 200 OK to avoid retry
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_lark_non_text_message(
        self, async_client, fake_redis
    ):
        """Test Lark non-text message type."""
        # Setup room mapping
        await fake_redis.setex(
            "room:lark:oc_a1b2c3d4e5f6",
            86400,
            "12345678",
        )

        # Image message
        image_message_data = {
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
                    "message_id": "om_test123",
                    "message_type": "image",  # Non-text type
                    "chat_id": "oc_a1b2c3d4e5f6",
                    "content": json.dumps({"image_key": "img_v2_xxx"}),
                },
            },
        }

        response = await async_client.post(
            "/webhook/lark/",
            json=image_message_data,
        )

        # Should return 200 OK but skip processing
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_lark_message_read_event(self, async_client):
        """Test Lark message read event (not yet implemented)."""
        read_event_data = {
            "schema": "2.0",
            "header": {
                "event_id": "evt_read_123",
                "event_type": "im.message.message_read_v1",
                "create_time": "1234567890",
                "token": settings.lark_verification_token,
                "app_id": "cli_test",
                "tenant_key": "tenant_test",
            },
            "event": {},
        }

        response = await async_client.post(
            "/webhook/lark/",
            json=read_event_data,
        )

        # Should return 200 OK but skip processing
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_lark_unknown_event_type(self, async_client):
        """Test Lark unknown event type."""
        unknown_event_data = {
            "schema": "2.0",
            "header": {
                "event_id": "evt_unknown_123",
                "event_type": "unknown.event.type",
                "create_time": "1234567890",
                "token": settings.lark_verification_token,
                "app_id": "cli_test",
                "tenant_key": "tenant_test",
            },
            "event": {},
        }

        response = await async_client.post(
            "/webhook/lark/",
            json=unknown_event_data,
        )

        # Should return 200 OK
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_lark_message_processing_error(
        self, async_client, lark_webhook_data, fake_redis
    ):
        """Test Lark message processing with unexpected error."""
        # Setup room mapping
        await fake_redis.setex(
            "room:lark:oc_a1b2c3d4e5f6",
            86400,
            "12345678",
        )

        with patch("src.api.lark.message_processor") as mock_processor:
            mock_processor.process_lark_message = AsyncMock(
                side_effect=Exception("Unexpected error")
            )

            response = await async_client.post(
                "/webhook/lark/",
                json=lark_webhook_data,
            )

            # Should return 500 for unexpected errors
            assert response.status_code == 500


@pytest.mark.integration
class TestHealthEndpoints:
    """Test health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, async_client, fake_redis):
        """Test /health endpoint."""
        response = await async_client.get("/health/")

        assert response.status_code == 200
        json_response = response.json()
        assert json_response["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_ready_check(self, async_client, fake_redis):
        """Test /health/ready endpoint."""
        response = await async_client.get("/health/ready")

        assert response.status_code == 200
        json_response = response.json()
        assert json_response["ready"] is True

    @pytest.mark.asyncio
    async def test_live_check(self, async_client):
        """Test /health/live endpoint."""
        response = await async_client.get("/health/live")

        assert response.status_code == 200
        json_response = response.json()
        assert json_response["alive"] is True
