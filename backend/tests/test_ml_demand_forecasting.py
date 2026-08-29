from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.models.category import Category
from app.models.demand_forecast import DemandForecast
from app.models.demand_history import DemandHistory
from app.models.pricing_rule import PricingRule, RuleType
from app.models.product import Product
from app.services.demand_forecast_service import (
    DemandForecastService,
    InsufficientDemandHistoryError,
)


def add_product(db_session):
    category = Category(category_name=f"Cat-{uuid4().hex[:8]}", slug=f"cat-{uuid4().hex[:8]}")
    rule = PricingRule(
        rule_name=f"Rule-{uuid4()}", rule_description="test", rule_type=RuleType.DEMAND_BASED,
        priority=1, is_active=True,
    )
    db_session.add_all([category, rule])
    db_session.flush()
    product = Product(
        sku=f"SKU-{uuid4()}", product_name="Forecast product", slug=f"product-{uuid4()}",
        category_id=category.category_id, rule_id=rule.rule_id,
        base_price=Decimal("10"), current_price=Decimal("12"),
        target_margin=Decimal("20"), safety_stock=5, is_active=True,
    )
    db_session.add(product)
    db_session.commit()
    return product


def add_history(db_session, product_id, *, days=35):
    start = date.today() - timedelta(days=days - 1)
    rows = [DemandHistory(
        product_id=product_id,
        demand_date=start + timedelta(days=index),
        quantity=20 + index + (index % 7),
    ) for index in range(days)]
    db_session.add_all(rows)
    db_session.commit()
    return rows


def test_feature_generation_contains_lags_rolling_calendar_and_trend():
    dates = [date(2026, 1, 1) + timedelta(days=index) for index in range(8)]
    features, targets, row_dates = DemandForecastService.build_features(dates, list(range(8)))

    assert features == [[6.0, 0.0, 3.0, 5.0, 1.0, 3.0, 1.0]]
    assert targets == [7.0]
    assert row_dates == [date(2026, 1, 8)]


def test_time_split_keeps_newest_rows_in_test_partition():
    dates = [date(2026, 1, 1) + timedelta(days=index) for index in range(28)]
    features = [[float(index)] for index in range(28)]
    targets = [float(index) for index in range(28)]

    train_x, test_x, _, _, train_dates, test_dates = DemandForecastService.time_train_test_split(
        features, targets, dates
    )

    assert train_dates[-1] < test_dates[0]
    assert train_x[-1][0] < test_x[0][0]
    assert len(test_x) == 7


def test_generate_rejects_insufficient_history(db_session):
    product = add_product(db_session)
    add_history(db_session, product.product_id, days=10)

    with pytest.raises(InsufficientDemandHistoryError, match="At least"):
        DemandForecastService(db_session).generate(product.product_id, horizon_days=7)


def test_forecast_generation_selects_model_and_persists_horizon(db_session):
    product = add_product(db_session)
    add_history(db_session, product.product_id)

    result = DemandForecastService(db_session).generate(product.product_id, horizon_days=7)

    assert result.model_name in {"ridge-lag-v1", "moving-average-7"}
    assert result.baseline_mae >= 0
    assert result.ml_mae >= 0
    assert len(result.forecasts) == 7
    assert all(item.forecast_date.date() > date.today() for item in result.forecasts)
    assert db_session.query(DemandForecast).filter_by(product_id=product.product_id).count() == 7


def test_baseline_is_selected_when_ml_is_worse(db_session, monkeypatch):
    product = add_product(db_session)
    add_history(db_session, product.product_id)

    class BadModel:
        def fit(self, _features, _targets):
            return self

        def predict(self, features):
            return [10_000.0] * len(features)

    monkeypatch.setattr("app.services.demand_forecast_service.make_pipeline", lambda *_: BadModel())
    result = DemandForecastService(db_session).generate(product.product_id, horizon_days=3)

    assert result.ml_mae > result.baseline_mae
    assert result.model_name == "moving-average-7"

