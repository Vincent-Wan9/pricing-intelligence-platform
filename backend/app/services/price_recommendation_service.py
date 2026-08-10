from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.crud.price_recommendation import price_recommendation_crud
from app.models.competitor_price import CompetitorPrice
from app.models.competitor_product import CompetitorProduct
from app.models.demand_forecast import DemandForecast
from app.models.inventory import Inventory
from app.models.price_recommendation import PriceRecommendation
from app.models.pricing_rule import PricingRule, RuleType
from app.models.product import Product
from app.models.product_price_history import ProductPriceHistory
from app.models.user import User
from app.schemas.price_recommendation_schema import CreatePriceRecommendationSchema, PriceRecommendationPublic
from app.services.product_cache_service import ProductCacheService


class PriceRecommendationServiceError(Exception):
    pass


class PriceRecommendationNotFoundError(PriceRecommendationServiceError):
    pass


class PriceRecommendationConflictError(PriceRecommendationServiceError):
    pass


class PriceRecommendationValidationError(PriceRecommendationServiceError):
    pass


class MissingPricingDataError(PriceRecommendationValidationError):
    pass


class NoApplicablePricingRuleError(PriceRecommendationValidationError):
    pass


class PriceRecommendationService:
    """Deterministic recommendation generation and review workflow."""

    REVIEW_ROLES = {"admin", "approver"}

    def __init__(self, db: Session, cache_service: ProductCacheService | None = None) -> None:
        self.db = db
        self.cache = cache_service
        self.crud = price_recommendation_crud

    def get(self, recommendation_id: UUID) -> PriceRecommendationPublic:
        return PriceRecommendationPublic.model_validate(self._get_model(recommendation_id))

    def list(self, *, skip: int = 0, limit: int = 100) -> list[PriceRecommendationPublic]:
        if skip < 0 or not 1 <= limit <= 1000:
            raise PriceRecommendationValidationError("Invalid pagination values")
        return [PriceRecommendationPublic.model_validate(item) for item in self.crud.list(self.db, skip=skip, limit=limit)]

    def create(self, recommendation_in: CreatePriceRecommendationSchema) -> PriceRecommendationPublic:
        """Retain explicit/manual creation while recording the price at generation."""
        product = self.db.get(Product, recommendation_in.product_id)
        rule = self.db.get(PricingRule, recommendation_in.rule_id)
        if product is None:
            raise PriceRecommendationValidationError("Product does not exist")
        if rule is None:
            raise PriceRecommendationValidationError("Pricing rule does not exist")
        if not product.is_active:
            raise PriceRecommendationValidationError("Product is inactive")
        if not rule.is_active:
            raise PriceRecommendationValidationError("Pricing rule is inactive")
        self._validate_price(product, recommendation_in.recommended_price)
        recommendation = PriceRecommendation(
            **recommendation_in.model_dump(), current_price=product.current_price, status="pending"
        )
        return self._insert(recommendation)

    def get_active_rules(self) -> list[PricingRule]:
        stmt = select(PricingRule).where(PricingRule.is_active.is_(True)).order_by(
            PricingRule.priority.desc(), PricingRule.created_at.asc()
        )
        return list(self.db.scalars(stmt).all())

    def generate(self, product_id: UUID) -> PriceRecommendationPublic:
        product = self.db.get(Product, product_id)
        if product is None:
            raise PriceRecommendationNotFoundError(f"Product {product_id} was not found")
        if not product.is_active:
            raise PriceRecommendationValidationError("Product is inactive")

        # Products already carry the rule assignment; priority provides stable ordering
        # when retrieving active rules without silently applying another product's policy.
        rules = self.get_active_rules()
        rule = next((item for item in rules if item.rule_id == product.rule_id), None)
        if rule is None:
            raise NoApplicablePricingRuleError("No active pricing rule is assigned to this product")

        inventory = self.db.scalar(select(Inventory).where(Inventory.product_id == product_id))
        forecast = self.db.scalar(select(DemandForecast).where(
            DemandForecast.product_id == product_id
        ).order_by(DemandForecast.forecast_date.desc()).limit(1))
        competitor_prices = self._latest_competitor_prices(product_id)
        price, reason = self.evaluate_rule(
            rule, product=product, inventory=inventory,
            forecast=forecast, competitor_prices=competitor_prices,
        )
        recommendation = PriceRecommendation(
            product_id=product.product_id,
            rule_id=rule.rule_id,
            current_price=product.current_price,
            recommended_price=price,
            recommendation_reason=reason,
            status="pending",
        )
        return self._insert(recommendation)

    def evaluate_rule(self, rule: PricingRule, *, product: Product, inventory: Inventory | None,
                      forecast: DemandForecast | None, competitor_prices: list[Decimal]) -> tuple[Decimal, str]:
        rule_type = getattr(rule.rule_type, "value", rule.rule_type)
        current = Decimal(product.current_price)
        cost = Decimal(inventory.cost_per_unit) if inventory is not None else None

        if rule_type == RuleType.COST_PLUS.value:
            if cost is None:
                raise MissingPricingDataError("Cost-plus pricing requires inventory cost data")
            margin = Decimal(product.target_margin or 0)
            if margin < 0 or margin >= 100:
                raise PriceRecommendationValidationError("target_margin must be between 0 and 100")
            candidate = cost / (Decimal("1") - margin / Decimal("100"))
            detail = f"cost {cost:.2f} with target margin {margin:.2f}%"
        elif rule_type == RuleType.COMPETITOR_BASED.value:
            if not competitor_prices:
                raise MissingPricingDataError("Competitor-based pricing requires recent competitor prices")
            candidate = sum(competitor_prices, Decimal("0")) / len(competitor_prices)
            detail = f"average of {len(competitor_prices)} latest in-stock competitor price(s)"
        elif rule_type == RuleType.INVENTORY_BASED.value:
            if inventory is None:
                raise MissingPricingDataError("Inventory-based pricing requires inventory data")
            safety = max(product.safety_stock, 1)
            if inventory.on_hand_qty <= safety:
                candidate, signal = current * Decimal("1.05"), "at or below safety stock"
            elif inventory.on_hand_qty >= safety * 2:
                candidate, signal = current * Decimal("0.95"), "at least twice safety stock"
            else:
                candidate, signal = current, "within the target stock band"
            detail = f"inventory {inventory.on_hand_qty}; {signal}"
        elif rule_type == RuleType.DEMAND_BASED.value:
            if forecast is None:
                raise MissingPricingDataError("Demand-based pricing requires demand forecast data")
            baseline = inventory.on_hand_qty if inventory is not None else max(product.safety_stock, 1)
            if forecast.predicted_demand > baseline:
                candidate, signal = current * Decimal("1.05"), "forecast exceeds available-stock baseline"
            elif forecast.predicted_demand < baseline:
                candidate, signal = current * Decimal("0.95"), "forecast is below available-stock baseline"
            else:
                candidate, signal = current, "forecast matches available-stock baseline"
            detail = f"forecast demand {forecast.predicted_demand}; {signal}"
        else:
            raise NoApplicablePricingRuleError(f"Unsupported pricing rule type: {rule_type}")

        constraints: list[str] = []
        if cost is not None and product.target_margin is not None:
            margin = Decimal(product.target_margin)
            if Decimal("0") <= margin < Decimal("100"):
                margin_floor = cost / (Decimal("1") - margin / Decimal("100"))
                if candidate < margin_floor:
                    candidate = margin_floor
                    constraints.append("target-margin floor")
        if product.min_price is not None and candidate < product.min_price:
            candidate = Decimal(product.min_price)
            constraints.append("minimum price")
        if product.max_price is not None and candidate > product.max_price:
            candidate = Decimal(product.max_price)
            constraints.append("maximum price")
        price = candidate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self._validate_price(product, price)
        suffix = f"; constrained by {', '.join(constraints)}" if constraints else ""
        return price, f"{rule.rule_name} ({rule_type}): {detail}{suffix}."

    def get_latest(self, product_id: UUID) -> PriceRecommendationPublic:
        self._validate_product(product_id)
        recommendation = self.crud.get_latest_recommendation(self.db, product_id)
        if recommendation is None:
            raise PriceRecommendationNotFoundError(f"No recommendation exists for product {product_id}")
        return PriceRecommendationPublic.model_validate(recommendation)

    def get_history(self, product_id: UUID) -> list[PriceRecommendationPublic]:
        self._validate_product(product_id)
        return [PriceRecommendationPublic.model_validate(item) for item in self.crud.get_recommendation_history(self.db, product_id)]

    def approve(self, recommendation_id: UUID, *, actor: User, reason: str | None = None) -> PriceRecommendationPublic:
        return self._review(recommendation_id, actor=actor, status="approved", reason=reason)

    def reject(self, recommendation_id: UUID, *, actor: User, reason: str | None = None) -> PriceRecommendationPublic:
        return self._review(recommendation_id, actor=actor, status="rejected", reason=reason)

    def _review(self, recommendation_id: UUID, *, actor: User, status: str, reason: str | None) -> PriceRecommendationPublic:
        self._validate_actor(actor)
        try:
            recommendation = self.crud.get_for_update(self.db, recommendation_id)
            if recommendation is None:
                raise PriceRecommendationNotFoundError(f"Price recommendation {recommendation_id} was not found")
            if recommendation.status != "pending":
                raise PriceRecommendationConflictError(
                    f"Recommendation was already processed with status {recommendation.status}"
                )
            recommendation.status = status
            recommendation.reviewed_by = actor.user_id
            recommendation.reviewed_at = datetime.now(timezone.utc)
            recommendation.review_reason = reason.strip() if reason else None
            self.db.commit()
            self.db.refresh(recommendation)
        except PriceRecommendationServiceError:
            self.db.rollback()
            raise
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise PriceRecommendationConflictError("Recommendation could not be reviewed") from exc
        return PriceRecommendationPublic.model_validate(recommendation)

    async def apply(self, recommendation_id: UUID, *, actor: User) -> PriceRecommendationPublic:
        self._validate_actor(actor)
        try:
            recommendation = self.crud.get_for_update(self.db, recommendation_id)
            if recommendation is None:
                raise PriceRecommendationNotFoundError(f"Price recommendation {recommendation_id} was not found")
            if recommendation.status != "approved":
                raise PriceRecommendationConflictError(
                    f"Only approved recommendations can be applied; current status is {recommendation.status}"
                )
            product = self.db.scalar(select(Product).where(
                Product.product_id == recommendation.product_id
            ).with_for_update())
            if product is None:
                raise PriceRecommendationValidationError("Recommendation product does not exist")
            self._validate_price(product, recommendation.recommended_price)
            old_price = product.current_price
            if old_price == recommendation.recommended_price:
                raise PriceRecommendationValidationError("Recommended price already matches the product price")

            product.current_price = recommendation.recommended_price
            self.db.add(ProductPriceHistory(
                product_id=product.product_id,
                old_price=old_price,
                new_price=recommendation.recommended_price,
                change_reason=recommendation.recommendation_reason,
                recommendation_id=recommendation.recommendation_id,
                changed_by=actor.user_id,
            ))
            recommendation.status = "applied"
            recommendation.applied_by = actor.user_id
            recommendation.applied_at = datetime.now(timezone.utc)
            self.db.flush()
            self.db.commit()
            self.db.refresh(recommendation)
        except PriceRecommendationServiceError:
            self.db.rollback()
            raise
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise PriceRecommendationConflictError("Recommendation price could not be applied") from exc
        except Exception:
            self.db.rollback()
            raise

        if self.cache is not None:
            await self.cache.invalidate(product.product_id, product.sku)
        return PriceRecommendationPublic.model_validate(recommendation)

    def _insert(self, recommendation: PriceRecommendation) -> PriceRecommendationPublic:
        try:
            self.db.add(recommendation)
            self.db.commit()
            self.db.refresh(recommendation)
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise PriceRecommendationConflictError("Price recommendation could not be created") from exc
        return PriceRecommendationPublic.model_validate(recommendation)

    def _latest_competitor_prices(self, product_id: UUID) -> list[Decimal]:
        ranked_prices = select(
            CompetitorPrice.competitor_price.label("price"),
            func.row_number().over(
                partition_by=CompetitorPrice.competitor_product_id,
                order_by=CompetitorPrice.crawl_timestamp.desc(),
            ).label("recency_rank"),
        ).join(CompetitorProduct).where(
            CompetitorProduct.product_id == product_id,
            CompetitorPrice.in_stock.is_(True),
        ).subquery()

        stmt = select(ranked_prices.c.price).where(
            ranked_prices.c.recency_rank == 1
        )
        return [Decimal(price) for price in self.db.scalars(stmt).all()]

    def _get_model(self, recommendation_id: UUID) -> PriceRecommendation:
        recommendation = self.crud.get(self.db, recommendation_id)
        if recommendation is None:
            raise PriceRecommendationNotFoundError(f"Price recommendation {recommendation_id} was not found")
        return recommendation

    @staticmethod
    def _validate_price(product: Product, price: Decimal) -> None:
        if price <= Decimal("0"):
            raise PriceRecommendationValidationError("recommended_price must be greater than zero")
        if product.min_price is not None and price < product.min_price:
            raise PriceRecommendationValidationError("recommended_price is below product min_price")
        if product.max_price is not None and price > product.max_price:
            raise PriceRecommendationValidationError("recommended_price is above product max_price")

    def _validate_product(self, product_id: UUID) -> None:
        if self.db.get(Product, product_id) is None:
            raise PriceRecommendationValidationError(f"Product {product_id} does not exist")

    @classmethod
    def _validate_actor(cls, actor: User) -> None:
        role = getattr(actor.role, "value", actor.role)
        if not actor.is_active or role not in cls.REVIEW_ROLES:
            raise PriceRecommendationValidationError("Only active approvers and admins can process recommendations")
