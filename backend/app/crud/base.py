from typing import Any, Generic, Type, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Generic CRUD operations."""

    def __init__(self, model: Type[ModelType]):
        self.model = model


    def create(self, db: Session, obj_in: CreateSchemaType):
        db_obj = self.model(**obj_in.model_dump())

        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj

        except IntegrityError:
            db.rollback()
            raise


    def get(self, db: Session, id: UUID):

        return db.get(self.model, id)


    def get_all(self, db: Session, skip: int = 0, limit: int = 100):
        stmt = (select(self.model).offset(skip).limit(limit))

        return list(db.scalars(stmt).all())


    def update(self, db: Session, db_obj: ModelType, obj_in: UpdateSchemaType):
        update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        try:
            db.commit()
            db.refresh(db_obj)
            return db_obj

        except IntegrityError:
            db.rollback()
            raise


    def delete(self, db: Session, db_obj: ModelType):
        try:
            db.delete(db_obj)
            db.commit()

        except IntegrityError:
            db.rollback()
            raise


    def exists(self, db: Session, id: UUID):

        return self.get(db, id) is not None