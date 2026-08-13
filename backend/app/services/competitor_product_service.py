from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.competitor_product import competitor_product_crud
from app.models.competitor import Competitor
from app.models.competitor_product import CompetitorProduct
from app.models.product import Product
from app.schemas.competitor_product_schema import (
    CompetitorProductPublic,
    CreateCompetitorProductSchema,
    UpdateCompetitorProductSchema,
)


class CompetitorProductServiceError(Exception):
    pass


class CompetitorProductNotFoundError(CompetitorProductServiceError):
    pass


class CompetitorProductConflictError(CompetitorProductServiceError):
    pass


class CompetitorProductValidationError(CompetitorProductServiceError):
    pass


class CompetitorProductService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.crud = competitor_product_crud

    def get(self, mapping_id: UUID) -> CompetitorProductPublic:
        return CompetitorProductPublic.model_validate(self._get_model(mapping_id))

    def list(self, *, skip: int = 0, limit: int = 100) -> list[CompetitorProductPublic]:
        self._validate_pagination(skip, limit)
        mappings = self.crud.get_all(self.db, skip=skip, limit=limit)
        return [CompetitorProductPublic.model_validate(item) for item in mappings]

    def list_for_competitor(self, competitor_id: UUID, *, active_only: bool = False) -> list[CompetitorProductPublic]:
        if self.db.get(Competitor, competitor_id) is None:
            raise CompetitorProductNotFoundError(f"Competitor {competitor_id} was not found")
        return [CompetitorProductPublic.model_validate(item) for item in self.crud.get_by_competitor(
            self.db, competitor_id, active_only=active_only
        )]

    def list_for_product(self, product_id: UUID, *, active_only: bool = False) -> list[CompetitorProductPublic]:
        if self.db.get(Product, product_id) is None:
            raise CompetitorProductNotFoundError(f"Product {product_id} was not found")
        return [CompetitorProductPublic.model_validate(item) for item in self.crud.get_by_product(
            self.db, product_id, active_only=active_only
        )]

    def create(self, mapping_in: CreateCompetitorProductSchema) -> CompetitorProductPublic:
        self._validate_references(
            product_id=mapping_in.product_id,
            competitor_id=mapping_in.competitor_id,
        )
        self._ensure_unique_mapping(
            product_id=mapping_in.product_id,
            competitor_id=mapping_in.competitor_id,
        )

        data = mapping_in.model_dump()
        if data.get("competitor_product_url") is not None:
            data["competitor_product_url"] = str(
                data["competitor_product_url"]
            )

        mapping = CompetitorProduct(**data)
        try:
            self.db.add(mapping)
            self.db.commit()
            self.db.refresh(mapping)
        except IntegrityError as exc:
            self.db.rollback()
            raise CompetitorProductConflictError(
                "Competitor-product mapping could not be created") from exc

        return CompetitorProductPublic.model_validate(mapping)

    def update(self, mapping_id: UUID, mapping_in: UpdateCompetitorProductSchema) -> CompetitorProductPublic:
        mapping = self._get_model(mapping_id)
        data = mapping_in.model_dump(exclude_unset=True)

        product_id = data.get("product_id", mapping.product_id)
        competitor_id = data.get("competitor_id", mapping.competitor_id)
        self._validate_references(
            product_id=product_id,
            competitor_id=competitor_id,
        )
        self._ensure_unique_mapping(
            product_id=product_id,
            competitor_id=competitor_id,
            exclude_id=mapping_id,
        )

        if data.get("competitor_product_url") is not None:
            data["competitor_product_url"] = str(
                data["competitor_product_url"]
            )

        try:
            for field, value in data.items():
                setattr(mapping, field, value)
            self.db.add(mapping)
            self.db.commit()
            self.db.refresh(mapping)
        except IntegrityError as exc:
            self.db.rollback()
            raise CompetitorProductConflictError(
                "Competitor-product mapping could not be updated") from exc

        return CompetitorProductPublic.model_validate(mapping)

    def delete(self, mapping_id: UUID) -> None:
        mapping = self._get_model(mapping_id)
        try:
            self.db.delete(mapping)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise CompetitorProductConflictError(
                "Mapping cannot be deleted while price records reference it") from exc

    def _get_model(self, mapping_id: UUID) -> CompetitorProduct:
        mapping = self.crud.get(self.db, mapping_id)
        if mapping is None:
            raise CompetitorProductNotFoundError(
                f"Competitor-product mapping {mapping_id} was not found")
        return mapping

    def _validate_references(self, *, product_id: UUID, competitor_id: UUID) -> None:
        product = self.db.get(Product, product_id)
        competitor = self.db.get(Competitor, competitor_id)

        if product is None:
            raise CompetitorProductValidationError(
                f"Product {product_id} does not exist")
        if competitor is None:
            raise CompetitorProductValidationError(
                f"Competitor {competitor_id} does not exist")
        if not getattr(product, "is_active", True):
            raise CompetitorProductValidationError("Product is inactive")
        if not getattr(competitor, "is_active", True):
            raise CompetitorProductValidationError("Competitor is inactive")

    def _ensure_unique_mapping(self, *, product_id: UUID, competitor_id: UUID, exclude_id: UUID | None = None) -> None:
        stmt = select(CompetitorProduct).where(
            CompetitorProduct.product_id == product_id,
            CompetitorProduct.competitor_id == competitor_id,
        )
        existing = self.db.scalar(stmt)
        if existing is not None and existing.competitor_product_id != exclude_id:
            raise CompetitorProductConflictError(
                "This product is already mapped to that competitor")

    @staticmethod
    def _validate_pagination(skip: int, limit: int) -> None:
        if skip < 0:
            raise CompetitorProductValidationError("skip cannot be negative")
        if not 1 <= limit <= 1000:
            raise CompetitorProductValidationError(
                "limit must be between 1 and 1000"
            )
