from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl


class CompetitorProductBase(BaseModel):
    competitor_sku: str = Field(..., max_length=100)
    competitor_product_name: str = Field(..., max_length=255)
    competitor_product_url: HttpUrl = Field(...)


class CreateCompetitorProductSchema(CompetitorProductBase):
    product_id: UUID
    competitor_id: UUID


class UpdateCompetitorProductSchema(BaseModel):
    competitor_sku: Optional[str] = Field(None, max_length=100)
    competitor_product_name: Optional[str] = Field(None, max_length=255)
    competitor_product_url: Optional[HttpUrl] = Field(None)


class CompetitorProductPublic(CompetitorProductBase):
    competitor_product_id: UUID
    product_id: UUID
    competitor_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class DeleteCompetitorProductResponseModel(BaseModel):
    detail: str