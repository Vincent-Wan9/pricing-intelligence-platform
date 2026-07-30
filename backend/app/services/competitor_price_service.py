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


class CompetitorPriceServiceError(Exception):
    pass


class CompetitorPriceNotFoundError(CompetitorPriceServiceError):
    pass


class CompetitorPriceConflictError(CompetitorPriceServiceError):
    pass


class CompetitorPriceValidationError(CompetitorPriceServiceError):
    pass


class CompetitorPriceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.crud = competitor_price_crud

    def get(self, price_id: UUID) -> CompetitorPricePublic:
        record = self.crud.get(self.db, price_id)
        if record is None:
            raise CompetitorPriceNotFoundError(
                f"Competitor price {price_id} was not found"
            )
        return CompetitorPricePublic.model_validate(record)

    def record(self, price_in: CreateCompetitorPriceSchema) -> CompetitorPricePublic:
        self._validate_mapping(price_in.competitor_product_id)
        self._validate_price(price_in.competitor_price)

        record = CompetitorPrice(**price_in.model_dump())
        try:
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
        except IntegrityError as exc:
            self.db.rollback()
            raise CompetitorPriceConflictError(
                "Competitor price could not be recorded") from exc
        return CompetitorPricePublic.model_validate(record)

    def get_latest(self, competitor_product_id: UUID) -> CompetitorPricePublic:
        self._validate_mapping(competitor_product_id)
        record = self.crud.get_latest_price(self.db, competitor_product_id)
        if record is None:
            raise CompetitorPriceNotFoundError(
                "No competitor price has been recorded for this mapping")
        return CompetitorPricePublic.model_validate(record)

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

    def _validate_mapping(self, competitor_product_id: UUID) -> None:
        if self.db.get(CompetitorProduct, competitor_product_id) is None:
            raise CompetitorPriceValidationError(
                f"Competitor product {competitor_product_id} does not exist")

    @staticmethod
    def _validate_price(price: Decimal) -> None:
        if price < Decimal("0"):
            raise CompetitorPriceValidationError(
                "competitor_price cannot be negative")
