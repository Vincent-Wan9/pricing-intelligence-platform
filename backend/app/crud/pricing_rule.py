from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.pricing_rule import PricingRule
from app.schemas.price_rule_schema import CreatePricingRuleSchema, UpdatePricingRuleSchema



class PricingRuleCRUD(CRUDBase[ PricingRule, CreatePricingRuleSchema, UpdatePricingRuleSchema]):

    def get_by_rule(self, db: Session, rule_name: UUID):
        stmt = (select(PricingRule).where(PricingRule.rule_name == rule_name))

        return list(db.scalars(stmt).all())

    def get_active_rules(self, db: Session):
        stmt = (select(PricingRule).where(PricingRule.is_active == True))

        return list(db.scalars(stmt).all())

    def get_by_rule_type(self, db: Session, rule_type: str):
        stmt = (select(PricingRule).where(PricingRule.rule_type == rule_type))

        return list(db.scalars(stmt).all())


pricing_rule_crud = PricingRuleCRUD(PricingRule)