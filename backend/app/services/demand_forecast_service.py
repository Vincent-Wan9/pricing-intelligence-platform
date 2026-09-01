from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import math
from uuid import UUID

from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.crud.demand_forecast import demand_forecast_crud
from app.models.demand_forecast import DemandForecast
from app.models.demand_history import DemandHistory
from app.models.product import Product
from app.schemas.demand_forecast_schema import (
    CreateDemandForecastSchema,
    CreateDemandHistorySchema,
    DemandForecastPublic,
    DemandHistoryPublic,
    ForecastGenerationResult,
    UpdateDemandForecastSchema,
)
from app.core.config import settings


class DemandForecastServiceError(Exception):
    pass


class DemandForecastNotFoundError(DemandForecastServiceError):
    pass


class DemandForecastConflictError(DemandForecastServiceError):
    pass


class DemandForecastValidationError(DemandForecastServiceError):
    pass


class InsufficientDemandHistoryError(DemandForecastValidationError):
    pass


class DemandForecastService:

    FEATURE_LAG_DAYS = 7
    BASELINE_WINDOW_DAYS = 7

    def __init__(self, db: Session) -> None:
        self.db = db
        self.crud = demand_forecast_crud

    def get(self, forecast_id: UUID) -> DemandForecastPublic:
        return DemandForecastPublic.model_validate(self._get_model(forecast_id))

    def create(self, forecast_in: CreateDemandForecastSchema) -> DemandForecastPublic:
        self._validate_product(forecast_in.product_id)
        forecast = DemandForecast(**forecast_in.model_dump())
        return self._save(forecast, "created")

    def record_demand(self, demand_in: CreateDemandHistorySchema) -> DemandHistoryPublic:
        """Record one observed daily quantity; duplicate product/date rows are rejected."""
        self._validate_product(demand_in.product_id, require_active=False)
        observation = DemandHistory(**demand_in.model_dump())
        try:
            self.db.add(observation)
            self.db.commit()
            self.db.refresh(observation)
        except IntegrityError as exc:
            self.db.rollback()
            raise DemandForecastConflictError("Historical demand could not be recorded") from exc
        return DemandHistoryPublic.model_validate(observation)

    def get_demand_history(self, product_id: UUID, *, limit: int = 365) -> list[DemandHistoryPublic]:
        self._validate_product(product_id, require_active=False)
        observations = list(self.db.scalars(
            select(DemandHistory)
            .where(DemandHistory.product_id == product_id)
            .order_by(DemandHistory.demand_date.desc())
            .limit(limit)
        ).all())
        observations.reverse()
        return [DemandHistoryPublic.model_validate(item) for item in observations]

    def generate(self, product_id: UUID, *, horizon_days: int | None = None) -> ForecastGenerationResult:
        """Evaluate baseline and ridge models, select the lower-MAE method, and persist forecasts."""
        self._validate_product(product_id)
        horizon = (
            settings.demand_forecast_default_horizon_days
            if horizon_days is None else horizon_days
        )
        if not 1 <= horizon <= 90:
            raise DemandForecastValidationError("horizon_days must be between 1 and 90")

        observations = list(self.db.scalars(
            select(DemandHistory).where(DemandHistory.product_id == product_id)
            .order_by(DemandHistory.demand_date)
        ).all())
        minimum = max(settings.demand_forecast_min_history_days, self.FEATURE_LAG_DAYS + 8)
        if len(observations) < minimum:
            raise InsufficientDemandHistoryError(
                f"At least {minimum} daily demand observations are required; found {len(observations)}"
            )

        dates, quantities = self._daily_series(observations)
        features, targets, feature_dates = self.build_features(dates, quantities)
        split = self.time_train_test_split(features, targets, feature_dates)
        train_x, test_x, train_y, test_y, _train_dates, test_dates = split

        model = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
        model.fit(train_x, train_y)
        ml_predictions = [max(0.0, float(value)) for value in model.predict(test_x)]
        ml_mae = float(mean_absolute_error(test_y, ml_predictions))

        baseline_predictions = self._walk_forward_baseline(dates, quantities, test_dates)
        baseline_mae = float(mean_absolute_error(test_y, baseline_predictions))
        use_ml = ml_mae <= baseline_mae
        model_name = "ridge-lag-v1" if use_ml else "moving-average-7"

        if use_ml:
            model.fit(features, targets)
        future = self._forecast_future(
            dates, quantities, horizon=horizon, model=model if use_ml else None
        )
        confidence = self._confidence_score(min(ml_mae, baseline_mae), quantities)
        persisted = self._replace_forecasts(product_id, future, model_name, confidence)
        return ForecastGenerationResult(
            product_id=product_id,
            horizon_days=horizon,
            model_name=model_name,
            baseline_mae=round(baseline_mae, 4),
            ml_mae=round(ml_mae, 4),
            forecasts=persisted,
        )

    @classmethod
    def build_features(
        cls, dates: list[date], quantities: list[int]
    ) -> tuple[list[list[float]], list[float], list[date]]:
        """Create lag, rolling, calendar, and recent-trend features in time order."""
        rows: list[list[float]] = []
        targets: list[float] = []
        row_dates: list[date] = []
        for index in range(cls.FEATURE_LAG_DAYS, len(quantities)):
            history = quantities[index - cls.FEATURE_LAG_DAYS:index]
            current_date = dates[index]
            rows.append(cls._feature_row(current_date, history))
            targets.append(float(quantities[index]))
            row_dates.append(current_date)
        return rows, targets, row_dates

    @staticmethod
    def time_train_test_split(features, targets, dates):
        """Reserve the newest observations for evaluation without shuffling."""
        test_size = max(7, math.ceil(len(features) * 0.2))
        if len(features) - test_size < 7:
            raise InsufficientDemandHistoryError("Not enough feature rows for time-based evaluation")
        split_at = len(features) - test_size
        return (
            features[:split_at], features[split_at:], targets[:split_at], targets[split_at:],
            dates[:split_at], dates[split_at:],
        )

    @staticmethod
    def _feature_row(current_date: date, history: list[int]) -> list[float]:
        recent_three = history[-3:]
        trend = (recent_three[-1] - recent_three[0]) / max(len(recent_three) - 1, 1)
        return [
            float(history[-1]),
            float(history[0]),
            sum(history) / len(history),
            sum(recent_three) / len(recent_three),
            float(trend),
            float(current_date.weekday()),
            float(current_date.month),
        ]

    @classmethod
    def _walk_forward_baseline(cls, dates, quantities, test_dates) -> list[float]:
        by_date = dict(zip(dates, quantities))
        predictions: list[float] = []
        for target_date in test_dates:
            previous = [
                by_date.get(target_date - timedelta(days=offset), 0)
                for offset in range(cls.BASELINE_WINDOW_DAYS, 0, -1)
            ]
            predictions.append(sum(previous) / len(previous))
        return predictions

    @classmethod
    def _forecast_future(cls, dates, quantities, *, horizon: int, model) -> list[tuple[datetime, int]]:
        values = list(quantities)
        cursor = dates[-1]
        first_forecast_date = max(cursor, date.today()) + timedelta(days=1)
        results: list[tuple[datetime, int]] = []
        while cursor < first_forecast_date + timedelta(days=horizon - 1):
            cursor += timedelta(days=1)
            history = values[-cls.FEATURE_LAG_DAYS:]
            if model is None:
                prediction = sum(history) / len(history)
            else:
                prediction = float(model.predict([cls._feature_row(cursor, history)])[0])
            quantity = max(0, int(round(prediction)))
            values.append(quantity)
            if cursor >= first_forecast_date:
                results.append((datetime.combine(cursor, datetime.min.time(), tzinfo=timezone.utc), quantity))
        return results

    def _replace_forecasts(self, product_id, future, model_name, confidence):
        forecast_dates = [item[0] for item in future]
        try:
            self.db.execute(delete(DemandForecast).where(
                DemandForecast.product_id == product_id,
                DemandForecast.forecast_date.in_(forecast_dates),
            ))
            records = [DemandForecast(
                product_id=product_id,
                forecast_date=forecast_date,
                predicted_demand=quantity,
                model_name=model_name,
                confidence_score=confidence,
            ) for forecast_date, quantity in future]
            self.db.add_all(records)
            self.db.commit()
            for record in records:
                self.db.refresh(record)
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise DemandForecastConflictError("Generated forecasts could not be persisted") from exc
        return [DemandForecastPublic.model_validate(record) for record in records]

    @staticmethod
    def _daily_series(observations):
        observed = {item.demand_date: item.quantity for item in observations}
        cursor, end = min(observed), max(observed)
        dates, quantities = [], []
        while cursor <= end:
            dates.append(cursor)
            quantities.append(observed.get(cursor, 0))
            cursor += timedelta(days=1)
        return dates, quantities

    @staticmethod
    def _confidence_score(mae: float, quantities: list[int]):
        mean_demand = sum(quantities) / len(quantities)
        score = 0.0 if mean_demand == 0 else max(0.0, 100.0 * (1.0 - mae / mean_demand))
        return round(min(score, 100.0), 2)

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
