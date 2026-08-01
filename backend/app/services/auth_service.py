from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.utils.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.crud.user import user_crud
from app.models.user import User
from app.schemas.user_schema import LoginSchema, TokenResponse


class AuthServiceError(Exception):
    pass


class InvalidCredentialsError(AuthServiceError):
    pass


class InactiveUserError(AuthServiceError):
    pass


class AuthService:

    def __init__(self, db: Session) -> None:
        self.db = db
        self.user_crud = user_crud

    def authenticate(self, credentials: LoginSchema) -> User:
        user = self.user_crud.get_by_email(self.db, credentials.email)
        if user is None or not verify_password(credentials.password, user.hashed_password):
            raise InvalidCredentialsError("Invalid email or password")

        if not user.is_active:
            raise InactiveUserError("User account is inactive")

        return user

    def login(self, credentials: LoginSchema) -> TokenResponse:
        user = self.authenticate(credentials)
        expiration = timedelta(minutes=settings.jwt_default_exp_minutes)
        token = create_access_token(data={"sub": str(user.user_id)}, expiration=expiration)
        return TokenResponse(access_token=token, token_type="bearer")

    @staticmethod
    def build_password_hash(password: str) -> str:
        return hash_password(password)
