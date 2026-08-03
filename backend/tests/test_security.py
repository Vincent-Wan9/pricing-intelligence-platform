from datetime import timedelta

import pytest

from app.core.config import settings
from app.utils.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


@pytest.fixture(autouse=True)
def secure_test_jwt_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        settings,
        "jwt_secret_key",
        "test-only-secret-key-with-32-bytes",
    )


def test_hash_and_verify_password():
    password = "correct-horse-battery-staple"

    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_same_password_produces_different_hashes():
    password = "correct-horse-battery-staple"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash
    assert verify_password(password, first_hash) is True
    assert verify_password(password, second_hash) is True


def test_jwt_round_trip():
    token = create_access_token({"sub": "user-123", "role": "admin"})

    payload = decode_access_token(token)

    assert payload["sub"] == "user-123"
    assert payload["role"] == "admin"
    assert "iat" in payload
    assert "exp" in payload
    assert payload["exp"] > payload["iat"]


def test_expired_token_is_rejected():
    token = create_access_token(
        {"sub": "user-123"},
        expiration=timedelta(seconds=-1),
    )

    with pytest.raises(TokenError, match="Token has expired"):
        decode_access_token(token)


def test_invalid_token_is_rejected():
    with pytest.raises(TokenError, match="Invalid token"):
        decode_access_token("not-a-valid-token")


def test_token_without_subject_is_rejected():
    token = create_access_token({"role": "admin"})

    with pytest.raises(TokenError, match="Invalid token"):
        decode_access_token(token)
