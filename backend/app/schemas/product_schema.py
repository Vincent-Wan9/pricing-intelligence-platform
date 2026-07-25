from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ProductBase(BaseModel):
    sku: str = Field(..., min_length=1, max_length=100)
    product_name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    brand: Optional[str] = Field(default=None, max_length=100)

    category_id: UUID
    rule_id: UUID

    safety_stock: int = Field(default=0, ge=0)

    image_url: Optional[HttpUrl] = None

    base_price: Decimal = Field(..., gt=0)
    current_price: Decimal = Field(..., gt=0)
    min_price: Optional[Decimal] = Field(default=None, gt=0)
    max_price: Optional[Decimal] = Field(default=None, gt=0)
    target_margin: Optional[Decimal] = Field(default=None, ge=0, le=100)

    auto_pricing_enabled: bool = False
    is_active: bool = True


class CreateProductSchema(ProductBase):
    pass


class UpdateProductSchema(BaseModel):
    sku: Optional[str] = Field(default=None, min_length=1, max_length=100)
    product_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = None
    brand: Optional[str] = Field(default=None, max_length=100)

    category_id: Optional[UUID] = None
    rule_id: Optional[UUID] = None

    safety_stock: Optional[int] = Field(default=None, ge=0)

    image_url: Optional[HttpUrl] = None

    base_price: Optional[Decimal] = Field(default=None, gt=0)
    current_price: Optional[Decimal] = Field(default=None, gt=0)
    min_price: Optional[Decimal] = Field(default=None, gt=0)
    max_price: Optional[Decimal] = Field(default=None, gt=0)
    target_margin: Optional[Decimal] = Field(default=None, ge=0, le=100)

    auto_pricing_enabled: Optional[bool] = None
    is_active: Optional[bool] = None


class ProductPublic(ProductBase):
    product_id: UUID
    slug: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
