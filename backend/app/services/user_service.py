from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.utils.security import hash_password
from app.crud.user import user_crud
from app.models.user import User
from app.schemas.user_schema import (
    CreateUserSchema,
    UpdateUserSchema,
    UserPublic,
)


class UserServiceError(Exception):
    pass


class UserNotFoundError(UserServiceError):
    pass


class UserConflictError(UserServiceError):
    pass


class UserValidationError(UserServiceError):
    pass


class UserAuthorizationError(UserServiceError):
    pass


class UserService:
    ADMIN_ROLE = "admin"

    def __init__(self, db: Session) -> None:
        self.db = db
        self.crud = user_crud

    def get(self, user_id: UUID) -> UserPublic:
        return UserPublic.model_validate(self._get_model(user_id))

    def list(self, *, skip: int = 0, limit: int = 100) -> list[UserPublic]:
        if skip < 0 or not 1 <= limit <= 1000:
            raise UserValidationError("Invalid pagination values")
        users = self.crud.get_all(self.db, skip=skip, limit=limit)
        return [UserPublic.model_validate(user) for user in users]

    def create(self, user_in: CreateUserSchema, *, actor: User | None = None) -> UserPublic:
        if actor is not None:
            self._require_admin(actor)

        if self.crud.get_by_email(self.db, user_in.email) is not None:
            raise UserConflictError(
                f"User with email '{user_in.email}' already exists")
        if self.crud.get_by_username(self.db, user_in.username) is not None:
            raise UserConflictError(
                f"Username '{user_in.username}' already exists")

        data = user_in.model_dump(exclude={"password"})
        data["hashed_password"] = hash_password(user_in.password)
        user = User(**data)

        try:
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        except IntegrityError as exc:
            self.db.rollback()
            raise UserConflictError("User could not be created") from exc

        return UserPublic.model_validate(user)

    def update(self, user_id: UUID, user_in: UpdateUserSchema, *, actor: User) -> UserPublic:
        user = self._get_model(user_id)
        data = user_in.model_dump(exclude_unset=True)

        actor_role = actor.role
        if actor.user_id != user_id and actor_role != self.ADMIN_ROLE:
            raise UserAuthorizationError(
                "Users may only update their own profile")

        if "role" in data or "is_active" in data:
            self._require_admin(actor)

        if "email" in data and data["email"] != user.email:
            existing = self.crud.get_by_email(self.db, data["email"])
            if existing is not None:
                raise UserConflictError("Email already exists")

        if "username" in data and data["username"] != user.username:
            existing = self.crud.get_by_username(self.db, data["username"])
            if existing is not None:
                raise UserConflictError("Username already exists")

        try:
            for field, value in data.items():
                setattr(user, field, value)
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        except IntegrityError as exc:
            self.db.rollback()
            raise UserConflictError("User could not be updated") from exc

        return UserPublic.model_validate(user)

    def deactivate(self, user_id: UUID, *, actor: User) -> UserPublic:
        self._require_admin(actor)
        if actor.user_id == user_id:
            raise UserValidationError(
                "Administrators cannot deactivate their own account")

        user = self._get_model(user_id)
        try:
            user.is_active = False
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        except IntegrityError as exc:
            self.db.rollback()
            raise UserConflictError(
                "User could not be deactivated") from exc
        return UserPublic.model_validate(user)

    def _get_model(self, user_id: UUID) -> User:
        user = self.crud.get(self.db, user_id)
        if user is None:
            raise UserNotFoundError(f"User {user_id} was not found")
        return user

    @classmethod
    def _require_admin(cls, actor: User) -> None:
        if actor.role != cls.ADMIN_ROLE:
            raise UserAuthorizationError("Administrator access is required")
