from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.price_recommendation import PriceRecommendation
from app.schemas.price_recommendation_schema import CreatePriceRecommendationSchema


class PriceRecommendationCRUD(
    CRUDBase[
        PriceRecommendation,
        CreatePriceRecommendationSchema,
        CreatePriceRecommendationSchema,
    ]
):

    def get_latest_recommendation(self, db: Session, product_id: UUID):
        stmt = (select(PriceRecommendation).where(PriceRecommendation.product_id == product_id)
            .order_by(PriceRecommendation.generated_at.desc())
            .limit(1))

        return db.scalar(stmt)

    def get_recommendation_history(self, db: Session, product_id: UUID):
        stmt = (select(PriceRecommendation).where(PriceRecommendation.product_id == product_id)
            .order_by(PriceRecommendation.generated_at.desc()))

        return list(db.scalars(stmt).all())


price_recommendation_crud = PriceRecommendationCRUD(PriceRecommendation)
