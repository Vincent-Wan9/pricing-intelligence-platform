from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.category import Category
from app.schemas.category_schema import CreateCategorySchema, UpdateCategorySchema


class CategoryCRUD(CRUDBase[Category, CreateCategorySchema, UpdateCategorySchema]):

    def get_by_name(self, db: Session, name: str) -> Category | None:

        stmt = select(Category).where(Category.category_name == name)
        return db.scalar(stmt)


category_crud = CategoryCRUD(Category)