from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.pricing_rule import RuleType


class PricingRuleBase(BaseModel):
    rule_name: str = Field(..., min_length=2, max_length=255)
    rule_description: str = Field(..., min_length=5)
    rule_type: RuleType = RuleType.COST_PLUS
    priority: int = Field(default=1, ge=1)
    is_active: bool = True


class CreatePricingRuleSchema(PricingRuleBase):
    pass


class UpdatePricingRuleSchema(BaseModel):
    rule_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    rule_description: Optional[str] = Field(default=None, min_length=5)
    rule_type: Optional[RuleType] = None
    priority: Optional[int] = Field(default=None, ge=1)
    is_active: Optional[bool] = None


class PricingRulePublic(PricingRuleBase):
    rule_id: UUID
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    created_by: Optional[UUID]
    updated_by: Optional[UUID]

    model_config = ConfigDict(from_attributes=True)