from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.product_price_history import ProductPriceHistory
from app.schemas.product_price_history_schema import CreateProductPriceHistorySchema



class ProductPriceHistoryCRUD(
    CRUDBase[
        ProductPriceHistory,
        CreateProductPriceHistorySchema,
        CreateProductPriceHistorySchema,
    ]
):

    def get_price_history(self, db: Session, product_id: UUID, *, skip: int = 0, limit: int = 100):
        stmt = (select(ProductPriceHistory)
            .where(ProductPriceHistory.product_id == product_id)
            .order_by(ProductPriceHistory.changed_at.desc())
            .offset(skip).limit(limit))

        return list(db.scalars(stmt).all())



product_price_history_crud = ProductPriceHistoryCRUD(ProductPriceHistory)
