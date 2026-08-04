from datetime import datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.demand_forecast import demand_forecast_crud
from app.models.demand_forecast import DemandForecast
from app.models.product import Product
from app.schemas.demand_forecast_schema import CreateDemandForecastSchema, DemandForecastPublic, UpdateDemandForecastSchema


class DemandForecastServiceError(Exception):
    pass


class DemandForecastNotFoundError(DemandForecastServiceError):
    pass


class DemandForecastConflictError(DemandForecastServiceError):
    pass


class DemandForecastValidationError(DemandForecastServiceError):
    pass


class DemandForecastService:

    def __init__(self, db: Session) -> None:
        self.db = db
        self.crud = demand_forecast_crud

    def get(self, forecast_id: UUID) -> DemandForecastPublic:
        return DemandForecastPublic.model_validate(self._get_model(forecast_id))

    def create(self, forecast_in: CreateDemandForecastSchema) -> DemandForecastPublic:
        self._validate_product(forecast_in.product_id)
        forecast = DemandForecast(**forecast_in.model_dump())
        return self._save(forecast, "created")

    def update(self, forecast_id: UUID, forecast_in: UpdateDemandForecastSchema) -> DemandForecastPublic:
        forecast = self._get_model(forecast_id)
        update_data = forecast_in.model_dump(exclude_unset=True)
        if not update_data:
            raise DemandForecastValidationError(
                "At least one field is required for an update")
        required_fields = ("forecast_date", "predicted_demand")
        null_fields = [
            field
            for field in required_fields
            if field in update_data and update_data[field] is None
        ]
        if null_fields:
            raise DemandForecastValidationError(
                f"{', '.join(null_fields)} cannot be null")

        for field, value in update_data.items():
            setattr(forecast, field, value)
        return self._save(forecast, "updated")

    def delete(self, forecast_id: UUID) -> None:
        forecast = self._get_model(forecast_id)
        try:
            self.db.delete(forecast)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DemandForecastConflictError(
                "Demand forecast could not be deleted") from exc

    def get_latest(self, product_id: UUID) -> DemandForecastPublic:
        self._validate_product(product_id, require_active=False)
        forecast = self.crud.get_latest_forecast(self.db, product_id)
        if forecast is None:
            raise DemandForecastNotFoundError(
                f"No demand forecast exists for product {product_id}")
        return DemandForecastPublic.model_validate(forecast)

    def get_history(self, product_id: UUID) -> list[DemandForecastPublic]:
        self._validate_product(product_id, require_active=False)
        forecasts = self.crud.get_forecast_history(self.db, product_id)
        return [DemandForecastPublic.model_validate(item) for item in forecasts]

    def get_between(self, product_id: UUID, *, start_date: datetime, end_date: datetime) -> list[DemandForecastPublic]:
        if start_date > end_date:
            raise DemandForecastValidationError(
                "start_date cannot be after end_date")
        self._validate_product(product_id, require_active=False)
        forecasts = self.crud.get_forecasts_between(
            self.db,
            product_id,
            start_date,
            end_date,
        )
        return [DemandForecastPublic.model_validate(item) for item in forecasts]

    def _save(self, forecast: DemandForecast, operation: str) -> DemandForecastPublic:
        try:
            self.db.add(forecast)
            self.db.commit()
            self.db.refresh(forecast)
        except IntegrityError as exc:
            self.db.rollback()
            raise DemandForecastConflictError(
                f"Demand forecast could not be {operation}") from exc
        return DemandForecastPublic.model_validate(forecast)

    def _get_model(self, forecast_id: UUID) -> DemandForecast:
        forecast = self.crud.get(self.db, forecast_id)
        if forecast is None:
            raise DemandForecastNotFoundError(
                f"Demand forecast {forecast_id} was not found")
        return forecast

    def _validate_product(self, product_id: UUID, *, require_active: bool = True) -> None:
        product = self.db.get(Product, product_id)
        if product is None:
            raise DemandForecastValidationError(
                f"Product {product_id} does not exist")
        if require_active and not product.is_active:
            raise DemandForecastValidationError(
                "Cannot create a forecast for an inactive product")
