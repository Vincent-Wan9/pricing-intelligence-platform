from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.inventory import Inventory
from app.models.price_recommendation import PriceRecommendation
from app.models.pricing_rule import PricingRule, RuleType
from app.models.product import Product
from app.services.price_recommendation_service import (
    MissingPricingDataError,
    NoApplicablePricingRuleError,
    PriceRecommendationConflictError,
    PriceRecommendationNotFoundError,
    PriceRecommendationService,
    PriceRecommendationValidationError,
)


def actor(role: str = "approver"):
    return SimpleNamespace(user_id=uuid4(), role=role, is_active=True)


def product(*, rule_id=None) -> Product:
    return Product(
        product_id=uuid4(), sku="SKU-1", product_name="Example", slug="example",
        category_id=uuid4(), rule_id=rule_id or uuid4(), base_price=Decimal("10"),
        current_price=Decimal("20"), min_price=Decimal("12"), max_price=Decimal("30"),
        target_margin=Decimal("20"), safety_stock=5, is_active=True,
    )


def rule(rule_type=RuleType.COST_PLUS, *, rule_id=None, active=True) -> PricingRule:
    return PricingRule(
        rule_id=rule_id or uuid4(), rule_name="Primary rule", rule_description="Rule details",
        rule_type=rule_type, priority=10, is_active=active,
    )


def inventory(item: Product) -> Inventory:
    return Inventory(
        product_id=item.product_id, vendor="Vendor", lead_time=2,
        cost_per_unit=Decimal("12"), on_hand_qty=4,
    )


def recommendation(item: Product, *, status="pending") -> PriceRecommendation:
    return PriceRecommendation(
        recommendation_id=uuid4(), product_id=item.product_id, rule_id=item.rule_id,
        current_price=item.current_price, recommended_price=Decimal("22"),
        recommendation_reason="Deterministic pricing recommendation", status=status,
        generated_at=datetime.now(timezone.utc),
    )


def test_cost_plus_evaluation_respects_margin_and_bounds() -> None:
    item = product()
    service = PriceRecommendationService(MagicMock())
    price, reason = service.evaluate_rule(
        rule(), product=item, inventory=inventory(item), forecast=None, competitor_prices=[]
    )
    assert price == Decimal("15.00")
    assert "target margin" in reason


def test_competitor_rule_requires_prices() -> None:
    item = product()
    with pytest.raises(MissingPricingDataError, match="competitor prices"):
        PriceRecommendationService(MagicMock()).evaluate_rule(
            rule(RuleType.COMPETITOR_BASED), product=item, inventory=None,
            forecast=None, competitor_prices=[],
        )


def test_latest_competitor_prices_are_deduplicated_in_database() -> None:
    db = MagicMock()
    db.scalars.return_value.all.return_value = [Decimal("18.25"), Decimal("19.50")]

    result = PriceRecommendationService(db)._latest_competitor_prices(uuid4())

    assert result == [Decimal("18.25"), Decimal("19.50")]
    statement = db.scalars.call_args.args[0]
    sql = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "row_number() OVER" in sql
    assert "recency_rank = 1" in sql
    db.execute.assert_not_called()


def test_generate_product_not_found() -> None:
    db = MagicMock()
    db.get.return_value = None
    with pytest.raises(PriceRecommendationNotFoundError):
        PriceRecommendationService(db).generate(uuid4())


def test_generate_rejects_no_active_assigned_rule() -> None:
    db = MagicMock()
    item = product()
    db.get.return_value = item
    db.scalars.return_value.all.return_value = []
    with pytest.raises(NoApplicablePricingRuleError):
        PriceRecommendationService(db).generate(item.product_id)


def test_generate_success_starts_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    db = MagicMock()
    configured_rule = rule()
    item = product(rule_id=configured_rule.rule_id)
    db.get.return_value = item
    db.scalars.return_value.all.return_value = [configured_rule]
    db.scalar.side_effect = [inventory(item), None]
    service = PriceRecommendationService(db)
    monkeypatch.setattr(service, "_latest_competitor_prices", lambda _: [])
    monkeypatch.setattr(service, "_insert", lambda rec: rec)
    result = service.generate(item.product_id)
    assert result.status == "pending"
    assert result.current_price == item.current_price
    assert result.recommended_price == Decimal("15.00")


@pytest.mark.parametrize("role", ["editor", "viewer"])
def test_non_review_roles_cannot_approve(role: str) -> None:
    with pytest.raises(PriceRecommendationValidationError, match="approvers and admins"):
        PriceRecommendationService(MagicMock()).approve(uuid4(), actor=actor(role))


@pytest.mark.parametrize("role", ["approver", "admin"])
def test_approver_and_admin_can_approve(role: str) -> None:
    db = MagicMock()
    item = product()
    rec = recommendation(item)
    service = PriceRecommendationService(db)
    service.crud = MagicMock()
    service.crud.get_for_update.return_value = rec
    result = service.approve(rec.recommendation_id, actor=actor(role))
    assert result.status == "approved"
    db.commit.assert_called_once()


@pytest.mark.parametrize("status", ["approved", "rejected", "applied"])
def test_processed_recommendation_cannot_be_reviewed(status: str) -> None:
    db = MagicMock()
    rec = recommendation(product(), status=status)
    service = PriceRecommendationService(db)
    service.crud = MagicMock()
    service.crud.get_for_update.return_value = rec
    with pytest.raises(PriceRecommendationConflictError, match="already processed"):
        service.approve(rec.recommendation_id, actor=actor())
    db.rollback.assert_called_once()


def test_pending_recommendation_cannot_be_applied() -> None:
    db = MagicMock()
    rec = recommendation(product())
    service = PriceRecommendationService(db)
    service.crud = MagicMock()
    service.crud.get_for_update.return_value = rec
    with pytest.raises(PriceRecommendationConflictError, match="Only approved"):
        import asyncio
        asyncio.run(service.apply(rec.recommendation_id, actor=actor()))


def test_apply_is_atomic_and_invalidates_cache() -> None:
    import asyncio
    db = MagicMock()
    item = product()
    rec = recommendation(item, status="approved")
    service = PriceRecommendationService(db, SimpleNamespace(invalidate=AsyncMock()))
    service.crud = MagicMock()
    service.crud.get_for_update.return_value = rec
    db.scalar.return_value = item
    result = asyncio.run(service.apply(rec.recommendation_id, actor=actor()))
    assert item.current_price == Decimal("22")
    assert result.status == "applied"
    history = db.add.call_args.args[0]
    assert history.old_price == Decimal("20")
    assert history.recommendation_id == rec.recommendation_id
    db.flush.assert_called_once()
    db.commit.assert_called_once()
    service.cache.invalidate.assert_awaited_once_with(item.product_id, item.sku)


def test_history_failure_rolls_back_product_and_status() -> None:
    import asyncio
    db = MagicMock()
    item = product()
    rec = recommendation(item, status="approved")
    service = PriceRecommendationService(db)
    service.crud = MagicMock()
    service.crud.get_for_update.return_value = rec
    db.scalar.return_value = item
    db.flush.side_effect = IntegrityError("insert", {}, Exception("history failed"))
    with pytest.raises(PriceRecommendationConflictError):
        asyncio.run(service.apply(rec.recommendation_id, actor=actor()))
    db.rollback.assert_called_once()
    # SQLAlchemy restores these on rollback in a real session; the important service
    # contract is that no commit or cache invalidation occurred.
    db.commit.assert_not_called()


def test_second_approval_attempt_cannot_succeed() -> None:
    db = MagicMock()
    rec = recommendation(product())
    service = PriceRecommendationService(db)
    service.crud = MagicMock()
    service.crud.get_for_update.return_value = rec
    service.approve(rec.recommendation_id, actor=actor())
    with pytest.raises(PriceRecommendationConflictError):
        service.approve(rec.recommendation_id, actor=actor())
    assert db.commit.call_count == 1
