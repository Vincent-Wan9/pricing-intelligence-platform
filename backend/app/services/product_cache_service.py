import logging
from uuid import UUID

from pydantic import ValidationError
from redis.exceptions import RedisError

from app.core.redis import RedisClient
from app.schemas.product_schema import ProductPublic

logger = logging.getLogger(__name__)


class ProductCacheService:
    """Cache-aside operations and key management for products."""

    def __init__(self, redis_client: RedisClient) -> None:
        self.redis = redis_client

    async def get_by_id(self, product_id: UUID) -> ProductPublic | None:
        return await self._get(self.id_key(product_id))

    async def get_by_sku(self, sku: str) -> ProductPublic | None:
        return await self._get(self.sku_key(sku))

    async def store(self, product: ProductPublic) -> None:
        payload = product.model_dump(mode="json")
        try:
            await self.redis.set_json(
                self.id_key(product.product_id),
                payload,
            )
            await self.redis.set_json(
                self.sku_key(product.sku),
                payload,
            )
        except (RedisError, RuntimeError):
            logger.warning(
                "Could not cache product %s",
                product.product_id,
                exc_info=True,
            )

    async def invalidate(self, product_id: UUID, *skus: str) -> None:
        await self._delete(self.id_key(product_id))
        for sku in set(skus):
            if sku:
                await self._delete(self.sku_key(sku))

    @staticmethod
    def id_key(product_id: UUID) -> str:
        return f"products:id:{product_id}"

    @staticmethod
    def sku_key(sku: str) -> str:
        return f"products:sku:{sku.strip().upper()}"

    async def _get(self, cache_key: str) -> ProductPublic | None:
        try:
            cached = await self.redis.get_json(cache_key)
        except (RedisError, RuntimeError):
            logger.warning(
                "Could not read product cache key %s",
                cache_key,
                exc_info=True,
            )
            return None

        if cached is None:
            return None

        try:
            return ProductPublic.model_validate(cached)
        except ValidationError:
            logger.warning(
                "Discarding invalid product cache key %s",
                cache_key,
                exc_info=True,
            )
            await self._delete(cache_key)
            return None

    async def _delete(self, cache_key: str) -> None:
        try:
            await self.redis.delete(cache_key)
        except (RedisError, RuntimeError):
            logger.warning(
                "Could not delete product cache key %s",
                cache_key,
                exc_info=True,
            )
