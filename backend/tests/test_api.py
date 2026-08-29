from datetime import datetime, timezone
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import urlencode, urlsplit
from uuid import uuid4

import pytest
import anyio.to_thread
from app.dependencies import get_auth_service, get_crawl_job_service, get_current_user, get_demand_forecast_service, get_price_recommendation_service, get_product_service, get_user_service
from app.main import create_app
from app.core.config import settings
from app.services import ProductNotFoundError
from app.services.auth_service import AuthService
from app.utils.security import create_access_token, hash_password


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret_key", "test-only-secret-key-with-32-bytes")
    application = create_app()
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(app, monkeypatch):
    async def run_sync_inline(func, *args, **kwargs):
        return func(*args)

    monkeypatch.setattr(anyio.to_thread, "run_sync", run_sync_inline)
    return ASGIClient(app)


class ASGIResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body

    def json(self):
        return json.loads(self._body)


class ASGIClient:
    def __init__(self, app):
        self.app = app

    def get(self, path, *, headers=None):
        return asyncio.run(self._request("GET", path, headers=headers))

    def post(self, path, *, json=None, data=None, headers=None):
        return asyncio.run(self._request("POST", path, json_data=json, form_data=data, headers=headers))

    async def _request(self, method, url, *, json_data=None, form_data=None, headers=None):
        split = urlsplit(url)
        body = b""
        request_headers = {key.lower(): value for key, value in (headers or {}).items()}
        if json_data is not None:
            body = json.dumps(json_data).encode()
            request_headers["content-type"] = "application/json"
        elif form_data is not None:
            body = urlencode(form_data).encode()
            request_headers["content-type"] = "application/x-www-form-urlencoded"
        messages = [{"type": "http.request", "body": body, "more_body": False}]
        sent = []

        async def receive():
            return messages.pop(0) if messages else {"type": "http.disconnect"}

        async def send(message):
            sent.append(message)

        scope = {"type":"http","asgi":{"version":"3.0"},"http_version":"1.1","method":method,"scheme":"http","path":split.path,"raw_path":split.path.encode(),"query_string":split.query.encode(),"root_path":"","headers":[(key.encode(),value.encode()) for key,value in request_headers.items()],"client":("test",1),"server":("test",80)}
        await self.app(scope, receive, send)
        start = next(message for message in sent if message["type"] == "http.response.start")
        response_body = b"".join(message.get("body", b"") for message in sent if message["type"] == "http.response.body")
        return ASGIResponse(start["status"], response_body)


def user(role="viewer", *, active=True):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(user_id=uuid4(), email=f"{role}@example.com", username=role, first_name=None, last_name=None, role=role, is_active=active, last_login=None, created_at=now, updated_at=now)


def auth_service_for(found_user):
    service = AuthService(MagicMock())
    service.user_crud = MagicMock()
    service.user_crud.get_by_email.return_value = found_user
    return service


def test_successful_login(app, client):
    account = user("viewer")
    account.hashed_password = hash_password("correct-password")
    app.dependency_overrides[get_auth_service] = lambda: auth_service_for(account)
    response = client.post("/auth/login", data={"username": account.email, "password": "correct-password"})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


@pytest.mark.parametrize("account,password", [(None, "wrong-password"), ("existing", "wrong-password")])
def test_unknown_user_and_incorrect_password_are_generic(app, client, account, password):
    existing = user() if account else None
    if existing:
        existing.hashed_password = hash_password("correct-password")
    app.dependency_overrides[get_auth_service] = lambda: auth_service_for(existing)
    response = client.post("/auth/login", data={"username": "person@example.com", "password": password})
    assert response.status_code == 401
    assert response.json() == {"error": {"code": "INVALID_CREDENTIALS", "message": "Could not validate credentials"}}


def test_inactive_user_login_is_rejected(app, client):
    account = user(active=False); account.hashed_password = hash_password("correct-password")
    app.dependency_overrides[get_auth_service] = lambda: auth_service_for(account)
    response = client.post("/auth/login", data={"username": account.email, "password": "correct-password"})
    assert response.status_code == 401


@pytest.mark.parametrize("token", [None, "invalid-token"])
def test_missing_and_invalid_token(app, client, token):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_expired_token(app, client):
    from datetime import timedelta
    response = client.get("/users/me", headers={"Authorization": f"Bearer {create_access_token({'sub': str(uuid4())}, expiration=timedelta(seconds=-1))}"})
    assert response.status_code == 401


def product_payload():
    return {"sku":"SKU-1","product_name":"Product","category_id":str(uuid4()),"rule_id":str(uuid4()),"base_price":"10.00","current_price":"12.00"}


def product_result(payload):
    now=datetime.now(timezone.utc)
    return {**payload,"product_id":uuid4(),"slug":"product","safety_stock":0,"auto_pricing_enabled":False,"is_active":True,"created_at":now,"updated_at":now}


def test_viewer_blocked_and_editor_allowed_to_manage_products(app, client):
    service=MagicMock(); service.create=AsyncMock(return_value=product_result(product_payload()))
    app.dependency_overrides[get_product_service]=lambda:service
    app.dependency_overrides[get_current_user]=lambda:user("viewer")
    assert client.post("/products",json=product_payload()).status_code == 403
    app.dependency_overrides[get_current_user]=lambda:user("editor")
    assert client.post("/products",json=product_payload()).status_code == 201
    service.create.assert_awaited_once()


def recommendation_result():
    return {"recommendation_id":uuid4(),"product_id":uuid4(),"rule_id":uuid4(),"recommended_price":"15.00","recommendation_reason":"Market demand","generated_at":datetime.now(timezone.utc),"status":"approved","reviewed_by":uuid4(),"reviewed_at":datetime.now(timezone.utc),"review_reason":"Looks good"}


def test_editor_blocked_and_approver_allowed_to_approve(app, client):
    service=MagicMock(); service.approve.return_value=recommendation_result()
    app.dependency_overrides[get_price_recommendation_service]=lambda:service
    app.dependency_overrides[get_current_user]=lambda:user("editor")
    path=f"/price-recommendations/{uuid4()}/approve"
    assert client.post(path,json={"reason":"Looks good"}).status_code == 403
    app.dependency_overrides[get_current_user]=lambda:user("approver")
    assert client.post(path,json={"reason":"Looks good"}).status_code == 200
    service.approve.assert_called_once()


def test_non_admin_blocked_from_user_administration(app, client):
    app.dependency_overrides[get_current_user]=lambda:user("approver")
    app.dependency_overrides[get_user_service]=lambda:MagicMock()
    assert client.get("/users").status_code == 403


@pytest.mark.parametrize(("role", "expected"), [("viewer", 403), ("editor", 202), ("admin", 202)])
def test_crawl_trigger_authorization(app, client, role, expected):
    competitor_id, job_id = uuid4(), uuid4()
    service = MagicMock()
    service.enqueue_competitor.return_value = ({
        "job_id": job_id, "competitor_id": competitor_id, "status": "pending",
        "started_at": None, "completed_at": None,
        "records_collected": 0, "error_message": None,
    }, True)
    app.dependency_overrides[get_crawl_job_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: user(role)
    response = client.post(f"/crawl-jobs/competitors/{competitor_id}")
    assert response.status_code == expected
    if expected == 202:
        assert response.json()["status"] == "pending"
        service.enqueue_competitor.assert_called_once_with(competitor_id)


def test_generate_demand_forecast_endpoint(app, client):
    product_id, forecast_id = uuid4(), uuid4()
    generated_at = datetime.now(timezone.utc)
    service = MagicMock()
    service.generate.return_value = {
        "product_id": product_id, "horizon_days": 7, "model_name": "ridge-lag-v1",
        "baseline_mae": 3.2, "ml_mae": 2.1,
        "forecasts": [{
            "forecast_id": forecast_id, "product_id": product_id,
            "forecast_date": generated_at, "predicted_demand": 25,
            "model_name": "ridge-lag-v1", "confidence_score": "90.00",
            "created_at": generated_at,
        }],
    }
    app.dependency_overrides[get_demand_forecast_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: user("editor")

    response = client.post(f"/demand-forecasts/generate/{product_id}?horizon_days=7")

    assert response.status_code == 201
    assert response.json()["model_name"] == "ridge-lag-v1"
    service.generate.assert_called_once_with(product_id, horizon_days=7)


@pytest.mark.parametrize("exception,status_code", [(ProductNotFoundError("Product not found"),404)])
def test_domain_exception_mapping(app, client, exception, status_code):
    service=MagicMock(); service.get=AsyncMock(side_effect=exception)
    app.dependency_overrides[get_product_service]=lambda:service
    app.dependency_overrides[get_current_user]=lambda:user("viewer")
    response=client.get(f"/products/{uuid4()}")
    assert response.status_code == status_code
    assert response.json()=={"error":{"code":"PRODUCT_NOT_FOUND","message":"Product not found"}}
