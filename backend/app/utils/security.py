from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings


password_hash = PasswordHash.recommended()


class TokenError(Exception):
    """Raised when JWT validation fails."""


def hash_password(password: str) -> str:
    """Hash a password using the recommended password hashing algorithm."""
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its stored hash."""
    return password_hash.verify(password=plain_password, hash=hashed_password)


def create_access_token(
    data: dict[str, Any], expiration: timedelta | None = None
) -> str:
    """Sign claims with server-controlled issued-at and expiration timestamps."""
    now = datetime.now(timezone.utc)

    if expiration is None:
        expiration = timedelta(minutes=settings.jwt_default_exp_minutes)

    payload = {
        **data,
        "iat": int(now.timestamp()),
        "exp": int((now + expiration).timestamp()),
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Validate a signed token and required claims, raising TokenError on failure."""
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub"]},
        )

    except ExpiredSignatureError as exc:
        raise TokenError("Token has expired") from exc

    except InvalidTokenError as exc:
        raise TokenError("Invalid token") from exc
