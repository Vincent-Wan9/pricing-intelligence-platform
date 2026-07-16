from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.competitor import Competitor
from app.schemas.competitor_schema import CreateCompetitorSchema, UpdateCompetitorSchema


class CompetitorCRUD(CRUDBase[Competitor, CreateCompetitorSchema, UpdateCompetitorSchema]):

    def get_by_name(self, db: Session, name: str):
        stmt = (select(Competitor).where(Competitor.competitor_name == name))

        return db.scalar(stmt)

    def get_by_website(self, db: Session, website: str):
        stmt = (select(Competitor).where(Competitor.website_url == website))

        return db.scalar(stmt)

    def get_active_competitors(self, db: Session):
        stmt = (select(Competitor).where(Competitor.is_active == True).order_by(Competitor.competitor_name))

        return list(db.scalars(stmt).all())


competitor_crud = CompetitorCRUD(Competitor)