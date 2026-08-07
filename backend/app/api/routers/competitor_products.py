from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response
from app.dependencies import CompetitorProductServiceDep, require_roles
from app.schemas.competitor_product_schema import CompetitorProductPublic, CreateCompetitorProductSchema, UpdateCompetitorProductSchema

router = APIRouter(prefix = "/competitor-products", tags = ["competitor products"])
read = Depends(require_roles("viewer", "editor", "approver", "admin"))
write = Depends(require_roles("editor", "admin"))


@router.get("", response_model = list[CompetitorProductPublic], dependencies = [read])
def list_items(service: CompetitorProductServiceDep, skip: int = Query(0,ge = 0), limit: int = Query(100,ge = 1,le = 1000)): 
    return service.list(skip = skip, limit = limit)


@router.get("/{item_id}", response_model=CompetitorProductPublic, dependencies = [read])
def get_item(item_id: UUID, service: CompetitorProductServiceDep): 
    return service.get(item_id)


@router.post("", response_model = CompetitorProductPublic, status_code = 201, dependencies = [write])
def create_item(data: CreateCompetitorProductSchema, service: CompetitorProductServiceDep): 
    return service.create(data)


@router.patch("/{item_id}", response_model = CompetitorProductPublic, dependencies = [write])
def update_item(item_id: UUID, data: UpdateCompetitorProductSchema, service: CompetitorProductServiceDep): 
    return service.update(item_id, data)


@router.delete("/{item_id}", status_code = 204, dependencies = [write])
def delete_item(item_id: UUID, service: CompetitorProductServiceDep): 
    service.delete(item_id); 
    return Response(status_code = 204)
