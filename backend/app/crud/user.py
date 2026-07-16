from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user_schema import CreateUserSchema, UpdateUserSchema


class UserCRUD(CRUDBase[User, CreateUserSchema, UpdateUserSchema]):

    def get_by_email(self, db: Session, email: str):
        stmt = (select(User).where(User.email == email))

        return db.scalar(stmt)

    def get_by_username(self, db: Session, username: str):
        stmt = (select(User).where(User.username == username))

        return db.scalar(stmt)

    def get_by_role(self, db: Session, role: str):
        stmt = (select(User).where(User.role == role))

        return list(db.scalars(stmt).all())

    def get_active_users(self, db: Session):
        stmt = (select(User).where(User.is_active == True).order_by(User.created_at.desc()))

        return list(db.scalars(stmt).all())


user_crud = UserCRUD(User)