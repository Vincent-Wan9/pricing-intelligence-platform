from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.competitor_price import competitor_price_crud
from app.models.competitor_price import CompetitorPrice
from app.models.competitor_product import CompetitorProduct
from app.schemas.competitor_price_schema import (
    CompetitorPricePublic,
    CreateCompetitorPriceSchema,
)
from app.services.competitor_cache_service import CompetitorCacheService


class CompetitorPriceServiceError(Exception):
    pass


class CompetitorPriceNotFoundError(CompetitorPriceServiceError):
    pass


class CompetitorPriceConflictError(CompetitorPriceServiceError):
    pass


class CompetitorPriceValidationError(CompetitorPriceServiceError):
    pass


class CompetitorPriceService:
    def __init__(self, db: Session, cache_service: CompetitorCacheService | None = None) -> None:
        self.db = db
        self.crud = competitor_price_crud
        self.cache = cache_service

    def get(self, price_id: UUID) -> CompetitorPricePublic:
        record = self.crud.get(self.db, price_id)
        if record is None:
            raise CompetitorPriceNotFoundError(
                f"Competitor price {price_id} was not found"
            )
        return CompetitorPricePublic.model_validate(record)

    async def record(self, price_in: CreateCompetitorPriceSchema) -> CompetitorPricePublic:
        mapping = self._validate_mapping(price_in.competitor_product_id)
        self._validate_price(price_in.competitor_price)

        record = CompetitorPrice(**price_in.model_dump())
        try:
            mapping.last_crawled_at = price_in.crawl_timestamp
            mapping.last_crawl_error = None
            self.db.add(mapping)
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
        except IntegrityError as exc:
            self.db.rollback()
            raise CompetitorPriceConflictError(
                "Competitor price could not be recorded") from exc
        result = CompetitorPricePublic.model_validate(record)
        if self.cache is not None:
            await self.cache.invalidate_price_inputs(
                product_id=mapping.product_id,
                competitor_id=mapping.competitor_id,
                mapping_id=mapping.competitor_product_id,
            )
            await self.cache.store_latest(mapping.competitor_product_id, result)
        return result

    async def get_latest(self, competitor_product_id: UUID) -> CompetitorPricePublic:
        if self.cache is not None:
            cached = await self.cache.get_latest(competitor_product_id)
            if cached is not None:
                return cached
        self._validate_mapping(competitor_product_id)
        record = self.crud.get_latest_price(self.db, competitor_product_id)
        if record is None:
            raise CompetitorPriceNotFoundError(
                "No competitor price has been recorded for this mapping")
        result = CompetitorPricePublic.model_validate(record)
        if self.cache is not None:
            await self.cache.store_latest(competitor_product_id, result)
        return result

    def get_history(self, competitor_product_id: UUID, *, start_at: datetime | None = None, end_at: datetime | None = None, limit: int = 500,
                    ) -> list[CompetitorPricePublic]:
        self._validate_mapping(competitor_product_id)
        if not 1 <= limit <= 5000:
            raise CompetitorPriceValidationError(
                "limit must be between 1 and 5000")
        if start_at and end_at and start_at > end_at:
            raise CompetitorPriceValidationError(
                "start_at cannot be after end_at")

        stmt = (
            select(CompetitorPrice)
            .where(CompetitorPrice.competitor_product_id == competitor_product_id)
            .order_by(CompetitorPrice.crawl_timestamp.desc())
            .limit(limit)
        )
        if start_at is not None:
            stmt = stmt.where(CompetitorPrice.crawl_timestamp >= start_at)
        if end_at is not None:
            stmt = stmt.where(CompetitorPrice.crawl_timestamp <= end_at)
        records = self.db.scalars(stmt).all()
        return [CompetitorPricePublic.model_validate(item) for item in records]

    def get_for_product(self, product_id: UUID, *, limit: int = 500) -> list[CompetitorPricePublic]:
        if not 1 <= limit <= 5000:
            raise CompetitorPriceValidationError("limit must be between 1 and 5000")
        stmt = (
            select(CompetitorPrice)
            .join(CompetitorProduct)
            .where(CompetitorProduct.product_id == product_id)
            .order_by(CompetitorPrice.crawl_timestamp.desc())
            .limit(limit)
        )
        return [CompetitorPricePublic.model_validate(item) for item in self.db.scalars(stmt).all()]

    def _validate_mapping(self, competitor_product_id: UUID) -> CompetitorProduct:
        mapping = self.db.get(CompetitorProduct, competitor_product_id)
        if mapping is None:
            raise CompetitorPriceValidationError(
                f"Competitor product {competitor_product_id} does not exist")
        return mapping

    @staticmethod
    def _validate_price(price: Decimal) -> None:
        if price <= Decimal("0"):
            raise CompetitorPriceValidationError(
                "competitor_price must be greater than zero")
