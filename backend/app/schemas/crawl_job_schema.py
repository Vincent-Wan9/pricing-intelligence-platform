from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl

class CreateCrawlJobSchema(BaseModel):
    competitor_id: UUID


class UpdateCrawlJobSchema(BaseModel):
    status: Optional[str] = None
    completed_at: Optional[datetime] = None
    records_collected: Optional[int] = None
    error_message: Optional[str] = None

class CrawlJobPublic(BaseModel):
    job_id: UUID
    competitor_id: UUID
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    records_collected: int
    error_message: Optional[str]

    model_config = {"from_attributes": True}


class CompleteCrawlJobSchema(BaseModel):
    records_collected: int = Field(ge=0)


class FailCrawlJobSchema(BaseModel):
    error_message: str = Field(min_length=1)
