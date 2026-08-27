from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class DemandForecastBase(BaseModel):
    product_id: UUID
    forecast_date: datetime
    predicted_demand: int = Field(..., ge=0)
    model_name: Optional[str] = Field(default=None, max_length=100)
    confidence_score: Optional[Decimal] = Field(default=None, ge=0, le=100)


class CreateDemandForecastSchema(DemandForecastBase):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "product_id": "6cb97c5e-f6ef-470d-8d0d-d2c3d6ab89c2",
                    "forecast_date": "2026-07-15T00:00:00",
                    "predicted_demand": 275,
                    "model_name": "xgboost-v1",
                    "confidence_score": 94.50,
                }
            ]
        }
    )


class UpdateDemandForecastSchema(BaseModel):
    forecast_date: Optional[datetime] = None
    predicted_demand: Optional[int] = Field(default=None, ge=0)
    model_name: Optional[str] = Field(default=None, max_length=100)
    confidence_score: Optional[Decimal] = Field(default=None, ge=0, le=100)


class DemandForecastPublic(DemandForecastBase):
    forecast_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreateDemandHistorySchema(BaseModel):
    product_id: UUID
    demand_date: date
    quantity: int = Field(..., ge=0)


class DemandHistoryPublic(CreateDemandHistorySchema):
    demand_history_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ForecastGenerationResult(BaseModel):
    product_id: UUID
    horizon_days: int
    model_name: str
    baseline_mae: float
    ml_mae: float
    forecasts: list[DemandForecastPublic]
