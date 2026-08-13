from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response
from app.dependencies import CompetitorProductServiceDep, CompetitorServiceDep, require_roles
from app.schemas.competitor_product_schema import CompetitorProductPublic
from app.schemas.competitor_schema import CompetitorPublic, CreateCompetitorSchema, UpdateCompetitorSchema

router = APIRouter(prefix="/competitors", tags=["competitors"])
read = Depends(require_roles("viewer", "editor", "approver", "admin"))
write = Depends(require_roles("editor", "admin"))


@router.get("", response_model = list[CompetitorPublic], dependencies = [read])
def list_items(service: CompetitorServiceDep,skip: int = Query(0,ge=0), limit: int = Query(100,ge=1,le=1000)): 
    return service.list(skip = skip, limit = limit)


@router.get("/{item_id}", response_model = CompetitorPublic, dependencies = [read])
def get_item(item_id: UUID, service: CompetitorServiceDep): 
    return service.get(item_id)


@router.get("/{item_id}/products", response_model=list[CompetitorProductPublic], dependencies=[read])
def products(item_id: UUID, service: CompetitorProductServiceDep, active_only: bool = False):
    return service.list_for_competitor(item_id, active_only=active_only)


@router.post("", response_model = CompetitorPublic,status_code=201, dependencies = [write])
def create_item(data:CreateCompetitorSchema, service:CompetitorServiceDep): 
    return service.create(data)


@router.patch("/{item_id}", response_model = CompetitorPublic, dependencies = [write])
def update_item(item_id: UUID, data: UpdateCompetitorSchema, service: CompetitorServiceDep): 
    return service.update(item_id, data)


@router.post("/{item_id}/deactivate", response_model = CompetitorPublic, dependencies = [write])
def deactivate(item_id: UUID, service: CompetitorServiceDep): 
    return service.deactivate(item_id)


@router.post("/{item_id}/reactivate", response_model = CompetitorPublic, dependencies = [write])
def reactivate(item_id: UUID, service: CompetitorServiceDep): 
    return service.reactivate(item_id)


@router.delete("/{item_id}", status_code = 204, dependencies = [write])
def delete_item(item_id: UUID, service: CompetitorServiceDep): 
    service.delete(item_id)
    return Response(status_code = 204)
