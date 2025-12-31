"""Pytest configuration and shared fixtures."""

import asyncio
import json
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import fakeredis.aioredis
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.core.config import settings
from src.services.redis_client import RedisClient
from src.main import app


# ============================================================================
# Event Loop Configuration
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for the entire test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Application Fixtures
# ============================================================================


@pytest.fixture
def test_client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
async def async_client(redis_client, mock_chatwork_client, mock_lark_client) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing with dependency overrides."""
    from src.services.redis_client import redis_client as actual_redis
    from src.services.chatwork_client import chatwork_client as actual_chatwork
    from src.services.lark_client import lark_client as actual_lark

    # Store original clients (access _client directly to avoid property check)
    original_redis = getattr(actual_redis, '_client', None)
    original_chatwork_send = getattr(actual_chatwork, 'send_message', None)
    original_lark_send = getattr(actual_lark, 'send_text_message', None)

    # Override with test clients
    try:
        actual_redis._client = redis_client.client
        actual_redis._connected = True
        if hasattr(actual_chatwork, 'send_message'):
            actual_chatwork.send_message = mock_chatwork_client.send_message
            actual_chatwork.format_message_from_lark = mock_chatwork_client.format_message_from_lark
        if hasattr(actual_lark, 'send_text_message'):
            actual_lark.send_text_message = mock_lark_client.send_text_message
            actual_lark.format_message_from_chatwork = mock_lark_client.format_message_from_chatwork

        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    finally:
        # Restore original clients
        if original_redis is not None:
            actual_redis._client = original_redis
        else:
            actual_redis._client = None
            actual_redis._connected = False
        if original_chatwork_send is not None:
            actual_chatwork.send_message = original_chatwork_send
        if original_lark_send is not None:
            actual_lark.send_text_message = original_lark_send


# ============================================================================
# Redis Fixtures
# ============================================================================


@pytest.fixture
async def fake_redis():
    """Create fake Redis client for testing."""
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield redis
    await redis.flushall()
    await redis.close()


@pytest.fixture
async def redis_client(fake_redis):
    """Create RedisClient instance with fake Redis."""
    client = RedisClient()
    client.client = fake_redis
    client._connected = True
    yield client
    await client.disconnect()


# ============================================================================
# Mock Service Fixtures
# ============================================================================


@pytest.fixture
def mock_chatwork_client():
    """Mock Chatwork API client."""
    mock = AsyncMock()
    mock.send_message = AsyncMock(return_value="999")
    mock.format_message_from_lark = MagicMock(
        return_value="[From Lark] User: Test message"
    )
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_lark_client():
    """Mock Lark API client."""
    mock = AsyncMock()
    mock.send_text_message = AsyncMock(return_value="om_test123")
    mock.format_message_from_chatwork = MagicMock(
        return_value="[From Chatwork] User: Test message"
    )
    return mock


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def chatwork_webhook_data() -> Dict[str, Any]:
    """Sample Chatwork webhook payload."""
    return {
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


@pytest.fixture
def chatwork_webhook_with_lark_prefix() -> Dict[str, Any]:
    """Chatwork webhook with message from Lark (should be filtered)."""
    return {
        "webhook_setting_id": "12345",
        "webhook_event_type": "message_created",
        "webhook_event_time": 1234567890,
        "webhook_event": {
            "message_id": "888",
            "room_id": 12345678,
            "account_id": 111,
            "body": "[From Lark] User ou_123: Message from Lark",
            "send_time": 1234567890,
            "update_time": 1234567890,
            "from_account_id": 111,
        },
    }


@pytest.fixture
def lark_webhook_data() -> Dict[str, Any]:
    """Sample Lark webhook payload."""
    return {
        "schema": "2.0",
        "header": {
            "event_id": "evt_123",
            "event_type": "im.message.receive_v1",
            "create_time": "1234567890",
            "token": "test_verification_token",
            "app_id": "cli_test",
            "tenant_key": "tenant_test",
        },
        "event": {
            "sender": {
                "sender_id": {
                    "open_id": "ou_test123",
                    "user_id": "user_test",
                },
                "sender_type": "user",
                "tenant_key": "tenant_test",
            },
            "message": {
                "message_id": "om_test123",
                "message_type": "text",
                "chat_id": "oc_a1b2c3d4e5f6",
                "content": json.dumps({"text": "Hello from Lark!"}),
                "create_time": "1234567890",
            },
        },
    }


@pytest.fixture
def lark_webhook_with_chatwork_prefix() -> Dict[str, Any]:
    """Lark webhook with message from Chatwork (should be filtered)."""
    return {
        "schema": "2.0",
        "header": {
            "event_id": "evt_456",
            "event_type": "im.message.receive_v1",
            "create_time": "1234567890",
            "token": "test_verification_token",
            "app_id": "cli_test",
            "tenant_key": "tenant_test",
        },
        "event": {
            "sender": {
                "sender_id": {
                    "open_id": "ou_test456",
                    "user_id": "user_test2",
                },
                "sender_type": "user",
                "tenant_key": "tenant_test",
            },
            "message": {
                "message_id": "om_test456",
                "message_type": "text",
                "chat_id": "oc_a1b2c3d4e5f6",
                "content": json.dumps(
                    {"text": "[From Chatwork] User 123: Message from Chatwork"}
                ),
                "create_time": "1234567890",
            },
        },
    }


@pytest.fixture
def lark_url_verification_data() -> Dict[str, Any]:
    """Lark URL verification challenge payload."""
    return {
        "type": "url_verification",
        "challenge": "test_challenge_string",
        "token": "test_verification_token",
    }


@pytest.fixture
def room_mapping_data() -> Dict[str, Any]:
    """Sample room mapping configuration."""
    return {
        "mappings": [
            {
                "chatwork_room_id": "12345678",
                "lark_chat_id": "oc_a1b2c3d4e5f6",
                "name": "Test Room 1",
                "is_active": True,
                "sync_direction": "both",
            },
            {
                "chatwork_room_id": "87654321",
                "lark_chat_id": "oc_g7h8i9j0k1l2",
                "name": "Test Room 2",
                "is_active": True,
                "sync_direction": "both",
            },
        ]
    }


@pytest.fixture
def user_mapping_data() -> Dict[str, Any]:
    """Sample user mapping configuration."""
    return {
        "mappings": [
            {
                "chatwork_user_id": "111",
                "lark_user_id": "ou_test123",
                "display_name": "Test User 1",
                "is_active": True,
            },
            {
                "chatwork_user_id": "222",
                "lark_user_id": "ou_test456",
                "display_name": "Test User 2",
                "is_active": True,
            },
        ]
    }


# ============================================================================
# Environment Configuration
# ============================================================================


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("CHATWORK_API_TOKEN", "test_chatwork_token")
    monkeypatch.setenv("CHATWORK_WEBHOOK_SECRET", "dGVzdF9zZWNyZXQ=")  # base64
    monkeypatch.setenv("LARK_APP_ID", "cli_test")
    monkeypatch.setenv("LARK_APP_SECRET", "test_lark_secret")
    monkeypatch.setenv("LARK_VERIFICATION_TOKEN", "test_verification_token")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("ENABLE_LOOP_DETECTION", "true")
    monkeypatch.setenv("MESSAGE_PREFIX_CHATWORK", "[From Chatwork]")
    monkeypatch.setenv("MESSAGE_PREFIX_LARK", "[From Lark]")

    # Reload settings to pick up new env vars
    import importlib
    from src.core import config
    importlib.reload(config)

    # Update the global settings object in all modules that imported it
    from src.core.config import settings as new_settings
    import src.utils.webhook_verification
    src.utils.webhook_verification.settings = new_settings
