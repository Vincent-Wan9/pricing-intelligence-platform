import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from redis.exceptions import RedisError

from app.core.config import settings
from app.crud.product import ProductCRUD
from app.models.product import Product
from app.schemas.competitor_price_schema import CompetitorPricePublic
from app.schemas.product_schema import ProductPublic
from app.services.competitor_cache_service import CompetitorCacheService
from app.services.competitor_price_service import CompetitorPriceService
from app.services.product_cache_service import ProductCacheService
from app.services.product_service import ProductService


def product_public(*, sku: str = "SKU-1") -> ProductPublic:
    now = datetime.now(timezone.utc)
    return ProductPublic(
        product_id=uuid4(), sku=sku, product_name="Cached product", slug="cached-product",
        category_id=uuid4(), rule_id=uuid4(), safety_stock=0,
        base_price=Decimal("10.00"), current_price=Decimal("12.00"),
        auto_pricing_enabled=False, is_active=True, created_at=now, updated_at=now,
    )


def competitor_price(mapping_id=None) -> CompetitorPricePublic:
    return CompetitorPricePublic(
        price_id=uuid4(), competitor_product_id=mapping_id or uuid4(),
        competitor_price=Decimal("11.50"), stock_qty=4, in_stock=True,
        crawl_timestamp=datetime.now(timezone.utc),
    )


def test_product_service_cache_hit_skips_database() -> None:
    cached = product_public()
    cache = MagicMock()
    cache.get_by_id = AsyncMock(return_value=cached)
    service = ProductService(MagicMock(), cache)
    service.crud = MagicMock()

    result = asyncio.run(service.get(cached.product_id))

    assert result == cached
    service.crud.get.assert_not_called()


def test_product_service_cache_miss_queries_and_populates_cache() -> None:
    product = product_public()
    cache = MagicMock()
    cache.get_by_sku = AsyncMock(return_value=None)
    cache.store = AsyncMock()
    service = ProductService(MagicMock(), cache)
    service.crud = MagicMock()
    service.crud.get_by_sku.return_value = product

    result = asyncio.run(service.get_by_sku(" sku-1 "))

    assert result == product
    service.crud.get_by_sku.assert_called_once_with(service.db, "SKU-1")
    cache.store.assert_awaited_once_with(product)


def test_product_cache_uses_explicit_ttl_and_invalidates_old_and_new_sku() -> None:
    redis = MagicMock()
    redis.set_json = AsyncMock()
    redis.delete = AsyncMock()
    cache = ProductCacheService(redis)
    product = product_public(sku="NEW-SKU")

    asyncio.run(cache.store(product))
    asyncio.run(cache.invalidate(product.product_id, "OLD-SKU", "NEW-SKU"))

    assert redis.set_json.await_count == 2
    assert all(
        call.kwargs["ttl_seconds"] == settings.redis_product_ttl_seconds
        for call in redis.set_json.await_args_list
    )
    deleted = {call.args[0] for call in redis.delete.await_args_list}
    assert deleted == {
        cache.id_key(product.product_id), cache.sku_key("OLD-SKU"), cache.sku_key("NEW-SKU")
    }


def test_redis_failure_falls_back_to_database() -> None:
    product = product_public()
    redis = MagicMock()
    redis.get_json = AsyncMock(side_effect=RedisError("unavailable"))
    redis.set_json = AsyncMock(side_effect=RedisError("unavailable"))
    service = ProductService(MagicMock(), ProductCacheService(redis))
    service.crud = MagicMock()
    service.crud.get_by_sku.return_value = product

    result = asyncio.run(service.get_by_sku(product.sku))

    assert result == product
    service.crud.get_by_sku.assert_called_once()


def test_latest_competitor_price_cache_hit_skips_database() -> None:
    mapping_id = uuid4()
    cached = competitor_price(mapping_id)
    cache = MagicMock()
    cache.get_latest = AsyncMock(return_value=cached)
    service = CompetitorPriceService(MagicMock(), cache)
    service.crud = MagicMock()

    result = asyncio.run(service.get_latest(mapping_id))

    assert result == cached
    service.crud.get_latest_price.assert_not_called()


def test_latest_competitor_price_miss_populates_cache() -> None:
    mapping_id = uuid4()
    record = competitor_price(mapping_id)
    db = MagicMock()
    db.get.return_value = SimpleNamespace(competitor_product_id=mapping_id)
    cache = MagicMock()
    cache.get_latest = AsyncMock(return_value=None)
    cache.store_latest = AsyncMock()
    service = CompetitorPriceService(db, cache)
    service.crud = MagicMock()
    service.crud.get_latest_price.return_value = record

    result = asyncio.run(service.get_latest(mapping_id))

    assert result == record
    service.crud.get_latest_price.assert_called_once_with(db, mapping_id)
    cache.store_latest.assert_awaited_once_with(mapping_id, record)


def test_competitor_cache_invalidation_includes_latest_mapping() -> None:
    redis = MagicMock()
    redis.delete = AsyncMock()
    redis.delete_pattern = AsyncMock()
    cache = CompetitorCacheService(redis)
    mapping_id, product_id, competitor_id = uuid4(), uuid4(), uuid4()

    asyncio.run(cache.invalidate_price_inputs(
        product_id=product_id, competitor_id=competitor_id, mapping_id=mapping_id,
    ))

    deleted = {call.args[0] for call in redis.delete.await_args_list}
    assert cache.latest_key(mapping_id) in deleted
    assert f"pricing-summary:product:{product_id}" in deleted


def test_product_crud_pagination_is_applied_in_sql() -> None:
    db = MagicMock()
    db.scalars.return_value.all.return_value = []

    ProductCRUD(Product).get_all(db, skip=25, limit=10)

    statement = db.scalars.call_args.args[0]
    assert statement._offset_clause.value == 25
    assert statement._limit_clause.value == 10
