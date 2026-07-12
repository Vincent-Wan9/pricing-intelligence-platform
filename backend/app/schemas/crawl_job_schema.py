from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl



class CrawlJobPublic(BaseModel):
    job_id: UUID
    competitor_id: UUID
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    records_collected: int
    error_message: Optional[str]

    model_config = {"from_attributes": True}

