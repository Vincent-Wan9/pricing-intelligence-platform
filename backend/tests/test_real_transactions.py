from __future__ import annotations

import asyncio
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.inventory import Inventory
from app.models.price_recommendation import PriceRecommendation
from app.models.pricing_rule import PricingRule, RuleType
from app.models.product import Product
from app.models.product_price_history import ProductPriceHistory
from app.models.user import User
from app.schemas.inventory_schema import UpdateInventorySchema
from app.services.inventory_service import InventoryConflictError, InventoryService
from app.services.price_recommendation_service import (
    PriceRecommendationConflictError,
    PriceRecommendationService,
)
from app.services.product_price_service import ProductPriceService


class NoopCache:
    async def invalidate(self, *args):
        return None

    async def store(self, value):
        return None


def seed_product(db: Session) -> Product:
    category = Category(category_name="Transactions", slug="transactions")
    rule = PricingRule(
        rule_name="Transaction rule",
        rule_description="test",
        rule_type=RuleType.COST_PLUS,
        is_active=True,
    )
    db.add_all([category, rule])
    db.flush()
    product = Product(
        sku="TX-1",
        product_name="Transaction product",
        slug="transaction-product",
        category_id=category.category_id,
        rule_id=rule.rule_id,
        base_price=Decimal("10.00"),
        current_price=Decimal("12.00"),
        min_price=Decimal("8.00"),
        max_price=Decimal("20.00"),
        is_active=True,
    )
    db.add(product)
    db.commit()
    return product


def actor(db: Session) -> User:
    user = User(
        email=f"approver-{uuid4()}@example.com",
        username=f"approver-{uuid4()}",
        hashed_password="unused",
        role="approver",
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


def test_price_and_history_are_rolled_back_together(db_session: Session) -> None:
    product = seed_product(db_session)
    missing_user = SimpleNamespace(user_id=uuid4(), role="approver", is_active=True)

    with pytest.raises(Exception):
        asyncio.run(ProductPriceService(db_session, NoopCache()).update_price(
            product.product_id, Decimal("14.00"), user=missing_user, reason="test failure"
        ))

    db_session.expire_all()
    assert db_session.get(Product, product.product_id).current_price == Decimal("12.00")
    assert db_session.scalars(select(ProductPriceHistory)).all() == []


def test_recommendation_apply_rolls_back_product_history_and_state(db_session: Session) -> None:
    product = seed_product(db_session)
    reviewer = actor(db_session)
    recommendation = PriceRecommendation(
        product_id=product.product_id,
        rule_id=product.rule_id,
        current_price=product.current_price,
        recommended_price=Decimal("15.00"),
        recommendation_reason="Approved recommendation",
        status="approved",
        reviewed_by=reviewer.user_id,
    )
    db_session.add(recommendation)
    db_session.commit()
    missing_actor = SimpleNamespace(user_id=uuid4(), role="approver", is_active=True)

    with pytest.raises(PriceRecommendationConflictError):
        asyncio.run(PriceRecommendationService(db_session).apply(
            recommendation.recommendation_id, actor=missing_actor
        ))

    db_session.expire_all()
    assert db_session.get(Product, product.product_id).current_price == Decimal("12.00")
    assert db_session.get(PriceRecommendation, recommendation.recommendation_id).status == "approved"
    assert db_session.scalars(select(ProductPriceHistory)).all() == []


def test_inventory_constraint_failure_restores_original_values(db_session: Session) -> None:
    product = seed_product(db_session)
    inventory = Inventory(
        product_id=product.product_id,
        vendor="Original vendor",
        lead_time=2,
        cost_per_unit=Decimal("5.00"),
        on_hand_qty=8,
    )
    db_session.add(inventory)
    db_session.commit()

    with pytest.raises(InventoryConflictError):
        InventoryService(db_session).update(
            inventory.inventory_id, UpdateInventorySchema(vendor=None)
        )

    db_session.expire_all()
    restored = db_session.get(Inventory, inventory.inventory_id)
    assert restored.vendor == "Original vendor"
    assert restored.on_hand_qty == 8


def test_real_unique_constraint_leaves_no_partial_insert(db_session: Session) -> None:
    product = seed_product(db_session)
    duplicate = Product(
        sku=product.sku,
        product_name="Duplicate",
        slug="duplicate",
        category_id=product.category_id,
        rule_id=product.rule_id,
        base_price=Decimal("9.00"),
        current_price=Decimal("11.00"),
        is_active=True,
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    assert db_session.scalar(select(Product).where(Product.sku == product.sku)).product_id == product.product_id
    assert len(db_session.scalars(select(Product)).all()) == 1
