import json
import logging
from typing import Any

import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:

    def __init__(self):
        self._client: redis.Redis | None = None

    async def connect(self):
        if self._client is not None:
            return

        client = redis.Redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.redis_max_connections,
            socket_connect_timeout=settings.redis_connect_timeout_seconds,
            socket_timeout=settings.redis_socket_timeout_seconds,
            health_check_interval=30,
        )

        try:
            await client.ping()
        except redis.RedisError:
            await client.aclose()
            logger.exception("Failed to connect to Redis")
            raise

        self._client = client
        logger.info("Redis connected")

    async def close(self):
        client, self._client = self._client, None
        if client is None:
            return

        await client.aclose()
        logger.info("Redis connection closed")


    @property
    def client(self):
        if self._client is None:
            raise RuntimeError("Redis is not connected; initialize it at app startup")
        return self._client


    async def get_json(self, key: str):
        value = await self.client.get(key)
        if value is None:
            return None

        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Invalid JSON stored in Redis key %s", key)
            return None

    async def set_json(self, key: str, value: Any, ttl_seconds: int | None = None):
        ttl = settings.redis_default_ttl_seconds if ttl_seconds is None else ttl_seconds
        await self.client.set(key, json.dumps(value, ensure_ascii=False, separators=(",", ":")), ex=ttl)

    async def delete(self, key: str):
        return await self.client.delete(key)

    async def delete_pattern(self, pattern: str, batch_size: int = 500):
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")

        deleted = 0
        batch: list[str] = []
        async for key in self.client.scan_iter(match=pattern, count=batch_size):
            batch.append(key)
            if len(batch) >= batch_size:
                deleted += await self.client.delete(*batch)
                batch.clear()

        if batch:
            deleted += await self.client.delete(*batch)
        return deleted


redis_client = RedisClient()
