from uuid import UUID
from fastapi import APIRouter, Depends
from app.dependencies import CurrentUser, PriceRecommendationServiceDep, require_roles
from app.schemas.price_recommendation_schema import CreatePriceRecommendationSchema, PriceRecommendationPublic, ReviewPriceRecommendationSchema

router = APIRouter(prefix="/price-recommendations", tags=["price recommendations"])
read = Depends(require_roles("viewer", "editor", "approver", "admin"))
generate = Depends(require_roles("editor", "admin"))
review = Depends(require_roles("approver", "admin"))


@router.get("/{recommendation_id}", response_model = PriceRecommendationPublic, dependencies = [read])
def get_item(recommendation_id: UUID, service: PriceRecommendationServiceDep):
    return service.get(recommendation_id)


@router.post("", response_model = PriceRecommendationPublic, status_code = 201, dependencies = [generate])
def create_item(data: CreatePriceRecommendationSchema, service: PriceRecommendationServiceDep):
    return service.create(data)


@router.get("/product/{product_id}/latest", response_model = PriceRecommendationPublic, dependencies = [read])
def latest(product_id: UUID, service: PriceRecommendationServiceDep):
    return service.get_latest(product_id)


@router.get("/product/{product_id}/history", response_model = list[PriceRecommendationPublic], dependencies = [read])
def history(product_id: UUID, service: PriceRecommendationServiceDep):
    return service.get_history(product_id)


@router.post("/{recommendation_id}/approve", response_model = PriceRecommendationPublic, dependencies = [review])
def approve(recommendation_id: UUID, data: ReviewPriceRecommendationSchema, service: PriceRecommendationServiceDep, actor: CurrentUser):
    return service.approve(recommendation_id, actor = actor, reason = data.reason)


@router.post("/{recommendation_id}/reject", response_model = PriceRecommendationPublic, dependencies = [review])
def reject(recommendation_id: UUID, data: ReviewPriceRecommendationSchema, service: PriceRecommendationServiceDep, actor: CurrentUser):
    return service.reject(recommendation_id, actor = actor, reason = data.reason)
