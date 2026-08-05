from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class InventoryBase(BaseModel):
    vendor: str = Field(..., min_length=1, max_length=255)
    lead_time: int = Field(..., ge=0)
    cost_per_unit: Decimal = Field(..., max_digits=10, decimal_places=2, gt=0)
    on_hand_qty: int = Field(default=0, ge=0)


class CreateInventorySchema(InventoryBase):
    product_id: UUID


class UpdateInventorySchema(BaseModel):
    vendor: Optional[str] = Field(None, min_length=1, max_length=255)
    lead_time: Optional[int] = Field(None, ge=0)
    cost_per_unit: Optional[Decimal] = Field(None, max_digits=10, decimal_places=2, gt=0)
    on_hand_qty: Optional[int] = Field(None, ge=0)


class InventoryPublic(InventoryBase):
    inventory_id: UUID
    product_id: UUID
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeleteInventoryResponseModel(BaseModel):
    detail: str


class StockAdjustmentSchema(BaseModel):
    quantity_delta: int
