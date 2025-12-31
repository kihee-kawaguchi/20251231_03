"""Redis client for data storage and caching."""

import json
from typing import Any, Optional
from datetime import datetime, timezone

import redis.asyncio as aioredis
from redis.asyncio import ConnectionPool

from ..core.config import settings
from ..core.exceptions import RedisConnectionError
from ..core.logging import get_logger

logger = get_logger(__name__)


class RedisClient:
    """Async Redis client wrapper."""

    def __init__(self):
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        """Establish Redis connection pool."""
        try:
            self._pool = ConnectionPool.from_url(
                settings.redis_url,
                password=settings.redis_password,
                max_connections=settings.redis_max_connections,
                decode_responses=True,
            )
            self._client = aioredis.Redis(connection_pool=self._pool)

            # Test connection
            await self._client.ping()
            logger.info("redis_connected", url=settings.redis_url)
        except Exception as e:
            logger.error("redis_connection_failed", error=str(e))
            raise RedisConnectionError(f"Failed to connect to Redis: {e}")

    async def disconnect(self) -> None:
        """Close Redis connection pool."""
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
        logger.info("redis_disconnected")

    def is_connected(self) -> bool:
        """Check if Redis client is connected."""
        return self._client is not None

    @property
    def client(self) -> aioredis.Redis:
        """Get Redis client instance."""
        if not self._client:
            raise RedisConnectionError("Redis client not connected")
        return self._client

    @client.setter
    def client(self, value: aioredis.Redis) -> None:
        """Set Redis client instance (mainly for testing)."""
        self._client = value

    # Message ID Mapping
    async def save_message_mapping(
        self,
        source_platform: str,
        source_message_id: str,
        target_platform: str,
        target_message_id: str,
        room_mapping_id: Optional[str] = None,
    ) -> None:
        """Save message ID mapping for loop detection."""
        key = f"msg:{source_platform}:{source_message_id}"
        value = {
            "source_platform": source_platform,
            "source_message_id": source_message_id,
            "target_platform": target_platform,
            "target_message_id": target_message_id,
            "room_mapping_id": room_mapping_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        await self.client.setex(
            key,
            settings.message_ttl_seconds,
            json.dumps(value),
        )
        logger.debug(
            "message_mapping_saved",
            source_platform=source_platform,
            source_message_id=source_message_id,
            target_message_id=target_message_id,
        )

    async def get_message_mapping(
        self, platform: str, message_id: str
    ) -> Optional[dict]:
        """Get message mapping by platform and message ID."""
        key = f"msg:{platform}:{message_id}"
        value = await self.client.get(key)

        if value:
            return json.loads(value)
        return None

    async def is_message_processed(self, platform: str, message_id: str) -> bool:
        """Check if message has already been processed."""
        return await self.client.exists(f"msg:{platform}:{message_id}") > 0

    # Room Mapping (cached from database)
    async def get_room_mapping(
        self, source_platform: str, source_room_id: str
    ) -> Optional[str]:
        """Get target room ID from mapping cache."""
        key = f"room:{source_platform}:{source_room_id}"
        return await self.client.get(key)

    async def set_room_mapping(
        self,
        source_platform: str,
        source_room_id: str,
        target_room_id: str,
        ttl: int = 3600,  # 1 hour cache
    ) -> None:
        """Cache room mapping."""
        key = f"room:{source_platform}:{source_room_id}"
        await self.client.setex(key, ttl, target_room_id)

    # User Mapping (cached from database)
    async def get_user_mapping(
        self, source_platform: str, source_user_id: str
    ) -> Optional[dict]:
        """Get user mapping from cache."""
        key = f"user:{source_platform}:{source_user_id}"
        value = await self.client.get(key)

        if value:
            return json.loads(value)
        return None

    async def set_user_mapping(
        self,
        source_platform: str,
        source_user_id: str,
        user_data: dict,
        ttl: int = 3600,
    ) -> None:
        """Cache user mapping."""
        key = f"user:{source_platform}:{source_user_id}"
        await self.client.setex(key, ttl, json.dumps(user_data))

    # Failed Messages Queue (Dead Letter Queue)
    async def add_to_failed_queue(
        self,
        source_platform: str,
        target_platform: str,
        message_data: dict,
        error: str,
        retry_count: int = 0,
    ) -> None:
        """Add failed message to DLQ."""
        timestamp = datetime.now(timezone.utc).isoformat()
        key = f"failed:{timestamp}:{source_platform}:{message_data.get('message_id', 'unknown')}"

        value = {
            "source_platform": source_platform,
            "target_platform": target_platform,
            "message": message_data,
            "error": error,
            "retry_count": retry_count,
            "failed_at": timestamp,
        }

        await self.client.setex(
            key,
            settings.message_ttl_seconds * 7,  # Keep failed messages for 7 days
            json.dumps(value),
        )

        logger.warning(
            "message_added_to_dlq",
            source_platform=source_platform,
            target_platform=target_platform,
            error=error,
            retry_count=retry_count,
        )

    async def get_failed_messages(
        self, limit: int = 100
    ) -> list[tuple[str, dict]]:
        """Get failed messages from DLQ."""
        keys = await self.client.keys("failed:*")
        keys = keys[:limit]

        messages = []
        for key in keys:
            value = await self.client.get(key)
            if value:
                messages.append((key, json.loads(value)))

        return messages

    # Rate Limiting
    async def check_rate_limit(
        self, key: str, limit: int, window_seconds: int
    ) -> bool:
        """
        Check if rate limit is exceeded.

        Returns True if under limit, False if exceeded.
        """
        current = await self.client.incr(key)

        if current == 1:
            await self.client.expire(key, window_seconds)

        return current <= limit

    # Health Check
    async def health_check(self) -> bool:
        """Check Redis connection health."""
        try:
            await self.client.ping()
            return True
        except Exception as e:
            logger.error("redis_health_check_failed", error=str(e))
            return False


# Global Redis client instance
redis_client = RedisClient()
