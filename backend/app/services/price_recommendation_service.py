from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.price_recommendation import price_recommendation_crud
from app.models.price_recommendation import PriceRecommendation
from app.models.pricing_rule import PricingRule
from app.models.product import Product
from app.schemas.price_recommendation_schema import (
    CreatePriceRecommendationSchema,
    PriceRecommendationPublic,
)


class PriceRecommendationServiceError(Exception):
    pass


class PriceRecommendationNotFoundError(PriceRecommendationServiceError):
    pass


class PriceRecommendationConflictError(PriceRecommendationServiceError):
    pass


class PriceRecommendationValidationError(PriceRecommendationServiceError):
    pass


class PriceRecommendationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.crud = price_recommendation_crud

    def get(self, recommendation_id: UUID) -> PriceRecommendationPublic:
        return PriceRecommendationPublic.model_validate(
            self._get_model(recommendation_id)
        )

    def create(self, recommendation_in: CreatePriceRecommendationSchema) -> PriceRecommendationPublic:
        product = self.db.get(Product, recommendation_in.product_id)
        rule = self.db.get(PricingRule, recommendation_in.rule_id)

        if product is None:
            raise PriceRecommendationValidationError("Product does not exist")
        if rule is None:
            raise PriceRecommendationValidationError(
                "Pricing rule does not exist"
            )
        if not getattr(product, "is_active", True):
            raise PriceRecommendationValidationError("Product is inactive")
        if not getattr(rule, "is_active", True):
            raise PriceRecommendationValidationError("Pricing rule is inactive")

        self._validate_price(product, recommendation_in.recommended_price)

        recommendation = PriceRecommendation(
            **recommendation_in.model_dump()
        )
        try:
            self.db.add(recommendation)
            self.db.commit()
            self.db.refresh(recommendation)
        except IntegrityError as exc:
            self.db.rollback()
            raise PriceRecommendationConflictError(
                "Price recommendation could not be created") from exc

        return PriceRecommendationPublic.model_validate(recommendation)

    def get_latest(self, product_id: UUID) -> PriceRecommendationPublic:
        self._validate_product(product_id)
        recommendation = self.crud.get_latest_recommendation(self.db, product_id)
        if recommendation is None:
            raise PriceRecommendationNotFoundError(
                f"No recommendation exists for product {product_id}")
        return PriceRecommendationPublic.model_validate(recommendation)

    def get_history(self, product_id: UUID) -> list[PriceRecommendationPublic]:
        self._validate_product(product_id)
        recommendations = self.crud.get_recommendation_history(self.db, product_id)
        return [PriceRecommendationPublic.model_validate(item) for item in recommendations]

    def _get_model(self, recommendation_id: UUID) -> PriceRecommendation:
        recommendation = self.crud.get(self.db, recommendation_id)
        if recommendation is None:
            raise PriceRecommendationNotFoundError(
                f"Price recommendation {recommendation_id} was not found")
        return recommendation

    @staticmethod
    def _validate_price(product: Product, price: Decimal) -> None:
        if price <= Decimal("0"):
            raise PriceRecommendationValidationError(
                "recommended_price must be greater than zero")
        if product.min_price is not None and price < product.min_price:
            raise PriceRecommendationValidationError(
                "recommended_price is below product min_price")
        if product.max_price is not None and price > product.max_price:
            raise PriceRecommendationValidationError(
                "recommended_price is above product max_price")

    def _validate_product(self, product_id: UUID) -> None:
        if self.db.get(Product, product_id) is None:
            raise PriceRecommendationValidationError(
                f"Product {product_id} does not exist")
