from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.inventory import Inventory
from app.services.auth_service import (
    AuthService,
    InactiveUserError,
    InvalidCredentialsError,
)
from app.services.crawl_job_service import (
    CrawlJobService,
    CrawlJobValidationError,
)
from app.services.inventory_service import (
    InventoryConflictError,
    InventoryNotFoundError,
    InventoryService,
    InventoryValidationError,
)
from app.services.pricing_validation import validate_prices
from app.services import ProductValidationError
from app.services.user_service import (
    UserAuthorizationError,
    UserService,
)
from app.schemas.user_schema import LoginSchema


def test_validate_prices_accepts_valid_bounds() -> None:
    validate_prices(
        base_price=Decimal("50"),
        current_price=Decimal("75"),
        min_price=Decimal("60"),
        max_price=Decimal("90"),
    )


@pytest.mark.parametrize(
    ("current_price", "min_price", "max_price", "message"),
    [
        (Decimal("0"), None, None, "current_price must be greater than zero"),
        (
            Decimal("50"),
            Decimal("60"),
            Decimal("90"),
            "current_price cannot be lower than min_price",
        ),
        (
            Decimal("100"),
            Decimal("60"),
            Decimal("90"),
            "current_price cannot be greater than max_price",
        ),
    ],
)
def test_validate_prices_rejects_invalid_values(current_price: Decimal, min_price: Decimal | None, max_price: Decimal | None, message: str,) -> None:
    with pytest.raises(ProductValidationError, match=message):
        validate_prices(
            base_price=Decimal("50"),
            current_price=current_price,
            min_price=min_price,
            max_price=max_price,
        )


def test_authentication_does_not_reveal_unknown_email(monkeypatch: pytest.MonkeyPatch,) -> None:
    db = MagicMock()
    service = AuthService(db)
    service.user_crud = MagicMock()
    service.user_crud.get_by_email.return_value = None
    monkeypatch.setattr("app.services.auth_service.verify_password", lambda *_: False)

    with pytest.raises(InvalidCredentialsError, match="Invalid email or password"):
        service.authenticate(LoginSchema(email="missing@example.com", password="password123"))


def test_authentication_rejects_inactive_user(monkeypatch: pytest.MonkeyPatch) -> None:
    service = AuthService(MagicMock())
    service.user_crud = MagicMock()
    service.user_crud.get_by_email.return_value = SimpleNamespace(
        hashed_password="hash",
        is_active=False,
    )
    monkeypatch.setattr("app.services.auth_service.verify_password", lambda *_: True)

    with pytest.raises(InactiveUserError, match="inactive"):
        service.authenticate(LoginSchema(email="inactive@example.com", password="password123"))


def test_non_admin_cannot_manage_another_user() -> None:
    actor = SimpleNamespace(role="viewer")

    with pytest.raises(UserAuthorizationError, match="Administrator"):
        UserService._require_admin(actor)


def test_crawl_job_rejects_invalid_state_transition() -> None:
    job = SimpleNamespace(status="completed")

    with pytest.raises(CrawlJobValidationError, match="completed -> running"):
        CrawlJobService(MagicMock())._transition(job, "running")


def _inventory(*, quantity: int) -> Inventory:
    return Inventory(
        inventory_id=uuid4(),
        product_id=uuid4(),
        vendor="Portfolio Vendor",
        lead_time=3,
        cost_per_unit=Decimal("12.50"),
        on_hand_qty=quantity,
        updated_at=datetime.now(timezone.utc),
    )


def test_adjust_stock_uses_atomic_update() -> None:
    db = MagicMock()
    inventory = _inventory(quantity=7)
    db.execute.return_value.scalar_one_or_none.return_value = inventory

    result = InventoryService(db).adjust_stock(inventory.product_id, 2)

    assert result.inventory_id == inventory.inventory_id
    db.execute.assert_called_once()
    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_adjust_stock_distinguishes_missing_inventory() -> None:
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = None
    service = InventoryService(db)
    service.crud = MagicMock()
    service.crud.get_by_product.return_value = None
    product_id = uuid4()

    with pytest.raises(InventoryNotFoundError, match=str(product_id)):
        service.adjust_stock(product_id, -1)

    db.rollback.assert_called_once()


def test_adjust_stock_prevents_negative_quantity() -> None:
    db = MagicMock()
    inventory = _inventory(quantity=1)
    db.execute.return_value.scalar_one_or_none.return_value = None
    service = InventoryService(db)
    service.crud = MagicMock()
    service.crud.get_by_product.return_value = inventory

    with pytest.raises(InventoryValidationError, match="negative"):
        service.adjust_stock(inventory.product_id, -2)

    db.rollback.assert_called_once()


def test_adjust_stock_rolls_back_database_conflict() -> None:
    db = MagicMock()
    db.execute.side_effect = IntegrityError("update", {}, Exception("boom"))

    with pytest.raises(InventoryConflictError, match="adjusted"):
        InventoryService(db).adjust_stock(uuid4(), 1)

    db.rollback.assert_called_once()
