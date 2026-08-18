from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from app.dependencies import CompetitorPriceServiceDep, require_roles
from app.schemas.competitor_price_schema import CompetitorPricePublic, CreateCompetitorPriceSchema

router = APIRouter(prefix = "/competitor-prices", tags = ["competitor prices"])
read = Depends(require_roles("viewer", "editor", "approver", "admin"))
write = Depends(require_roles("editor", "admin"))


@router.get("/{price_id}", response_model = CompetitorPricePublic, dependencies = [read])
def get_item(price_id: UUID, service: CompetitorPriceServiceDep): 
    return service.get(price_id)


@router.post("", response_model = CompetitorPricePublic, status_code = 201, dependencies = [write])
async def record(data: CreateCompetitorPriceSchema, service: CompetitorPriceServiceDep):
    return await service.record(data)


@router.get("/product/{mapping_id}/latest", response_model = CompetitorPricePublic, dependencies = [read])
async def latest(mapping_id: UUID, service: CompetitorPriceServiceDep):
    return await service.get_latest(mapping_id)


@router.get("/product/{mapping_id}/history", response_model = list[CompetitorPricePublic], dependencies = [read])
def history(mapping_id: UUID, service: CompetitorPriceServiceDep, start_at: datetime|None=None, end_at: datetime | None = None, limit: int = Query(100,ge=1,le=500)): 
    return service.get_history(mapping_id, start_at = start_at, end_at = end_at, limit = limit)
