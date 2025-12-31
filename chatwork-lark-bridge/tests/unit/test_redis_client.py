"""Unit tests for Redis client."""

import json
import pytest
from datetime import datetime, timezone

from src.services.redis_client import RedisClient


@pytest.mark.unit
@pytest.mark.redis
class TestRedisClient:
    """Test Redis client operations."""

    @pytest.mark.asyncio
    async def test_save_and_get_message_mapping(self, redis_client):
        """Test saving and retrieving message mapping."""
        await redis_client.save_message_mapping(
            source_platform="chatwork",
            source_message_id="999",
            target_platform="lark",
            target_message_id="om_test123",
        )

        mapping = await redis_client.get_message_mapping("chatwork", "999")

        assert mapping is not None
        assert mapping["source_platform"] == "chatwork"
        assert mapping["target_platform"] == "lark"
        assert mapping["target_message_id"] == "om_test123"
        assert "timestamp" in mapping

    @pytest.mark.asyncio
    async def test_get_non_existent_message_mapping(self, redis_client):
        """Test retrieving non-existent message mapping."""
        mapping = await redis_client.get_message_mapping("chatwork", "nonexistent")

        assert mapping is None

    @pytest.mark.asyncio
    async def test_is_message_processed(self, redis_client):
        """Test checking if message is already processed."""
        # Initially not processed
        is_processed = await redis_client.is_message_processed("chatwork", "999")
        assert is_processed is False

        # Save mapping
        await redis_client.save_message_mapping(
            "chatwork", "999", "lark", "om_test123"
        )

        # Now should be processed
        is_processed = await redis_client.is_message_processed("chatwork", "999")
        assert is_processed is True

    @pytest.mark.asyncio
    async def test_set_and_get_room_mapping(self, redis_client):
        """Test setting and getting room mapping."""
        await redis_client.set_room_mapping(
            source_platform="chatwork",
            source_room_id="12345678",
            target_room_id="oc_a1b2c3d4e5f6",
            ttl=3600,
        )

        target_room_id = await redis_client.get_room_mapping("chatwork", "12345678")

        assert target_room_id == "oc_a1b2c3d4e5f6"

    @pytest.mark.asyncio
    async def test_get_non_existent_room_mapping(self, redis_client):
        """Test retrieving non-existent room mapping."""
        target_room_id = await redis_client.get_room_mapping("chatwork", "nonexistent")

        assert target_room_id is None

    @pytest.mark.asyncio
    async def test_bidirectional_room_mapping(self, redis_client):
        """Test bidirectional room mapping."""
        # Set both directions
        await redis_client.set_room_mapping(
            "chatwork", "12345678", "oc_a1b2c3d4e5f6"
        )
        await redis_client.set_room_mapping(
            "lark", "oc_a1b2c3d4e5f6", "12345678"
        )

        # Verify both directions
        lark_room = await redis_client.get_room_mapping("chatwork", "12345678")
        chatwork_room = await redis_client.get_room_mapping("lark", "oc_a1b2c3d4e5f6")

        assert lark_room == "oc_a1b2c3d4e5f6"
        assert chatwork_room == "12345678"

    @pytest.mark.asyncio
    async def test_set_and_get_user_mapping(self, redis_client):
        """Test setting and getting user mapping."""
        user_data = {
            "name": "Test User",
            "lark_user_id": "ou_test123",
        }

        await redis_client.set_user_mapping(
            source_platform="chatwork",
            source_user_id="111",
            user_data=user_data,
            ttl=3600,
        )

        retrieved_data = await redis_client.get_user_mapping("chatwork", "111")

        assert retrieved_data is not None
        assert retrieved_data["name"] == "Test User"
        assert retrieved_data["lark_user_id"] == "ou_test123"

    @pytest.mark.asyncio
    async def test_add_to_failed_queue(self, redis_client):
        """Test adding message to failed queue (DLQ)."""
        message_data = {
            "message_id": "999",
            "room_id": "12345",
        }

        await redis_client.add_to_failed_queue(
            source_platform="chatwork",
            target_platform="lark",
            message_data=message_data,
            error="API error",
        )

        # Verify it was added (check using Redis directly)
        failed_keys = await redis_client.client.keys("failed:*")

        assert len(failed_keys) == 1
        stored_json = await redis_client.client.get(failed_keys[0])
        stored_data = json.loads(stored_json)
        assert stored_data["message"]["message_id"] == "999"
        assert stored_data["error"] == "API error"
        assert stored_data["source_platform"] == "chatwork"
        assert stored_data["target_platform"] == "lark"

    @pytest.mark.asyncio
    async def test_get_failed_messages(self, redis_client):
        """Test retrieving failed messages from DLQ."""
        # Add some failed messages
        await redis_client.add_to_failed_queue(
            "chatwork", "lark", {"message_id": "999"}, "Error 1"
        )
        await redis_client.add_to_failed_queue(
            "lark", "chatwork", {"message_id": "om_123"}, "Error 2"
        )

        # Retrieve failed messages (returns list of tuples: (key, data))
        failed_messages = await redis_client.get_failed_messages(limit=10)

        assert len(failed_messages) == 2
        # Each item is a tuple (key, data_dict)
        keys_and_data = [(key, data) for key, data in failed_messages]
        message_ids = [data["message"]["message_id"] for _, data in failed_messages]
        assert "999" in message_ids
        assert "om_123" in message_ids

    @pytest.mark.asyncio
    async def test_get_failed_messages_with_limit(self, redis_client):
        """Test retrieving failed messages with limit."""
        # Add 5 failed messages
        for i in range(5):
            await redis_client.add_to_failed_queue(
                "chatwork", "lark",
                {"message_id": f"msg_{i}"},
                f"Error {i}"
            )

        # Get only 3
        failed_messages = await redis_client.get_failed_messages(limit=3)

        assert len(failed_messages) == 3

    @pytest.mark.asyncio
    async def test_message_ttl(self, redis_client):
        """Test message mapping TTL."""
        await redis_client.save_message_mapping(
            "chatwork", "999", "lark", "om_123"
        )

        # Check TTL is set (should be around 86400 seconds = 24 hours)
        ttl = await redis_client.client.ttl("msg:chatwork:999")
        assert ttl > 0
        assert ttl <= 86400  # Within 24 hours

    @pytest.mark.asyncio
    async def test_room_mapping_ttl(self, redis_client):
        """Test room mapping TTL."""
        await redis_client.set_room_mapping(
            "chatwork", "12345678", "oc_test", ttl=2
        )

        # Check TTL is set
        ttl = await redis_client.client.ttl("room:chatwork:12345678")
        assert ttl > 0
        assert ttl <= 2

    @pytest.mark.asyncio
    async def test_connection_state(self, redis_client):
        """Test Redis connection state tracking."""
        assert redis_client.is_connected() is True

        await redis_client.disconnect()
        assert redis_client.is_connected() is False
