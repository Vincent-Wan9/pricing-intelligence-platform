from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl


class CompetitorBase(BaseModel):
    competitor_name: str = Field(..., min_length=1, max_length=255)
    website_url: HttpUrl = Field(...)
    is_active: bool = Field(default=True)


class CreateCompetitorSchema(CompetitorBase):
    pass


class UpdateCompetitorSchema(BaseModel):
    competitor_name: Optional[str] = Field(None, min_length=1, max_length=255)
    website_url: Optional[HttpUrl] = Field(None)
    is_active: Optional[bool] = Field(None)


class CompetitorPublic(CompetitorBase):
    competitor_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class DeleteCompetitorResponseModel(BaseModel):
    detail: str