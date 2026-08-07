from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response
from app.dependencies import InventoryServiceDep, require_roles
from app.schemas.inventory_schema import CreateInventorySchema, InventoryPublic, StockAdjustmentSchema, UpdateInventorySchema


router = APIRouter(prefix="/inventory",tags=["inventory"])
read = Depends(require_roles("viewer", "editor", "approver", "admin"))
write = Depends(require_roles("editor", "admin"))


@router.get("",response_model=list[InventoryPublic], dependencies=[read],)
def list_items(service: InventoryServiceDep, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000),):
    return service.list(skip=skip, limit=limit)


@router.get("/{item_id}", response_model=InventoryPublic, dependencies=[read])
def get_item(item_id: UUID, service: InventoryServiceDep,):
    return service.get(item_id)


@router.get("/product/{product_id}", response_model=InventoryPublic, dependencies=[read])
def by_product(product_id: UUID, service: InventoryServiceDep):
    return service.get_by_product(product_id)


@router.post("",response_model=InventoryPublic, status_code=201, dependencies=[write])
def create_item(data: CreateInventorySchema, service: InventoryServiceDep):
    return service.create(data)


@router.patch("/{item_id}", response_model=InventoryPublic, dependencies=[write])
def update_item(item_id: UUID, data: UpdateInventorySchema, service: InventoryServiceDep):
    return service.update(item_id, data)


@router.post("/product/{product_id}/adjust", response_model=InventoryPublic, dependencies=[write])
def adjust(product_id: UUID, data: StockAdjustmentSchema, service: InventoryServiceDep):
    return service.adjust_stock(product_id, data.quantity_delta)


@router.delete("/{item_id}", status_code=204, dependencies=[write])
def delete_item(item_id: UUID, service: InventoryServiceDep):
    service.delete(item_id)
    return Response(status_code=204)