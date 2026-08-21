from __future__ import annotations

from collections.abc import Generator
import asyncio

import pytest
import httpx
import anyio.to_thread
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - register every mapped table
from app.core.database import Base, get_db
from app.core.config import settings
from app.dependencies import get_redis_client
from app.main import create_app


class MemoryRedis:
    """Small async cache double; persistence remains real in integration tests."""

    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    async def get_json(self, key: str):
        return self.values.get(key)

    async def set_json(self, key: str, value, ttl_seconds: int | None = None):
        self.values[key] = value

    async def delete(self, key: str):
        return int(self.values.pop(key, None) is not None)

    async def delete_pattern(self, pattern: str, batch_size: int = 500):
        prefix = pattern.removesuffix("*")
        keys = [key for key in self.values if key.startswith(prefix)]
        for key in keys:
            del self.values[key]
        return len(keys)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def integration_client(db_session: Session, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "jwt_secret_key", "phase-7-test-secret-key-at-least-32-bytes")

    async def run_sync_inline(func, *args, **kwargs):
        return func(*args)

    monkeypatch.setattr(anyio.to_thread, "run_sync", run_sync_inline)
    application = create_app()
    redis = MemoryRedis()

    def override_db():
        yield db_session

    application.dependency_overrides[get_db] = override_db
    application.dependency_overrides[get_redis_client] = lambda: redis
    class Client:
        def request(self, method: str, path: str, **kwargs):
            async def send():
                transport = httpx.ASGITransport(app=application)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    return await client.request(method, path, **kwargs)

            return asyncio.run(send())

        def get(self, path: str, **kwargs):
            return self.request("GET", path, **kwargs)

        def post(self, path: str, **kwargs):
            return self.request("POST", path, **kwargs)

        def patch(self, path: str, **kwargs):
            return self.request("PATCH", path, **kwargs)

        def delete(self, path: str, **kwargs):
            return self.request("DELETE", path, **kwargs)

    yield Client()
    application.dependency_overrides.clear()
