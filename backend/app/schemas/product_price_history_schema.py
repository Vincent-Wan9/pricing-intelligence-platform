from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ProductPriceHistoryBase(BaseModel):
    product_id: UUID
    old_price: Decimal = Field(..., max_digits=10, decimal_places=2, ge=0)
    new_price: Decimal = Field(..., max_digits=10, decimal_places=2, ge=0)


class CreateProductPriceHistorySchema(ProductPriceHistoryBase):
    pass


class ProductPriceHistoryPublic(ProductPriceHistoryBase):
    history_id: UUID
    changed_at: datetime

    model_config = {"from_attributes": True}

