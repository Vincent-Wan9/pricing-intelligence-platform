from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response, status
from app.dependencies import CategoryServiceDep, require_roles
from app.schemas.category_schema import CategoryPublic, CreateCategorySchema, UpdateCategorySchema

router = APIRouter(prefix = "/categories", tags = ["categories"])
read = Depends(require_roles("viewer", "editor", "approver", "admin"))
write = Depends(require_roles("editor", "admin"))

@router.get("", response_model = list[CategoryPublic], dependencies = [read])
def list_items(service: CategoryServiceDep, skip: int = Query(0,ge=0), limit: int = Query(100, ge=1, le=1000)): 
    return service.list(skip=skip,limit=limit)


@router.get("/{item_id}", response_model = CategoryPublic, dependencies = [read])
def get_item(item_id: UUID, service: CategoryServiceDep): 
    return service.get(item_id)


@router.post("", response_model = CategoryPublic, status_code=201, dependencies = [write])
def create_item(data: CreateCategorySchema, service: CategoryServiceDep): 
    return service.create(data)


@router.patch("/{item_id}", response_model = CategoryPublic, dependencies = [write])
def update_item(item_id: UUID, data: UpdateCategorySchema, service: CategoryServiceDep):
     return service.update(item_id,data)


@router.delete("/{item_id}", status_code = 204, dependencies = [write])
def delete_item(item_id: UUID, service: CategoryServiceDep): service.delete(item_id); 
return Response(status_code = 204)
