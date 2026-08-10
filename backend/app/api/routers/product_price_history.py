from uuid import UUID
from fastapi import APIRouter, Depends, Query
from app.dependencies import ProductPriceServiceDep, require_roles
from app.schemas.product_price_history_schema import ProductPriceHistoryPublic

router = APIRouter(prefix="/product-price-history", tags=["product price history"])
read = Depends(require_roles("viewer", "editor", "approver", "admin"))


@router.get("/product/{product_id}", response_model = list[ProductPriceHistoryPublic], dependencies = [read])
def history(product_id: UUID, service: ProductPriceServiceDep, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000)):
    return service.get_history(product_id, skip = skip, limit = limit)


products_router = APIRouter(prefix="/products", tags=["product price history"])


@products_router.get("/{product_id}/price-history", response_model=list[ProductPriceHistoryPublic], dependencies=[read])
def product_history(product_id: UUID, service: ProductPriceServiceDep, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000)):
    return service.get_history(product_id, skip=skip, limit=limit)
