"""Load and cache room/user mappings from configuration files."""

import json
from pathlib import Path
from typing import Optional

from ..core.logging import get_logger
from ..services.redis_client import redis_client

logger = get_logger(__name__)


class MappingLoader:
    """Loads and caches room and user mappings."""

    def __init__(self, config_dir: str = "config"):
        """Initialize mapping loader."""
        self.config_dir = Path(config_dir)
        self.redis = redis_client

    async def load_room_mappings(self) -> int:
        """
        Load room mappings from JSON file and cache in Redis.

        Returns:
            Number of mappings loaded
        """
        mapping_file = self.config_dir / "room_mappings.json"

        if not mapping_file.exists():
            logger.warning(
                "room_mappings_file_not_found",
                path=str(mapping_file),
            )
            return 0

        try:
            with open(mapping_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            mappings = data.get("mappings", [])
            loaded_count = 0

            for mapping in mappings:
                if not mapping.get("is_active", True):
                    continue

                chatwork_room_id = mapping["chatwork_room_id"]
                lark_chat_id = mapping["lark_chat_id"]
                name = mapping.get("name", "")

                # Cache bidirectional mapping
                await self.redis.set_room_mapping(
                    source_platform="chatwork",
                    source_room_id=chatwork_room_id,
                    target_room_id=lark_chat_id,
                    ttl=86400,  # 24 hours
                )

                await self.redis.set_room_mapping(
                    source_platform="lark",
                    source_room_id=lark_chat_id,
                    target_room_id=chatwork_room_id,
                    ttl=86400,
                )

                loaded_count += 1

                logger.info(
                    "room_mapping_loaded",
                    name=name,
                    chatwork_room_id=chatwork_room_id,
                    lark_chat_id=lark_chat_id,
                )

            logger.info(
                "room_mappings_loaded",
                total_count=loaded_count,
            )

            return loaded_count

        except Exception as e:
            logger.error(
                "failed_to_load_room_mappings",
                error=str(e),
            )
            raise

    async def load_user_mappings(self) -> int:
        """
        Load user mappings from JSON file and cache in Redis.

        Returns:
            Number of mappings loaded
        """
        mapping_file = self.config_dir / "user_mappings.json"

        if not mapping_file.exists():
            logger.info(
                "user_mappings_file_not_found_skipping",
                path=str(mapping_file),
            )
            return 0

        try:
            with open(mapping_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            mappings = data.get("mappings", [])
            loaded_count = 0

            for mapping in mappings:
                if not mapping.get("is_active", True):
                    continue

                chatwork_user_id = mapping.get("chatwork_user_id")
                lark_user_id = mapping.get("lark_user_id")
                display_name = mapping.get("display_name", "")

                if chatwork_user_id:
                    await self.redis.set_user_mapping(
                        source_platform="chatwork",
                        source_user_id=chatwork_user_id,
                        user_data={
                            "name": display_name,
                            "lark_user_id": lark_user_id,
                        },
                        ttl=86400,
                    )

                if lark_user_id:
                    await self.redis.set_user_mapping(
                        source_platform="lark",
                        source_user_id=lark_user_id,
                        user_data={
                            "name": display_name,
                            "chatwork_user_id": chatwork_user_id,
                        },
                        ttl=86400,
                    )

                loaded_count += 1

                logger.info(
                    "user_mapping_loaded",
                    name=display_name,
                    chatwork_user_id=chatwork_user_id,
                    lark_user_id=lark_user_id,
                )

            logger.info(
                "user_mappings_loaded",
                total_count=loaded_count,
            )

            return loaded_count

        except Exception as e:
            logger.error(
                "failed_to_load_user_mappings",
                error=str(e),
            )
            # User mappings are optional, don't raise
            return 0


# Global mapping loader instance
mapping_loader = MappingLoader()
