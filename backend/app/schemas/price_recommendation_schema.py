from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PriceRecommendationBase(BaseModel):
    product_id: UUID
    rule_id: UUID
    recommended_price: Decimal = Field(..., gt=0)
    recommendation_reason: str = Field(..., min_length=5)


class CreatePriceRecommendationSchema(PriceRecommendationBase):
    pass



class PriceRecommendationPublic(PriceRecommendationBase):
    recommendation_id: UUID
    generated_at: datetime
    status: Literal["pending", "approved", "rejected"]
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    review_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ReviewPriceRecommendationSchema(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=2000)
