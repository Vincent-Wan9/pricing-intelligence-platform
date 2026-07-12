from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class CompetitorPriceBase(BaseModel):
    competitor_price: Decimal = Field(..., max_digits=10, decimal_places=2, gt=0)
    stock_qty: Optional[int] = Field(default=None)
    in_stock: Optional[bool] = Field(default=None)
    crawl_timestamp: datetime = Field(...)


class CreateCompetitorPriceSchema(CompetitorPriceBase):
    competitor_product_id: UUID


class UpdateCompetitorPriceSchema(BaseModel):
    competitor_price: Optional[Decimal] = Field(None, max_digits=10, decimal_places=2, gt=0)
    stock_qty: Optional[int] = Field(default=None)
    in_stock: Optional[bool] = Field(None)
    crawl_timestamp: Optional[datetime] = Field(None)


class CompetitorPricePublic(CompetitorPriceBase):
    price_id: UUID
    competitor_product_id: UUID

    model_config = {"from_attributes": True}


class DeleteCompetitorPriceResponseModel(BaseModel):
    detail: str