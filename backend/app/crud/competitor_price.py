from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.competitor_price import CompetitorPrice
from app.schemas.competitor_price_schema import CreateCompetitorPriceSchema,UpdateCompetitorPriceSchema


class CompetitorPriceCRUD(CRUDBase[CompetitorPrice, CreateCompetitorPriceSchema, UpdateCompetitorPriceSchema]):

    def get_latest_price(self, db: Session, competitor_product_id: UUID):
        stmt = (select(CompetitorPrice).where(CompetitorPrice.competitor_product_id == competitor_product_id)
            .order_by(CompetitorPrice.crawl_timestamp.desc())
            .limit(1)
        )

        return db.scalar(stmt)

    def get_price_history(self, db: Session, competitor_product_id: UUID):
        stmt = (select(CompetitorPrice).where(CompetitorPrice.competitor_product_id == competitor_product_id)
            .order_by(CompetitorPrice.crawl_timestamp.desc())
        )

        return list(db.scalars(stmt).all())

    def get_prices_between(self, db: Session, competitor_product_id: UUID, start_date: datetime, end_date: datetime,):
        stmt = (
            select(CompetitorPrice)
            .where(
                CompetitorPrice.competitor_product_id
                == competitor_product_id,
                CompetitorPrice.crawl_timestamp >= start_date,
                CompetitorPrice.crawl_timestamp <= end_date,
            )
            .order_by(CompetitorPrice.crawl_timestamp)
        )

        return list(db.scalars(stmt).all())


competitor_price_crud = CompetitorPriceCRUD(CompetitorPrice)
