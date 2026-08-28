import logging

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.product import Product
from app.services.demand_forecast_service import DemandForecastService
from app.tasks.celery_app import celery_app


logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.refresh_demand_forecasts")
def refresh_demand_forecasts() -> dict[str, int]:
    """Refresh active products independently so one failure cannot abort the batch."""
    db = SessionLocal()
    try:
        product_ids = list(db.scalars(
            select(Product.product_id).where(Product.is_active.is_(True))
        ).all())
        generated = 0
        failures = 0
        for product_id in product_ids:
            try:
                DemandForecastService(db).generate(
                    product_id, horizon_days=settings.demand_forecast_default_horizon_days
                )
                generated += 1
            except Exception:
                failures += 1
                db.rollback()
                logger.exception("Could not refresh demand forecast for product %s", product_id)
        return {"products": len(product_ids), "generated": generated, "failures": failures}
    finally:
        db.close()
