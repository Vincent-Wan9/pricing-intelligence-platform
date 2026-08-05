from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.dependencies import (
    get_current_user,
    get_demand_forecast_service,
    get_optional_user,
    get_product_cache_service,
    require_admin,
)
from app.services.demand_forecast_service import DemandForecastService
from app.services.product_cache_service import ProductCacheService
from app.core.config import settings
from app.utils.security import create_access_token


def _credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_current_user_resolves_valid_uuid_subject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()
    user = SimpleNamespace(user_id=uuid4(), is_active=True, role="viewer")
    db.get.return_value = user
    monkeypatch.setattr(
        settings,
        "jwt_secret_key",
        "test-only-secret-key-with-32-bytes",
    )

    result = get_current_user(db, _credentials(create_access_token({"sub": str(user.user_id)})))

    assert result is user
    db.get.assert_called_once()


def test_current_user_rejects_missing_credentials() -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(MagicMock(), None)

    assert exc_info.value.status_code == 401
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


def test_optional_user_swallows_invalid_token() -> None:
    assert get_optional_user(MagicMock(), _credentials("invalid")) is None


def test_require_admin_rejects_non_admin() -> None:
    with pytest.raises(HTTPException) as exc_info:
        require_admin(SimpleNamespace(role="editor"))

    assert exc_info.value.status_code == 403


def test_request_scoped_service_factories_use_supplied_resources() -> None:
    db = MagicMock()
    redis = MagicMock()

    forecast_service = get_demand_forecast_service(db)
    cache_service = get_product_cache_service(redis)

    assert isinstance(forecast_service, DemandForecastService)
    assert forecast_service.db is db
    assert isinstance(cache_service, ProductCacheService)
    assert cache_service.redis is redis
