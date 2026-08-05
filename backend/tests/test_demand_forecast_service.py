from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.schemas.demand_forecast_schema import (
    CreateDemandForecastSchema,
    UpdateDemandForecastSchema,
)
from app.services.demand_forecast_service import (
    DemandForecastConflictError,
    DemandForecastService,
    DemandForecastValidationError,
)


def _forecast_input(product_id):
    return CreateDemandForecastSchema(
        product_id=product_id,
        forecast_date=datetime(2026, 8, 10, tzinfo=timezone.utc),
        predicted_demand=125,
        model_name="xgboost-v1",
        confidence_score=Decimal("91.50"),
    )


def test_create_forecast_commits_and_refreshes() -> None:
    db = MagicMock()
    product_id = uuid4()
    db.get.return_value = SimpleNamespace(is_active=True)

    def populate_server_fields(forecast) -> None:
        forecast.forecast_id = uuid4()
        forecast.created_at = datetime.now(timezone.utc)

    db.refresh.side_effect = populate_server_fields

    result = DemandForecastService(db).create(_forecast_input(product_id))

    assert result.product_id == product_id
    assert result.predicted_demand == 125
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()
    db.rollback.assert_not_called()


def test_create_forecast_rolls_back_conflict() -> None:
    db = MagicMock()
    db.get.return_value = SimpleNamespace(is_active=True)
    db.commit.side_effect = IntegrityError("insert", {}, Exception("duplicate"))

    with pytest.raises(DemandForecastConflictError, match="created"):
        DemandForecastService(db).create(_forecast_input(uuid4()))

    db.rollback.assert_called_once()
    db.refresh.assert_not_called()


def test_create_forecast_rejects_inactive_product_without_writing() -> None:
    db = MagicMock()
    db.get.return_value = SimpleNamespace(is_active=False)

    with pytest.raises(DemandForecastValidationError, match="inactive"):
        DemandForecastService(db).create(_forecast_input(uuid4()))

    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_update_forecast_requires_at_least_one_field() -> None:
    service = DemandForecastService(MagicMock())
    service.crud = MagicMock()
    service.crud.get.return_value = SimpleNamespace()

    with pytest.raises(DemandForecastValidationError, match="At least one"):
        service.update(uuid4(), UpdateDemandForecastSchema())


def test_update_forecast_rejects_null_required_field() -> None:
    service = DemandForecastService(MagicMock())
    service.crud = MagicMock()
    service.crud.get.return_value = SimpleNamespace()

    with pytest.raises(DemandForecastValidationError, match="predicted_demand"):
        service.update(
            uuid4(),
            UpdateDemandForecastSchema(predicted_demand=None),
        )

    service.db.commit.assert_not_called()


def test_date_range_validation_happens_before_query() -> None:
    service = DemandForecastService(MagicMock())
    start = datetime(2026, 8, 2, tzinfo=timezone.utc)
    end = datetime(2026, 8, 1, tzinfo=timezone.utc)

    with pytest.raises(DemandForecastValidationError, match="start_date"):
        service.get_between(uuid4(), start_date=start, end_date=end)

    service.db.get.assert_not_called()
