from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl


class CompetitorProductBase(BaseModel):
    competitor_sku: str = Field(..., max_length=100)
    competitor_product_name: str = Field(..., max_length=255)
    competitor_product_url: HttpUrl = Field(...)
    price_selector: str | None = Field(None, min_length=1, max_length=500)
    is_active: bool = True


class CreateCompetitorProductSchema(CompetitorProductBase):
    product_id: UUID
    competitor_id: UUID


class UpdateCompetitorProductSchema(BaseModel):
    competitor_sku: Optional[str] = Field(None, max_length=100)
    competitor_product_name: Optional[str] = Field(None, max_length=255)
    competitor_product_url: Optional[HttpUrl] = Field(None)
    price_selector: Optional[str] = Field(None, min_length=1, max_length=500)
    is_active: Optional[bool] = None


class CompetitorProductPublic(CompetitorProductBase):
    competitor_product_id: UUID
    product_id: UUID
    competitor_id: UUID
    created_at: datetime
    last_crawled_at: datetime | None = None
    last_crawl_error: str | None = None

    model_config = {"from_attributes": True}


class DeleteCompetitorProductResponseModel(BaseModel):
    detail: str
