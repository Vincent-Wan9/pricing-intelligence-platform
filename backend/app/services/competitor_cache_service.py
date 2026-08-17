import logging
from uuid import UUID

from pydantic import ValidationError
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.redis import RedisClient
from app.schemas.competitor_price_schema import CompetitorPricePublic

logger = logging.getLogger(__name__)


class CompetitorCacheService:
    """Cache-aside access and best-effort invalidation for competitor prices."""

    def __init__(self, redis_client: RedisClient) -> None:
        self.redis = redis_client

    async def get_latest(self, mapping_id: UUID) -> CompetitorPricePublic | None:
        key = self.latest_key(mapping_id)
        try:
            cached = await self.redis.get_json(key)
        except (RedisError, RuntimeError):
            logger.warning("Could not read latest competitor price cache", exc_info=True)
            return None
        if cached is None:
            return None
        try:
            return CompetitorPricePublic.model_validate(cached)
        except ValidationError:
            logger.warning("Discarding invalid latest competitor price cache", exc_info=True)
            await self._delete(key)
            return None

    async def store_latest(self, mapping_id: UUID, price: CompetitorPricePublic) -> None:
        try:
            await self.redis.set_json(
                self.latest_key(mapping_id),
                price.model_dump(mode="json"),
                ttl_seconds=settings.redis_competitor_price_ttl_seconds,
            )
        except (RedisError, RuntimeError):
            logger.warning("Could not cache latest competitor price", exc_info=True)

    async def invalidate_price_inputs(
        self, *, product_id: UUID, competitor_id: UUID,
        mapping_id: UUID | None = None,
    ) -> None:
        keys = (
            f"competitor-prices:product:{product_id}",
            f"pricing-summary:product:{product_id}",
            f"recommendation-inputs:product:{product_id}",
        )
        try:
            if mapping_id is not None:
                await self.redis.delete(self.latest_key(mapping_id))
            for key in keys:
                await self.redis.delete(key)
            await self.redis.delete_pattern(f"dashboard:*:{competitor_id}*")
        except (RedisError, RuntimeError):
            logger.warning("Could not invalidate competitor-derived cache keys", exc_info=True)

    @staticmethod
    def latest_key(mapping_id: UUID) -> str:
        return f"competitor-prices:mapping:{mapping_id}:latest"

    async def _delete(self, key: str) -> None:
        try:
            await self.redis.delete(key)
        except (RedisError, RuntimeError):
            logger.warning("Could not delete competitor price cache key %s", key, exc_info=True)
