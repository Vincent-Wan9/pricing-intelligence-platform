from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response
from app.dependencies import PricingRuleServiceDep, require_roles
from app.schemas.price_rule_schema import CreatePricingRuleSchema, PricingRulePublic, UpdatePricingRuleSchema

router = APIRouter(prefix="/pricing-rules", tags=["pricing rules"])
read = Depends(require_roles("viewer", "editor", "approver", "admin"))
write = Depends(require_roles("editor", "admin"))


@router.get("", response_model = list[PricingRulePublic], dependencies = [read])
def list_items(service: PricingRuleServiceDep, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000)):
    return service.list(skip = skip, limit = limit)


@router.get("/{item_id}", response_model = PricingRulePublic, dependencies = [read])
def get_item(item_id: UUID, service: PricingRuleServiceDep):
    return service.get(item_id)


@router.post("", response_model = PricingRulePublic, status_code = 201, dependencies = [write])
def create_item(data: CreatePricingRuleSchema, service: PricingRuleServiceDep):
    return service.create(data)


@router.patch("/{item_id}", response_model = PricingRulePublic, dependencies = [write])
def update_item(item_id: UUID, data: UpdatePricingRuleSchema, service: PricingRuleServiceDep):
    return service.update(item_id, data)


@router.post("/{item_id}/activate", response_model = PricingRulePublic, dependencies = [write])
def activate(item_id: UUID, service: PricingRuleServiceDep):
    return service.activate(item_id)


@router.post("/{item_id}/deactivate", response_model = PricingRulePublic, dependencies = [write])
def deactivate(item_id: UUID, service: PricingRuleServiceDep):
    return service.deactivate(item_id)


@router.delete("/{item_id}", status_code = 204, dependencies = [write])
def delete_item(item_id: UUID, service: PricingRuleServiceDep):
    service.delete(item_id)
    return Response(status_code = 204)
