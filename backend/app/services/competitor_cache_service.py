import logging
from uuid import UUID

from redis.exceptions import RedisError

from app.core.redis import RedisClient

logger = logging.getLogger(__name__)


class CompetitorCacheService:
    """Best-effort invalidation for data derived from competitor observations."""

    def __init__(self, redis_client: RedisClient) -> None:
        self.redis = redis_client

    async def invalidate_price_inputs(self, *, product_id: UUID, competitor_id: UUID) -> None:
        keys = (
            f"competitor-prices:product:{product_id}",
            f"pricing-summary:product:{product_id}",
            f"recommendation-inputs:product:{product_id}",
        )
        try:
            for key in keys:
                await self.redis.delete(key)
            await self.redis.delete_pattern(f"dashboard:*:{competitor_id}*")
        except (RedisError, RuntimeError):
            logger.warning("Could not invalidate competitor-derived cache keys", exc_info=True)
