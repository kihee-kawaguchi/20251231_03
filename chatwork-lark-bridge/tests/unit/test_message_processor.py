"""Unit tests for message processor."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.message_processor import MessageProcessor
from src.core.exceptions import (
    LoopDetectedError,
    MappingNotFoundError,
)


@pytest.mark.unit
class TestMessageProcessor:
    """Test message processing logic."""

    @pytest.fixture
    def message_processor(self, redis_client, mock_chatwork_client, mock_lark_client):
        """Create message processor instance with mocks."""
        processor = MessageProcessor()
        processor.redis = redis_client
        processor.chatwork = mock_chatwork_client
        processor.lark = mock_lark_client
        return processor

    @pytest.mark.asyncio
    async def test_process_chatwork_message_success(
        self, message_processor, redis_client
    ):
        """Test successful Chatwork message processing."""
        # Set up room mapping
        await redis_client.set_room_mapping("chatwork", "12345678", "oc_test")

        result = await message_processor.process_chatwork_message(
            room_id="12345678",
            message_id="999",
            sender_name="Test User",
            message_body="Hello from Chatwork!",
        )

        assert result == "om_test123"  # Mock Lark client returns this
        message_processor.lark.send_text_message.assert_called_once()

        # Verify message mapping was saved
        mapping = await redis_client.get_message_mapping("chatwork", "999")
        assert mapping is not None
        assert mapping["target_message_id"] == "om_test123"

    @pytest.mark.asyncio
    async def test_process_chatwork_message_already_processed(
        self, message_processor, redis_client
    ):
        """Test processing already processed message."""
        # Mark message as already processed
        await redis_client.save_message_mapping(
            "chatwork", "999", "lark", "om_existing"
        )

        result = await message_processor.process_chatwork_message(
            room_id="12345678",
            message_id="999",
            sender_name="Test User",
            message_body="Duplicate message",
        )

        assert result is None
        message_processor.lark.send_text_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_chatwork_message_loop_detection(
        self, message_processor, redis_client
    ):
        """Test loop detection for Chatwork message."""
        # Set up room mapping
        await redis_client.set_room_mapping("chatwork", "12345678", "oc_test")

        # Message with Lark prefix (came from Lark originally)
        with pytest.raises(LoopDetectedError):
            await message_processor.process_chatwork_message(
                room_id="12345678",
                message_id="999",
                sender_name="Test User",
                message_body="[From Lark] User: This is from Lark",
            )

        message_processor.lark.send_text_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_chatwork_message_no_mapping(
        self, message_processor, redis_client
    ):
        """Test processing message with no room mapping."""
        # No mapping set

        with pytest.raises(MappingNotFoundError):
            await message_processor.process_chatwork_message(
                room_id="99999999",  # Non-existent room
                message_id="999",
                sender_name="Test User",
                message_body="Hello",
            )

        message_processor.lark.send_text_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_lark_message_success(
        self, message_processor, redis_client
    ):
        """Test successful Lark message processing."""
        # Set up room mapping
        await redis_client.set_room_mapping("lark", "oc_test", "12345678")

        result = await message_processor.process_lark_message(
            chat_id="oc_test",
            message_id="om_123",
            sender_name="Lark User",
            message_text="Hello from Lark!",
        )

        assert result == "999"  # Mock Chatwork client returns this
        message_processor.chatwork.send_message.assert_called_once()

        # Verify message mapping was saved
        mapping = await redis_client.get_message_mapping("lark", "om_123")
        assert mapping is not None
        assert mapping["target_message_id"] == "999"

    @pytest.mark.asyncio
    async def test_process_lark_message_already_processed(
        self, message_processor, redis_client
    ):
        """Test processing already processed Lark message."""
        # Mark message as already processed
        await redis_client.save_message_mapping(
            "lark", "om_123", "chatwork", "888"
        )

        result = await message_processor.process_lark_message(
            chat_id="oc_test",
            message_id="om_123",
            sender_name="Lark User",
            message_text="Duplicate message",
        )

        assert result is None
        message_processor.chatwork.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_lark_message_loop_detection(
        self, message_processor, redis_client
    ):
        """Test loop detection for Lark message."""
        # Set up room mapping
        await redis_client.set_room_mapping("lark", "oc_test", "12345678")

        # Message with Chatwork prefix (came from Chatwork originally)
        with pytest.raises(LoopDetectedError):
            await message_processor.process_lark_message(
                chat_id="oc_test",
                message_id="om_123",
                sender_name="Lark User",
                message_text="[From Chatwork] User: This is from Chatwork",
            )

        message_processor.chatwork.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_lark_message_no_mapping(
        self, message_processor, redis_client
    ):
        """Test processing Lark message with no room mapping."""
        # No mapping set

        with pytest.raises(MappingNotFoundError):
            await message_processor.process_lark_message(
                chat_id="oc_nonexistent",
                message_id="om_123",
                sender_name="Lark User",
                message_text="Hello",
            )

        message_processor.chatwork.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_message_formatting(self, message_processor):
        """Test message formatting with sender name."""
        # Chatwork format
        message_processor.lark.format_message_from_chatwork.return_value = (
            "[From Chatwork] Alice: Hello!"
        )

        formatted = message_processor.lark.format_message_from_chatwork(
            "Alice", "Hello!"
        )

        assert formatted.startswith("[From Chatwork]")
        assert "Alice" in formatted
        assert "Hello!" in formatted

    def test_loop_detection_logic(self, message_processor):
        """Test loop detection method."""
        # Should detect Lark prefix in Chatwork message
        assert message_processor._is_from_bridge(
            "[From Lark] User: test", "lark"
        ) is True

        # Should detect Chatwork prefix in Lark message
        assert message_processor._is_from_bridge(
            "[From Chatwork] User: test", "chatwork"
        ) is True

        # Should not detect for normal messages
        assert message_processor._is_from_bridge(
            "Normal message", "lark"
        ) is False
        assert message_processor._is_from_bridge(
            "Normal message", "chatwork"
        ) is False

    def test_loop_detection_case_sensitivity(self, message_processor):
        """Test loop detection is case-insensitive."""
        # Lowercase
        assert message_processor._is_from_bridge(
            "[from lark] test", "lark"
        ) is True

        # Uppercase
        assert message_processor._is_from_bridge(
            "[FROM CHATWORK] test", "chatwork"
        ) is True

        # Mixed case
        assert message_processor._is_from_bridge(
            "[From Lark] test", "lark"
        ) is True
