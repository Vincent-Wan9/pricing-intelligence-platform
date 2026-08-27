from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.demand_forecast import DemandForecast
from app.schemas.demand_forecast_schema import CreateDemandForecastSchema, UpdateDemandForecastSchema



class DemandForecastCRUD(CRUDBase[DemandForecast, CreateDemandForecastSchema, UpdateDemandForecastSchema]):

    def get_latest_forecast(self, db: Session, product_id: UUID):
        stmt = (select(DemandForecast).where(DemandForecast.product_id == product_id)
            .order_by(DemandForecast.created_at.desc(), DemandForecast.forecast_date.asc())
            .limit(1))

        return db.scalar(stmt)

    def get_forecast_history(self, db: Session, product_id: UUID):
        stmt = (select(DemandForecast).where(DemandForecast.product_id == product_id)
            .order_by(DemandForecast.forecast_date.desc()))

        return list(db.scalars(stmt).all())

    def get_forecasts_between(self, db: Session, product_id: UUID, start_date: datetime, end_date: datetime):
        stmt = (select(DemandForecast).where(
                DemandForecast.product_id == product_id,
                DemandForecast.forecast_date >= start_date,
                DemandForecast.forecast_date <= end_date
            ).order_by(DemandForecast.forecast_date)
        )

        return list(db.scalars(stmt).all())


demand_forecast_crud = DemandForecastCRUD(DemandForecast)
