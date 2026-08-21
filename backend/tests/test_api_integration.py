from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.pricing_rule import PricingRule, RuleType
from app.models.product import Product
from app.models.user import User
from app.utils.security import create_access_token, hash_password


PASSWORD = "correct-password"


def add_user(db: Session, role: str, *, active: bool = True) -> User:
    user = User(
        email=f"{role}-{uuid4()}@example.com",
        username=f"{role}-{uuid4()}",
        hashed_password=hash_password(PASSWORD),
        role=role,
        is_active=active,
    )
    db.add(user)
    db.commit()
    return user


def bearer(user: User, *, expiration: timedelta | None = None) -> dict[str, str]:
    token = create_access_token({"sub": str(user.user_id)}, expiration=expiration)
    return {"Authorization": f"Bearer {token}"}


def seed_references(db: Session) -> tuple[Category, PricingRule]:
    category = Category(category_name="Electronics", slug="electronics")
    rule = PricingRule(
        rule_name="Cost Plus",
        rule_description="Cost based rule",
        rule_type=RuleType.COST_PLUS,
        priority=1,
        is_active=True,
    )
    db.add_all([category, rule])
    db.commit()
    return category, rule


def product_payload(category: Category, rule: PricingRule, sku: str) -> dict[str, object]:
    return {
        "sku": sku,
        "product_name": f"Product {sku}",
        "category_id": str(category.category_id),
        "rule_id": str(rule.rule_id),
        "base_price": "10.00",
        "current_price": "12.00",
    }


def test_product_crud_pagination_conflict_and_not_found_use_real_database(
    integration_client, db_session: Session
) -> None:
    editor = add_user(db_session, "editor")
    category, rule = seed_references(db_session)
    headers = bearer(editor)

    first = integration_client.post(
        "/products", json=product_payload(category, rule, "sku-001"), headers=headers
    )
    second = integration_client.post(
        "/products", json=product_payload(category, rule, "SKU-002"), headers=headers
    )
    assert first.status_code == second.status_code == 201
    assert first.json()["sku"] == "SKU-001"

    product_id = first.json()["product_id"]
    assert integration_client.get(f"/products/{product_id}", headers=headers).status_code == 200

    updated = integration_client.patch(
        f"/products/{product_id}", json={"product_name": "Renamed product"}, headers=headers
    )
    assert updated.status_code == 200
    assert updated.json()["product_name"] == "Renamed product"

    page = integration_client.get("/products?skip=1&limit=1", headers=headers)
    assert page.status_code == 200
    assert len(page.json()) == 1

    duplicate = integration_client.post(
        "/products", json=product_payload(category, rule, " sku-001 "), headers=headers
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "PRODUCT_CONFLICT"

    assert integration_client.get(f"/products/{uuid4()}", headers=headers).status_code == 404
    assert integration_client.get("/products?limit=0", headers=headers).status_code == 422

    assert integration_client.delete(f"/products/{product_id}", headers=headers).status_code == 400
    assert integration_client.post(f"/products/{product_id}/deactivate", headers=headers).status_code == 200
    assert integration_client.delete(f"/products/{product_id}", headers=headers).status_code == 204
    assert db_session.get(Product, UUID(product_id)) is None


def test_inventory_endpoints_prevent_negative_stock_and_duplicate_inventory(
    integration_client, db_session: Session
) -> None:
    editor = add_user(db_session, "editor")
    category, rule = seed_references(db_session)
    headers = bearer(editor)
    created_product = integration_client.post(
        "/products", json=product_payload(category, rule, "INV-1"), headers=headers
    ).json()
    payload = {
        "product_id": created_product["product_id"],
        "vendor": "Warehouse A",
        "lead_time": 3,
        "cost_per_unit": "7.50",
        "on_hand_qty": 5,
    }

    created = integration_client.post("/inventory", json=payload, headers=headers)
    assert created.status_code == 201
    assert integration_client.post("/inventory", json=payload, headers=headers).status_code == 409

    failed = integration_client.post(
        f"/inventory/product/{created_product['product_id']}/adjust",
        json={"quantity_delta": -6},
        headers=headers,
    )
    assert failed.status_code == 400
    unchanged = integration_client.get(
        f"/inventory/product/{created_product['product_id']}", headers=headers
    )
    assert unchanged.json()["on_hand_qty"] == 5


@pytest.mark.parametrize(
    ("role", "can_read", "can_write"),
    [
        ("viewer", True, False),
        ("editor", True, True),
        ("approver", True, False),
        ("admin", True, True),
    ],
)
def test_product_role_matrix_with_real_jwt(
    integration_client, db_session: Session, role: str, can_read: bool, can_write: bool
) -> None:
    account = add_user(db_session, role)
    category, rule = seed_references(db_session)
    headers = bearer(account)
    assert integration_client.get("/products", headers=headers).status_code == (200 if can_read else 403)
    response = integration_client.post(
        "/products", json=product_payload(category, rule, f"{role}-SKU"), headers=headers
    )
    assert response.status_code == (201 if can_write else 403)


def test_login_and_token_failures_use_real_users(integration_client, db_session: Session) -> None:
    active = add_user(db_session, "viewer")
    inactive = add_user(db_session, "viewer", active=False)

    success = integration_client.post(
        "/auth/login", data={"username": active.email, "password": PASSWORD}
    )
    assert success.status_code == 200
    assert integration_client.get(
        "/users/me", headers={"Authorization": f"Bearer {success.json()['access_token']}"}
    ).status_code == 200

    assert integration_client.post(
        "/auth/login", data={"username": active.email, "password": "wrong-password"}
    ).status_code == 401
    assert integration_client.post(
        "/auth/login", data={"username": inactive.email, "password": PASSWORD}
    ).status_code == 401
    assert integration_client.get(
        "/users/me", headers={"Authorization": "Bearer invalid"}
    ).status_code == 401
    assert integration_client.get(
        "/users/me", headers=bearer(active, expiration=timedelta(seconds=-1))
    ).status_code == 401
