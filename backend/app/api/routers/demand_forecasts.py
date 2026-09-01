from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response
from app.dependencies import DemandForecastServiceDep, require_roles
from app.schemas.demand_forecast_schema import (
    CreateDemandForecastSchema, CreateDemandHistorySchema, DemandForecastPublic,
    DemandHistoryPublic, ForecastGenerationResult, UpdateDemandForecastSchema,
)

router = APIRouter(prefix = "/demand-forecasts", tags = ["demand forecasts"])
read = Depends(require_roles("viewer", "editor", "approver", "admin"))
write = Depends(require_roles("editor", "admin"))


@router.post("/history", response_model=DemandHistoryPublic, status_code=201, dependencies=[write])
def record_history(data: CreateDemandHistorySchema, service: DemandForecastServiceDep):
    return service.record_demand(data)


@router.get("/history/product/{product_id}", response_model=list[DemandHistoryPublic], dependencies=[read])
def demand_history(product_id: UUID, service: DemandForecastServiceDep,
                   limit: int = Query(365, ge=1, le=2000)):
    return service.get_demand_history(product_id, limit=limit)


@router.post("/generate/{product_id}", response_model=ForecastGenerationResult, status_code=201, dependencies=[write])
def generate(product_id: UUID, service: DemandForecastServiceDep,
             horizon_days: int = Query(7, ge=1, le=90)):
    return service.generate(product_id, horizon_days=horizon_days)


@router.get("/{forecast_id}", response_model = DemandForecastPublic, dependencies = [read])
def get_item(forecast_id: UUID, service: DemandForecastServiceDep): 
    return service.get(forecast_id)


@router.post("", response_model = DemandForecastPublic, status_code = 201, dependencies = [write])
def create_item(data: CreateDemandForecastSchema, service: DemandForecastServiceDep): 
    return service.create(data)


@router.patch("/{forecast_id}", response_model = DemandForecastPublic, dependencies = [write])
def update_item(forecast_id: UUID, data: UpdateDemandForecastSchema, service: DemandForecastServiceDep): 
    return service.update(forecast_id, data)


@router.delete("/{forecast_id}", status_code = 204, dependencies = [write])
def delete_item(forecast_id: UUID, service: DemandForecastServiceDep): 
    service.delete(forecast_id)
    return Response(status_code = 204)


@router.get("/product/{product_id}/latest", response_model = DemandForecastPublic, dependencies = [read])
def latest(product_id: UUID, service: DemandForecastServiceDep): 
    return service.get_latest(product_id)


@router.get("/product/{product_id}/history", response_model = list[DemandForecastPublic], dependencies = [read])
def history(product_id:UUID, service: DemandForecastServiceDep, start_date: datetime | None = None, end_date: datetime | None = None):
    return service.get_between(product_id, start_date = start_date, end_date = end_date) if start_date is not None and end_date is not None else service.get_history(product_id)
