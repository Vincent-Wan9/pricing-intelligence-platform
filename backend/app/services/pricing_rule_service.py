from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.pricing_rule import pricing_rule_crud
from app.models.pricing_rule import PricingRule
from app.schemas.price_rule_schema import (
    CreatePricingRuleSchema,
    PricingRulePublic,
    UpdatePricingRuleSchema,
)


class PricingRuleServiceError(Exception):
    pass


class PricingRuleNotFoundError(PricingRuleServiceError):
    pass


class PricingRuleConflictError(PricingRuleServiceError):
    pass


class PricingRuleValidationError(PricingRuleServiceError):
    pass


class PricingRuleService:
    SUPPORTED_RULE_TYPES = {
        "COST_PLUS",
        "COMPETITOR_BASED",
        "INVENTORY_BASED",
        "DEMAND_BASED",
    }

    def __init__(self, db: Session) -> None:
        self.db = db
        self.crud = pricing_rule_crud

    def get(self, rule_id: UUID) -> PricingRulePublic:
        return PricingRulePublic.model_validate(self._get_model(rule_id))

    def list(self, *, skip: int = 0, limit: int = 100) -> list[PricingRulePublic]:
        if skip < 0 or not 1 <= limit <= 1000:
            raise PricingRuleValidationError("Invalid pagination values")
        rules = self.crud.get_all(self.db, skip=skip, limit=limit)
        return [PricingRulePublic.model_validate(rule) for rule in rules]

    def create(self, rule_in: CreatePricingRuleSchema) -> PricingRulePublic:
        self._ensure_unique_name(rule_in.rule_name)
        self._validate_rule_type(rule_in.rule_type)

        rule = PricingRule(**rule_in.model_dump())
        try:
            self.db.add(rule)
            self.db.commit()
            self.db.refresh(rule)
        except IntegrityError as exc:
            self.db.rollback()
            raise PricingRuleConflictError(
                "Pricing rule could not be created") from exc
        return PricingRulePublic.model_validate(rule)

    def update(self, rule_id: UUID, rule_in: UpdatePricingRuleSchema) -> PricingRulePublic:
        rule = self._get_model(rule_id)
        data = rule_in.model_dump(exclude_unset=True)

        if "rule_name" in data and data["rule_name"] != rule.rule_name:
            self._ensure_unique_name(data["rule_name"], exclude_id=rule_id)
        if "rule_type" in data:
            self._validate_rule_type(data["rule_type"])

        try:
            for field, value in data.items():
                setattr(rule, field, value)
            self.db.add(rule)
            self.db.commit()
            self.db.refresh(rule)
        except IntegrityError as exc:
            self.db.rollback()
            raise PricingRuleConflictError(
                "Pricing rule could not be updated") from exc
        return PricingRulePublic.model_validate(rule)

    def activate(self, rule_id: UUID) -> PricingRulePublic:
        return self._set_active(rule_id, is_active=True)

    def deactivate(self, rule_id: UUID) -> PricingRulePublic:
        return self._set_active(rule_id, is_active=False)

    def _set_active(self, rule_id: UUID, *, is_active: bool) -> PricingRulePublic:
        rule = self._get_model(rule_id)
        try:
            rule.is_active = is_active
            self.db.add(rule)
            self.db.commit()
            self.db.refresh(rule)
        except IntegrityError as exc:
            self.db.rollback()
            action = "activated" if is_active else "deactivated"
            raise PricingRuleConflictError(
                f"Pricing rule could not be {action}") from exc
        return PricingRulePublic.model_validate(rule)

    def delete(self, rule_id: UUID) -> None:
        rule = self._get_model(rule_id)
        if getattr(rule, "is_active", False):
            raise PricingRuleValidationError(
                "Active pricing rules must be deactivated before deletion")
        try:
            self.db.delete(rule)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise PricingRuleConflictError(
                "Pricing rule cannot be deleted while products reference it") from exc

    def _get_model(self, rule_id: UUID) -> PricingRule:
        rule = self.crud.get(self.db, rule_id)
        if rule is None:
            raise PricingRuleNotFoundError(
                f"Pricing rule {rule_id} was not found")
        return rule

    def _ensure_unique_name(self, rule_name: str, *, exclude_id: UUID | None = None) -> None:
        stmt = select(PricingRule).where(
            PricingRule.rule_name.ilike(rule_name.strip())
        )
        existing = self.db.scalar(stmt)
        if existing is not None and existing.rule_id != exclude_id:
            raise PricingRuleConflictError(
                f"Pricing rule '{rule_name}' already exists")

    def _validate_rule_type(self, rule_type: object) -> None:
        value = getattr(rule_type, "value", rule_type)
        if value not in self.SUPPORTED_RULE_TYPES:
            raise PricingRuleValidationError(
                f"Unsupported pricing rule type: {value}")
