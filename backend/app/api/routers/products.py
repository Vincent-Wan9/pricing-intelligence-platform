from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response
from app.dependencies import CompetitorPriceServiceDep, CompetitorProductServiceDep, ProductServiceDep, require_roles
from app.schemas.competitor_price_schema import CompetitorPricePublic
from app.schemas.competitor_product_schema import CompetitorProductPublic
from app.schemas.product_schema import CreateProductSchema, ProductPublic, UpdateProductSchema

router = APIRouter(prefix="/products", tags=["products"])
read = Depends(require_roles("viewer", "editor", "approver", "admin"))
write = Depends(require_roles("editor", "admin"))


@router.get("", response_model = list[ProductPublic], dependencies = [read])
def list_items(service: ProductServiceDep, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000), active_only: bool = False):
    return service.list(skip = skip, limit = limit, active_only = active_only)


@router.get("/{item_id}", response_model = ProductPublic, dependencies = [read])
async def get_item(item_id: UUID, service: ProductServiceDep):
    return await service.get(item_id)


@router.get("/{item_id}/competitor-mappings", response_model=list[CompetitorProductPublic], dependencies=[read])
def competitor_mappings(item_id: UUID, service: CompetitorProductServiceDep, active_only: bool = False):
    return service.list_for_product(item_id, active_only=active_only)


@router.get("/{item_id}/competitor-prices", response_model=list[CompetitorPricePublic], dependencies=[read])
def competitor_prices(item_id: UUID, service: CompetitorPriceServiceDep, limit: int = Query(500, ge=1, le=5000)):
    return service.get_for_product(item_id, limit=limit)


@router.post("", response_model = ProductPublic, status_code = 201, dependencies = [write])
async def create_item(data: CreateProductSchema, service: ProductServiceDep):
    return await service.create(data)


@router.patch("/{item_id}", response_model = ProductPublic, dependencies = [write])
async def update_item(item_id: UUID, data: UpdateProductSchema, service: ProductServiceDep):
    return await service.update(item_id, data)


@router.post("/{item_id}/deactivate", response_model = ProductPublic, dependencies = [write])
async def deactivate(item_id: UUID, service: ProductServiceDep):
    return await service.deactivate(item_id)


@router.post("/{item_id}/reactivate", response_model = ProductPublic, dependencies = [write])
async def reactivate(item_id: UUID, service: ProductServiceDep):
    return await service.reactivate(item_id)


@router.delete("/{item_id}", status_code = 204, dependencies = [write])
async def delete_item(item_id: UUID, service: ProductServiceDep):
    await service.delete(item_id)
    return Response(status_code = 204)
