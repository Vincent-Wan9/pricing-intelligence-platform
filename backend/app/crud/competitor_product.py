from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.competitor_product import CompetitorProduct
from app.schemas.competitor_product_schema import CreateCompetitorProductSchema, UpdateCompetitorProductSchema



class CompetitorProductCRUD(CRUDBase[CompetitorProduct, CreateCompetitorProductSchema, UpdateCompetitorProductSchema]):

    def get_by_product(self, db: Session, product_id: UUID, *, active_only: bool = False):
        stmt = select(CompetitorProduct).where(CompetitorProduct.product_id == product_id)
        if active_only:
            stmt = stmt.where(CompetitorProduct.is_active.is_(True))

        return list(db.scalars(stmt).all())

    def get_by_competitor(self, db: Session, competitor_id: UUID, *, active_only: bool = False):
        stmt = select(CompetitorProduct).where(CompetitorProduct.competitor_id == competitor_id)
        if active_only:
            stmt = stmt.where(CompetitorProduct.is_active.is_(True))

        return list(db.scalars(stmt).all())

    def get_by_url(self, db: Session, competitor_product_url: str):
        stmt = (select(CompetitorProduct).where(CompetitorProduct.competitor_product_url == competitor_product_url))

        return db.scalar(stmt)

    def get_by_product_and_competitor(self,db: Session, product_id: UUID, competitor_id: UUID):
        stmt = (select(CompetitorProduct).where(CompetitorProduct.product_id == product_id, CompetitorProduct.competitor_id == competitor_id))

        return db.scalar(stmt)


competitor_product_crud = CompetitorProductCRUD(CompetitorProduct)
